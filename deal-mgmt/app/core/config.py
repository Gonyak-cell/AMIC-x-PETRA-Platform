import logging
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_flag(cls, value: object) -> object:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production"}:
                return False
            if lowered in {"debug", "development", "dev"}:
                return True
        return value

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

    # Celery 워커 전용 DB 풀 (동시성 2에 맞춤)
    CELERY_DB_POOL_SIZE: int = 3
    CELERY_DB_POOL_MAX_OVERFLOW: int = 2

    # 금융위 공공데이터포털 API (기업재무정보 수집)
    DATA_GO_KR_API_KEY: str = ""
    DATA_GO_KR_BASE_URL: str = "https://apis.data.go.kr"

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

    # Gemini File API — VDR 문서 분류 + Q&A
    GEMINI_VDR_CLASSIFICATION_ENABLED: bool = False  # A1: Gemini 기반 VDR 분류
    GEMINI_CLASSIFICATION_MODEL: str = "gemini-2.0-flash"
    GEMINI_FILE_TTL_HOURS: int = 47  # 48h API 제한보다 1h 여유

    # Cloudflare Browser Rendering — /crawl API (Phase B 뉴스 확장)
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_API_TOKEN: str = ""
    CF_CRAWL_ENABLED: bool = False  # Phase B 활성화 플래그
    CF_CRAWL_REQUEST_DELAY: float = 3.0  # 소스 간 요청 간격(초)
    CF_CRAWL_MAX_PAGES: int = 5  # 소스당 최대 크롤링 페이지

    # LDD Multi-LLM Pipeline
    LDD_MULTI_LLM_ENABLED: bool = False  # 멀티 LLM 파이프라인 활성화
    LDD_STAGE3_DUAL_RISK: bool = True  # 듀얼 리스크 분석
    LDD_STAGE4_GAP_DETECTION: bool = True  # 누락 탐지
    LDD_STAGE5_JURISDICTION: bool = False  # 관할권 교차 (크로스보더 시만)
    LDD_STAGE6_NARRATIVE: bool = False  # 6블록 서술 생성 (비용 ~$2-4 추가)
    LDD_STAGE7_QA: bool = True  # 최종 QA
    LDD_RISK_GAP_AUTO_RESOLVE: int = 1  # gap≤N 자동 해결
    LDD_MAX_COST_USD: float = 15.0  # 세션 비용 한도
    LDD_TEMPLATE_SLOTFILL_ENABLED: bool = True  # 부동문자 bank + slot-fill 렌더링 활성화
    LDD_TEMPLATE_SLOTFILL_USE_LLM: bool = False  # L3 슬롯에 한해 LLM 보조 사용
    LDD_TEMPLATE_SLOTFILL_DIR: str = ""  # 비어 있으면 templates/ldd_slotfill 사용
    LDD_ROUTER_MIN_COMMON_CONFIDENCE: float = 0.55  # COMMON 문서를 LDD에 허용할 최소 라우팅 신뢰도

    # LDD QA Gate
    LDD_MIN_DRAFT_SCORE: int = 3  # 초안 최소 품질 (1-5), REVIEW 시 경고
    LDD_MIN_FINAL_SCORE: int = 3  # 최종 최소 품질 (1-5), READY 차단
    LDD_QA_CRITICAL_BLOCKS_READY: bool = True  # critical 이슈 시 READY 차단


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
