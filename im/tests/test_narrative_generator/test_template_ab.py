"""템플릿 vs 레거시 A/B 비교 테스트.

> 마지막 수정: 2026-02-17

template_enabled=True (슬롯 채우기) vs template_enabled=False (자유 생성)
동일 입력에 대해 두 방식 모두 정상 동작하며 결과를 비교한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock


from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.config import NarrativeConfig
from src.narrative_generator.engine.orchestrator import (
    NarrativeOrchestrator,
    NarrativeResult,
)
from src.narrative_generator.engine.structured_output import SectionNarrative
from src.narrative_generator.templates.registry import TemplateRegistry

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "src" / "narrative_generator" / "templates"


# ---------------------------------------------------------------------------
# 헬퍼: Mock LLM 클라이언트
# ---------------------------------------------------------------------------


def _create_mock_llm_client(response_text: str = "") -> MagicMock:
    """chat.completions.create()를 모킹한 LLM 클라이언트."""
    mock_message = MagicMock()
    mock_message.content = response_text

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


def _create_slot_fill_mock() -> MagicMock:
    """슬롯 채우기용 JSON 응답을 반환하는 Mock LLM."""
    slot_response = json.dumps({
        "company_intro": "테스트기업은 국내 B2B IT 서비스 시장의 선도기업으로, 2010년 설립 이래 지속적으로 성장하여 현재 300명의 임직원을 보유하고 있습니다.",
        "revenue_highlight": "2024년 매출 150,000원을 기록하며 연평균 22.5% 성장하였습니다.",
        "ebitda_comment": "EBITDA는 35,000원으로 마진 23.3%를 달성하며 수익성이 꾸준히 개선되고 있습니다.",
        "market_opportunity": "국내 IT 서비스 시장은 TAM 500,000원 규모로, 연 8.0% 성장이 예상됩니다.",
        "investment_appeal": "견조한 재무 성과, 확장 가능한 사업 모델, 유리한 시장 환경을 갖춘 매력적인 투자 기회입니다.",
    }, ensure_ascii=False)
    return _create_mock_llm_client(slot_response)


def _create_legacy_mock() -> MagicMock:
    """레거시 자유 생성용 응답을 반환하는 Mock LLM."""
    legacy_response = (
        "테스트기업은 국내 IT 서비스 시장의 선도기업으로, "
        "최근 3개년 매출은 연평균 22.5% 성장하였습니다.\n\n"
        "2024년 매출 150,000원, 영업이익률 18.7%를 기록하며 "
        "견조한 수익성을 유지하고 있습니다.\n\n"
        "안정적인 현금흐름과 탄탄한 재무구조를 바탕으로 "
        "지속 가능한 성장이 기대됩니다."
    )
    return _create_mock_llm_client(legacy_response)


# ===========================================================================
# TestTemplateEnabled — template_enabled=True 동작 검증
# ===========================================================================


class TestTemplateEnabled:
    """template_enabled=True일 때 슬롯 채우기 방식 동작 검증."""

    def test_orchestrator_uses_template_mode(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """템플릿 모드에서 NarrativeResult를 정상 반환하는지 확인."""
        mock_client = _create_slot_fill_mock()
        registry = TemplateRegistry(_TEMPLATE_DIR)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
            template_dir=str(_TEMPLATE_DIR),
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
            template_registry=registry,
        )

        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        assert isinstance(result, NarrativeResult)
        assert "executive_summary" in result.narratives
        text = result.narratives["executive_summary"]
        # 템플릿 모드: 부동문자가 포함되어야 함
        assert "대상회사" in text
        assert "사업 모델의 견고함" in text  # L1 부동문자
        # LLM 슬롯 채워짐
        assert "테스트기업" in text  # L2 치환
        # metadata에 template 모드 표시
        sn = result.section_narratives["executive_summary"]
        assert sn.metadata.get("mode") == "template"

    def test_template_mode_contact_no_llm_call(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """contact 섹션은 L2만 있으므로 LLM 호출 없이 렌더링."""
        mock_client = _create_mock_llm_client("")
        registry = TemplateRegistry(_TEMPLATE_DIR)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
            template_registry=registry,
        )

        result = orchestrator.generate_section(
            "contact",
            sample_im_data,
        )

        assert isinstance(result, SectionNarrative)
        assert result.section_id == "contact"
        # L2 치환: 담당자 이름
        assert "홍길동" in result.text
        assert "Managing Director" in result.text
        # contact은 L3 슬롯 없으므로 LLM 호출 0번
        assert mock_client.chat.completions.create.call_count == 0

    def test_template_mode_with_industry(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """산업별 오버라이드가 적용되는지 확인 (tech)."""
        mock_client = _create_slot_fill_mock()
        registry = TemplateRegistry(_TEMPLATE_DIR)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
            template_registry=registry,
        )

        result = orchestrator.generate(
            sample_im_data,
            industry="tech",
            sections=["executive_summary"],
        )

        text = result.narratives.get("executive_summary", "")
        # tech 조건부 블록: SaaS 관련 문구가 포함되어야 함
        assert "SaaS" in text


# ===========================================================================
# TestLegacyMode — template_enabled=False 동작 검증
# ===========================================================================


class TestLegacyMode:
    """template_enabled=False (기본값)일 때 기존 방식 동작 검증."""

    def test_legacy_mode_generates_normally(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """레거시 모드에서 NarrativeResult를 정상 반환하는지 확인."""
        mock_client = _create_legacy_mock()

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=False,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
        )

        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        assert isinstance(result, NarrativeResult)
        assert "executive_summary" in result.narratives
        text = result.narratives["executive_summary"]
        # 레거시 모드: LLM이 자유 생성한 텍스트
        assert "테스트기업" in text

    def test_legacy_regression_no_template(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """template_enabled=False일 때 기존 테스트와 동일하게 동작하는지 회귀 테스트."""
        mock_response = "테스트 레거시 응답"
        mock_client = _create_mock_llm_client(mock_response)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=False,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
        )

        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        assert isinstance(result, NarrativeResult)
        # LLM이 호출되었는지 확인
        assert mock_client.chat.completions.create.call_count >= 1


# ===========================================================================
# TestABComparison — 동일 입력, 두 모드 비교
# ===========================================================================


class TestABComparison:
    """template vs legacy 결과 비교."""

    def test_both_modes_produce_output(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """동일 입력에 대해 두 모드 모두 비어있지 않은 결과를 반환."""
        # --- Template 모드 ---
        template_mock = _create_slot_fill_mock()
        registry = TemplateRegistry(_TEMPLATE_DIR)

        template_config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
        )
        template_orchestrator = NarrativeOrchestrator(
            config=template_config,
            llm_client=template_mock,
            template_registry=registry,
        )
        template_result = template_orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        # --- Legacy 모드 ---
        legacy_mock = _create_legacy_mock()

        legacy_config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=False,
        )
        legacy_orchestrator = NarrativeOrchestrator(
            config=legacy_config,
            llm_client=legacy_mock,
        )
        legacy_result = legacy_orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        # 두 모드 모두 결과 존재
        assert "executive_summary" in template_result.narratives
        assert "executive_summary" in legacy_result.narratives

        template_text = template_result.narratives["executive_summary"]
        legacy_text = legacy_result.narratives["executive_summary"]

        # 두 결과 모두 비어있지 않음
        assert len(template_text) > 0
        assert len(legacy_text) > 0

    def test_template_mode_has_boilerplate(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """템플릿 모드에서 부동문자(고정 텍스트)가 포함되는지 확인."""
        mock_client = _create_slot_fill_mock()
        registry = TemplateRegistry(_TEMPLATE_DIR)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
            template_registry=registry,
        )

        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )
        text = result.narratives["executive_summary"]

        # 부동문자가 일관되게 포함
        assert "이하 \"대상회사\"" in text
        assert "사업 모델의 견고함을 입증" in text
        assert "유의미한 성장 기회를 제공" in text
        assert "매력적인 수익 창출 기회" in text

    def test_template_mode_metadata(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """템플릿 모드에서 metadata에 mode=template이 기록되는지 확인."""
        mock_client = _create_slot_fill_mock()
        registry = TemplateRegistry(_TEMPLATE_DIR)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
            template_registry=registry,
        )

        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        sn = result.section_narratives["executive_summary"]
        assert sn.metadata["mode"] == "template"
        assert sn.metadata["l3_slots_filled"] >= 1

    def test_multi_section_mixed_mode(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """여러 섹션 생성 시 템플릿/레거시 혼합 동작."""
        # 슬롯 채우기 응답과 자유 생성 응답을 번갈아 반환
        slot_response = json.dumps({
            "company_intro": "소개",
            "revenue_highlight": "매출 하이라이트",
            "ebitda_comment": "EBITDA 코멘트",
            "market_opportunity": "시장 기회",
            "investment_appeal": "투자 매력",
        }, ensure_ascii=False)

        mock_client = _create_mock_llm_client(slot_response)
        registry = TemplateRegistry(_TEMPLATE_DIR)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
            template_registry=registry,
        )

        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary", "contact"],
        )

        # executive_summary: 템플릿 모드 (L3 슬롯 → LLM 호출)
        assert "executive_summary" in result.narratives
        es = result.section_narratives["executive_summary"]
        assert es.metadata.get("mode") == "template"

        # contact: 템플릿 모드 (L2만 → LLM 호출 없음)
        assert "contact" in result.narratives
        ct = result.section_narratives["contact"]
        assert ct.metadata.get("mode") == "template"
        assert ct.metadata.get("l3_slots_filled") == 0

    def test_graceful_degradation_on_slot_parse_failure(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """슬롯 파싱 실패 시 빈 텍스트가 아닌 부동문자만이라도 반환."""
        # JSON이 아닌 응답
        mock_client = _create_mock_llm_client("이것은 JSON이 아닙니다.")
        registry = TemplateRegistry(_TEMPLATE_DIR)

        config = NarrativeConfig(
            openai_api_key="sk-test",
            pinecone_api_key="",
            template_enabled=True,
        )
        orchestrator = NarrativeOrchestrator(
            config=config,
            llm_client=mock_client,
            template_registry=registry,
        )

        result = orchestrator.generate(
            sample_im_data,
            sections=["executive_summary"],
        )

        # 슬롯 파싱 실패해도 부동문자는 남아있어야 함
        assert "executive_summary" in result.narratives
        text = result.narratives["executive_summary"]
        assert len(text) > 0
        # L1 부동문자가 포함
        assert "대상회사" in text
