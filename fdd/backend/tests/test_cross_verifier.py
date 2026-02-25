"""교차검증 에이전트 테스트 — 7개 케이스.

모든 LLM 호출은 unittest.mock.patch로 모킹.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.agents.base import AgentResponse
from app.agents.cross_verifier import (
    CrossVerificationAgent,
    CrossVerificationResult,
    DisagreementLevel,
    ReviewMode,
)
from app.services.llm.client import LLMProvider, LLMResponse


# ── 공통 헬퍼 ──────────────────────────────────────────────────────


def _make_writer_result(items: list[dict]) -> AgentResponse:
    """Writer AgentResponse를 생성한다."""
    return AgentResponse(
        success=True,
        result={"analysis_results": items},
        raw_output="",
    )


def _make_reviewer_client(response_items: list[dict]) -> MagicMock:
    """Reviewer LLMClient 모킹 객체를 생성한다."""
    client = MagicMock()
    client.is_available.return_value = True
    client.chat.return_value = LLMResponse(
        content=json.dumps({"analysis_results": response_items}),
        model="mock-model",
        provider=LLMProvider.ANTHROPIC,
        token_usage={"input_tokens": 1000, "output_tokens": 500},
    )
    return client


def _make_source_data(entries: list[dict] | None = None) -> dict:
    """원본 소스 데이터를 생성한다."""
    return {"gl_entries": entries or []}


def _make_context() -> dict:
    """기본 컨텍스트를 생성한다."""
    return {
        "deal_name": "Test Deal",
        "gl_entries": [
            {"entry_id": "GL-001", "amount": 100000},
            {"entry_id": "GL-002", "amount": 200000},
        ],
    }


# ── Test 1: BLIND 모드에서 Writer 결과가 프롬프트에 포함되지 않음 ──────


def test_blind_mode_independent():
    """BLIND 프롬프트에는 Writer 결과가 포함되지 않아야 한다."""
    writer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "NON_RECURRING",
            "rationale": "One-time legal fee",
            "amount": 100000,
        },
    ]
    reviewer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "NON_RECURRING",
            "rationale": "Exceptional legal cost",
            "amount": 100000,
        },
    ]

    reviewer_client = _make_reviewer_client(reviewer_items)
    agent = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client,
        review_mode=ReviewMode.BLIND,
        analysis_type="qoe",
    )

    writer_result = _make_writer_result(writer_items)
    context = _make_context()
    source_data = _make_source_data()

    agent.run_cross_verification(writer_result, source_data, context)

    # Reviewer client.chat가 호출되었는지 확인
    assert reviewer_client.chat.called

    # 호출된 프롬프트를 확인
    call_kwargs = reviewer_client.chat.call_args
    user_prompt = call_kwargs.kwargs.get("user_prompt", "") or call_kwargs[1].get("user_prompt", "")
    if not user_prompt:
        # positional args fallback
        user_prompt = str(call_kwargs)

    system_prompt = call_kwargs.kwargs.get("system_prompt", "") or call_kwargs[1].get("system_prompt", "")

    # BLIND 모드: "Junior Analyst" 키워드가 없어야 함
    assert "Junior Analyst" not in system_prompt
    assert "independent" in system_prompt.lower()

    # Writer 결과 (assessment 값)가 user_prompt에 포함되지 않아야 함
    # (BLIND 모드에서는 Writer의 classification을 보지 않음)
    assert "Junior Analyst's Classification" not in user_prompt


# ── Test 2: QoE assessment 불일치 탐지 (NON_RECURRING ↔ OPERATING → MAJOR) ──


def test_assessment_mismatch_detected():
    """NON_RECURRING ↔ OPERATING 불일치는 MAJOR로 판정되어야 한다."""
    writer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "NON_RECURRING",
            "rationale": "One-time consulting fee",
            "amount": 500000,
        },
    ]
    reviewer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "OPERATING",
            "rationale": "Regular consulting expense",
            "amount": 500000,
        },
    ]

    reviewer_client = _make_reviewer_client(reviewer_items)
    agent = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client,
        review_mode=ReviewMode.BLIND,
        analysis_type="qoe",
    )

    result = agent.run_cross_verification(
        _make_writer_result(writer_items),
        _make_source_data(),
        _make_context(),
    )

    assert isinstance(result, CrossVerificationResult)
    assert len(result.disagreements) >= 1

    assessment_disagreement = next(
        (d for d in result.disagreements if d.field == "assessment"), None,
    )
    assert assessment_disagreement is not None
    assert assessment_disagreement.level == DisagreementLevel.MAJOR
    assert assessment_disagreement.writer_value == "NON_RECURRING"
    assert assessment_disagreement.reviewer_value == "OPERATING"


# ── Test 3: 금액 분산 임계값 (5% → MODERATE, 15%+ → MAJOR) ──────


def test_amount_variance_thresholds():
    """금액 분산이 5%+ → MODERATE, 15%+ → MAJOR로 판정되어야 한다."""
    # Case A: 7% 차이 → MODERATE
    writer_items_a = [
        {"entry_id": "GL-A", "assessment": "NON_RECURRING", "amount": 100000, "rationale": ""},
    ]
    reviewer_items_a = [
        {"entry_id": "GL-A", "assessment": "NON_RECURRING", "amount": 107000, "rationale": ""},
    ]

    reviewer_client_a = _make_reviewer_client(reviewer_items_a)
    agent_a = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client_a,
        analysis_type="qoe",
    )
    result_a = agent_a.run_cross_verification(
        _make_writer_result(writer_items_a), _make_source_data(), _make_context(),
    )

    amount_d_a = next(
        (d for d in result_a.disagreements if d.field == "amount"), None,
    )
    assert amount_d_a is not None
    assert amount_d_a.level == DisagreementLevel.MODERATE

    # Case B: 20% 차이 → MAJOR
    writer_items_b = [
        {"entry_id": "GL-B", "assessment": "NON_RECURRING", "amount": 100000, "rationale": ""},
    ]
    reviewer_items_b = [
        {"entry_id": "GL-B", "assessment": "NON_RECURRING", "amount": 120000, "rationale": ""},
    ]

    reviewer_client_b = _make_reviewer_client(reviewer_items_b)
    agent_b = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client_b,
        analysis_type="qoe",
    )
    result_b = agent_b.run_cross_verification(
        _make_writer_result(writer_items_b), _make_source_data(), _make_context(),
    )

    amount_d_b = next(
        (d for d in result_b.disagreements if d.field == "amount"), None,
    )
    assert amount_d_b is not None
    assert amount_d_b.level == DisagreementLevel.MAJOR


# ── Test 4: UNCLEAR vs 명확 → 자동 해결 ──────────────────────────


def test_auto_resolve_unclear():
    """한쪽이 UNCLEAR이고 다른 쪽이 명확하면 자동 해결되어야 한다."""
    writer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "UNCLEAR",
            "rationale": "Cannot determine without more info",
            "amount": 100000,
        },
    ]
    reviewer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "NON_RECURRING",
            "rationale": "Clear one-time legal settlement",
            "amount": 100000,
        },
    ]

    reviewer_client = _make_reviewer_client(reviewer_items)
    agent = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client,
        analysis_type="qoe",
    )

    result = agent.run_cross_verification(
        _make_writer_result(writer_items),
        _make_source_data(),
        _make_context(),
    )

    assert len(result.disagreements) >= 1
    assessment_d = next(
        (d for d in result.disagreements if d.field == "assessment"), None,
    )
    assert assessment_d is not None
    assert assessment_d.resolved is True
    assert "Reviewer" in assessment_d.resolution
    assert result.auto_resolved >= 1


# ── Test 5: Reviewer만 발견한 항목 포함 확인 ─────────────────────


def test_reviewer_only_items():
    """Reviewer만 발견한 항목이 reviewer_only_items에 포함되어야 한다."""
    writer_items = [
        {"entry_id": "GL-001", "assessment": "NON_RECURRING", "amount": 100000, "rationale": ""},
    ]
    reviewer_items = [
        {"entry_id": "GL-001", "assessment": "NON_RECURRING", "amount": 100000, "rationale": ""},
        {"entry_id": "GL-002", "assessment": "OPERATING", "amount": 50000, "rationale": "Missed by writer"},
    ]

    reviewer_client = _make_reviewer_client(reviewer_items)
    agent = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client,
        analysis_type="qoe",
    )

    result = agent.run_cross_verification(
        _make_writer_result(writer_items),
        _make_source_data(),
        _make_context(),
    )

    assert len(result.reviewer_only_items) == 1
    assert result.reviewer_only_items[0]["entry_id"] == "GL-002"


# ── Test 6: Reviewer 사용 불가 시 graceful skip ──────────────────


def test_fallback_provider():
    """Reviewer LLM 호출이 실패하면 graceful하게 건너뛰어야 한다."""
    writer_items = [
        {"entry_id": "GL-001", "assessment": "NON_RECURRING", "amount": 100000, "rationale": ""},
    ]

    # Reviewer가 예외를 던지도록 설정
    reviewer_client = MagicMock()
    reviewer_client.is_available.return_value = True
    reviewer_client.chat.side_effect = RuntimeError("API connection failed")

    agent = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client,
        analysis_type="qoe",
    )

    result = agent.run_cross_verification(
        _make_writer_result(writer_items),
        _make_source_data(),
        _make_context(),
    )

    # 파이프라인이 중단되지 않아야 함
    assert isinstance(result, CrossVerificationResult)
    assert result.total_items == 1
    assert result.agreed_items == 0
    assert result.agreement_rate == Decimal("0")


# ── Test 7: max_cost_usd 초과 시 skip ───────────────────────────


def test_cost_limit():
    """누적 비용이 max_cost_usd를 초과하면 교차검증을 건너뛰어야 한다."""
    writer_items = [
        {"entry_id": "GL-001", "assessment": "NON_RECURRING", "amount": 100000, "rationale": ""},
    ]

    reviewer_client = _make_reviewer_client([])
    agent = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client,
        analysis_type="qoe",
        max_cost_usd=Decimal("0.001"),  # 매우 낮은 한도
    )

    # 비용을 인위적으로 한도 이상으로 설정
    agent._accumulated_cost = Decimal("0.002")

    result = agent.run_cross_verification(
        _make_writer_result(writer_items),
        _make_source_data(),
        _make_context(),
    )

    # Reviewer가 호출되지 않아야 함
    assert not reviewer_client.chat.called
    assert result.total_items == 1
    assert result.agreed_items == 0


# ── Test 8: confidence 차이 0.4+ → 자동 해결 (규칙 3) ──────────────


def test_auto_resolve_confidence_gap():
    """confidence 차이가 0.4 이상이면 높은 쪽이 채택되어야 한다."""
    writer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "NON_RECURRING",
            "rationale": "Likely one-time",
            "amount": 100000,
            "confidence": 0.3,
        },
    ]
    reviewer_items = [
        {
            "entry_id": "GL-001",
            "assessment": "OPERATING",
            "rationale": "Recurring consulting cost",
            "amount": 100000,
            "confidence": 0.9,
        },
    ]

    reviewer_client = _make_reviewer_client(reviewer_items)
    agent = CrossVerificationAgent(
        writer_provider="openai",
        reviewer_provider="anthropic",
        reviewer_client=reviewer_client,
        review_mode=ReviewMode.BLIND,
        analysis_type="qoe",
    )

    result = agent.run_cross_verification(
        _make_writer_result(writer_items),
        _make_source_data(),
        _make_context(),
    )

    assert len(result.disagreements) >= 1
    assessment_d = next(
        (d for d in result.disagreements if d.field == "assessment"), None,
    )
    assert assessment_d is not None
    assert assessment_d.resolved is True
    assert "Reviewer" in assessment_d.resolution
    assert result.auto_resolved >= 1
