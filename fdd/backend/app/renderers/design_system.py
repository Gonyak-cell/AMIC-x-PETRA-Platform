"""Design System 로더.

Big 4 스타일 디자인 시스템 설정을 로드하고 캐싱합니다.
딜별 커스텀 브랜딩이 필요한 경우 deal_id별 오버라이드를 지원합니다.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.errors import ErrorCode
from app.core.exceptions import FDDError

# 프로젝트 루트 기준 기본 경로
DEFAULT_CONFIG_PATH = (
    Path(__file__).parent.parent.parent.parent / "config" / "design_system.yaml"
)


class DesignSystemError(FDDError):
    """Design System 관련 에러."""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.SYS_FILE_PROCESSING, message)


@lru_cache(maxsize=4)
def load_design_system(config_path: str | None = None) -> dict[str, Any]:
    """Design system 설정을 로드합니다 (캐시됨).

    Args:
        config_path: YAML 설정 파일 경로. None이면 기본 경로 사용.

    Returns:
        디자인 시스템 설정 딕셔너리

    Raises:
        DesignSystemError: 파일이 없거나 파싱 실패 시

    Example:
        >>> ds = load_design_system()
        >>> ds["colors"]["primary"]
        '#003366'
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        raise DesignSystemError(f"Design system config not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise DesignSystemError(f"Invalid YAML in design system config: {e}") from e

    if not isinstance(config, dict):
        raise DesignSystemError("Design system config must be a YAML mapping")

    return config


def get_colors(config_path: str | None = None) -> dict[str, str]:
    """색상 팔레트만 반환합니다.

    Example:
        >>> colors = get_colors()
        >>> colors["positive"]
        '#2E7D32'
    """
    return load_design_system(config_path).get("colors", {})


def get_fonts(config_path: str | None = None) -> dict[str, str]:
    """폰트 설정만 반환합니다."""
    return load_design_system(config_path).get("fonts", {})


def get_sizes(config_path: str | None = None) -> dict[str, int]:
    """폰트 크기 설정만 반환합니다."""
    return load_design_system(config_path).get("sizes", {})


def get_number_formats(config_path: str | None = None) -> dict[str, str]:
    """숫자 포맷 설정만 반환합니다."""
    return load_design_system(config_path).get("number_formats", {})


def get_layout(config_path: str | None = None) -> dict[str, float]:
    """레이아웃 설정만 반환합니다."""
    return load_design_system(config_path).get("layout", {})


def get_chart_style(chart_type: str, config_path: str | None = None) -> dict[str, Any]:
    """특정 차트 타입의 스타일 설정을 반환합니다.

    Args:
        chart_type: 차트 타입 (waterfall, bar, line, common)
        config_path: 설정 파일 경로

    Returns:
        차트 스타일 딕셔너리. common 설정이 병합됨.
    """
    charts = load_design_system(config_path).get("charts", {})
    common = charts.get("common", {})
    specific = charts.get(chart_type, {})

    # common 설정 위에 specific 설정 오버라이드
    return {**common, **specific}


def get_fdd_config(config_path: str | None = None) -> dict[str, Any]:
    """FDD 특화 설정을 반환합니다."""
    return load_design_system(config_path).get("fdd", {})


def get_adjustment_color(category: str, config_path: str | None = None) -> str:
    """조정 항목 카테고리에 해당하는 색상을 반환합니다.

    Args:
        category: 조정 카테고리 (one_off, non_operating, run_rate, normalization, pro_forma)

    Returns:
        Hex 색상 코드. 없으면 neutral 색상 반환.
    """
    fdd = get_fdd_config(config_path)
    colors = fdd.get("adjustment_colors", {})
    default_color = get_colors(config_path).get("neutral", "#666666")
    return colors.get(category, default_color)


def get_risk_color(level: str, config_path: str | None = None) -> str:
    """리스크 등급에 해당하는 색상을 반환합니다.

    Args:
        level: 리스크 등급 (high, medium, low)

    Returns:
        Hex 색상 코드
    """
    fdd = get_fdd_config(config_path)
    colors = fdd.get("risk_colors", {})
    default = {"high": "#E0301E", "medium": "#F9A825", "low": "#2E7D32"}
    return colors.get(level, default.get(level, "#666666"))


def clear_cache() -> None:
    """캐시를 초기화합니다. 설정 파일 변경 후 호출 필요."""
    load_design_system.cache_clear()


# FastAPI Depends 용 의존성 함수
def get_design_system() -> dict[str, Any]:
    """FastAPI Depends에서 사용할 Design System 의존성.

    Example:
        @router.get("/charts/ebitda-bridge")
        async def get_chart(design: dict = Depends(get_design_system)):
            colors = design["colors"]
            ...
    """
    return load_design_system()
