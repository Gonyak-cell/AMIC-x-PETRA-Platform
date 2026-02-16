"""Brand Extractor 설정 (T-B01).

> 마지막 수정: 2026-02-10 22:00:00

Pydantic BaseSettings 기반으로 Brandfetch API, 로고/색상 추출 설정을 관리한다.
환경변수 또는 .env 파일에서 값을 로드한다.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class BrandExtractorConfig(BaseSettings):
    """Brand Extractor 통합 설정.

    환경변수 매핑:
        BRANDFETCH_API_KEY, BRAND_EXTRACTOR_TIMEOUT,
        BRAND_EXTRACTOR_MIN_LOGO_SIZE, BRAND_EXTRACTOR_MAX_COLORS, ...

    Examples:
        >>> config = BrandExtractorConfig()  # .env에서 자동 로드
        >>> config = get_config()            # 캐싱된 싱글턴
    """

    # ── Brandfetch API ──
    brandfetch_api_key: str = Field(
        default="",
        description="Brandfetch API 키",
    )
    brandfetch_base_url: str = Field(
        default="https://api.brandfetch.io/v2",
        description="Brandfetch API 기본 URL",
    )

    # ── HTTP ──
    timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="HTTP 요청 타임아웃 (초)",
    )

    # ── Logo ──
    min_logo_size: int = Field(
        default=64,
        ge=16,
        description="최소 로고 크기 (px). 이보다 작으면 0점",
    )
    preferred_logo_size: int = Field(
        default=512,
        ge=64,
        description="선호 로고 크기 (px). 스코어링 기준",
    )

    # ── Color ──
    max_colors: int = Field(
        default=5,
        ge=2,
        le=10,
        description="K-Means 클러스터 수",
    )

    # ── Fallback ──
    fallback_enabled: bool = Field(
        default=True,
        description="폴백 활성화 여부",
    )

    # ── Output ──
    logo_output_dir: str = Field(
        default="",
        description="로고 저장 디렉토리 (빈값: 시스템 임시 디렉토리)",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("preferred_logo_size")
    @classmethod
    def _preferred_ge_min(cls, v: int, info: object) -> int:
        """preferred_logo_size >= min_logo_size 검증."""
        data = getattr(info, "data", {})
        min_size = data.get("min_logo_size", 64)
        if v < min_size:
            msg = f"preferred_logo_size({v})는 min_logo_size({min_size}) 이상이어야 합니다"
            raise ValueError(msg)
        return v

    @property
    def has_brandfetch(self) -> bool:
        """Brandfetch API 키가 설정되었는지 확인."""
        return bool(self.brandfetch_api_key)


@lru_cache(maxsize=1)
def get_config() -> BrandExtractorConfig:
    """캐싱된 BrandExtractorConfig 싱글턴을 반환한다.

    Returns:
        BrandExtractorConfig 인스턴스 (.env에서 로드).
    """
    return BrandExtractorConfig()
