"""
Shared FastAPI dependencies ("things an endpoint needs before it runs").

get_current_user - reads "Authorization: Bearer <token>", validates the JWT,
                   loads the user. Any endpoint that uses it is protected.
get_classifier   - the model loaded at startup.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.ml.classifier import CatDogClassifier
from app.models import User
from app.utils.security import decode_access_token

bearer = HTTPBearer(auto_error=False)

UNAUTHORIZED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated or token expired.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: DbSession = Depends(get_db),
) -> User:
    if creds is None:
        raise UNAUTHORIZED
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise UNAUTHORIZED
    user = db.get(User, user_id)
    if user is None:
        raise UNAUTHORIZED
    return user


def get_classifier(request: Request) -> CatDogClassifier:
    classifier = getattr(request.app.state, "classifier", None)
    if classifier is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Model is not loaded.")
    return classifier
