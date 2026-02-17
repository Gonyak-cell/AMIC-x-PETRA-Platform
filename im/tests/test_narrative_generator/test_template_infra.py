"""템플릿 슬롯 채우기 인프라 단위 테스트.

> 마지막 수정: 2026-02-17

TemplateLoader, TemplateRegistry, TemplateRenderer, SlotResponseParser,
SlotFillPromptBuilder의 핵심 로직을 외부 API 없이 테스트한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.engine.slot_parser import SlotResponseParser
from src.narrative_generator.prompts.slot_fill import SlotFillPromptBuilder
from src.narrative_generator.templates.loader import (
    BaseBlocks,
    ConditionalBlock,
    SectionTemplate,
    SlotDefinition,
    TemplateLoader,
)
from src.narrative_generator.templates.registry import TemplateRegistry
from src.narrative_generator.templates.renderer import TemplateRenderer

# ---------------------------------------------------------------------------
# 경로 상수 (실제 YAML 템플릿 디렉터리)
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "src" / "narrative_generator" / "templates"


# ===========================================================================
# TestSlotDefinition
# ===========================================================================


class TestSlotDefinition:
    """SlotDefinition 데이터클래스 프로퍼티 테스트."""

    def test_l2_slot_properties(self) -> None:
        slot = SlotDefinition(
            name="company_name",
            level="L2",
            source="company_name_kr",
        )
        assert slot.is_data_slot is True
        assert slot.is_llm_slot is False

    def test_l3_slot_properties(self) -> None:
        slot = SlotDefinition(
            name="company_intro",
            level="L3",
            hint="기업 소개",
            max_tokens=100,
            data_keys=("company_name_kr", "company_overview.business_model"),
        )
        assert slot.is_llm_slot is True
        assert slot.is_data_slot is False
        assert len(slot.data_keys) == 2

    def test_frozen_immutable(self) -> None:
        slot = SlotDefinition(name="test", level="L1")
        with pytest.raises(AttributeError):
            slot.name = "changed"  # type: ignore[misc]


# ===========================================================================
# TestTemplateLoader
# ===========================================================================


class TestTemplateLoader:
    """YAML 파일 로딩 테스트. 실제 templates/ 디렉터리 사용."""

    @pytest.fixture()
    def loader(self) -> TemplateLoader:
        return TemplateLoader(_TEMPLATE_DIR)

    def test_load_base_blocks(self, loader: TemplateLoader) -> None:
        base = loader.load_base()
        assert isinstance(base, BaseBlocks)
        assert len(base.blocks) > 0
        assert "disclaimer_short" in base.blocks
        assert "confidentiality" in base.blocks
        assert "transition_financial" in base.blocks

    def test_load_section_executive_summary(self, loader: TemplateLoader) -> None:
        tpl = loader.load_section("executive_summary")
        assert tpl is not None
        assert tpl.section_id == "executive_summary"
        assert tpl.version == "1.0"
        # L2 슬롯 확인
        assert "company_name" in tpl.slots
        assert tpl.slots["company_name"].level == "L2"
        # L3 슬롯 확인
        assert "company_intro" in tpl.slots
        assert tpl.slots["company_intro"].level == "L3"
        assert tpl.slots["company_intro"].max_tokens > 0
        # body에 슬롯 마커 존재
        assert "{{company_name}}" in tpl.body
        assert "{{company_intro}}" in tpl.body

    def test_load_section_contact_l2_only(self, loader: TemplateLoader) -> None:
        tpl = loader.load_section("contact")
        assert tpl is not None
        assert tpl.section_id == "contact"
        # contact은 L2 슬롯만 존재 (LLM 호출 불필요)
        assert len(tpl.l3_slots) == 0
        assert len(tpl.l2_slots) > 0
        # 베이스 블록 참조 확인
        assert "{{@confidentiality}}" in tpl.body

    def test_load_section_nonexistent(self, loader: TemplateLoader) -> None:
        tpl = loader.load_section("nonexistent_section")
        assert tpl is None

    def test_load_all_sections(self, loader: TemplateLoader) -> None:
        templates = loader.load_all_sections()
        assert len(templates) >= 2  # 최소 executive_summary, contact
        assert "executive_summary" in templates
        assert "contact" in templates

    def test_load_industry_override_tech(self, loader: TemplateLoader) -> None:
        override = loader.load_industry_override("financial_analysis", "tech")
        # tech/financial_analysis.yaml가 존재
        assert override is not None
        assert override.section_id == "financial_analysis"

    def test_load_industry_override_nonexistent(self, loader: TemplateLoader) -> None:
        override = loader.load_industry_override("contact", "tech")
        assert override is None

    def test_conditional_blocks_loaded(self, loader: TemplateLoader) -> None:
        tpl = loader.load_section("executive_summary")
        assert tpl is not None
        assert len(tpl.conditional_blocks) >= 1
        tech_cb = [cb for cb in tpl.conditional_blocks if "tech" in cb.condition]
        assert len(tech_cb) >= 1
        assert tech_cb[0].insert_after == "ebitda_comment"


# ===========================================================================
# TestTemplateRegistry
# ===========================================================================


class TestTemplateRegistry:
    """캐시, 산업별 병합 테스트."""

    @pytest.fixture()
    def registry(self) -> TemplateRegistry:
        return TemplateRegistry(_TEMPLATE_DIR)

    def test_has_section(self, registry: TemplateRegistry) -> None:
        assert registry.has("executive_summary") is True
        assert registry.has("contact") is True
        assert registry.has("nonexistent") is False

    def test_get_base_template(self, registry: TemplateRegistry) -> None:
        tpl = registry.get("executive_summary")
        assert tpl is not None
        assert tpl.section_id == "executive_summary"

    def test_get_with_industry_override(self, registry: TemplateRegistry) -> None:
        tpl_base = registry.get("financial_analysis")
        tpl_tech = registry.get("financial_analysis", industry="tech")
        assert tpl_base is not None
        assert tpl_tech is not None
        # tech 오버라이드에 추가 슬롯이 있어야 함
        assert len(tpl_tech.slots) >= len(tpl_base.slots)

    def test_get_without_override_returns_base(self, registry: TemplateRegistry) -> None:
        tpl = registry.get("contact", industry="tech")
        # contact에는 tech 오버라이드 없음 → 기본 반환
        assert tpl is not None
        assert tpl.section_id == "contact"

    def test_industry_cache(self, registry: TemplateRegistry) -> None:
        """같은 산업+섹션 조합 2번 호출 시 캐시 적중."""
        tpl1 = registry.get("financial_analysis", industry="tech")
        tpl2 = registry.get("financial_analysis", industry="tech")
        assert tpl1 is tpl2  # 같은 객체 (캐시)

    def test_base_blocks_property(self, registry: TemplateRegistry) -> None:
        base = registry.base_blocks
        assert isinstance(base, BaseBlocks)
        assert len(base.blocks) > 0

    def test_section_ids(self, registry: TemplateRegistry) -> None:
        ids = registry.section_ids
        assert "executive_summary" in ids
        assert "contact" in ids
        assert len(ids) >= 2

    def test_merge_templates(self) -> None:
        """_merge_templates 정적 메서드 직접 테스트."""
        base = SectionTemplate(
            section_id="test",
            body="기본 body",
            slots={
                "a": SlotDefinition(name="a", level="L2", source="x"),
                "b": SlotDefinition(name="b", level="L3", hint="기본 힌트"),
            },
            conditional_blocks=[
                ConditionalBlock(condition="industry == 'tech'", insert_after="a", text="기본 CB"),
            ],
        )
        override = SectionTemplate(
            section_id="test",
            body="오버라이드 body",
            slots={
                "b": SlotDefinition(name="b", level="L3", hint="오버라이드 힌트"),
                "c": SlotDefinition(name="c", level="L3", hint="신규 슬롯"),
            },
            conditional_blocks=[
                ConditionalBlock(condition="has_market_data", insert_after="b", text="추가 CB"),
            ],
        )
        merged = TemplateRegistry._merge_templates(base, override)
        # body는 오버라이드 우선
        assert merged.body == "오버라이드 body"
        # slots: 기본(a) + 오버라이드(b, c)
        assert "a" in merged.slots
        assert "b" in merged.slots
        assert "c" in merged.slots
        assert merged.slots["b"].hint == "오버라이드 힌트"
        # conditional_blocks: 누적
        assert len(merged.conditional_blocks) == 2


# ===========================================================================
# TestTemplateRenderer
# ===========================================================================


class TestTemplateRenderer:
    """L1/L2/L3/L4 렌더링 엔진 테스트."""

    @pytest.fixture()
    def renderer(self) -> TemplateRenderer:
        return TemplateRenderer()

    @pytest.fixture()
    def base_blocks(self) -> BaseBlocks:
        return BaseBlocks(blocks={
            "disclaimer_short": "면책조항 텍스트",
            "confidentiality": "비밀유지 텍스트",
        })

    def test_render_l2_only(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        """L2 슬롯만 있는 간단한 템플릿 렌더링."""
        template = SectionTemplate(
            section_id="test",
            body="기업명: {{company_name}}, 날짜: {{report_date}}",
            slots={
                "company_name": SlotDefinition(
                    name="company_name", level="L2", source="company_name_kr",
                ),
                "report_date": SlotDefinition(
                    name="report_date", level="L2", source="date", format_spec="date",
                ),
            },
        )
        result = renderer.render(template, sample_im_data)
        assert "테스트기업" in result
        assert "2026-02-10" in result

    def test_render_l3_with_llm_slots(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        """L3 슬롯이 LLM 결과로 치환되는지 확인."""
        template = SectionTemplate(
            section_id="test",
            body="소개: {{intro}}",
            slots={
                "intro": SlotDefinition(
                    name="intro", level="L3", hint="소개 텍스트",
                ),
            },
        )
        llm_slots = {"intro": "테스트기업은 B2B IT 서비스 기업입니다."}
        result = renderer.render(template, sample_im_data, llm_slots)
        assert "테스트기업은 B2B IT 서비스 기업입니다." in result

    def test_render_base_block_ref(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
        base_blocks: BaseBlocks,
    ) -> None:
        """{{@block_name}} 참조가 치환되는지 확인."""
        template = SectionTemplate(
            section_id="test",
            body="본문 내용\n\n{{@disclaimer_short}}",
            slots={},
        )
        result = renderer.render(
            template, sample_im_data, base_blocks=base_blocks,
        )
        assert "면책조항 텍스트" in result
        assert "{{@" not in result

    def test_render_l4_conditional_block_inserted(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        """L4 조건 일치 시 조건부 블록이 삽입되는지 확인."""
        template = SectionTemplate(
            section_id="test",
            body="분석: {{analysis}}",
            slots={
                "analysis": SlotDefinition(name="analysis", level="L3"),
            },
            conditional_blocks=[
                ConditionalBlock(
                    condition="industry == 'tech'",
                    insert_after="analysis",
                    text="SaaS 특화 분석 추가",
                ),
            ],
        )
        llm_slots = {"analysis": "재무 분석 결과"}
        result = renderer.render(
            template, sample_im_data, llm_slots, industry="tech",
        )
        assert "SaaS 특화 분석 추가" in result
        assert "재무 분석 결과" in result

    def test_render_l4_condition_not_matched(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        """L4 조건 불일치 시 조건부 블록이 삽입되지 않는지 확인."""
        template = SectionTemplate(
            section_id="test",
            body="분석: {{analysis}}",
            slots={
                "analysis": SlotDefinition(name="analysis", level="L3"),
            },
            conditional_blocks=[
                ConditionalBlock(
                    condition="industry == 'tech'",
                    insert_after="analysis",
                    text="SaaS 특화",
                ),
            ],
        )
        llm_slots = {"analysis": "재무 분석"}
        result = renderer.render(
            template, sample_im_data, llm_slots, industry="manufacturing",
        )
        assert "SaaS 특화" not in result

    def test_render_unresolved_slot_uses_default(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        """body에 정의되지 않은 슬롯(L2/L3 외)이 있을 때 default로 치환."""
        # L2/L3로 분류되지 않은 unknown 슬롯이 body에 있는 경우
        template = SectionTemplate(
            section_id="test",
            body="값: {{unknown_slot}}",
            slots={
                "unknown_slot": SlotDefinition(
                    name="unknown_slot", level="L1", default="[기본값]",
                ),
            },
        )
        result = renderer.render(template, sample_im_data)
        assert "[기본값]" in result
        assert "{{" not in result

    def test_render_l3_missing_from_llm_replaced_empty(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        """LLM이 L3 슬롯을 반환하지 않으면 빈 문자열로 치환."""
        template = SectionTemplate(
            section_id="test",
            body="소개: {{intro}}",
            slots={
                "intro": SlotDefinition(name="intro", level="L3", hint="소개"),
            },
        )
        # llm_slots에 intro가 없음
        result = renderer.render(template, sample_im_data, {})
        assert "{{intro}}" not in result

    def test_format_l2_currency(self) -> None:
        """L2 currency 포맷 테스트."""
        assert TemplateRenderer._format_l2_value(15_000_000_000, "currency") == "150억원"
        assert TemplateRenderer._format_l2_value(5_000_000, "currency") == "5백만원"
        assert TemplateRenderer._format_l2_value(50_000, "currency") == "50,000원"

    def test_format_l2_percent(self) -> None:
        assert TemplateRenderer._format_l2_value(0.225, "percent") == "22.5%"

    def test_format_l2_count(self) -> None:
        assert TemplateRenderer._format_l2_value(300, "count") == "300명"

    def test_format_l2_dict(self) -> None:
        """dict 데이터 포맷팅 (연도별 수치)."""
        value = {"2022": 100_000, "2023": 120_000, "2024": 150_000}
        result = TemplateRenderer._format_l2_value(value, "")
        assert "2022년" in result
        assert "2024년" in result

    def test_resolve_data_path_dotted(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        """dotted notation 데이터 경로 조회."""
        # 1단계
        assert renderer._resolve_data_path(sample_im_data, "company_name_kr") == "테스트기업"
        # 2단계 (중첩)
        model = renderer._resolve_data_path(sample_im_data, "company_overview.business_model")
        assert model == "B2B IT 서비스"
        # 리스트 인덱싱
        name = renderer._resolve_data_path(sample_im_data, "contacts.0.name")
        assert name == "홍길동"

    def test_resolve_data_path_none(
        self,
        renderer: TemplateRenderer,
        sample_im_data: IMDocumentData,
    ) -> None:
        assert renderer._resolve_data_path(sample_im_data, "nonexistent.field") is None
        assert renderer._resolve_data_path(sample_im_data, "") is None

    def test_evaluate_condition_industry_eq(self) -> None:
        """industry == 'tech' 조건 평가."""
        # sample_im_data is not needed for static method-like calls
        from unittest.mock import MagicMock
        mock_data = MagicMock(spec=IMDocumentData)
        assert TemplateRenderer._evaluate_condition("industry == 'tech'", "tech", mock_data) is True
        assert TemplateRenderer._evaluate_condition("industry == 'tech'", "healthcare", mock_data) is False

    def test_evaluate_condition_industry_ne(self) -> None:
        from unittest.mock import MagicMock
        mock_data = MagicMock(spec=IMDocumentData)
        assert TemplateRenderer._evaluate_condition("industry != 'general'", "tech", mock_data) is True
        assert TemplateRenderer._evaluate_condition("industry != 'general'", "general", mock_data) is False

    def test_evaluate_condition_has_flags(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """has_xxx 플래그 평가."""
        assert TemplateRenderer._evaluate_condition(
            "has_deal_structure", "", sample_im_data,
        ) is True
        assert TemplateRenderer._evaluate_condition(
            "has_market_data", "", sample_im_data,
        ) is True

    def test_normalize_whitespace(self) -> None:
        text = "줄1\n\n\n\n줄2  연속   공백\n줄3 \n"
        result = TemplateRenderer._normalize_whitespace(text)
        assert "\n\n\n" not in result
        assert "  " not in result

    def test_render_full_executive_summary(
        self,
        sample_im_data: IMDocumentData,
    ) -> None:
        """실제 executive_summary.yaml + 실제 데이터로 풀 렌더링."""
        registry = TemplateRegistry(_TEMPLATE_DIR)
        renderer = TemplateRenderer()

        tpl = registry.get("executive_summary")
        assert tpl is not None

        llm_slots = {
            "company_intro": "B2B IT 서비스 시장의 선도 기업으로, 2010년 설립 이래 지속 성장하였습니다.",
            "revenue_highlight": "2024년 매출 150,000원을 기록하며 연평균 22.5% 성장하였습니다.",
            "ebitda_comment": "EBITDA 마진은 23.3%로 업계 평균을 상회합니다.",
            "market_opportunity": "국내 IT 서비스 시장은 연 8% 성장이 예상되며, 클라우드 전환 수요가 핵심 동인입니다.",
            "investment_appeal": "안정적 재무 성과와 성장 잠재력을 겸비한 매력적인 투자 기회입니다.",
        }
        result = renderer.render(
            tpl, sample_im_data, llm_slots,
            industry="tech",
            base_blocks=registry.base_blocks,
        )
        # L2 치환 확인
        assert "테스트기업" in result
        # L3 치환 확인
        assert "B2B IT 서비스 시장의 선도 기업" in result
        assert "EBITDA 마진은 23.3%" in result
        # L4 조건부 블록 확인 (tech 산업)
        assert "SaaS" in result
        # 미해결 슬롯 없음
        assert "{{" not in result


# ===========================================================================
# TestSlotResponseParser
# ===========================================================================


class TestSlotResponseParser:
    """3단계 폴백 JSON 파싱 테스트."""

    @pytest.fixture()
    def parser(self) -> SlotResponseParser:
        return SlotResponseParser()

    def test_parse_standard_json(self, parser: SlotResponseParser) -> None:
        response = '{"company_intro": "테스트 소개", "revenue_highlight": "매출 150억원"}'
        result = parser.parse(response, ["company_intro", "revenue_highlight"])
        assert result["company_intro"] == "테스트 소개"
        assert result["revenue_highlight"] == "매출 150억원"

    def test_parse_json_code_block(self, parser: SlotResponseParser) -> None:
        response = (
            "다음은 슬롯 값입니다:\n"
            "```json\n"
            '{"intro": "기업 소개 텍스트"}\n'
            "```"
        )
        result = parser.parse(response, ["intro"])
        assert result["intro"] == "기업 소개 텍스트"

    def test_parse_regex_fallback(self, parser: SlotResponseParser) -> None:
        response = 'company_intro: "테스트 기업 소개"\nrevenue: "150억원"'
        result = parser.parse(response, ["company_intro", "revenue"])
        assert "company_intro" in result

    def test_parse_single_slot_fulltext_fallback(self, parser: SlotResponseParser) -> None:
        """단일 슬롯일 때 전체 응답을 매핑하는 폴백."""
        response = "테스트기업은 국내 IT 서비스 시장의 선도기업입니다."
        result = parser.parse(response, ["company_intro"])
        assert result["company_intro"] == response

    def test_parse_empty_response(self, parser: SlotResponseParser) -> None:
        assert parser.parse("", ["slot1"]) == {}

    def test_parse_empty_expected(self, parser: SlotResponseParser) -> None:
        assert parser.parse("some response", []) == {}

    def test_parse_partial_match(self, parser: SlotResponseParser) -> None:
        """기대 슬롯 중 일부만 응답에 포함된 경우."""
        response = '{"company_intro": "소개 텍스트"}'
        result = parser.parse(response, ["company_intro", "revenue_highlight"])
        assert "company_intro" in result
        assert "revenue_highlight" not in result

    def test_sanitize_list_value(self, parser: SlotResponseParser) -> None:
        response = '{"highlights": ["매출 성장", "시장 확대", "수익성 개선"]}'
        result = parser.parse(response, ["highlights"])
        assert "- 매출 성장" in result["highlights"]
        assert "- 시장 확대" in result["highlights"]

    def test_sanitize_strips_whitespace(self, parser: SlotResponseParser) -> None:
        response = '{"intro": "  여백 포함 텍스트  "}'
        result = parser.parse(response, ["intro"])
        assert result["intro"] == "여백 포함 텍스트"

    def test_parse_json_with_surrounding_text(self, parser: SlotResponseParser) -> None:
        """JSON 앞뒤에 불필요한 텍스트가 있는 경우."""
        response = (
            "네, 슬롯을 채우겠습니다.\n"
            '{"intro": "소개 텍스트"}\n'
            "완료했습니다."
        )
        result = parser.parse(response, ["intro"])
        assert result["intro"] == "소개 텍스트"


# ===========================================================================
# TestSlotFillPromptBuilder
# ===========================================================================


class TestSlotFillPromptBuilder:
    """슬롯 채우기 프롬프트 조립 테스트."""

    @pytest.fixture()
    def builder(self) -> SlotFillPromptBuilder:
        return SlotFillPromptBuilder()

    def test_build_system_prompt_default(self, builder: SlotFillPromptBuilder) -> None:
        prompt = builder.build_system_prompt()
        assert "JSON" in prompt
        assert "슬롯" in prompt
        assert "역할" in prompt

    def test_build_system_prompt_with_industry(self, builder: SlotFillPromptBuilder) -> None:
        prompt = builder.build_system_prompt(industry_context="SaaS 기업 특화")
        assert "SaaS 기업 특화" in prompt
        assert "산업 컨텍스트" in prompt

    def test_build_user_prompt_with_l3_slots(
        self,
        builder: SlotFillPromptBuilder,
        sample_im_data: IMDocumentData,
    ) -> None:
        """L3 슬롯이 있는 템플릿으로 유저 프롬프트 생성."""
        template = SectionTemplate(
            section_id="executive_summary",
            body="{{company_name}}은 {{company_intro}}",
            slots={
                "company_name": SlotDefinition(
                    name="company_name", level="L2", source="company_name_kr",
                ),
                "company_intro": SlotDefinition(
                    name="company_intro",
                    level="L3",
                    slot_type="paragraph",
                    hint="기업 소개 2-3문장",
                    max_tokens=100,
                    data_keys=("company_name_kr", "company_overview.business_model"),
                ),
            },
        )
        prompt = builder.build_user_prompt(template, sample_im_data)
        # 기업 정보
        assert "테스트기업" in prompt
        # 슬롯 정보
        assert "company_intro" in prompt
        assert "paragraph" in prompt
        assert "100" in prompt  # max_tokens
        assert "기업 소개" in prompt
        # JSON 형식 지시
        assert "JSON" in prompt

    def test_build_user_prompt_no_l3_returns_empty(
        self,
        builder: SlotFillPromptBuilder,
        sample_im_data: IMDocumentData,
    ) -> None:
        """L3 슬롯이 없으면 빈 문자열 반환."""
        template = SectionTemplate(
            section_id="contact",
            body="{{company_name}}",
            slots={
                "company_name": SlotDefinition(
                    name="company_name", level="L2", source="company_name_kr",
                ),
            },
        )
        prompt = builder.build_user_prompt(template, sample_im_data)
        assert prompt == ""

    def test_user_prompt_includes_data_values(
        self,
        builder: SlotFillPromptBuilder,
        sample_im_data: IMDocumentData,
    ) -> None:
        """data_keys에 해당하는 실제 데이터가 프롬프트에 포함되는지 확인."""
        template = SectionTemplate(
            section_id="test",
            body="{{revenue_highlight}}",
            slots={
                "revenue_highlight": SlotDefinition(
                    name="revenue_highlight",
                    level="L3",
                    hint="매출 하이라이트",
                    data_keys=("company_name_kr",),
                ),
            },
        )
        prompt = builder.build_user_prompt(template, sample_im_data)
        assert "테스트기업" in prompt
