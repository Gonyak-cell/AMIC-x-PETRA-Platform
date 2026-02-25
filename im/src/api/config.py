"""API 통합 설정 모듈 (T-I02).

> 마지막 수정: 2026-02-11 21:38:33

Pydantic BaseSettings 기반으로 DB, Redis, JWT, 외부 API 키 등 전체 설정을 통합 관리한다.
환경변수 또는 .env 파일에서 값을 로드한다.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class APIConfig(BaseSettings):
    """API 통합 설정.

    환경변수 매핑:
        DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, DART_API_KEY, OPENAI_API_KEY, ...

    Examples:
        >>> config = APIConfig()       # .env에서 자동 로드
        >>> config = get_config()      # 캐싱된 싱글턴
    """

    # ── Database ──
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5434/imgen",
        description="PostgreSQL 비동기 연결 URL",
    )
    db_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="DB 커넥션 풀 크기",
    )
    db_max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="DB 커넥션 풀 최대 초과 수",
    )
    db_echo: bool = Field(
        default=False,
        description="SQL 쿼리 로깅 활성화",
    )

    # ── Redis ──
    redis_url: str = Field(
        default="redis://localhost:6380/0",
        description="Redis 브로커 URL",
    )
    redis_result_backend: str = Field(
        default="redis://localhost:6380/1",
        description="Celery 결과 백엔드 URL",
    )

    # ── JWT ──
    jwt_secret_key: str = Field(
        default="change-me-in-production",
        alias="JWT_SECRET",
        description="JWT 서명 시크릿 키 (크로스 백엔드 공유)",
    )
    jwt_private_key_path: str = Field(
        default="keys/private.pem",
        description="JWT RS256 개인키 파일 경로",
    )
    jwt_public_key_path: str = Field(
        default="keys/public.pem",
        description="JWT RS256 공개키 파일 경로",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT 서명 알고리즘",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="Access token 만료 시간 (분)",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        description="Refresh token 만료 시간 (일)",
    )

    # ── 외부 API 키 ──
    dart_api_key: str = Field(
        default="",
        description="Open DART API 키",
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API 키",
    )
    brandfetch_api_key: str = Field(
        default="",
        description="Brandfetch API 키",
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API 키",
    )
    google_api_key: str = Field(
        default="",
        description="Google AI API 키",
    )
    pinecone_api_key: str = Field(
        default="",
        description="Pinecone API 키",
    )

    # ── Auth ──
    auth_enabled: bool = Field(
        default=True,
        description="인증 활성화 여부 (False=dev 모드, 인증 우회)",
    )

    # ── App ──
    secret_key: str = Field(
        default="change-me-in-production",
        description="애플리케이션 시크릿 키",
    )
    debug: bool = Field(
        default=False,
        description="디버그 모드 활성화",
    )
    log_level: str = Field(
        default="INFO",
        description="로그 레벨 (DEBUG, INFO, WARNING, ERROR)",
    )
    log_dir: str = Field(
        default="",
        description="로그 파일 저장 디렉토리 (비어있으면 파일 저장 안 함)",
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        description="CORS 허용 오리진 목록",
        alias="CORS_ORIGINS",
    )

    # ── Rate Limiting ──
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        description="분당 최대 요청 수",
    )

    # ── Celery ──
    celery_task_soft_time_limit: int = Field(
        default=300,
        ge=30,
        description="Celery 태스크 소프트 타임아웃 (초)",
    )
    celery_task_hard_time_limit: int = Field(
        default=600,
        ge=60,
        description="Celery 태스크 하드 타임아웃 (초)",
    )

    # ── Cross-Backend (VDR 연동) ──
    deal_mgmt_internal_url: str = Field(
        default="http://deal-mgmt-api:8003",
        description="deal-mgmt 내부 API URL (Docker 서비스명)",
        alias="DEAL_MGMT_INTERNAL_URL",
    )
    internal_service_key: str = Field(
        default="",
        description="내부 서비스 인증 키 (deal-mgmt 내부 API 접근용)",
        alias="INTERNAL_SERVICE_KEY",
    )

    # ── Ralph Loop ──
    ralph_pass_threshold: float = Field(
        default=4.0,
        ge=1.0,
        le=5.0,
        description="Ralph Loop 통과 기준 (5점 만점)",
    )
    ralph_max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="섹션당 최대 반복 횟수",
    )
    ralph_budget_per_pass: float = Field(
        default=5.0,
        ge=0.0,
        description="Pass당 비용 한도 (USD)",
    )
    ralph_vision_enabled: bool = Field(
        default=True,
        description="Vision Gate (GPT-4o) 활성화",
    )

    # ── File Storage ──
    output_dir: str = Field(
        default="output/",
        description="생성된 문서 출력 디렉토리",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        """DB URL이 postgresql로 시작하는지 검증."""
        if not v.startswith("postgresql"):
            msg = f"database_url은 'postgresql'로 시작해야 합니다: {v}"
            raise ValueError(msg)
        return v

    @field_validator("redis_url", "redis_result_backend")
    @classmethod
    def _validate_redis_url(cls, v: str) -> str:
        """Redis URL이 redis://로 시작하는지 검증."""
        if not v.startswith("redis://"):
            msg = f"Redis URL은 'redis://'로 시작해야 합니다: {v}"
            raise ValueError(msg)
        return v

    @field_validator("celery_task_hard_time_limit")
    @classmethod
    def _hard_gt_soft(cls, v: int, info: object) -> int:
        """hard_time_limit이 soft_time_limit보다 큰지 검증."""
        data = getattr(info, "data", {})
        soft = data.get("celery_task_soft_time_limit", 300)
        if v <= soft:
            msg = f"hard_time_limit({v})은 soft_time_limit({soft})보다 커야 합니다"
            raise ValueError(msg)
        return v

    @property
    def has_dart(self) -> bool:
        """DART API 키가 설정되었는지 확인."""
        return bool(self.dart_api_key)

    @property
    def has_openai(self) -> bool:
        """OpenAI API 키가 설정되었는지 확인."""
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        """Anthropic API 키가 설정되었는지 확인."""
        return bool(self.anthropic_api_key)

    @property
    def has_google(self) -> bool:
        """Google AI API 키가 설정되었는지 확인."""
        return bool(self.google_api_key)


@lru_cache(maxsize=1)
def get_config() -> APIConfig:
    """캐싱된 APIConfig 싱글턴을 반환한다.

    Returns:
        APIConfig 인스턴스 (.env에서 로드).
    """
    return APIConfig()
