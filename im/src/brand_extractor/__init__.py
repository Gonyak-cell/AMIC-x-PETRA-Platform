"""Brand Extractor — 기업 브랜드 자산 자동 추출 모듈.

> 마지막 수정: 2026-02-10 22:00:00

Brandfetch API / 웹사이트 크롤링 / AMIC 폴백의 3단계 우선순위 체인으로
로고와 색상을 추출하여 IMDocumentData.brand_assets에 공급한다.

파이프라인: Brandfetch API → Website crawl → AMIC fallback

사용 예시::

    from src.brand_extractor import extract_brand, BrandAssets
    from src.design_renderer.design_tokens import IMDesignTokens

    brand: BrandAssets = await extract_brand("samsung.com", "삼성전자")
    tokens = IMDesignTokens.from_brand_assets(brand)
"""

from __future__ import annotations

import logging

# ── Config ──
from src.brand_extractor.config import BrandExtractorConfig, get_config

# ── Models ──
from src.brand_extractor.models import BrandAssets, ExtractedColor, LogoCandidate

# ── Extractors ──
from src.brand_extractor.extractors.brandfetch import BrandfetchClient
from src.brand_extractor.extractors.fallback import FallbackExtractor
from src.brand_extractor.extractors.website import WebsiteExtractor

# ── Logo ──
from src.brand_extractor.logo.detector import LogoDetector
from src.brand_extractor.logo.processor import LogoProcessor
from src.brand_extractor.logo.scorer import LogoScorer

# ── Color ──
from src.brand_extractor.color.classifier import ColorClassifier
from src.brand_extractor.color.extractor import ColorExtractor
from src.brand_extractor.color.token_mapper import BrandTokenMapper

# ── Exceptions ──
from src.brand_extractor.exceptions import (
    BrandfetchAPIError,
    BrandExtractorError,
    ColorExtractionError,
    LogoDetectionError,
    WebsiteAccessError,
)

logger = logging.getLogger(__name__)

__version__ = "0.8.0"

__all__ = [
    # Public API
    "extract_brand",
    # Config
    "BrandExtractorConfig",
    "get_config",
    # Models
    "BrandAssets",
    "ExtractedColor",
    "LogoCandidate",
    # Extractors
    "BrandfetchClient",
    "WebsiteExtractor",
    "FallbackExtractor",
    # Logo
    "LogoDetector",
    "LogoScorer",
    "LogoProcessor",
    # Color
    "ColorExtractor",
    "ColorClassifier",
    "BrandTokenMapper",
    # Exceptions
    "BrandExtractorError",
    "BrandfetchAPIError",
    "LogoDetectionError",
    "ColorExtractionError",
    "WebsiteAccessError",
]


async def extract_brand(
    domain: str,
    company_name: str = "",
    *,
    config: BrandExtractorConfig | None = None,
) -> BrandAssets:
    """브랜드 자산을 추출한다 — 3단계 우선순위 체인.

    추출 우선순위:
    1. Brandfetch API (config.has_brandfetch일 때)
    2. Website crawl (domain → https://{domain})
    3. AMIC fallback (항상 성공)

    각 단계 실패 시 warning을 추가하고 다음 단계로 넘어간다.

    Args:
        domain: 기업 도메인 (예: "samsung.com").
        company_name: 기업명 (한글/영문).
        config: 설정 오버라이드. None이면 get_config() 사용.

    Returns:
        추출된 BrandAssets 인스턴스.
    """
    cfg = config or get_config()
    warnings: list[str] = []

    # 1. Brandfetch API
    if cfg.has_brandfetch:
        try:
            logger.info("1단계: Brandfetch API 시도 — domain='%s'", domain)
            async with BrandfetchClient(cfg) as client:
                brand = await client.extract(domain)
            brand.company_name = brand.company_name or company_name
            logger.info("Brandfetch 추출 성공: confidence=%.2f", brand.confidence)
            return brand
        except BrandfetchAPIError as e:
            warnings.append(f"Brandfetch 실패: {e.message}")
            logger.warning("Brandfetch API 실패: %s", e.message)
    else:
        logger.info("Brandfetch API 키 없음 — 건너뜀")

    # 2. Website crawl
    try:
        url = (
            domain
            if domain.startswith(("http://", "https://"))
            else f"https://{domain}"
        )
        logger.info("2단계: 웹사이트 크롤링 시도 — url='%s'", url)
        extractor = WebsiteExtractor(cfg)
        brand = await extractor.extract(url, company_name=company_name)
        brand.warnings = warnings + brand.warnings
        logger.info("웹사이트 추출 성공: confidence=%.2f", brand.confidence)
        return brand
    except (WebsiteAccessError, Exception) as e:
        warnings.append(f"웹사이트 추출 실패: {e}")
        logger.warning("웹사이트 추출 실패: %s", e)

    # 3. AMIC fallback
    if cfg.fallback_enabled:
        logger.info("3단계: AMIC 폴백 사용")
        fallback = FallbackExtractor()
        brand = fallback.extract(company_name=company_name)
        brand.warnings = warnings
        return brand

    # 폴백도 비활성화된 경우 (드문 케이스)
    raise BrandExtractorError(
        message=f"브랜드 추출 실패: domain='{domain}' — 모든 추출 방법 실패",
        details={"domain": domain, "warnings": warnings},
    )
