"""Chart Engine 설정 및 컬러 인터페이스.

> 마지막 수정: 2026-02-10 13:45:13

chart_engine 모듈이 design_renderer에 의존하지 않도록
자체 ChartColorConfig / ChartConfig를 정의한다.
design_renderer 측 adapter가 IMDesignTokens → ChartColorConfig 변환을 담당.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

CHART_DPI: int = 300
DEFAULT_WIDTH: int = 900  # px
DEFAULT_HEIGHT: int = 500  # px
KOREAN_FONT: str = "Noto Sans KR"

AMIC_CHART_COLORS: list[str] = [
    "#0F3A32",  # Signature Green (primary)
    "#1C8F57",  # Solid Green (secondary)
    "#26C260",  # Highlight Green (accent)
    "#A3E96B",  # Fresh Green
    "#000000",  # text body
    "#777777",  # text secondary
    "#EF6C00",  # caution (amber)
    "#BC2C1A",  # negative (red)
    "#E6FDD6",  # Light Green bg
    "#F4F6F8",  # cool grey
]


# ---------------------------------------------------------------------------
# 컬러 설정
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChartColorConfig:
    """차트 엔진에 전달하는 컬러 설정.

    design_renderer.IMDesignTokens와 의존성 없이,
    차트 렌더링에 필요한 색상만 추출한 경량 인터페이스.
    """

    primary: str = "#0F3A32"  # Signature Green
    secondary: str = "#1C8F57"  # Solid Green
    accent: str = "#26C260"  # Highlight Green
    fresh: str = "#A3E96B"  # Fresh Green
    text_body: str = "#000000"
    text_secondary: str = "#777777"
    positive: str = "#26C260"
    negative: str = "#BC2C1A"
    caution: str = "#EF6C00"
    gray_medium: str = "#757575"
    gray_border: str = "#E0E0E0"
    bg_light_green: str = "#E6FDD6"  # AMIC Light Green
    bg_cool_grey: str = "#F4F6F8"
    text_white: str = "#FFFFFF"
    text_dark: str = "#000000"


# ---------------------------------------------------------------------------
# 차트 설정
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChartConfig:
    """차트 엔진 전역 설정."""

    colors: ChartColorConfig = field(default_factory=ChartColorConfig)
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    font: str = KOREAN_FONT
    dpi_scale: int = 3  # 3 = 300 DPI at base 100


DEFAULT_CHART_CONFIG: ChartConfig = ChartConfig()


def chart_config_from_design_tokens(tokens: Any) -> ChartConfig:
    """IMDesignTokens → ChartConfig 변환 어댑터.

    design_tokens 모듈에 대한 런타임 의존 없이,
    colors 속성의 덕 타이핑으로 변환한다.

    Args:
        tokens: IMDesignTokens 인스턴스 (colors 속성 필수).

    Returns:
        토큰 색상이 반영된 ChartConfig.
    """
    c = getattr(tokens, "colors", None)
    if c is None:
        return DEFAULT_CHART_CONFIG

    return ChartConfig(
        colors=ChartColorConfig(
            primary=getattr(c, "primary", ChartColorConfig.primary),
            secondary=getattr(c, "secondary", ChartColorConfig.secondary),
            accent=getattr(c, "accent", ChartColorConfig.accent),
            fresh=getattr(c, "fresh", ChartColorConfig.fresh),
            text_body=getattr(c, "text_body", ChartColorConfig.text_body),
            text_secondary=getattr(
                c, "text_secondary", ChartColorConfig.text_secondary
            ),
            positive=getattr(c, "positive", ChartColorConfig.positive),
            negative=getattr(c, "negative", ChartColorConfig.negative),
            caution=getattr(c, "caution", ChartColorConfig.caution),
            bg_light_green=getattr(
                c, "bg_light_green", ChartColorConfig.bg_light_green
            ),
            bg_cool_grey=getattr(c, "bg_cool_grey", ChartColorConfig.bg_cool_grey),
            text_white=getattr(c, "text_white", ChartColorConfig.text_white),
            text_dark=getattr(c, "text_dark", ChartColorConfig.text_dark),
        ),
    )
