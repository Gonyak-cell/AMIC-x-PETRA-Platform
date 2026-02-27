"""레포트 QA 에이전트 테스트 — 2개 케이스.

모든 LLM 호출은 unittest.mock.patch로 모킹.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.report_qa import ReportQAAgent
from app.services.llm.routing.model_router import DEFAULT_FDD_ROUTING

# ── Test 1: 수치 불일치 탐지 ─────────────────────────────────────


def test_number_accuracy_detection():
    """parse_response가 수치 불일치 이슈를 올바르게 파싱해야 한다."""
    agent = ReportQAAgent()

    raw_response = json.dumps({
        "overall_score": 3,
        "issues": [
            {
                "severity": "major",
                "category": "number_accuracy",
                "location": "executive_summary.adjusted_ebitda",
                "description": "Adjusted EBITDA 15.2B in report vs 14.8B in source",
                "expected": "14,800,000,000",
                "found": "15,200,000,000",
            },
            {
                "severity": "minor",
                "category": "terminology",
                "location": "nwc_section.title",
                "description": "운전자본 → 순운전자본으로 수정 필요",
            },
        ],
        "passed_checks": ["cross_reference", "completeness"],
        "summary": "Adjusted EBITDA 수치 불일치 발견. 나머지 항목은 정상.",
    })

    result = agent.parse_response(raw_response)

    assert result["overall_score"] == 3
    assert len(result["issues"]) == 2
    assert result["issues"][0]["severity"] == "major"
    assert result["issues"][0]["category"] == "number_accuracy"
    assert "14.8B" in result["issues"][0]["description"] or "14,800" in result["issues"][0].get("expected", "")
    assert "cross_reference" in result["passed_checks"]
    assert "completeness" in result["passed_checks"]

    # validate_output 확인
    errors = agent.validate_output(result, {})
    assert errors == []  # 유효한 출력이므로 오류 없음


# ── Test 2: section_id="report_qa" → Gemini 라우팅 ────────────────


def test_uses_different_provider():
    """ReportQAAgent의 section_id가 'report_qa'이고, 라우팅 맵에서 Gemini로 매핑되어야 한다."""
    agent = ReportQAAgent()

    # section_id 확인
    assert agent.section_id == "report_qa"
    assert agent.agent_name == "report_qa"

    # 라우팅 맵에서 report_qa → gemini 확인
    assert "report_qa" in DEFAULT_FDD_ROUTING
    assert DEFAULT_FDD_ROUTING["report_qa"] == "gemini"

    # 분석(openai), 서술(anthropic)과 다른 프로바이더인지 확인
    qoe_provider = DEFAULT_FDD_ROUTING.get("qoe_adjustment_classification")
    narrative_provider = DEFAULT_FDD_ROUTING.get("executive_summary")
    qa_provider = DEFAULT_FDD_ROUTING["report_qa"]

    assert qa_provider != qoe_provider, "QA는 분석과 다른 프로바이더여야 함"
    assert qa_provider != narrative_provider, "QA는 서술과 다른 프로바이더여야 함"
