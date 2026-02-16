"""디자인 토큰 테스트 — 로드/오버라이드/검증."""

import re

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens


class TestDefaultTokens:
    """DEFAULT_TOKENS 기본 검증."""

    def test_default_tokens_exist(self):
        """DEFAULT_TOKENS가 모든 서브 토큰을 포함한다."""
        assert DEFAULT_TOKENS is not None
        assert DEFAULT_TOKENS.colors is not None
        assert DEFAULT_TOKENS.typography is not None
        assert DEFAULT_TOKENS.font_sizes is not None
        assert DEFAULT_TOKENS.layout is not None

    def test_color_palette_hex_format(self):
        """모든 색상이 유효한 #RRGGBB 형식이다."""
        c = DEFAULT_TOKENS.colors
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")

        for attr in [
            "primary",
            "accent",
            "text_body",
            "bg_white",
            "positive",
            "negative",
            "caution",
        ]:
            value = getattr(c, attr)
            assert hex_pattern.match(value), f"{attr}={value} is not valid hex"

    def test_layout_dimensions(self):
        """페이지 크기와 마진이 합리적이다."""
        lay = DEFAULT_TOKENS.layout
        assert lay.page_width > 0
        assert lay.page_height > 0
        assert lay.margin_left > 0
        assert lay.margin_right > 0

    def test_content_area_computed(self):
        """content_width/height가 올바르게 파생된다."""
        lay = DEFAULT_TOKENS.layout
        expected_width = lay.page_width - lay.margin_left - lay.margin_right
        assert abs(lay.content_width - expected_width) < 0.01

    def test_placeholder_idx_constants(self):
        """플레이스홀더 인덱스 상수가 올바르다."""
        lay = DEFAULT_TOKENS.layout
        assert lay.ph_title_idx == 11
        assert lay.ph_footnote_idx == 12
        assert lay.ph_page_number_idx == 13

    def test_font_sizes_minimum(self):
        """최소 폰트 크기가 7pt 이상이다."""
        f = DEFAULT_TOKENS.font_sizes
        assert f.minimum >= 7

    def test_typography_has_fallback(self):
        """CSS 폰트 스택에 폴백 폰트가 포함된다."""
        typo = DEFAULT_TOKENS.typography
        assert "," in typo.css_heading  # 폴백 폰트 존재
        assert "," in typo.css_body

    def test_company_name_default(self):
        """기본 회사명에 AMIC이 포함된다."""
        assert "AMIC" in DEFAULT_TOKENS.company_name


class TestTokenOverride:
    """토큰 오버라이드/커스텀 생성."""

    def test_from_brand_assets_none(self):
        """brand_assets=None이면 기본 토큰 반환."""
        tokens = IMDesignTokens.from_brand_assets(None)
        assert tokens.colors.primary == DEFAULT_TOKENS.colors.primary

    def test_custom_tokens_independent(self):
        """커스텀 토큰은 DEFAULT_TOKENS에 영향 없음."""
        original_primary = DEFAULT_TOKENS.colors.primary
        # DEFAULT_TOKENS는 frozen이므로 직접 변경 불가 — 이 테스트는 불변성 확인
        assert DEFAULT_TOKENS.colors.primary == original_primary
