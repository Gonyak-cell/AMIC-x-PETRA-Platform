"""NarrativeOrchestrator 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

LLM을 완전히 모킹하여 generate/generate_section/에러 처리를 테스트한다.
외부 API 호출(OpenAI, Pinecone) 없이 모든 테스트가 동작한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.config import NarrativeConfig
from src.narrative_generator.engine.orchestrator import (
    NarrativeOrchestrator,
    NarrativeResult,
)
from src.narrative_generator.engine.structured_output import SectionNarrative


# ---------------------------------------------------------------------------
# 헬퍼: Mock LLM 클라이언트
# ---------------------------------------------------------------------------


def _create_mock_llm_client(response_text: str = "") -> MagicMock:
    """chat.completions.create()를 모킹한 LLM 클라이언트를 생성한다.

    Args:
        response_text: LLM이 반환할 응답 텍스트.

    Returns:
        MagicMock으로 구성된 LLM 클라이언트.
    """
    mock_message = MagicMock()
    mock_message.content = response_text

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


def _create_failing_llm_client() -> MagicMock:
    """LLM 호출 시 예외를 발생시키는 모킹 클라이언트를 생성한다."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception(
        "API connection error"
    )
    return mock_client


# ---------------------------------------------------------------------------
# TestNarrativeOrchestrator
# ---------------------------------------------------------------------------


class TestNarrativeOrchestrator:
    """NarrativeOrchestrator 통합 파이프라인 테스트."""

    def test_generate_with_mock_llm(
        self, sample_im_data: IMDocumentData
    ) -> None:
        """모킹된 LLM으로 generate()가 NarrativeResult를 반환하는지 확인한다."""
        mock_response = (
            "테스트기업은 국내 IT 서비스 시장의 선도기업으로, "
            "최근 3개년 매출은 연평균 22.5% 성장하였습니다.\n\n"
            "2024년 매출 150,000억원, 영업이익률 18.7%를 기록하며 "
            "견조한 수익성을 유지하고 있습니다.\n\n"
            "안정적인 현금흐름과 탄탄한 재무구조를 바탕으로 "
            "지속 가능한 성장이 기대됩니다."
        )
        mock_client = _create_mock_llm_client(mock_response)

        config = NarrativeConfig(
            openai_api_key="sk-test-mock-key",
            pinecone_api_key="",
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
        )

        # 일부 섹션만 생성
        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary", "financial_analysis"],
        )

        assert isinstance(result, NarrativeResult)
        assert len(result.narratives) > 0
        # LLM이 호출되었는지 확인
        assert mock_client.chat.completions.create.call_count >= 1

    def test_generate_section_returns_section_narrative(
        self, sample_im_data: IMDocumentData
    ) -> None:
        """generate_section()이 SectionNarrative를 반환하는지 확인한다."""
        mock_response = (
            "테스트기업은 2024년 매출 150억원을 달성하였습니다.\n\n"
            "영업이익은 28억원으로 전년 대비 성장하였습니다."
        )
        mock_client = _create_mock_llm_client(mock_response)

        config = NarrativeConfig(
            openai_api_key="sk-test-mock-key",
            pinecone_api_key="",
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
        )

        result = orchestrator.generate_section(
            "executive_summary",
            sample_im_data,
        )

        assert isinstance(result, SectionNarrative)
        assert result.section_id == "executive_summary"
        assert len(result.text) > 0

    def test_graceful_degradation_when_llm_fails(
        self, sample_im_data: IMDocumentData
    ) -> None:
        """LLM 호출 실패 시 예외 없이 경고와 함께 결과를 반환하는지 확인한다."""
        mock_client = _create_failing_llm_client()

        config = NarrativeConfig(
            openai_api_key="sk-test-mock-key",
            pinecone_api_key="",
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
        )

        # generate()는 예외를 전파하지 않고 warnings에 기록
        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        assert isinstance(result, NarrativeResult)
        # 내러티브가 생성되지 않았으므로 비어있어야 함
        assert "executive_summary" not in result.narratives
        # 경고 메시지가 있어야 함
        assert len(result.warnings) >= 1
        assert any("executive_summary" in w for w in result.warnings)
