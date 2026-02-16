"""Jinja2 템플릿 환경 설정 및 커스텀 필터.

IM HTML 렌더링에 사용되는 Jinja2 Environment를 생성하고,
디자인 토큰을 글로벌 변수로, 포맷팅 유틸리티를 커스텀 필터로 등록한다.
"""

from __future__ import annotations

import math
from html import escape as html_escape
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

# 기본 템플릿 디렉토리 (Sprint 3/4에서 HTML 템플릿 추가 예정)
TEMPLATE_DIR = Path(__file__).parent / "html_templates"


def create_jinja_env(
    tokens: IMDesignTokens | None = None,
    *,
    template_dir: Path | None = None,
) -> Environment:
    """Jinja2 환경 생성.

    디자인 토큰 변수 + 커스텀 필터가 등록된 Environment를 반환한다.

    Args:
        tokens: 디자인 토큰. None이면 AMIC 기본값.
        template_dir: 템플릿 디렉토리. None이면 기본 경로.

    Returns:
        설정 완료된 Jinja2 Environment.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    tpl_dir = template_dir or TEMPLATE_DIR
    # 디렉토리가 없으면 생성
    tpl_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    _register_global_variables(env, tokens)
    _register_custom_filters(env)

    return env


# ---------------------------------------------------------------------------
# 글로벌 변수 등록
# ---------------------------------------------------------------------------


def _register_global_variables(env: Environment, tokens: IMDesignTokens) -> None:
    """디자인 토큰을 Jinja2 글로벌 변수로 등록."""
    env.globals.update(
        {
            "tokens": tokens,
            "colors": tokens.colors,
            "typo": tokens.typography,
            "sizes": tokens.font_sizes,
            "layout": tokens.layout,
            "company_name": tokens.company_name,
            "footer_note": tokens.footer_note,
            "logo_text": tokens.logo_text,
        }
    )


# ---------------------------------------------------------------------------
# 커스텀 필터 등록
# ---------------------------------------------------------------------------


def _register_custom_filters(env: Environment) -> None:
    """커스텀 Jinja2 필터 등록."""
    env.filters["format_currency"] = _filter_format_currency
    env.filters["format_pct"] = _filter_format_pct
    env.filters["korean_number"] = _filter_korean_number
    env.filters["safe_text"] = _filter_safe_text
    env.filters["growth_color"] = _filter_growth_color


def _filter_format_currency(
    value: float | None,
    unit: str = "억원",
    decimal: int = 0,
) -> str:
    """{{ value | format_currency }} → '150,000억원'"""
    if value is None:
        return "N/A"
    if math.isnan(value) or math.isinf(value):
        return "N/A"

    # 천단위 구분
    if decimal <= 0:
        formatted = f"{int(round(value)):,}"
    else:
        formatted = f"{value:,.{decimal}f}"

    return f"{formatted}{unit}"


def _filter_format_pct(
    value: float | None,
    decimal: int = 1,
) -> str:
    """{{ value | format_pct }} → '15.2%'"""
    if value is None:
        return "N/A"
    if math.isnan(value) or math.isinf(value):
        return "N/A"

    pct = value * 100
    return f"{pct:.{decimal}f}%"


def _filter_korean_number(value: int | float | None) -> str:
    """{{ value | korean_number }} → '1조 5,000억'"""
    if value is None:
        return "N/A"

    value = float(value)
    if value < 0:
        return f"-{_filter_korean_number(abs(value))}"

    parts: list[str] = []
    if value >= 1_0000_0000_0000:
        jo = int(value // 1_0000_0000_0000)
        parts.append(f"{jo:,}조")
        value %= 1_0000_0000_0000

    if value >= 1_0000_0000:
        eok = int(value // 1_0000_0000)
        parts.append(f"{eok:,}억")
        value %= 1_0000_0000

    if value >= 1_0000:
        man = int(value // 1_0000)
        parts.append(f"{man:,}만")
        value %= 1_0000

    if value >= 1 or not parts:
        parts.append(f"{int(value):,}")

    return " ".join(parts)


def _filter_safe_text(text: str | None) -> str:
    """HTML 이스케이프 (XSS 방지)."""
    if text is None:
        return ""
    return html_escape(str(text))


def _filter_growth_color(value: float | None) -> str:
    """성장률에 따른 CSS 색상 클래스 반환.

    {{ value | growth_color }} → 'positive' | 'negative' | 'neutral'
    """
    if value is None:
        return "neutral"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"
