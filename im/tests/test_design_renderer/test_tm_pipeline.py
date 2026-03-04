"""TM (Teaser Memorandum) 파이프라인 테스트.

- IMDocumentData(im_style=IMStyle.TEASER) 생성 → sections == TEASER_SECTIONS 검증
- TM 렌더러 8개 단위 테스트 (최소 데이터 + 전체 데이터)
- IMPipeline 통합 테스트 → 17슬라이드 이상 생성 확인
- 기존 IM/DM 회귀 테스트 → 기존 스타일 출력 불변
"""

import pytest
from pptx import Presentation

from src.design_renderer.design_tokens import DEFAULT_TOKENS
from src.design_renderer.im_document import (
    TEASER_SECTIONS,
    TEASER_SECTION_IDS,
    DM_SECTIONS,
    IMDocumentData,
    IMStyle,
    CompanyOverview,
    DealStructure,
    FinancialStatements,
    MarketData,
    TransactionType,
)
from src.design_renderer.pipeline import IMPipeline
from src.design_renderer.pptx_engine.slide_factory import SlideFactory
from src.design_renderer.pptx_engine.template_manager import TemplateManager
from src.design_renderer.section_renderers import RENDERER_REGISTRY, get_renderer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager() -> TemplateManager:
    return TemplateManager(tokens=DEFAULT_TOKENS)


@pytest.fixture
def prs(manager: TemplateManager) -> Presentation:
    return manager.new_presentation()


@pytest.fixture
def factory(manager: TemplateManager, prs: Presentation) -> SlideFactory:
    return SlideFactory(manager, prs=prs, tokens=DEFAULT_TOKENS)


@pytest.fixture
def minimal_tm_data() -> IMDocumentData:
    """최소 데이터로 TM 생성."""
    return IMDocumentData(
        project_name="Test TM",
        company_name_kr="테스트 주식회사",
        im_style=IMStyle.TEASER,
    )


@pytest.fixture
def full_tm_data() -> IMDocumentData:
    """전체 데이터로 TM 생성."""
    return IMDocumentData(
        project_name="Project NX3",
        company_name_kr="NX3 Games",
        im_style=IMStyle.TEASER,
        company_overview=CompanyOverview(
            headquarters="서울특별시 강남구",
            established_date="2015-03-01",
            employee_count=250,
            key_products=["모바일 RPG", "PC 온라인 게임", "콘솔 게임"],
        ),
        deal_structure=DealStructure(
            transaction_type=TransactionType.MA,
            seller="기존 주주",
            stake_pct=0.65,
            valuation_method="EV/EBITDA",
            valuation_low=1500,
            valuation_high=2000,
            deal_background="전략적 투자자 유치",
        ),
        market_data=MarketData(
            tam=50000,
            sam=15000,
            som=3000,
            market_cagr=0.12,
            market_growth_rate=0.15,
            industry_trends=["모바일 게임 성장", "글로벌 진출 가속화"],
            competitors=[
                {"name": "넷마블", "market_share": 0.15, "revenue": 8000},
                {"name": "엔씨소프트", "market_share": 0.12, "revenue": 6500},
            ],
            regulatory_notes="게임산업진흥법 규제 동향",
        ),
        financial_statements=FinancialStatements(
            revenue={"2023": 500, "2024": 650, "2025E": 800},
            operating_income={"2023": 80, "2024": 120, "2025E": 160},
            ebitda={"2023": 100, "2024": 150, "2025E": 200},
            net_income={"2023": 60, "2024": 90, "2025E": 120},
        ),
        investment_highlights=[
            "모바일 게임 시장 1위",
            "연평균 30% 매출 성장",
            "글로벌 확장 가능성",
        ],
    )


# ---------------------------------------------------------------------------
# 1. 데이터 모델 테스트
# ---------------------------------------------------------------------------


class TestTmDataModel:
    """IMDocumentData TEASER 스타일 프리셋."""

    def test_teaser_style_sets_sections(self, minimal_tm_data: IMDocumentData):
        """TEASER 스타일 선택 시 TEASER_SECTIONS 프리셋 적용."""
        assert minimal_tm_data.sections == list(TEASER_SECTIONS)

    def test_teaser_sections_structure(self, minimal_tm_data: IMDocumentData):
        """TM 섹션 구조: cover + disclaimer + 4 toc_divider + 10 콘텐츠 + contact."""
        sections = minimal_tm_data.sections
        assert sections[0] == "cover"
        assert sections[1] == "disclaimer"
        assert sections[-1] == "contact"
        # 4개 toc_divider + 10개 콘텐츠 + 3개 구조 = 17
        assert len(sections) == 17

    def test_teaser_active_sections(self, minimal_tm_data: IMDocumentData):
        """get_active_sections()에서 TM 섹션 반환."""
        active = minimal_tm_data.get_active_sections()
        assert "target_positioning" in active
        assert "market_outlook" in active
        assert "demand_driver" in active
        assert "supply_driver" in active
        assert "target_overview" in active
        assert "target_highlights" in active
        assert "proforma_plan" in active
        assert "proforma_financials" in active

    def test_teaser_no_dm_sections(self, minimal_tm_data: IMDocumentData):
        """TEASER는 DM 섹션을 포함하지 않음."""
        assert "dm_market_trends" not in minimal_tm_data.sections
        assert "dm_deal_structure" not in minimal_tm_data.sections


# ---------------------------------------------------------------------------
# 2. 렌더러 등록 테스트
# ---------------------------------------------------------------------------


class TestTmRendererRegistry:
    """TM 렌더러 레지스트리 등록 확인."""

    TM_SECTION_IDS = list(TEASER_SECTION_IDS)

    @pytest.mark.parametrize("section_id", TM_SECTION_IDS)
    def test_tm_renderer_registered(self, section_id: str):
        """각 TM section_id가 레지스트리에 등록됨."""
        assert section_id in RENDERER_REGISTRY

    @pytest.mark.parametrize("section_id", TM_SECTION_IDS)
    def test_tm_renderer_instantiable(self, section_id: str):
        """get_renderer()로 인스턴스 생성 가능."""
        renderer = get_renderer(section_id)
        assert renderer is not None
        assert renderer.section_id == section_id


# ---------------------------------------------------------------------------
# 3. 개별 렌더러 PPTX 단위 테스트
# ---------------------------------------------------------------------------


class TestTmRenderersPptx:
    """TM 렌더러 render_pptx() 단위 테스트."""

    TM_SECTION_IDS = list(TEASER_SECTION_IDS)

    @pytest.mark.parametrize("section_id", TM_SECTION_IDS)
    def test_render_pptx_minimal(
        self,
        section_id: str,
        factory: SlideFactory,
        prs: Presentation,
        minimal_tm_data: IMDocumentData,
    ):
        """최소 데이터로 PPTX 렌더링 — 에러 없이 1개 이상 슬라이드 생성."""
        renderer = get_renderer(section_id)
        slides = renderer.render_pptx(
            factory, minimal_tm_data, prs=prs, tokens=DEFAULT_TOKENS
        )
        assert len(slides) >= 1

    @pytest.mark.parametrize("section_id", TM_SECTION_IDS)
    def test_render_pptx_full(
        self,
        section_id: str,
        factory: SlideFactory,
        prs: Presentation,
        full_tm_data: IMDocumentData,
    ):
        """전체 데이터로 PPTX 렌더링 — 에러 없이 1개 이상 슬라이드 생성."""
        renderer = get_renderer(section_id)
        slides = renderer.render_pptx(
            factory, full_tm_data, prs=prs, tokens=DEFAULT_TOKENS
        )
        assert len(slides) >= 1


# ---------------------------------------------------------------------------
# 4. 개별 렌더러 HTML 단위 테스트
# ---------------------------------------------------------------------------


class TestTmRenderersHtml:
    """TM 렌더러 render_html() 단위 테스트."""

    TM_SECTION_IDS = list(TEASER_SECTION_IDS)

    @pytest.mark.parametrize("section_id", TM_SECTION_IDS)
    def test_render_html_minimal(
        self,
        section_id: str,
        minimal_tm_data: IMDocumentData,
    ):
        """최소 데이터로 HTML 렌더링."""
        renderer = get_renderer(section_id)
        html_slides = renderer.render_html(minimal_tm_data, tokens=DEFAULT_TOKENS)
        assert len(html_slides) >= 1
        assert all(isinstance(s, str) for s in html_slides)

    @pytest.mark.parametrize("section_id", TM_SECTION_IDS)
    def test_render_html_full(
        self,
        section_id: str,
        full_tm_data: IMDocumentData,
    ):
        """전체 데이터로 HTML 렌더링."""
        renderer = get_renderer(section_id)
        html_slides = renderer.render_html(full_tm_data, tokens=DEFAULT_TOKENS)
        assert len(html_slides) >= 1
        assert all("<div" in s or "<p" in s or "<table" in s for s in html_slides)


# ---------------------------------------------------------------------------
# 5. 파이프라인 통합 테스트
# ---------------------------------------------------------------------------


class TestTmPipeline:
    """IMPipeline TM 통합 테스트."""

    def test_tm_pipeline_generates_slides(self, full_tm_data: IMDocumentData):
        """TM 파이프라인 실행 → 17개 이상 슬라이드 (cover+disclaimer + 4 TOC + 10 content + contact)."""
        pipeline = IMPipeline()
        result = pipeline.generate(full_tm_data)

        assert result.success
        assert result.total_pptx_slides >= 17
        assert len(result.errors) == 0

    def test_tm_pipeline_minimal_data(self, minimal_tm_data: IMDocumentData):
        """최소 데이터 TM 파이프라인 — 에러 없이 완료."""
        pipeline = IMPipeline()
        result = pipeline.generate(minimal_tm_data)

        assert result.success
        assert result.total_pptx_slides >= 17
        assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# 6. 회귀 테스트 — 기존 IM/DM 불변 확인
# ---------------------------------------------------------------------------


class TestRegressionExistingStyles:
    """기존 IM/DM 스타일이 TM 수정으로 영향받지 않는지 확인."""

    def test_full_style_unchanged(self):
        """FULL 스타일 섹션 수 불변."""
        data = IMDocumentData(
            project_name="Regression Test",
            company_name_kr="테스트",
            im_style=IMStyle.FULL,
        )
        assert "cover" in data.sections
        assert "contact" in data.sections
        assert "target_positioning" not in data.sections

    def test_dm_style_unchanged(self):
        """DM 스타일 섹션 수 불변."""
        data = IMDocumentData(
            project_name="Regression Test",
            company_name_kr="테스트",
            im_style=IMStyle.DM,
        )
        assert data.sections == list(DM_SECTIONS)
        assert "target_positioning" not in data.sections

    def test_titan_style_unchanged(self):
        """TITAN 스타일 섹션 수 불변."""
        data = IMDocumentData(
            project_name="Regression Test",
            company_name_kr="테스트",
            im_style=IMStyle.TITAN,
        )
        assert "cover" in data.sections
        assert "target_positioning" not in data.sections


# ---------------------------------------------------------------------------
# 7. 프롬프트 레지스트리 테스트
# ---------------------------------------------------------------------------


class TestTmPrompts:
    """TM 프롬프트 레지스트리 테스트."""

    TM_PROMPT_SECTION_IDS = list(TEASER_SECTION_IDS)

    def test_tm_prompts_registered(self):
        """TM 프롬프트 8개가 레지스트리에 등록됨."""
        from src.narrative_generator.prompts import create_default_registry

        registry = create_default_registry()
        for section_id in self.TM_PROMPT_SECTION_IDS:
            prompt = registry.get(section_id)
            assert prompt is not None, f"프롬프트 미등록: {section_id}"

    def test_tm_prompts_extract_data(self, full_tm_data: IMDocumentData):
        """TM 프롬프트 extract_data() 에러 없이 실행."""
        from src.narrative_generator.prompts import create_default_registry

        registry = create_default_registry()
        for section_id in self.TM_PROMPT_SECTION_IDS:
            prompt = registry.get(section_id)
            data = prompt.extract_data(full_tm_data)
            assert isinstance(data, dict)

    def test_tm_prompts_token_budget(self):
        """TM 프롬프트 토큰 버짓이 적절한 범위."""
        from src.narrative_generator.prompts import create_default_registry

        registry = create_default_registry()
        for section_id in self.TM_PROMPT_SECTION_IDS:
            prompt = registry.get(section_id)
            budget = prompt.get_token_budget()
            assert 200 <= budget <= 1000, f"{section_id}: budget={budget}"
