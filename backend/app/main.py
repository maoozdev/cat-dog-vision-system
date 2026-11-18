"""
FastAPI application entry point.

Start (from the backend/ folder):
    uvicorn app.main:app --reload
Interactive API docs: http://localhost:8000/docs
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.ml.classifier import CatDogClassifier
from app.routers import auth, health, predictions
from app.utils.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("app")
request_logger = logging.getLogger("app.request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup (before `yield`) and once at shutdown (after)."""
    settings.check_production_safety()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app.state.classifier = CatDogClassifier(settings.model_path, settings.confidence_threshold)
    logger.info("startup complete", extra={"event": "startup"})
    yield
    logger.info("shutdown", extra={"event": "shutdown"})


app = FastAPI(
    title="Cat vs Dog Vision API",
    version="1.0.0",
    description="Upload an image and get Cat / Dog / Neither predictions. "
                "Log in via /auth/login, then click 'Authorize' and paste the access token.",
    lifespan=lifespan,
    # Behind Caddy the API lives under /api; tell the /docs page so "Try it out" works.
    servers=[{"url": settings.api_public_prefix}] if settings.api_public_prefix else None,
)

# CORS: which browser origins (frontend URLs) may call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # needed so the browser sends the refresh cookie
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Give every request an id, time it, and write one structured log line."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled error", extra={"request_id": request_id,
                                                   "path": request.url.path})
        response = JSONResponse(status_code=500, content={
            "detail": "Internal server error.", "request_id": request_id})
    response.headers["X-Request-ID"] = request_id
    request_logger.info("request", extra={
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        "request_id": request_id,
    })
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(predictions.router)
