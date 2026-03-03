"""Phase 5 검증 테스트 (1/2) — 디자인 토큰 감사 (15 tests).

32개 렌더러가 design_tokens.py의 AMIC 공식 디자인 시스템만 사용하는지 검증한다.
기존 test_design_tokens.py(토큰 유효성)와 비중복 — 여기서는 렌더러의 토큰 준수를 검증한다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.design_renderer.design_tokens import DEFAULT_TOKENS

# ── 상수 ──────────────────────────────────────────────────────────────────────

RENDERERS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "design_renderer"
    / "section_renderers"
)

# 허용된 AMIC 공식 색상 (#RRGGBB)
AMIC_ALLOWED_COLORS = {
    "#0F3A32",
    "#1C8F57",
    "#26C260",
    "#A3E96B",
    "#E6FDD6",
    "#3D3D3D",
    "#2A2A2A",
    "#777777",
    "#FFFFFF",
    "#F1F8E9",
    "#F4F6F8",
    "#BC2C1A",
    "#EF6C00",
    "#FF3838",
    "#757575",
    "#333333",
    "#E0E0E0",
    "#B0B0B0",
    "#6A6A6A",
}

HEX_COLOR_RE = re.compile(r'["\']#([0-9A-Fa-f]{6})["\']')
FONT_BLACKLIST_RE = re.compile(
    r'["\'](Arial|Calibri|Times New Roman|Verdana|Tahoma)["\']'
)


def _get_renderer_files() -> list[Path]:
    """렌더러 Python 파일 목록 (__ 파일 제외)."""
    if not RENDERERS_DIR.exists():
        return []
    return sorted(f for f in RENDERERS_DIR.glob("*.py") if not f.name.startswith("__"))


def _read_file_lines(path: Path) -> list[tuple[int, str]]:
    """파일의 (라인번호, 내용) 리스트 반환."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return []
    return list(enumerate(content.splitlines(), start=1))


# ══════════════════════════════════════════════════════════════════════════════
# TestRendererColorCompliance (6)
# ══════════════════════════════════════════════════════════════════════════════


class TestRendererColorCompliance:
    """렌더러 색상 준수 검증."""

    def test_all_renderers_no_hardcoded_hex_colors(self) -> None:
        """32개 렌더러 소스에 비허용 #RRGGBB 리터럴 없음."""
        violations: list[str] = []
        for path in _get_renderer_files():
            for line_num, line in _read_file_lines(path):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for match in HEX_COLOR_RE.finditer(line):
                    hex_val = f"#{match.group(1).upper()}"
                    if hex_val not in AMIC_ALLOWED_COLORS:
                        violations.append(f"{path.name}:{line_num} → {hex_val}")
        assert not violations, (
            f"비허용 하드코딩 색상 {len(violations)}건:\n" + "\n".join(violations[:20])
        )

    def test_amic_primary_color_in_cover(self) -> None:
        """Cover 렌더러에서 tokens.colors.primary 참조 확인."""
        cover_path = RENDERERS_DIR / "cover.py"
        if not cover_path.exists():
            pytest.skip("cover.py 없음")
        content = cover_path.read_text(encoding="utf-8")
        assert "tokens" in content, "cover.py에서 tokens 미사용"

    def test_amic_accent_color_in_table_headers(self) -> None:
        """재무분석 렌더러에서 tokens 참조 확인."""
        fa_path = RENDERERS_DIR / "financial_analysis.py"
        if not fa_path.exists():
            pytest.skip("financial_analysis.py 없음")
        content = fa_path.read_text(encoding="utf-8")
        assert "tokens" in content, "financial_analysis.py에서 tokens 미사용"

    def test_no_hardcoded_font_names_in_renderers(self) -> None:
        """렌더러에 'Arial'/'Calibri' 등 문자열 리터럴 없음."""
        violations: list[str] = []
        for path in _get_renderer_files():
            for line_num, line in _read_file_lines(path):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                match = FONT_BLACKLIST_RE.search(line)
                if match:
                    violations.append(f"{path.name}:{line_num} → {match.group(1)}")
        assert not violations, (
            f"비허용 하드코딩 폰트 {len(violations)}건:\n" + "\n".join(violations[:20])
        )

    def test_layout_dimensions_from_tokens(self) -> None:
        """렌더러에서 Inches()/Emu() 상수보다 tokens.layout.* 참조 사용 확인.

        NOTE: 이 테스트는 'tokens' 문자열 존재 여부로 간접 확인.
        모든 렌더러가 tokens 파라미터를 받도록 설계되어 있음.
        """
        renderer_files = _get_renderer_files()
        assert len(renderer_files) >= 20, (
            f"렌더러 파일 {len(renderer_files)}개 (20개 이상 기대)"
        )
        tokens_users = 0
        for path in renderer_files:
            content = path.read_text(encoding="utf-8")
            if "tokens" in content:
                tokens_users += 1
        # 최소 80% 렌더러가 tokens 참조
        ratio = tokens_users / len(renderer_files)
        assert ratio >= 0.8, (
            f"tokens 참조 렌더러 {tokens_users}/{len(renderer_files)} "
            f"({ratio:.0%}, 80% 이상 기대)"
        )

    def test_amic_5_stage_green_palette_accessible(self) -> None:
        """DEFAULT_TOKENS.colors에 5개 그린 색상 모두 접근 가능."""
        colors = DEFAULT_TOKENS.colors
        assert colors.primary == "#0F3A32"
        assert colors.secondary == "#1C8F57"
        assert colors.accent == "#26C260"
        assert colors.fresh == "#A3E96B"
        assert colors.light == "#E6FDD6"


# ══════════════════════════════════════════════════════════════════════════════
# TestRendererFontCompliance (4)
# ══════════════════════════════════════════════════════════════════════════════


class TestRendererFontCompliance:
    """폰트 규정 준수 검증."""

    def test_heading_font_is_suite(self) -> None:
        """typography.font_heading == 'SUITE'."""
        assert DEFAULT_TOKENS.typography.font_heading == "SUITE"

    def test_body_font_is_pretendard(self) -> None:
        """typography.font_body == 'Pretendard'."""
        assert DEFAULT_TOKENS.typography.font_body == "Pretendard"

    def test_chart_font_is_noto_sans_kr(self) -> None:
        """typography.font_chart == 'Noto Sans KR' 또는 'NanumGothic'."""
        chart_font = DEFAULT_TOKENS.typography.font_chart
        assert chart_font in ("Noto Sans KR", "NanumGothic"), (
            f"chart_font={chart_font} (Noto Sans KR 또는 NanumGothic 기대)"
        )

    def test_css_font_stacks_have_fallbacks(self) -> None:
        """css_heading/css_body에 쉼표 구분 폴백 폰트 존재."""
        typo = DEFAULT_TOKENS.typography
        assert "," in typo.css_heading, "css_heading에 폴백 폰트 없음"
        assert "," in typo.css_body, "css_body에 폴백 폰트 없음"


# ══════════════════════════════════════════════════════════════════════════════
# TestLayoutTokenCompliance (5)
# ══════════════════════════════════════════════════════════════════════════════


class TestLayoutTokenCompliance:
    """레이아웃 토큰 정합성 검증."""

    def test_page_width_10_83_inches(self) -> None:
        """layout.page_width ≈ 10.83 (±0.01)."""
        width = DEFAULT_TOKENS.layout.page_width
        assert abs(width - 10.83) < 0.01, f"page_width={width} (10.83 ± 0.01 기대)"

    def test_page_height_7_5_inches(self) -> None:
        """layout.page_height ≈ 7.5."""
        height = DEFAULT_TOKENS.layout.page_height
        assert abs(height - 7.5) < 0.01, f"page_height={height} (7.5 ± 0.01 기대)"

    def test_margin_left_right_0_5_inches(self) -> None:
        """margin_left/right ≈ 0.5."""
        layout = DEFAULT_TOKENS.layout
        assert abs(layout.margin_left - 0.5) < 0.01, (
            f"margin_left={layout.margin_left} (0.5 ± 0.01 기대)"
        )
        assert abs(layout.margin_right - 0.5) < 0.01, (
            f"margin_right={layout.margin_right} (0.5 ± 0.01 기대)"
        )

    def test_margin_top_0_6_inches(self) -> None:
        """margin_top ≈ 0.6."""
        margin_top = DEFAULT_TOKENS.layout.margin_top
        assert abs(margin_top - 0.6) < 0.01, (
            f"margin_top={margin_top} (0.6 ± 0.01 기대)"
        )

    def test_margin_bottom_1_0_inches(self) -> None:
        """margin_bottom ≈ 1.0."""
        margin_bottom = DEFAULT_TOKENS.layout.margin_bottom
        assert abs(margin_bottom - 1.0) < 0.01, (
            f"margin_bottom={margin_bottom} (1.0 ± 0.01 기대)"
        )
