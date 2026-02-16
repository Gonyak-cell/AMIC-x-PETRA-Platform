"""Chart Engine 설정 및 컬러 인터페이스.

> 마지막 수정: 2026-02-10 13:45:13

chart_engine 모듈이 design_renderer에 의존하지 않도록
자체 ChartColorConfig / ChartConfig를 정의한다.
design_renderer 측 adapter가 IMDesignTokens → ChartColorConfig 변환을 담당.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

CHART_DPI: int = 300
DEFAULT_WIDTH: int = 900  # px
DEFAULT_HEIGHT: int = 500  # px
KOREAN_FONT: str = "NanumGothic"

AMIC_CHART_COLORS: list[str] = [
    "#0F3A32",  # primary (dark green)
    "#26C260",  # accent (green)
    "#3D3D3D",  # text body
    "#777777",  # secondary
    "#E8F5E9",  # light green bg
    "#EF6C00",  # caution (amber)
    "#BC2C1A",  # negative (red)
    "#4CAF50",  # extra green
    "#2196F3",  # extra blue
    "#9C27B0",  # extra purple
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

    primary: str = "#0F3A32"
    accent: str = "#26C260"
    text_body: str = "#3D3D3D"
    text_secondary: str = "#777777"
    positive: str = "#26C260"
    negative: str = "#BC2C1A"
    caution: str = "#EF6C00"
    gray_medium: str = "#757575"
    gray_border: str = "#E0E0E0"
    bg_light_green: str = "#E8F5E9"
    bg_cool_grey: str = "#F4F6F8"
    text_white: str = "#FFFFFF"
    text_dark: str = "#212121"


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
