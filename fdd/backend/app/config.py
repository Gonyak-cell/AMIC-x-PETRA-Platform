import logging
import os

from pydantic_settings import BaseSettings

_logger = logging.getLogger(__name__)

_DEV_SECRET = "dev-secret-change-in-production-!!"


class Settings(BaseSettings):
    database_url: str = "postgresql://autofdd:autofdd_dev@localhost:5432/autofdd"
    pptx_service_url: str = "http://localhost:3100"
    engine_version: str = "0.1.0"
    upload_dir: str = "./uploads"

    # Auth settings (Sprint 11)
    auth_enabled: bool = True
    jwt_secret: str = _DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Production settings
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    log_dir: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()

# ── Startup validation ────────────────────────────────────
_is_production = os.getenv("ENV", "").lower() in ("production", "prod")

if settings.jwt_secret == _DEV_SECRET:
    if _is_production:
        raise RuntimeError(
            "CRITICAL: JWT_SECRET must be set in production. "
            "Generate a strong secret (≥32 chars) and set the JWT_SECRET env var."
        )
    _logger.warning(
        "Using default dev JWT secret. Set JWT_SECRET env var for production."
    )

if not settings.auth_enabled:
    if _is_production:
        raise RuntimeError(
            "CRITICAL: AUTH_ENABLED cannot be False in production. "
            "Remove AUTH_ENABLED=False or set AUTH_ENABLED=True."
        )
    _logger.warning(
        "AUTH_ENABLED=False — all requests will be processed as ADMIN dev user. "
        "Do NOT use in production."
    )
