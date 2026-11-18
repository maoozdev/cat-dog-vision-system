"""GET /health - is the server up, can it reach the database, is the model loaded?"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from app.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health(request: Request, db: DbSession = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"

    classifier = getattr(request.app.state, "classifier", None)
    healthy = database == "ok" and classifier is not None
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "database": database,
            "model_loaded": classifier is not None,
            "model_version": classifier.version if classifier else None,
        },
    )
