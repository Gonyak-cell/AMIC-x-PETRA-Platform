import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Deal Management"
    DEBUG: bool = False
    SECRET_KEY: str = ""
    JWT_SECRET: str = ""  # .env 필수 — 하드코딩 금지

    # Database
    DATABASE_URL: str = ""  # .env 필수 — 하드코딩 금지

    # JWT
    JWT_ALGORITHM: str = "HS256"
    AUTH_ENABLED: bool = True

    # Logging
    LOG_DIR: str = ""

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    # Database Pool
    DB_POOL_SIZE: int = 10
    DB_POOL_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_TIMEOUT: int = 30

    # Service URLs (inter-service communication)
    FDD_API_URL: str = "http://localhost:8000/api/v1"
    IM_API_URL: str = "http://localhost:8002/api"
    KIIS_API_URL: str = "http://localhost:8001/api/v1"

    # Ralph Loop — LLM API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # Naver Clova Speech STT
    CLOVA_CLIENT_ID: str = ""
    CLOVA_CLIENT_SECRET: str = ""

    # Azure Blob Storage (VDR)
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_VDR_CONTAINER_NAME: str = "amic-vdr"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_SOFT_TIME_LIMIT: int = 1800  # 30분
    CELERY_TASK_HARD_TIME_LIMIT: int = 3600  # 60분

    # Ralph Loop — Model Configuration
    RALPH_PRIMARY_MODEL: str = "claude-sonnet-4-20250514"
    RALPH_JUDGE_MODEL: str = "gpt-4o"
    RALPH_MAX_COST_PER_DOC: float = 10.0

    # LDD Multi-LLM Pipeline
    LDD_MULTI_LLM_ENABLED: bool = False  # 멀티 LLM 파이프라인 활성화
    LDD_STAGE3_DUAL_RISK: bool = True  # 듀얼 리스크 분석
    LDD_STAGE4_GAP_DETECTION: bool = True  # 누락 탐지
    LDD_STAGE5_JURISDICTION: bool = False  # 관할권 교차 (크로스보더 시만)
    LDD_STAGE6_NARRATIVE: bool = False  # 6블록 서술 생성 (비용 ~$2-4 추가)
    LDD_STAGE7_QA: bool = True  # 최종 QA
    LDD_RISK_GAP_AUTO_RESOLVE: int = 1  # gap≤N 자동 해결
    LDD_MAX_COST_USD: float = 15.0  # 세션 비용 한도


settings = Settings()

# ── Startup validation ────────────────────────────────────
_env_name = os.getenv("ENV", "").lower()
_is_production = _env_name in ("production", "prod")
_is_staging = _env_name in ("staging", "stg")

_effective_jwt = settings.JWT_SECRET or settings.SECRET_KEY
if not _effective_jwt:
    if _is_production or _is_staging:
        raise RuntimeError(
            "CRITICAL: JWT_SECRET must be set in production/staging. "
            "Generate a strong secret (≥32 chars) and set the JWT_SECRET env var."
        )
    _logger.warning("JWT_SECRET not set. Set JWT_SECRET in .env for development.")

if not settings.DATABASE_URL:
    if _is_production or _is_staging:
        raise RuntimeError("CRITICAL: DATABASE_URL must be set in production/staging.")
    _logger.warning("DATABASE_URL not set. Set DATABASE_URL in .env for development.")
