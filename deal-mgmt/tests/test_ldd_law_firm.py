"""LDD 법무법인 스타일 2단계 파이프라인 테스트.

Phase A~E 전 모듈의 핵심 동작을 검증:
- enum 확장 (LAW_FIRM)
- 매퍼 (DDRL 10 → 법무법인 8)
- 어댑터 (6블록 → 3단)
- 프롬프트 (A/B/C/D 라벨링)
- 파이프라인 설정 (law_firm_mode)
"""

import pytest

from app.models.enums import LDDReportType

# ── Phase A: enum + 모델 ──────────────────────────────────────────────────────


class TestLDDReportTypeEnum:
    """LDDReportType에 LAW_FIRM 값이 추가되었는지 검증."""

    def test_law_firm_exists(self):
        assert hasattr(LDDReportType, "LAW_FIRM")
        assert LDDReportType.LAW_FIRM == "LAW_FIRM"

    def test_existing_types_preserved(self):
        assert LDDReportType.FULL == "FULL"
        assert LDDReportType.REDFLAG == "REDFLAG"


# ── Phase B: 빈 템플릿 생성기 ─────────────────────────────────────────────────


class TestLawFirmTemplateGenerator:
    """LawFirmTemplateGenerator의 XML 유틸리티 함수 검증."""

    def test_import(self):
        from app.ralph.generators.ldd.law_firm_template import LawFirmTemplateGenerator

        assert LawFirmTemplateGenerator is not None

    def test_constants(self):
        from app.ralph.generators.ldd.law_firm_template import (
            PRESERVE_STYLES,
            RECOMMENDATION_FILL,
            SECTION_BAR_FILLS,
            SECTION_PLACEHOLDERS,
        )

        assert "26382A" in SECTION_BAR_FILLS
        assert "385623" in SECTION_BAR_FILLS
        assert RECOMMENDATION_FILL == "E2EFD9"
        assert {"11", "22", "31", "40"} == PRESERVE_STYLES
        assert 0 in SECTION_PLACEHOLDERS
        assert 1 in SECTION_PLACEHOLDERS
        assert 2 in SECTION_PLACEHOLDERS

    def test_source_not_found(self):
        from app.ralph.generators.ldd.law_firm_template import LawFirmTemplateGenerator

        with pytest.raises(FileNotFoundError):
            LawFirmTemplateGenerator("/nonexistent/path.docx")


# ── Phase C-1: 매퍼 ──────────────────────────────────────────────────────────


class TestLawFirmMapper:
    """DDRL 10개 섹션 → 법무법인 8개 목차 매핑 검증."""

    def test_import(self):
        from app.ralph.generators.ldd.law_firm_mapper import LawFirmChapter, LawFirmMapper

        assert LawFirmMapper is not None
        assert LawFirmChapter is not None

    def test_empty_sections(self):
        from app.ralph.generators.ldd.law_firm_mapper import LawFirmMapper

        mapper = LawFirmMapper()
        chapters = mapper.map_sections({})
        assert len(chapters) == 8
        assert chapters[0].number == "I"
        assert chapters[0].title == "대상사업 일반 및 거래구조"
        assert chapters[7].number == "VIII"
        assert chapters[7].title == "소송 및 분쟁"

    def test_governance_maps_to_chapter_I(self):
        from app.ralph.generators.ldd.law_firm_mapper import LawFirmMapper

        mapper = LawFirmMapper()
        section_results = {
            "GOVERNANCE": [
                {"item_id": "GOV-01", "name": "회사 일반", "status": "OK"},
            ],
            "CAPITAL": [
                {"item_id": "CAP-01", "name": "자본구조", "status": "ISSUE", "issue_level": "HIGH"},
            ],
        }
        chapters = mapper.map_sections(section_results)
        ch_I = chapters[0]
        assert ch_I.number == "I"
        assert len(ch_I.items) == 2
        assert ch_I.items[0]["item_id"] == "GOV-01"
        assert ch_I.items[1]["item_id"] == "CAP-01"

    def test_real_estate_split_IV_V(self):
        """REAL_ESTATE RE-01~03 → IV, RE-04~05 → V 분할 검증."""
        from app.ralph.generators.ldd.law_firm_mapper import LawFirmMapper

        mapper = LawFirmMapper()
        section_results = {
            "REAL_ESTATE": [
                {"item_id": "RE-01", "name": "부동산 소유권", "status": "OK"},
                {"item_id": "RE-03", "name": "담보권", "status": "ISSUE", "issue_level": "MEDIUM"},
                {"item_id": "RE-04", "name": "환경오염", "status": "ISSUE", "issue_level": "HIGH"},
                {"item_id": "RE-05", "name": "환경인허가", "status": "PENDING"},
            ],
        }
        chapters = mapper.map_sections(section_results)
        ch_IV = chapters[3]  # IV. 부동산 및 자산
        ch_V = chapters[4]  # V. 환경
        assert ch_IV.number == "IV"
        assert len(ch_IV.items) == 2
        assert all(
            not it["item_id"].startswith("RE-04") and not it["item_id"].startswith("RE-05") for it in ch_IV.items
        )
        assert ch_V.number == "V"
        assert len(ch_V.items) == 2
        assert all(it["item_id"].startswith("RE-04") or it["item_id"].startswith("RE-05") for it in ch_V.items)

    def test_litigation_maps_to_chapter_VIII(self):
        from app.ralph.generators.ldd.law_firm_mapper import LawFirmMapper

        mapper = LawFirmMapper()
        section_results = {
            "LITIGATION": [
                {"item_id": "LIT-01", "name": "소송현황", "status": "ISSUE", "issue_level": "CRITICAL"},
            ],
        }
        chapters = mapper.map_sections(section_results)
        ch_VIII = chapters[7]
        assert len(ch_VIII.items) == 1
        assert ch_VIII.items[0]["item_id"] == "LIT-01"

    def test_build_toc_data(self):
        from app.ralph.generators.ldd.law_firm_mapper import LawFirmMapper

        mapper = LawFirmMapper()
        section_results = {
            "GOVERNANCE": [{"item_id": "GOV-01", "name": "회사 일반", "status": "OK"}],
        }
        chapters = mapper.map_sections(section_results)
        toc = mapper.build_toc_data(chapters)
        assert "chapters" in toc
        assert toc["total_chapters"] == 8
        assert toc["total_items"] == 1
        assert toc["chapters"][0]["item_count"] == 1


# ── Phase C-2: 프롬프트 ──────────────────────────────────────────────────────


class TestLawFirmPrompts:
    """법무법인 전용 프롬프트 상수 검증."""

    def test_certainty_labels_in_system_prompt(self):
        from app.ralph.generators.ldd.law_firm_prompts import LAW_FIRM_SYSTEM_PROMPT

        assert "(A)" in LAW_FIRM_SYSTEM_PROMPT
        assert "(B)" in LAW_FIRM_SYSTEM_PROMPT
        assert "(C)" in LAW_FIRM_SYSTEM_PROMPT
        assert "(D)" in LAW_FIRM_SYSTEM_PROMPT

    def test_hallucination_zero(self):
        from app.ralph.generators.ldd.law_firm_prompts import LAW_FIRM_SYSTEM_PROMPT

        assert "할루시네이션" in LAW_FIRM_SYSTEM_PROMPT or "hallucination" in LAW_FIRM_SYSTEM_PROMPT.lower()

    def test_narrative_prompt_has_3_sections(self):
        from app.ralph.generators.ldd.law_firm_prompts import LAW_FIRM_NARRATIVE_PROMPT

        assert "status_section" in LAW_FIRM_NARRATIVE_PROMPT
        assert "review_section" in LAW_FIRM_NARRATIVE_PROMPT
        assert "recommendation_section" in LAW_FIRM_NARRATIVE_PROMPT

    def test_exec_summary_prompt(self):
        from app.ralph.generators.ldd.law_firm_prompts import LAW_FIRM_EXEC_SUMMARY_PROMPT

        assert "summary_rows" in LAW_FIRM_EXEC_SUMMARY_PROMPT
        assert "overall_opinion" in LAW_FIRM_EXEC_SUMMARY_PROMPT

    def test_addendum_in_law_firm_prompts(self):
        from app.ralph.generators.ldd.law_firm_prompts import CERTAINTY_LABELING_ADDENDUM

        assert "(A)" in CERTAINTY_LABELING_ADDENDUM
        assert "(D)" in CERTAINTY_LABELING_ADDENDUM
        assert "IRL" in CERTAINTY_LABELING_ADDENDUM
        assert "할루시네이션" in CERTAINTY_LABELING_ADDENDUM


# ── Phase C-3: 어댑터 ────────────────────────────────────────────────────────


class TestLawFirmNarrativeAdapter:
    """6블록 → 3단 변환 어댑터 검증."""

    def test_convert_item_from_6blocks(self):
        from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter

        adapter = LawFirmNarrativeAdapter()

        narrative_dict = {
            "item_id": "GOV-01",
            "item_name": "회사 일반",
            "blocks": [
                {"block_type": "FACTS", "content": "사실 관계 서술"},
                {"block_type": "LEGAL_REVIEW", "content": "법률 검토"},
                {"block_type": "ANALYSIS", "content": "분석 결과"},
                {"block_type": "DEAL_IMPACT", "content": "거래 영향"},
                {"block_type": "PENALTY", "content": "위약 벌칙"},
                {"block_type": "RECOMMENDATION", "content": "권고사항"},
            ],
        }

        result = adapter.convert_item(narrative_dict, "I")
        assert result.item_id == "GOV-01"
        assert result.chapter_number == "I"
        assert "사실 관계 서술" in result.status_section
        assert "법률 검토" in result.review_section
        assert "분석 결과" in result.review_section
        assert "거래 영향" in result.review_section
        assert "위약 벌칙" in result.review_section
        assert "권고사항" in result.recommendation_section

    def test_convert_from_llm_response(self):
        from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter

        adapter = LawFirmNarrativeAdapter()

        llm_response = {
            "status_section": "현황 내용",
            "review_section": "검토 내용",
            "recommendation_section": "권고 내용",
            "irl_items": ["추가 확인 A", "추가 확인 B"],
            "cited_laws": ["상법 제374조"],
            "cited_documents": ["정관.pdf"],
        }

        result = adapter.convert_from_llm_response(
            llm_response,
            item_id="GOV-01",
            item_name="회사 일반",
            chapter_number="I",
        )
        assert result.status_section == "현황 내용"
        assert result.review_section == "검토 내용"
        assert result.recommendation_section == "권고 내용"
        assert len(result.irl_items) == 2
        assert "상법 제374조" in result.cited_laws

    def test_collect_irl_items(self):
        from app.ralph.generators.ldd.law_firm_narrative_adapter import (
            LawFirmNarrative,
            LawFirmNarrativeAdapter,
        )

        adapter = LawFirmNarrativeAdapter()

        narratives_by_chapter = {
            "I": [
                LawFirmNarrative(
                    item_id="GOV-01",
                    item_name="회사 일반",
                    irl_items=["정관 사본 요청"],
                ),
            ],
            "III": [
                LawFirmNarrative(
                    item_id="CON-01",
                    item_name="주요 계약",
                    irl_items=["계약서 원본 요청", "부속합의서 요청"],
                ),
            ],
        }

        irl_list = adapter.collect_irl_items(narratives_by_chapter)
        assert len(irl_list) == 3
        assert irl_list[0]["chapter"] == "I"
        assert irl_list[0]["request"] == "정관 사본 요청"
        assert irl_list[1]["chapter"] == "III"

    def test_to_dict(self):
        from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrative

        n = LawFirmNarrative(
            item_id="GOV-01",
            item_name="회사 일반",
            chapter_number="I",
            status_section="현황",
            review_section="검토",
            recommendation_section="권고",
        )
        d = n.to_dict()
        assert d["item_id"] == "GOV-01"
        assert d["chapter_number"] == "I"
        assert d["status_section"] == "현황"

    def test_convert_item_extracts_irl_from_d_labels(self):
        """6블록 텍스트의 (D) 라벨에서 IRL 항목을 추출하는지 검증."""
        from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter

        adapter = LawFirmNarrativeAdapter()

        narrative_dict = {
            "item_id": "RE-04",
            "item_name": "환경오염",
            "blocks": [
                {
                    "block_type": "FACTS",
                    "content": "환경영향평가 실시 여부 확인 불가 (D) → IRL: 환경영향평가서 사본 요청",
                },
                {
                    "block_type": "RECOMMENDATION",
                    "content": "토양오염 검사 필요 (D) → IRL: 토양오염조사보고서 요청",
                },
            ],
        }

        result = adapter.convert_item(narrative_dict, "V")
        assert len(result.irl_items) == 2
        assert "환경영향평가서 사본 요청" in result.irl_items
        assert "토양오염조사보고서 요청" in result.irl_items

    def test_convert_item_extracts_cited_laws(self):
        """6블록 텍스트에서 법률 인용을 추출하는지 검증."""
        from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter

        adapter = LawFirmNarrativeAdapter()

        narrative_dict = {
            "item_id": "GOV-01",
            "item_name": "회사 일반",
            "blocks": [
                {
                    "block_type": "LEGAL_REVIEW",
                    "content": "상법 제374조에 따라 이사회 특별결의가 필요하며, 독점규제법 제7조 위반 소지가 있다 (B)",
                },
            ],
        }

        result = adapter.convert_item(narrative_dict, "I")
        assert "상법 제374조" in result.cited_laws
        assert "독점규제법 제7조" in result.cited_laws

    def test_convert_item_extracts_cited_documents(self):
        """6블록 텍스트에서 출처 문서를 추출하는지 검증."""
        from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter

        adapter = LawFirmNarrativeAdapter()

        narrative_dict = {
            "item_id": "GOV-01",
            "item_name": "회사 일반",
            "blocks": [
                {
                    "block_type": "FACTS",
                    "content": "발행주식총수는 100,000주이다 (A) (출처: 정관.pdf, 제5조)",
                },
            ],
        }

        result = adapter.convert_item(narrative_dict, "I")
        assert "정관.pdf, 제5조" in result.cited_documents

    def test_convert_item_no_d_labels_returns_empty_irl(self):
        """(D) 라벨이 없으면 IRL은 빈 리스트."""
        from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter

        adapter = LawFirmNarrativeAdapter()

        narrative_dict = {
            "item_id": "GOV-01",
            "item_name": "회사 일반",
            "blocks": [
                {"block_type": "FACTS", "content": "이슈 없음 (A)"},
            ],
        }

        result = adapter.convert_item(narrative_dict, "I")
        assert result.irl_items == []


# ── Phase D: 렌더러 import 검증 ──────────────────────────────────────────────


class TestLawFirmRendererImport:
    """LawFirmDocxRenderer import 검증."""

    def test_import(self):
        from app.ralph.generators.ldd.law_firm_renderer import LawFirmDocxRenderer

        assert LawFirmDocxRenderer is not None

    def test_renderer_has_render_method(self):
        from app.ralph.generators.ldd.law_firm_renderer import LawFirmDocxRenderer

        renderer = LawFirmDocxRenderer()
        assert callable(getattr(renderer, "render", None))

    def test_no_dead_code_add_paragraph_after(self):
        """데드 코드 _add_paragraph_after가 제거되었는지 검증."""
        import app.ralph.generators.ldd.law_firm_renderer as mod

        assert not hasattr(mod, "_add_paragraph_after")


# ── Phase E: 파이프라인 설정 ──────────────────────────────────────────────────


class TestPipelineConfigLawFirmMode:
    """LDDPipelineConfig에 law_firm_mode 플래그 검증."""

    def test_default_false(self):
        from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig

        config = LDDPipelineConfig()
        assert config.law_firm_mode is False

    def test_explicit_true(self):
        from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig

        config = LDDPipelineConfig(law_firm_mode=True)
        assert config.law_firm_mode is True


# ── Phase E-2: 파이프라인 Stage 6 law_firm_mode 연동 ──────────────────────────


class TestPipelineStage6LawFirmMode:
    """pipeline.py Stage 6에서 law_firm_mode가 NarrativeGenerator에 전달되는지 검증."""

    def test_narrative_generator_accepts_system_prompt_override(self):
        from app.ralph.generators.ldd.law_firm_prompts import LAW_FIRM_SYSTEM_PROMPT
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator(system_prompt_override=LAW_FIRM_SYSTEM_PROMPT)
        assert gen._system_prompt_override == LAW_FIRM_SYSTEM_PROMPT
        assert "(A)" in gen._system_prompt_override
        assert "(D)" in gen._system_prompt_override

    def test_narrative_generator_default_no_override(self):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator()
        assert gen._system_prompt_override is None

    def test_law_firm_system_prompt_has_abcd_labels(self):
        from app.ralph.generators.ldd.law_firm_prompts import LAW_FIRM_SYSTEM_PROMPT

        assert "(A) 확인된 사실" in LAW_FIRM_SYSTEM_PROMPT
        assert "(B) 합리적 추론" in LAW_FIRM_SYSTEM_PROMPT
        assert "(C) 가정/조건부" in LAW_FIRM_SYSTEM_PROMPT
        assert "(D) 불확실/추가확인 필요" in LAW_FIRM_SYSTEM_PROMPT
        assert "할루시네이션 제로" in LAW_FIRM_SYSTEM_PROMPT
