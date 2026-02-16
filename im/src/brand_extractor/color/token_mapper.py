"""브랜드 → 디자인 토큰 매퍼 (T-B07).

> 마지막 수정: 2026-02-10 22:00:00

BrandAssets의 primary/secondary 색상으로부터 IMDesignTokens를 생성한다.
기본적으로 IMDesignTokens.from_brand_assets()를 호출하며,
추가로 파생 색상(배경, 테이블 헤더 등)을 보강한다.
"""

from __future__ import annotations

import logging

from src.brand_extractor.models import BrandAssets
from src.design_renderer.design_tokens import IMColorPalette, IMDesignTokens

logger = logging.getLogger(__name__)


class BrandTokenMapper:
    """BrandAssets → IMDesignTokens 매핑.

    brand primary/secondary 2개 색상으로부터
    전체 IMColorPalette 파생 색상을 자동 생성한다.

    Examples:
        >>> mapper = BrandTokenMapper()
        >>> tokens = mapper.map_to_tokens(brand)
        >>> tokens.colors.primary == brand.primary_color
        True
    """

    def map_to_tokens(self, brand: BrandAssets) -> IMDesignTokens:
        """BrandAssets를 IMDesignTokens로 변환한다.

        Args:
            brand: 브랜드 자산.

        Returns:
            브랜드 오버라이드가 적용된 IMDesignTokens.
        """
        palette = self.build_full_palette(brand.primary_color, brand.secondary_color)

        tokens = IMDesignTokens(
            colors=palette,
            company_name=brand.company_name or IMDesignTokens.company_name,
            logo_dark_path=brand.logo_dark_path or IMDesignTokens.logo_dark_path,
            logo_white_path=brand.logo_white_path or IMDesignTokens.logo_white_path,
            cover_bg_path=brand.cover_bg_path or IMDesignTokens.cover_bg_path,
        )

        logger.info(
            "브랜드 토큰 매핑 완료: primary=%s, secondary=%s, source=%s",
            brand.primary_color,
            brand.secondary_color,
            brand.source,
        )
        return tokens

    def build_full_palette(
        self,
        primary: str,
        secondary: str,
    ) -> IMColorPalette:
        """2개 브랜드 색상으로 전체 IMColorPalette를 생성한다.

        파생 규칙:
        - primary → primary, table_header_bg
        - secondary → accent, positive
        - primary lightened → bg_light_green, bg_lighter_green
        - 나머지 (text, gray, negative 등) → AMIC 기본값 유지

        Args:
            primary: 1차 브랜드 색상 HEX.
            secondary: 2차 브랜드 색상 HEX.

        Returns:
            파생 색상이 적용된 IMColorPalette.
        """
        return IMColorPalette(
            primary=primary,
            accent=secondary,
            # 배경: primary를 밝게
            bg_light_green=self._lighten_color(primary, 0.92),
            bg_lighter_green=self._lighten_color(primary, 0.96),
            # 테이블 헤더 = primary
            table_header_bg=primary,
            # 긍정 지표 = secondary
            positive=secondary,
        )

    @staticmethod
    def _lighten_color(hex_color: str, factor: float) -> str:
        """색상을 흰색 방향으로 보간하여 밝게 한다.

        Args:
            hex_color: HEX 컬러 코드 (예: "#0F3A32").
            factor: 밝기 계수 (0=원색, 1=흰색). 0.92면 거의 흰색.

        Returns:
            밝아진 HEX 컬러 코드.
        """
        hex_clean = hex_color.lstrip("#")
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)

        # 흰색(255) 방향으로 보간
        r_new = int(r + (255 - r) * factor)
        g_new = int(g + (255 - g) * factor)
        b_new = int(b + (255 - b) * factor)

        return f"#{r_new:02X}{g_new:02X}{b_new:02X}"
