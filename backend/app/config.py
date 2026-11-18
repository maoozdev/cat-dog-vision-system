"""
Application settings.

Values come from environment variables (or the project-root .env file).
Pydantic converts them to the right Python types and fails fast if one is invalid.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../project_cate_dog_other


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
        protected_namespaces=(),  # allow a field called "model_path"
    )

    # Database
    database_url: str = "postgresql+psycopg://catdog:catdog@localhost:5432/catdog"

    # Security
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cookie_secure: bool = False
    refresh_cookie_name: str = "refresh_token"

    # Files & model
    model_path: Path = PROJECT_ROOT / "models" / "cat_dog_model.pth"
    upload_dir: Path = PROJECT_ROOT / "uploads"
    max_upload_mb: int = 5
    confidence_threshold: float | None = None  # None -> use value saved in the model file

    # HTTP
    cors_origins: str = "http://localhost:5173"  # comma-separated list
    log_level: str = "INFO"
    # Public URL prefix in front of the API (e.g. "/api" behind Caddy). Used by /docs.
    api_public_prefix: str = ""

    # Rate limits (requests per minute)
    auth_rate_limit: int = 10      # register + login (password guessing protection)
    refresh_rate_limit: int = 60   # every page load refreshes, so allow more
    predict_rate_limit: int = 30

    @field_validator("confidence_threshold", mode="before")
    @classmethod
    def empty_is_none(cls, v):
        return None if v in ("", None) else v

    def check_production_safety(self) -> None:
        """Refuse to run over HTTPS (production) with a weak or default JWT secret."""
        if self.cookie_secure and (
            self.jwt_secret.startswith("dev-only") or len(self.jwt_secret) < 32
        ):
            raise RuntimeError(
                "JWT_SECRET is missing or too short for production. "
                "Set a random value of 32+ characters in .env."
            )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Create the settings object once and reuse it everywhere."""
    return Settings()
