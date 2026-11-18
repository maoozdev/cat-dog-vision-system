"""
Prediction endpoints (all require login).

POST /predict                    upload an image -> label, confidence, probabilities
GET  /predictions?page=&page_size=   your history, newest first
GET  /predictions/{id}/image     the stored image (only for its owner)
"""

import logging
import math
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_classifier, get_current_user
from app.ml.classifier import CatDogClassifier
from app.models import Prediction, User
from app.schemas.prediction import PredictionOut, PredictionPage, PredictResponse
from app.services.image_service import read_and_validate, save_image
from app.utils.rate_limit import RateLimiter

router = APIRouter(tags=["predictions"])
logger = logging.getLogger(__name__)
predict_limiter = RateLimiter(get_settings().predict_rate_limit)


def to_out(p: Prediction) -> dict:
    return {
        "id": p.id,
        "predicted_label": p.predicted_label,
        "confidence": p.confidence,
        "probabilities": p.probabilities,
        "model_version": p.model_version,
        "created_at": p.created_at,
        "image_url": f"/predictions/{p.id}/image",
    }


@router.post("/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(..., description="JPEG, PNG or WEBP image, max 5 MB"),
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
    classifier: CatDogClassifier = Depends(get_classifier),
):
    predict_limiter.check(f"predict:{user.id}")
    settings = get_settings()

    image = await read_and_validate(file, settings.max_upload_bytes)
    # Model inference is CPU work: run it in a thread so the server stays responsive.
    result = await run_in_threadpool(classifier.predict, image)
    image_path = await run_in_threadpool(save_image, image, settings.upload_dir, user.id)

    row = Prediction(
        user_id=user.id,
        image_path=image_path,
        predicted_label=result["label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        model_version=result["model_version"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    logger.info("prediction", extra={"user_id": str(user.id), "label": result["label"],
                                     "confidence": result["confidence"], "event": "predict"})
    return {**to_out(row), "low_confidence": result["low_confidence"],
            "threshold": result["threshold"]}


@router.get("/predictions", response_model=PredictionPage)
def list_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(Prediction)
                      .where(Prediction.user_id == user.id)) or 0
    rows = db.scalars(
        select(Prediction)
        .where(Prediction.user_id == user.id)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [to_out(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.get("/predictions/{prediction_id}/image")
def prediction_image(
    prediction_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    row = db.get(Prediction, prediction_id)
    # 404 (not 403) for other users' images, so ids of others can't even be confirmed.
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prediction not found.")
    upload_dir = get_settings().upload_dir.resolve()
    path = (upload_dir / row.image_path).resolve()
    if not path.is_relative_to(upload_dir) or not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image file not found.")
    return FileResponse(path, media_type="image/jpeg")
