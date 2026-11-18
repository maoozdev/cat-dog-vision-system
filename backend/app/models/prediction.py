"""predictions table - history of every image a user classified.

The image itself lives on disk (uploads/); only its relative path is stored here.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(512))
    predicted_label: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    # {"cat": 0.97, "dog": 0.02, "other": 0.01}. JSONB on PostgreSQL, plain JSON elsewhere (tests).
    probabilities: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    model_version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped["User"] = relationship(back_populates="predictions")
