"""Import every table here so SQLAlchemy and Alembic know about all of them."""

from app.models.prediction import Prediction
from app.models.session import Session
from app.models.user import User

__all__ = ["User", "Session", "Prediction"]
