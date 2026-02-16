"""AMIC 기본값 폴백 추출기 (T-B09).

> 마지막 수정: 2026-02-10 22:00:00

Brandfetch API 및 웹사이트 추출이 모두 실패했을 때
AMIC 기본 브랜드 자산을 반환한다. 항상 성공을 보장한다.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from src.brand_extractor.models import BrandAssets

logger = logging.getLogger(__name__)


class FallbackExtractor:
    """AMIC 기본값을 반환하는 폴백 추출기.

    Examples:
        >>> extractor = FallbackExtractor()
        >>> brand = extractor.extract("삼성전자")
        >>> brand.primary_color
        '#0F3A32'
        >>> brand.source
        'fallback'
    """

    AMIC_PRIMARY: ClassVar[str] = "#0F3A32"
    AMIC_SECONDARY: ClassVar[str] = "#26C260"
    AMIC_LOGO_DARK: ClassVar[str] = "amic_logo_dark.png"
    AMIC_LOGO_WHITE: ClassVar[str] = "amic_logo_white.png"
    AMIC_COVER_BG: ClassVar[str] = "amic_cover_bg.jpeg"

    def extract(self, company_name: str = "") -> BrandAssets:
        """AMIC 기본 BrandAssets를 반환한다.

        Args:
            company_name: 기업명 (BrandAssets.company_name에 설정).

        Returns:
            AMIC 기본 색상/로고가 적용된 BrandAssets.
            confidence=0.0, source="fallback".
        """
        logger.info("폴백 추출기 사용: company_name='%s'", company_name)
        return BrandAssets(
            company_name=company_name,
            primary_color=self.AMIC_PRIMARY,
            secondary_color=self.AMIC_SECONDARY,
            logo_dark_path=self.AMIC_LOGO_DARK,
            logo_white_path=self.AMIC_LOGO_WHITE,
            cover_bg_path=self.AMIC_COVER_BG,
            confidence=0.0,
            source="fallback",
        )
