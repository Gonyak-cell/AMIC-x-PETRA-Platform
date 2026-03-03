"""BrandTokenMapper 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from src.brand_extractor.color.token_mapper import BrandTokenMapper
from src.brand_extractor.models import BrandAssets


class TestBrandTokenMapper:
    """BrandTokenMapper 디자인 토큰 매핑 테스트."""

    def setup_method(self) -> None:
        """테스트 초기화."""
        self.mapper = BrandTokenMapper()

    def test_map_to_tokens(self, sample_brand_assets: BrandAssets) -> None:
        """BrandAssets → IMDesignTokens 변환 검증."""
        tokens = self.mapper.map_to_tokens(sample_brand_assets)
        assert tokens.colors.primary == "#FF5733"
        assert tokens.colors.accent == "#33FF57"
        assert tokens.company_name == "테스트 기업"

    def test_fallback_brand_to_tokens(self, fallback_brand_assets: BrandAssets) -> None:
        """AMIC 폴백 BrandAssets → IMDesignTokens 변환 검증."""
        tokens = self.mapper.map_to_tokens(fallback_brand_assets)
        assert tokens.colors.primary == "#0F3A32"
        assert tokens.colors.accent == "#26C260"
        assert tokens.logo_dark_path == "amic_logo_dark.png"

    def test_full_palette_derived_colors(self) -> None:
        """전체 팔레트 파생 색상 검증."""
        palette = self.mapper.build_full_palette("#1428A0", "#00A1E0")
        assert palette.primary == "#1428A0"
        assert palette.accent == "#00A1E0"
        assert palette.table_header_bg == "#1428A0"
        assert palette.positive == "#00A1E0"
        # bg_light_green은 primary를 밝게 한 값
        assert palette.bg_light_green.startswith("#")
        assert palette.bg_light_green != "#1428A0"

    def test_lighten_color(self) -> None:
        """색상 밝게 하기 검증."""
        # 검정을 92% 밝게 하면 거의 흰색
        result = BrandTokenMapper._lighten_color("#000000", 0.92)
        assert result.startswith("#")
        # 각 채널이 ~235 이상이어야 함
        r = int(result[1:3], 16)
        g = int(result[3:5], 16)
        b = int(result[5:7], 16)
        assert r >= 230
        assert g >= 230
        assert b >= 230

    def test_lighten_white_stays_white(self) -> None:
        """흰색을 밝게 해도 흰색."""
        result = BrandTokenMapper._lighten_color("#FFFFFF", 0.92)
        assert result == "#FFFFFF"

    def test_empty_logo_paths_use_defaults(self) -> None:
        """로고 경로가 빈값이면 AMIC 기본값 유지."""
        brand = BrandAssets(
            primary_color="#FF0000",
            secondary_color="#00FF00",
            logo_dark_path="",
            logo_white_path="",
            cover_bg_path="",
        )
        tokens = self.mapper.map_to_tokens(brand)
        # 빈값이면 IMDesignTokens의 클래스 기본값 사용
        assert tokens.logo_dark_path == "amic_logo_dark.png"
        assert tokens.logo_white_path == "amic_logo_white.png"
        assert tokens.cover_bg_path == "forest_cover.jpg"
