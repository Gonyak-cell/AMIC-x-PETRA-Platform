"""Phase 3 검증 테스트 — TM 완전한 콘텐츠 (36 tests).

get_full_tm_data()가 반환하는 IMDocumentData(TEASER 스타일)의 완성도를 검증한다.
기존 test_tm_pipeline.py(렌더러 메커닉스)와 비중복 — 여기서는 콘텐츠 품질을 검증한다.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from src.design_renderer.im_document import (
    IMDocumentData,
    IMStyle,
    TEASER_SECTIONS,
    TEASER_TOC_GROUPS,
)
from src.design_renderer.sample_data.im_full import get_full_im_data
from src.design_renderer.sample_data.narratives_tm import get_tm_narrative_section_ids
from src.design_renderer.sample_data.tm_full import get_full_tm_data

if TYPE_CHECKING:
    from src.design_renderer.pipeline import PipelineResult

# ── 공통 상수 ──────────────────────────────────────────────────────────────────

KOREAN_RE = re.compile(r"[가-힣]")
PLACEHOLDER_RE = re.compile(r"(TODO|TBD|\{\{|\[INSERT\])", re.IGNORECASE)
NUMBER_RE = re.compile(r"\d[\d,.]*")

# TM 마케팅 톤 용어 — 4+개 이상 매칭 기대
TM_MARKETING_TERMS = [
    "기회",
    "성장",
    "잠재력",
    "강점",
    "경쟁우위",
    "수혜",
    "해자",
    "매력",
    "전략적",
    "확대",
    "확보",
    "선점",
    "독보적",
    "가속",
]


# ── 픽스처 ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def full_tm_data() -> IMDocumentData:
    """모듈 전체에서 공유하는 TM(TEASER) 데이터."""
    return get_full_tm_data()


# ══════════════════════════════════════════════════════════════════════════════
# TestTmFullDataCompleteness (15)
# ══════════════════════════════════════════════════════════════════════════════


class TestTmFullDataCompleteness:
    """TM 데이터 완성도 검증."""

    def test_full_tm_data_is_teaser_style(self, full_tm_data: IMDocumentData) -> None:
        """im_style == TEASER."""
        assert full_tm_data.im_style == IMStyle.TEASER

    def test_tm_sections_count(self, full_tm_data: IMDocumentData) -> None:
        """len(sections) == len(TEASER_SECTIONS)."""
        expected = len(TEASER_SECTIONS)
        assert len(full_tm_data.sections) == expected, (
            f"섹션 {len(full_tm_data.sections)}개 ({expected}개 기대): "
            f"{full_tm_data.sections}"
        )

    def test_tm_financial_statements_populated(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """3년+ revenue + EBITDA."""
        fs = full_tm_data.financial_statements
        assert len(fs.revenue) >= 3, f"매출 {len(fs.revenue)}개 연도 (3개 이상 기대)"
        assert len(fs.ebitda) >= 3, f"EBITDA {len(fs.ebitda)}개 연도 (3개 이상 기대)"

    def test_tm_deal_structure_populated(self, full_tm_data: IMDocumentData) -> None:
        """seller, valuation_method, transaction_type 존재."""
        ds = full_tm_data.deal_structure
        assert ds is not None, "deal_structure가 None"
        assert ds.seller.strip() != "", "seller 비어있음"
        assert ds.valuation_method is not None and ds.valuation_method.strip() != "", (
            "valuation_method 비어있음"
        )
        assert ds.transaction_type is not None, "transaction_type 미설정"

    def test_tm_market_data_has_competitors(self, full_tm_data: IMDocumentData) -> None:
        """competitors >= 2."""
        md = full_tm_data.market_data
        assert md is not None, "market_data가 None"
        assert len(md.competitors) >= 2, (
            f"경쟁사 {len(md.competitors)}개 (2개 이상 기대)"
        )

    def test_tm_investment_highlights_minimum_3(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """investment_highlights >= 3."""
        assert len(full_tm_data.investment_highlights) >= 3, (
            f"투자 하이라이트 {len(full_tm_data.investment_highlights)}개 (3개 이상 기대)"
        )

    def test_tm_company_overview_basic_fields(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """headquarters, key_products, employee_count 설정됨."""
        co = full_tm_data.company_overview
        assert co is not None, "company_overview가 None"
        assert co.headquarters.strip() != "", "headquarters 비어있음"
        assert len(co.key_products) >= 1, "key_products 비어있음"
        assert co.employee_count is not None and co.employee_count > 0, (
            "employee_count 미설정"
        )

    def test_tm_sections_match_teaser_preset(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """sections == TEASER_SECTIONS."""
        assert full_tm_data.sections == TEASER_SECTIONS, (
            f"TM sections 불일치:\n"
            f"  actual={full_tm_data.sections}\n"
            f"  expected={TEASER_SECTIONS}"
        )

    def test_tm_valuation_data_populated(self, full_tm_data: IMDocumentData) -> None:
        """valuation_data에 EV, EV/EBITDA, IRR/MOIC 시나리오 존재."""
        vd = full_tm_data.valuation_data
        assert vd is not None, "valuation_data가 None"
        assert len(vd.ev) >= 1, f"EV {len(vd.ev)}개 연도 (1개 이상 기대)"
        assert len(vd.ev_ebitda) >= 1, "EV/EBITDA 배수 미설정"
        assert len(vd.irr_scenarios) >= 1, "IRR 시나리오 미설정"
        assert len(vd.moic_scenarios) >= 1, "MOIC 시나리오 미설정"

    def test_tm_contacts_populated(self, full_tm_data: IMDocumentData) -> None:
        """연락처 2명 이상, name·email 비어있지 않음."""
        assert len(full_tm_data.contacts) >= 2, (
            f"연락처 {len(full_tm_data.contacts)}명 (2명 이상 기대)"
        )
        for i, c in enumerate(full_tm_data.contacts):
            assert c.name.strip() != "", f"contacts[{i}] name 비어있음"
            assert c.email.strip() != "", f"contacts[{i}] email 비어있음"

    def test_tm_source_citations_populated(self, full_tm_data: IMDocumentData) -> None:
        """source_citations 최소 1개 섹션 이상."""
        assert len(full_tm_data.source_citations) >= 1, (
            f"source_citations {len(full_tm_data.source_citations)}개 (1개 이상 기대)"
        )

    def test_tm_growth_strategy_populated(self, full_tm_data: IMDocumentData) -> None:
        """growth_strategy organic_growth, new_business 비어있지 않음."""
        gs = full_tm_data.growth_strategy
        assert gs is not None, "growth_strategy가 None"
        assert len(gs.organic_growth) >= 1, "organic_growth 비어있음"
        assert len(gs.new_business) >= 1, "new_business 비어있음"

    def test_tm_management_team_count(self, full_tm_data: IMDocumentData) -> None:
        """management_team 1명 이상."""
        assert len(full_tm_data.management_team) >= 1, (
            f"management_team {len(full_tm_data.management_team)}명 (1명 이상 기대)"
        )

    def test_tm_shareholders_populated(self, full_tm_data: IMDocumentData) -> None:
        """shareholders 1명 이상."""
        assert len(full_tm_data.shareholders) >= 1, (
            f"shareholders {len(full_tm_data.shareholders)}명 (1명 이상 기대)"
        )

    def test_tm_segment_revenue_populated(self, full_tm_data: IMDocumentData) -> None:
        """segment_revenue 최소 1개 세그먼트."""
        sr = full_tm_data.segment_revenue
        assert sr is not None, "segment_revenue가 None"
        assert len(sr.segments) >= 1, (
            f"segment_revenue {len(sr.segments)}개 세그먼트 (1개 이상 기대)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestTmFullNarratives (6)
# ══════════════════════════════════════════════════════════════════════════════


class TestTmFullNarratives:
    """TM 내러티브 품질 검증."""

    def test_tm_narratives_cover_8_sections(self, full_tm_data: IMDocumentData) -> None:
        """narratives에 8개 TEASER_SECTION_IDS 키 존재."""
        expected_ids = set(get_tm_narrative_section_ids())
        actual_ids = set(full_tm_data.narratives.keys())
        missing = expected_ids - actual_ids
        assert not missing, f"누락된 TM 내러티브 섹션: {missing}"

    def test_tm_narrative_minimum_length(self, full_tm_data: IMDocumentData) -> None:
        """각 TM 내러티브 >= 150자."""
        for section_id, text in full_tm_data.narratives.items():
            assert len(text) >= 150, (
                f"'{section_id}' 내러티브 {len(text)}자 (150자 이상 기대)"
            )

    def test_tm_narratives_korean_text(self, full_tm_data: IMDocumentData) -> None:
        """모든 TM 내러티브에 한국어 포함."""
        for section_id, text in full_tm_data.narratives.items():
            assert KOREAN_RE.search(text), f"'{section_id}' 내러티브에 한국어 없음"

    def test_tm_narratives_no_placeholders(self, full_tm_data: IMDocumentData) -> None:
        """TODO/TBD/{{ 없음."""
        for section_id, text in full_tm_data.narratives.items():
            match = PLACEHOLDER_RE.search(text)
            assert match is None, (
                f"'{section_id}' 내러티브에 플레이스홀더 발견: '{match.group()}'"
            )

    def test_tm_narrative_marketing_tone(self, full_tm_data: IMDocumentData) -> None:
        """TM 전체 내러티브 섹션(8개) 모두 마케팅 용어 포함."""
        sections_with_marketing = 0
        for text in full_tm_data.narratives.values():
            if any(term in text for term in TM_MARKETING_TERMS):
                sections_with_marketing += 1
        threshold = len(get_tm_narrative_section_ids())
        assert sections_with_marketing >= threshold, (
            f"마케팅 톤 내러티브 {sections_with_marketing}개 ({threshold}개 이상 기대)"
        )

    def test_tm_proforma_narrative_has_numbers(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """proforma 내러티브에 숫자 참조."""
        for key in ("proforma_plan", "proforma_financials"):
            text = full_tm_data.narratives.get(key, "")
            numbers = NUMBER_RE.findall(text)
            assert len(numbers) >= 2, (
                f"'{key}' 내러티브에 숫자 {len(numbers)}개 (2개 이상 기대)"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TestTmProformaData (4)
# ══════════════════════════════════════════════════════════════════════════════


class TestTmProformaData:
    """Pro-Forma 재무 데이터 검증."""

    def test_proforma_revenue_projection_3to5_years(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """기본 재무제표에 'E' 접미사 포함 3~5년 매출 전망 존재."""
        fs = full_tm_data.financial_statements
        estimate_years = [y for y in fs.revenue if "E" in y]
        assert len(estimate_years) >= 1, (
            f"전망 연도(E 접미사) {len(estimate_years)}개 (1개 이상 기대)"
        )

    def test_proforma_ebitda_projection_exists(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """EBITDA 전망 3년+ 존재."""
        fs = full_tm_data.financial_statements
        assert len(fs.ebitda) >= 3, f"EBITDA {len(fs.ebitda)}개 연도 (3개 이상 기대)"

    def test_proforma_margins_reasonable(self, full_tm_data: IMDocumentData) -> None:
        """영업이익률 0%~50% 범위 내."""
        fs = full_tm_data.financial_statements
        for year in fs.revenue:
            if year in fs.operating_income:
                rev = fs.revenue[year]
                oi = fs.operating_income[year]
                if rev > 0:
                    margin = oi / rev
                    assert 0.0 <= margin <= 0.50, (
                        f"{year} 영업이익률 {margin:.1%} (0%~50% 기대)"
                    )

    def test_proforma_growth_rates_positive(self, full_tm_data: IMDocumentData) -> None:
        """전망 연도 간 매출 성장률 > 0."""
        fs = full_tm_data.financial_statements
        sorted_years = sorted(fs.revenue.keys(), key=lambda y: int(y.replace("E", "")))
        for i in range(1, len(sorted_years)):
            prev_year = sorted_years[i - 1]
            curr_year = sorted_years[i]
            prev_rev = fs.revenue[prev_year]
            curr_rev = fs.revenue[curr_year]
            if prev_rev > 0:
                growth = (curr_rev - prev_rev) / prev_rev
                assert growth > 0, (
                    f"{prev_year}→{curr_year} 매출 성장률 {growth:.1%} (양수 기대)"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TestTmFullPipeline (4)
# ══════════════════════════════════════════════════════════════════════════════


class TestTmFullPipeline:
    """TM 파이프라인 E2E 테스트."""

    @pytest.fixture(scope="class")
    def pipeline_result(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> PipelineResult:
        """파이프라인 실행 결과 (클래스 전체에서 공유)."""
        from src.design_renderer.pipeline import IMPipeline

        data = get_full_tm_data()
        out_dir = tmp_path_factory.mktemp("tm_full_output")
        pptx_path = out_dir / "test_tm_full.pptx"

        pipeline = IMPipeline(continue_on_error=True)
        return pipeline.generate(data, pptx_path=pptx_path)

    def test_tm_full_pipeline_success(self, pipeline_result: PipelineResult) -> None:
        """pipeline.generate() 성공."""
        assert pipeline_result.success is True, (
            f"파이프라인 실패: errors={pipeline_result.errors}"
        )

    def test_tm_full_slide_count_minimum(self, pipeline_result: PipelineResult) -> None:
        """slides >= len(TEASER_SECTIONS)."""
        count = pipeline_result.total_pptx_slides
        assert count >= len(TEASER_SECTIONS), (
            f"슬라이드 {count}개 ({len(TEASER_SECTIONS)}개 이상 기대)"
        )

    def test_tm_full_zero_errors(self, pipeline_result: PipelineResult) -> None:
        """errors 없음."""
        assert pipeline_result.errors == [], (
            f"에러 {len(pipeline_result.errors)}건: {pipeline_result.errors}"
        )

    def test_tm_full_no_failed_sections(self, pipeline_result: PipelineResult) -> None:
        """failed_sections 없음."""
        failed = pipeline_result.failed_sections
        assert len(failed) == 0, (
            f"실패 섹션 {len(failed)}개: {[(f.section_id, f.error) for f in failed]}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestTmFullCharts (2)
# ══════════════════════════════════════════════════════════════════════════════


class TestTmFullCharts:
    """TM 차트 데이터 검증."""

    def test_tm_charts_include_proforma_keys(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """charts에 proforma_plan, proforma_financials 키 존재."""
        charts = full_tm_data.charts
        assert "proforma_plan" in charts, "charts에 proforma_plan 키 없음"
        assert "proforma_financials" in charts, "charts에 proforma_financials 키 없음"

    def test_tm_proforma_charts_non_empty(self, full_tm_data: IMDocumentData) -> None:
        """proforma 차트 각 1개 이상."""
        charts = full_tm_data.charts
        plan_charts = charts.get("proforma_plan", [])
        fin_charts = charts.get("proforma_financials", [])
        assert len(plan_charts) >= 1, (
            f"proforma_plan 차트 {len(plan_charts)}개 (1개 이상 기대)"
        )
        assert len(fin_charts) >= 1, (
            f"proforma_financials 차트 {len(fin_charts)}개 (1개 이상 기대)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestTmFullDerivedMetrics (2)
# ══════════════════════════════════════════════════════════════════════════════


class TestTmFullDerivedMetrics:
    """TM 파생 지표 검증."""

    def test_tm_derived_metrics_computed(self, full_tm_data: IMDocumentData) -> None:
        """derived_metrics가 None이 아님."""
        assert full_tm_data.derived_metrics is not None, (
            "derived_metrics가 None — compute_derived_metrics() 호출 여부 확인"
        )

    def test_tm_derived_metrics_cagr_present(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """revenue_cagr_3y 키 존재 및 양수."""
        dm = full_tm_data.derived_metrics
        assert dm is not None, "derived_metrics가 None"
        assert "revenue_cagr_3y" in dm, (
            f"revenue_cagr_3y 없음 — 존재하는 키: {list(dm.keys())}"
        )
        assert dm["revenue_cagr_3y"] > 0, (
            f"revenue_cagr_3y={dm['revenue_cagr_3y']:.2%} (양수 기대)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestTmContentQuality (3)
# ══════════════════════════════════════════════════════════════════════════════


class TestTmContentQuality:
    """TM 콘텐츠 품질 및 독립성 검증."""

    def test_tm_no_im_only_section_data_leaks(
        self, full_tm_data: IMDocumentData
    ) -> None:
        """TM 데이터에 IM 전용 섹션 참조 없음.

        TM narratives는 TM 전용 8개 섹션만 포함해야 한다.
        IM 전용 섹션(company_overview, business_model 등)이 혼입되면 안 된다.
        """
        im_only_sections = {
            "company_overview",
            "business_model",
            "business_overview",
            "market_overview",
            "financial_analysis",
            "value_creation",
            "management_team",
            "deal_overview",
            "shareholder_structure",
            "transaction_structure",
            "valuation",
        }
        leaked = im_only_sections & set(full_tm_data.narratives.keys())
        assert not leaked, f"TM narratives에 IM 전용 섹션 혼입: {leaked}"

    def test_tm_toc_groups_match_sections(self, full_tm_data: IMDocumentData) -> None:
        """4개 TOC 그룹 하위 섹션 ID 전부 get_active_sections()에 존재."""
        active = set(full_tm_data.get_active_sections())
        for group in TEASER_TOC_GROUPS:
            for section_id, _label in group["subsections"]:
                assert section_id in active, (
                    f"TOC 그룹 '{group['title']}' 섹션 '{section_id}'가 "
                    f"active_sections에 없음"
                )

    def test_tm_data_independent_from_im_full(self) -> None:
        """get_full_tm_data() ≠ get_full_im_data() (별도 객체, 별도 im_style)."""
        tm_data = get_full_tm_data()
        im_data = get_full_im_data()
        assert tm_data is not im_data, "TM과 IM이 동일 객체"
        assert tm_data.im_style != im_data.im_style, (
            f"TM im_style={tm_data.im_style} == IM im_style={im_data.im_style}"
        )
        # narratives 내용도 다른지 확인
        tm_keys = set(tm_data.narratives.keys())
        im_keys = set(im_data.narratives.keys())
        assert tm_keys != im_keys, "TM과 IM의 narrative 키가 동일 — 별도 콘텐츠여야 함"
