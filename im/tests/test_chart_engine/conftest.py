"""Chart Engine 테스트 공유 픽스처.

> 마지막 수정: 2026-02-11 10:00:00
"""

from __future__ import annotations

from typing import Any

import pytest

from src.chart_engine.config import ChartColorConfig, ChartConfig


@pytest.fixture
def default_config() -> ChartConfig:
    """기본 차트 설정."""
    return ChartConfig()


@pytest.fixture
def custom_config() -> ChartConfig:
    """커스텀 색상 차트 설정."""
    return ChartConfig(
        colors=ChartColorConfig(primary="#FF0000", accent="#00FF00"),
        width=800,
        height=400,
    )


@pytest.fixture
def waterfall_data() -> dict[str, Any]:
    """워터폴 차트 샘플 데이터."""
    return {
        "categories": ["매출", "COGS", "판관비", "영업이익"],
        "values": [150_000, -85_000, -37_000, 28_000],
        "measure": ["absolute", "relative", "relative", "total"],
    }


@pytest.fixture
def combo_data() -> dict[str, Any]:
    """콤보 차트 샘플 데이터."""
    return {
        "years": ["2022", "2023", "2024"],
        "bar_values": [100_000, 120_000, 150_000],
        "bar_name": "매출",
        "line_values": [0.15, 0.167, 0.187],
        "line_name": "영업이익률",
    }


@pytest.fixture
def stacked_bar_data() -> dict[str, Any]:
    """누적 막대 차트 샘플 데이터."""
    return {
        "categories": ["2022", "2023", "2024"],
        "series": [
            {"name": "IT서비스", "values": [60_000, 70_000, 90_000]},
            {"name": "SI", "values": [30_000, 40_000, 45_000]},
            {"name": "기타", "values": [10_000, 10_000, 15_000]},
        ],
    }


@pytest.fixture
def donut_data() -> dict[str, Any]:
    """도넛 차트 샘플 데이터."""
    return {
        "labels": ["IT서비스", "SI", "기타"],
        "values": [80_000, 50_000, 20_000],
    }


@pytest.fixture
def line_data() -> dict[str, Any]:
    """라인 차트 샘플 데이터."""
    return {
        "x": ["2022", "2023", "2024"],
        "series": [
            {"name": "매출", "values": [100_000, 120_000, 150_000]},
        ],
    }


@pytest.fixture
def hbar_data() -> dict[str, Any]:
    """수평 바 차트 샘플 데이터."""
    return {
        "categories": ["경쟁사A", "경쟁사B", "자사"],
        "values": [80_000, 60_000, 150_000],
        "highlight": "자사",
    }


@pytest.fixture
def funnel_data() -> dict[str, Any]:
    """퍼널 차트 샘플 데이터."""
    return {
        "stages": ["TAM", "SAM", "SOM"],
        "values": [50_000, 12_000, 3_000],
    }


@pytest.fixture
def sensitivity_heatmap_data() -> dict[str, Any]:
    """민감도 히트맵 샘플 데이터."""
    return {
        "x_labels": ["8x", "9x", "10x", "11x", "12x"],
        "y_labels": ["6x", "7x", "8x", "9x", "10x"],
        "z_values": [
            [12.5, 15.2, 17.8, 20.1, 22.3],
            [10.1, 12.8, 15.3, 17.7, 19.9],
            [7.8, 10.4, 12.9, 15.3, 17.5],
            [5.6, 8.1, 10.5, 12.9, 15.1],
            [3.5, 5.9, 8.2, 10.5, 12.7],
        ],
        "x_title": "Exit Multiple",
        "y_title": "Entry Multiple",
        "z_suffix": "%",
    }


@pytest.fixture
def cohort_heatmap_data() -> dict[str, Any]:
    """코호트 히트맵 샘플 데이터."""
    return {
        "cohorts": ["2024-01", "2024-02", "2024-03"],
        "periods": ["M0", "M1", "M2", "M3"],
        "retention_rates": [
            [100.0, 85.0, 72.0, 65.0],
            [100.0, 82.0, 68.0, None],
            [100.0, 78.0, None, None],
        ],
    }


@pytest.fixture
def treemap_data() -> dict[str, Any]:
    """트리맵 샘플 데이터."""
    return {
        "labels": ["전체", "IT서비스", "SI", "컨설팅", "클라우드", "보안"],
        "parents": ["", "전체", "전체", "전체", "IT서비스", "IT서비스"],
        "values": [0, 60_000, 30_000, 10_000, 40_000, 20_000],
    }


@pytest.fixture
def org_chart_structure() -> dict[str, Any]:
    """조직도 샘플 데이터."""
    return {
        "nodes": [
            {"id": "ceo", "label": "홍길동\nCEO", "level": 0},
            {"id": "cfo", "label": "김철수\nCFO", "level": 1},
            {"id": "cto", "label": "이영희\nCTO", "level": 1},
            {"id": "dev", "label": "개발팀", "level": 2},
        ],
        "edges": [
            {"from": "ceo", "to": "cfo"},
            {"from": "ceo", "to": "cto"},
            {"from": "cto", "to": "dev"},
        ],
    }


@pytest.fixture
def flow_steps() -> dict[str, Any]:
    """플로우 다이어그램 샘플 데이터."""
    return {
        "nodes": [
            {"id": "start", "label": "인수 의향서", "type": "start"},
            {"id": "dd", "label": "실사 진행", "type": "process"},
            {"id": "nego", "label": "가격 협상", "type": "decision"},
            {"id": "close", "label": "계약 체결", "type": "end"},
        ],
        "edges": [
            {"from": "start", "to": "dd"},
            {"from": "dd", "to": "nego"},
            {"from": "nego", "to": "close", "label": "합의"},
        ],
    }


@pytest.fixture
def shareholding_data() -> dict[str, Any]:
    """주주구조 샘플 데이터."""
    return {
        "entities": [
            {"id": "founder", "label": "창업자", "type": "person", "level": 0},
            {"id": "holding", "label": "지주회사", "type": "company", "level": 0},
            {"id": "sub1", "label": "자회사A", "type": "company", "level": 1},
            {"id": "sub2", "label": "자회사B", "type": "company", "level": 1},
        ],
        "stakes": [
            {"from": "founder", "to": "holding", "pct": 51.0, "label": "51%"},
            {"from": "holding", "to": "sub1", "pct": 100.0, "label": "100%"},
            {"from": "holding", "to": "sub2", "pct": 70.0, "label": "70%"},
        ],
    }
