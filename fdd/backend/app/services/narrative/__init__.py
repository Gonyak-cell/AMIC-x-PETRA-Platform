"""Narrative Engine 모듈.

FDD 분석 결과 기반 서술문 자동 생성 엔진.
"""

from app.services.narrative.engine import (
    NARRATIVE_VERSION,
    NarrativeTemplate,
    generate_debt_narrative,
    generate_executive_summary,
    generate_narrative,
    generate_nwc_narrative,
    generate_qoe_narrative,
    load_narrative_template,
)

__all__ = [
    "NARRATIVE_VERSION",
    "NarrativeTemplate",
    "generate_narrative",
    "generate_qoe_narrative",
    "generate_nwc_narrative",
    "generate_debt_narrative",
    "generate_executive_summary",
    "load_narrative_template",
]
