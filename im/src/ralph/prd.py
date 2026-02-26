"""IM 품질 PRD(Product Requirements Document) 정의.

각 IM 스타일(Full IM, Teaser/TM)에 대한 품질 수용 기준을 정의한다.
Ralph Loop 오케스트레이터가 이 PRD를 기반으로 품질 평가를 수행한다.
"""

from __future__ import annotations

from typing import Any

# ── IM Full PRD ──────────────────────────────────────────────────────────────

IM_FULL_PRD: dict[str, Any] = {
    "memo_type": "IM",
    "min_slides": 30,
    "max_slides": 80,
    "required_slides": ["Cover", "Disclaimer", "Table of Contents"],
    "required_sections": [
        "executive_summary",
        "company_overview",
        "financial_summary",
        "market_analysis",
        "management",
    ],
    "design_standards": {
        "font_heading": "SUITE",
        "font_body": "Pretendard",
        "color_primary": "#0F3A32",
        "color_secondary": "#1C8F57",
        "color_accent": "#26C260",
        "color_fresh": "#A3E96B",
        "color_light": "#E6FDD6",
    },
    "quality_dimensions": {
        "information_density": {
            "weight": 0.20,
            "description": "슬라이드당 정보량 적절성 — 과밀/과소 방지",
            "min_text_per_slide": 50,
            "max_text_per_slide": 500,
        },
        "visual_hierarchy": {
            "weight": 0.20,
            "description": "제목→본문→수치 시각적 위계 명확성",
        },
        "chart_effectiveness": {
            "weight": 0.20,
            "description": "데이터→인사이트 전달력, 차트 유형 적절성",
        },
        "slide_narrative_flow": {
            "weight": 0.15,
            "description": "슬라이드 간 스토리텔링 흐름",
        },
        "brand_consistency": {
            "weight": 0.10,
            "description": "AMIC 디자인 시스템 일관성",
        },
        "investor_readiness": {
            "weight": 0.15,
            "description": "투자자 대면 준비도 — IB 수준",
        },
    },
    "pass_threshold": 4.0,
    "max_iterations": 3,
    "budget_usd": 5.0,
}

# ── TM (Teaser Memorandum) PRD ───────────────────────────────────────────────

IM_TEASER_PRD: dict[str, Any] = {
    "memo_type": "TM",
    "min_slides": 15,
    "max_slides": 40,
    "required_slides": ["Cover", "Disclaimer"],
    "required_sections": [
        "executive_summary",
        "company_overview",
        "financial_summary",
    ],
    "design_standards": {
        "font_heading": "SUITE",
        "font_body": "Pretendard",
        "color_primary": "#0F3A32",
        "color_secondary": "#1C8F57",
        "color_accent": "#26C260",
        "color_fresh": "#A3E96B",
        "color_light": "#E6FDD6",
    },
    "quality_dimensions": {
        "information_density": {"weight": 0.15},
        "visual_hierarchy": {"weight": 0.20},
        "chart_effectiveness": {"weight": 0.20},
        "slide_narrative_flow": {"weight": 0.20},
        "brand_consistency": {"weight": 0.10},
        "investor_readiness": {"weight": 0.15},
    },
    "pass_threshold": 4.0,
    "max_iterations": 3,
    "budget_usd": 5.0,
}

# ── DM (Discussion Memorandum) PRD ────────────────────────────────────────────

IM_DM_PRD: dict[str, Any] = {
    "memo_type": "DM",
    "min_slides": 6,
    "max_slides": 15,
    "required_slides": ["Cover", "Disclaimer"],
    "required_sections": [
        "dm_deal_structure",
        "dm_investment_thesis",
        "dm_valuation",
    ],
    "design_standards": {
        "font_heading": "SUITE",
        "font_body": "Pretendard",
        "color_primary": "#0F3A32",
        "color_secondary": "#1C8F57",
        "color_accent": "#26C260",
        "color_fresh": "#A3E96B",
        "color_light": "#E6FDD6",
    },
    "quality_dimensions": {
        "information_density": {"weight": 0.25},
        "visual_hierarchy": {"weight": 0.15},
        "chart_effectiveness": {"weight": 0.25},
        "slide_narrative_flow": {"weight": 0.15},
        "brand_consistency": {"weight": 0.05},
        "investor_readiness": {"weight": 0.15},
    },
    "pass_threshold": 3.5,
    "max_iterations": 2,
    "budget_usd": 3.0,
}

# ── PRD 레지스트리 ───────────────────────────────────────────────────────────

_PRD_REGISTRY: dict[str, dict[str, Any]] = {
    "im_full": IM_FULL_PRD,
    "im_teaser": IM_TEASER_PRD,
    "im_dm": IM_DM_PRD,
}


def get_prd(doc_type: str) -> dict[str, Any]:
    """문서 유형에 맞는 PRD를 반환한다.

    Args:
        doc_type: "im_full", "im_teaser", 또는 "im_dm".

    Returns:
        PRD dict.

    Raises:
        ValueError: 알 수 없는 문서 유형.
    """
    prd = _PRD_REGISTRY.get(doc_type)
    if prd is None:
        raise ValueError(
            f"알 수 없는 IM PRD 유형: {doc_type!r}. "
            f"가능한 값: {list(_PRD_REGISTRY.keys())}"
        )
    return prd
