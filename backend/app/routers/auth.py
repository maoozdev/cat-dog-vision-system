"""
/auth endpoints.

POST /auth/register  create account
POST /auth/login     check password -> access token (JSON) + refresh token (HttpOnly cookie)
POST /auth/refresh   cookie -> new access token (and a new rotated cookie)
POST /auth/logout    revoke the session in the cookie and delete the cookie
GET  /auth/me        current user (needs access token)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service
from app.utils.rate_limit import RateLimiter, client_ip
from app.utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
auth_limiter = RateLimiter(get_settings().auth_rate_limit)
refresh_limiter = RateLimiter(get_settings().refresh_rate_limit)


def limit_by_ip(request: Request) -> None:
    auth_limiter.check(f"auth:{client_ip(request)}")


def limit_refresh_by_ip(request: Request) -> None:
    refresh_limiter.check(f"refresh:{client_ip(request)}")


def set_refresh_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        key=s.refresh_cookie_name,
        value=token,
        httponly=True,              # JavaScript cannot read it (protects against XSS theft)
        secure=s.cookie_secure,     # only sent over HTTPS when true
        samesite="lax",             # not sent on cross-site POSTs (CSRF protection)
        max_age=s.refresh_token_days * 24 * 3600,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(s.refresh_cookie_name, path="/", secure=s.cookie_secure,
                           httponly=True, samesite="lax")


def token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=get_settings().access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(limit_by_ip)])
def register(body: RegisterRequest, db: DbSession = Depends(get_db)):
    if auth_service.get_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = auth_service.create_user(db, body.email, body.password)
    logger.info("user registered", extra={"user_id": str(user.id), "event": "register"})
    return user


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit_by_ip)])
def login(body: LoginRequest, request: Request, response: Response,
          db: DbSession = Depends(get_db)):
    user = auth_service.authenticate(db, body.email, body.password)
    if user is None:
        logger.info("login failed", extra={"event": "login_failed", "client_ip": client_ip(request)})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    token = auth_service.create_session(db, user.id, request.headers.get("user-agent"),
                                        client_ip(request))
    set_refresh_cookie(response, token)
    logger.info("login ok", extra={"user_id": str(user.id), "event": "login"})
    return token_response(user)


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(limit_refresh_by_ip)])
def refresh(request: Request, response: Response, db: DbSession = Depends(get_db)):
    token = request.cookies.get(get_settings().refresh_cookie_name)
    result = auth_service.rotate_session(
        db, token, request.headers.get("user-agent"), client_ip(request)
    ) if token else None
    if result is None:
        # FastAPI would drop headers set on `response` when we raise, so build the error ourselves.
        error = Response(status_code=status.HTTP_401_UNAUTHORIZED,
                         content='{"detail":"Session expired. Please log in again."}',
                         media_type="application/json")
        clear_refresh_cookie(error)
        return error
    user, new_token = result
    set_refresh_cookie(response, new_token)
    return token_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DbSession = Depends(get_db)):
    token = request.cookies.get(get_settings().refresh_cookie_name)
    if token:
        auth_service.revoke_session(db, token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(response)
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
