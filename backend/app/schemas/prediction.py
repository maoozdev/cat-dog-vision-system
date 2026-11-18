"""Request/response shapes for /predict and /predictions."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    predicted_label: str            # "cat" | "dog" | "other" (other = Neither / Unknown)
    confidence: float               # probability of the predicted class, 0..1
    probabilities: dict[str, float]
    model_version: str
    created_at: datetime
    image_url: str                  # protected URL to fetch the stored image


class PredictResponse(PredictionOut):
    low_confidence: bool            # True if the model was unsure and answered "other"
    threshold: float


class PredictionPage(BaseModel):
    items: list[PredictionOut]
    total: int
    page: int
    page_size: int
    pages: int
