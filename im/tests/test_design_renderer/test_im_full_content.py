"""Phase 2 검증 테스트 — IM 완전한 콘텐츠 (40 tests).

get_full_im_data()가 반환하는 IMDocumentData의 완성도를 검증한다.
기존 conftest.py의 TITAN/COVENANT/FULL 픽스처와 비중복.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from src.design_renderer.im_document import (
    IMDocumentData,
    IMStyle,
)
from src.design_renderer.sample_data.im_full import get_full_im_data
from src.design_renderer.sample_data.narratives_im import get_im_narrative_section_ids

if TYPE_CHECKING:
    from src.design_renderer.pipeline import PipelineResult

# ── 공통 상수 ──────────────────────────────────────────────────────────────────

KOREAN_RE = re.compile(r"[가-힣]")
PLACEHOLDER_RE = re.compile(r"(TODO|TBD|\{\{|\[INSERT\])", re.IGNORECASE)
NUMBER_RE = re.compile(r"\d[\d,.]*")

MA_PROFESSIONAL_TERMS = [
    "EBITDA",
    "EV/EBITDA",
    "IRR",
    "MOIC",
    "CAGR",
    "DCF",
    "P/E",
    "Enterprise Value",
    "클로징",
    "매각",
    "인수",
    "밸류에이션",
    "영업이익",
    "매출",
    "지분",
    "경영권",
    "실사",
    "SPA",
]


# ── 픽스처 ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def full_im_data() -> IMDocumentData:
    """모듈 전체에서 공유하는 IM FULL 데이터."""
    return get_full_im_data()


# ══════════════════════════════════════════════════════════════════════════════
# TestImFullDataCompleteness (15)
# ══════════════════════════════════════════════════════════════════════════════


class TestImFullDataCompleteness:
    """IM FULL 데이터 완성도 검증."""

    def test_full_im_data_returns_full_style(
        self, full_im_data: IMDocumentData
    ) -> None:
        """im_style == FULL."""
        assert full_im_data.im_style == IMStyle.FULL

    def test_financial_statements_has_5_years(
        self, full_im_data: IMDocumentData
    ) -> None:
        """years 5개 (2021~2025E)."""
        years = full_im_data.financial_statements.years
        assert len(years) >= 5, f"연도 {len(years)}개 (5개 이상 기대): {years}"

    def test_all_income_statement_fields_populated(
        self, full_im_data: IMDocumentData
    ) -> None:
        """revenue ~ sga_expenses 5년 전부 채워짐."""
        fs = full_im_data.financial_statements
        fields = [
            fs.revenue,
            fs.cost_of_goods_sold,
            fs.gross_profit,
            fs.operating_income,
            fs.ebitda,
            fs.net_income,
            fs.sga_expenses,
        ]
        for fld in fields:
            assert len(fld) >= 5, f"손익 항목 {len(fld)}개 연도 (5개 이상 기대)"

    def test_all_balance_sheet_fields_populated(
        self, full_im_data: IMDocumentData
    ) -> None:
        """total_assets ~ total_debt 3년+ 채워짐."""
        fs = full_im_data.financial_statements
        bs_fields = [
            fs.total_assets,
            fs.total_liabilities,
            fs.total_equity,
            fs.cash_and_equivalents,
            fs.total_debt,
        ]
        for fld in bs_fields:
            assert len(fld) >= 3, f"재무상태표 항목 {len(fld)}개 연도 (3개 이상 기대)"

    def test_segment_revenue_has_multiple_segments(
        self, full_im_data: IMDocumentData
    ) -> None:
        """segment_revenue.segments >= 2개."""
        assert full_im_data.segment_revenue is not None
        segments = full_im_data.segment_revenue.segments
        assert len(segments) >= 2, f"세그먼트 {len(segments)}개 (2개 이상 기대)"

    def test_valuation_data_present_and_complete(
        self, full_im_data: IMDocumentData
    ) -> None:
        """irr_scenarios, moic_scenarios, sensitivity_data 비어있지 않음."""
        vd = full_im_data.valuation_data
        assert vd is not None, "valuation_data가 None"
        assert len(vd.irr_scenarios) > 0, "irr_scenarios 비어있음"
        assert len(vd.moic_scenarios) > 0, "moic_scenarios 비어있음"
        assert len(vd.sensitivity_data) > 0, "sensitivity_data 비어있음"

    def test_deal_structure_fully_populated(self, full_im_data: IMDocumentData) -> None:
        """seller, stake_pct, valuation_low/high 모두 채워짐."""
        ds = full_im_data.deal_structure
        assert ds is not None, "deal_structure가 None"
        assert ds.seller.strip() != "", "seller 비어있음"
        assert ds.stake_pct is not None and ds.stake_pct > 0, "stake_pct 미설정"
        assert ds.valuation_low is not None and ds.valuation_low > 0, (
            "valuation_low 미설정"
        )
        assert ds.valuation_high is not None and ds.valuation_high > 0, (
            "valuation_high 미설정"
        )

    def test_company_overview_populated(self, full_im_data: IMDocumentData) -> None:
        """headquarters, established_date, employee_count, key_products >= 2."""
        co = full_im_data.company_overview
        assert co is not None, "company_overview가 None"
        assert co.headquarters.strip() != "", "headquarters 비어있음"
        assert co.established_date.strip() != "", "established_date 비어있음"
        assert co.employee_count is not None and co.employee_count > 0, (
            "employee_count 미설정"
        )
        assert len(co.key_products) >= 2, (
            f"key_products {len(co.key_products)}개 (2개 이상 기대)"
        )

    def test_market_data_has_competitors(self, full_im_data: IMDocumentData) -> None:
        """market_data.competitors >= 5개 (name, market_share 키 포함)."""
        md = full_im_data.market_data
        assert md is not None, "market_data가 None"
        assert len(md.competitors) >= 5, (
            f"경쟁사 {len(md.competitors)}개 (5개 이상 기대)"
        )
        for comp in md.competitors:
            assert "name" in comp, "경쟁사에 'name' 키 누락"
            assert "market_share" in comp, (
                f"{comp.get('name', '?')}에 'market_share' 키 누락"
            )

    def test_investment_highlights_count(self, full_im_data: IMDocumentData) -> None:
        """investment_highlights >= 5개."""
        assert len(full_im_data.investment_highlights) >= 5, (
            f"투자 하이라이트 {len(full_im_data.investment_highlights)}개 (5개 이상 기대)"
        )

    def test_growth_strategy_populated(self, full_im_data: IMDocumentData) -> None:
        """organic_growth, new_business 비어있지 않음."""
        gs = full_im_data.growth_strategy
        assert gs is not None, "growth_strategy가 None"
        assert len(gs.organic_growth) > 0, "organic_growth 비어있음"
        assert len(gs.new_business) > 0, "new_business 비어있음"

    def test_management_team_count(self, full_im_data: IMDocumentData) -> None:
        """6~8명, 각각 name/title/role 보유."""
        mt = full_im_data.management_team
        assert 6 <= len(mt) <= 10, f"경영진 {len(mt)}명 (6~10명 기대)"
        for member in mt:
            assert member.name.strip() != "", "경영진 name 비어있음"
            assert member.title.strip() != "", f"{member.name}: title 비어있음"
            assert member.role.strip() != "", f"{member.name}: role 비어있음"

    def test_org_structure_present(self, full_im_data: IMDocumentData) -> None:
        """org_structure is not None, 비어있지 않은 dict."""
        assert full_im_data.org_structure is not None, "org_structure가 None"
        assert isinstance(full_im_data.org_structure, dict), "org_structure가 dict 아님"
        assert len(full_im_data.org_structure) > 0, "org_structure 비어있음"

    def test_shareholders_populated(self, full_im_data: IMDocumentData) -> None:
        """3+명, stake_pct 합 ≈ 1.0 (±0.01)."""
        shareholders = full_im_data.shareholders
        assert len(shareholders) >= 3, f"주주 {len(shareholders)}명 (3명 이상 기대)"
        total_pct = sum(s.stake_pct for s in shareholders)
        assert abs(total_pct - 1.0) < 0.01, (
            f"주주 지분합 {total_pct:.4f} (1.0 ± 0.01 기대)"
        )

    def test_source_citations_count(self, full_im_data: IMDocumentData) -> None:
        """5+개 섹션에 source_citations 존재."""
        assert len(full_im_data.source_citations) >= 5, (
            f"출처 {len(full_im_data.source_citations)}개 섹션 (5개 이상 기대)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestImFullNarratives (7)
# ══════════════════════════════════════════════════════════════════════════════


class TestImFullNarratives:
    """IM 내러티브 품질 검증."""

    def test_narratives_cover_all_14_sections(
        self, full_im_data: IMDocumentData
    ) -> None:
        """narratives dict 14개 키 존재."""
        expected_ids = set(get_im_narrative_section_ids())
        actual_ids = set(full_im_data.narratives.keys())
        missing = expected_ids - actual_ids
        assert not missing, f"누락된 내러티브 섹션: {missing}"

    def test_narrative_minimum_length_per_section(
        self, full_im_data: IMDocumentData
    ) -> None:
        """각 내러티브 >= 200자."""
        for section_id, text in full_im_data.narratives.items():
            assert len(text) >= 200, (
                f"'{section_id}' 내러티브 {len(text)}자 (200자 이상 기대)"
            )

    def test_narratives_contain_korean_text(self, full_im_data: IMDocumentData) -> None:
        """각 내러티브에 한국어 포함 ([가-힣])."""
        for section_id, text in full_im_data.narratives.items():
            assert KOREAN_RE.search(text), f"'{section_id}' 내러티브에 한국어 없음"

    def test_narratives_professional_vocabulary(
        self, full_im_data: IMDocumentData
    ) -> None:
        """M&A 전문 용어 5+개 포함 (전체 내러티브 통합)."""
        all_text = " ".join(full_im_data.narratives.values())
        found_terms = [t for t in MA_PROFESSIONAL_TERMS if t in all_text]
        assert len(found_terms) >= 5, (
            f"M&A 전문용어 {len(found_terms)}개 발견 (5개 이상 기대): {found_terms}"
        )

    def test_narrative_no_placeholder_text(self, full_im_data: IMDocumentData) -> None:
        """TODO, TBD, {{, [INSERT] 없음."""
        for section_id, text in full_im_data.narratives.items():
            match = PLACEHOLDER_RE.search(text)
            assert match is None, (
                f"'{section_id}' 내러티브에 플레이스홀더 발견: '{match.group()}'"
            )

    def test_financial_narrative_references_numbers(
        self, full_im_data: IMDocumentData
    ) -> None:
        """financial_analysis 내러티브에 숫자 3+개."""
        text = full_im_data.narratives.get("financial_analysis", "")
        numbers = NUMBER_RE.findall(text)
        assert len(numbers) >= 3, (
            f"financial_analysis에 숫자 {len(numbers)}개 (3개 이상 기대)"
        )

    def test_executive_summary_is_concise(self, full_im_data: IMDocumentData) -> None:
        """500~3000자."""
        text = full_im_data.narratives.get("executive_summary", "")
        length = len(text)
        assert 500 <= length <= 3000, f"executive_summary {length}자 (500~3000자 기대)"


# ══════════════════════════════════════════════════════════════════════════════
# TestImFullCharts (4)
# ══════════════════════════════════════════════════════════════════════════════


class TestImFullCharts:
    """차트 데이터 검증."""

    def test_charts_count_minimum_5(self, full_im_data: IMDocumentData) -> None:
        """전체 ChartData 5+개."""
        total = sum(len(v) for v in full_im_data.charts.values())
        assert total >= 5, f"차트 {total}개 (5개 이상 기대)"

    def test_chart_types_diverse(self, full_im_data: IMDocumentData) -> None:
        """chart_type 3+종."""
        types: set[str] = set()
        for chart_list in full_im_data.charts.values():
            for chart in chart_list:
                types.add(chart.chart_type)
        assert len(types) >= 3, f"차트 유형 {len(types)}종 (3종 이상 기대): {types}"

    def test_chart_data_non_empty(self, full_im_data: IMDocumentData) -> None:
        """모든 ChartData에 title, data 비어있지 않음."""
        for section_id, chart_list in full_im_data.charts.items():
            for i, chart in enumerate(chart_list):
                assert chart.title.strip() != "", f"[{section_id}][{i}] title 비어있음"
                assert len(chart.data) > 0, f"[{section_id}][{i}] data 비어있음"

    def test_chart_data_consistent_with_financials(
        self, full_im_data: IMDocumentData
    ) -> None:
        """매출 차트 값 = financial_statements.revenue 값."""
        fs_revenue = full_im_data.financial_statements.revenue
        revenue_values = list(fs_revenue.values())

        # financial_analysis 차트에서 매출 시리즈 찾기
        fa_charts = full_im_data.charts.get("financial_analysis", [])
        found_match = False
        for chart in fa_charts:
            for series in chart.data.get("bar_series", []):
                if series.get("name") == "매출액":
                    chart_values = series["values"]
                    assert chart_values == revenue_values, (
                        f"매출 차트 값 불일치: chart={chart_values} vs fs={revenue_values}"
                    )
                    found_match = True
        assert found_match, (
            "financial_analysis 차트에서 '매출액' bar_series를 찾을 수 없음"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestImFullPipeline (5)
# ══════════════════════════════════════════════════════════════════════════════


class TestImFullPipeline:
    """IM FULL 파이프라인 E2E 테스트."""

    @pytest.fixture(scope="class")
    def pipeline_result(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> PipelineResult:
        """파이프라인 실행 결과 (클래스 전체에서 공유)."""
        from src.design_renderer.pipeline import IMPipeline

        data = get_full_im_data()
        out_dir = tmp_path_factory.mktemp("im_full_output")
        pptx_path = out_dir / "test_im_full.pptx"

        pipeline = IMPipeline(continue_on_error=True)
        return pipeline.generate(data, pptx_path=pptx_path)

    def test_im_full_pipeline_success(self, pipeline_result: PipelineResult) -> None:
        """pipeline.generate() → success == True."""
        assert pipeline_result.success is True, (
            f"파이프라인 실패: errors={pipeline_result.errors}"
        )

    def test_im_full_slide_count_range(self, pipeline_result: PipelineResult) -> None:
        """30 ≤ slides ≤ 70."""
        count = pipeline_result.total_pptx_slides
        assert 30 <= count <= 70, f"슬라이드 {count}개 (30~70 기대)"

    def test_im_full_zero_errors(self, pipeline_result: PipelineResult) -> None:
        """errors 빈 리스트."""
        assert pipeline_result.errors == [], (
            f"에러 {len(pipeline_result.errors)}건: {pipeline_result.errors}"
        )

    def test_im_full_all_sections_rendered(
        self, pipeline_result: PipelineResult
    ) -> None:
        """section_results 19개 섹션 포함."""
        rendered_ids = {r.section_id for r in pipeline_result.section_results}
        assert len(rendered_ids) >= 19, (
            f"렌더링된 섹션 {len(rendered_ids)}개 (19개 이상 기대): {rendered_ids}"
        )

    def test_im_full_no_failed_sections(self, pipeline_result: PipelineResult) -> None:
        """failed_sections 빈 리스트."""
        failed = pipeline_result.failed_sections
        assert len(failed) == 0, (
            f"실패 섹션 {len(failed)}개: {[(f.section_id, f.error) for f in failed]}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestImFullDerivedMetrics (4)
# ══════════════════════════════════════════════════════════════════════════════


class TestImFullDerivedMetrics:
    """파생 지표 검증."""

    def test_derived_metrics_computed(self, full_im_data: IMDocumentData) -> None:
        """compute_derived_metrics() 후 None 아님."""
        assert full_im_data.derived_metrics is not None, (
            "derived_metrics가 None (compute_derived_metrics 미호출?)"
        )

    def test_revenue_cagr_5y_in_range(self, full_im_data: IMDocumentData) -> None:
        """-0.5 < CAGR < 1.0."""
        assert full_im_data.derived_metrics is not None
        cagr = full_im_data.derived_metrics.get("revenue_cagr_5y")
        assert cagr is not None, "revenue_cagr_5y 미계산"
        assert -0.5 < cagr < 1.0, f"revenue_cagr_5y={cagr:.4f} (범위 밖)"

    def test_operating_margin_latest_positive(
        self, full_im_data: IMDocumentData
    ) -> None:
        """영업이익률 > 0."""
        assert full_im_data.derived_metrics is not None
        margin = full_im_data.derived_metrics.get("operating_margin_latest")
        assert margin is not None, "operating_margin_latest 미계산"
        assert margin > 0, f"operating_margin_latest={margin:.4f} (양수 기대)"

    def test_debt_to_equity_reasonable(self, full_im_data: IMDocumentData) -> None:
        """0 ≤ D/E ≤ 5.0."""
        assert full_im_data.derived_metrics is not None
        de = full_im_data.derived_metrics.get("debt_to_equity_latest")
        assert de is not None, "debt_to_equity_latest 미계산"
        assert 0 <= de <= 5.0, f"debt_to_equity_latest={de:.4f} (0~5.0 기대)"


# ══════════════════════════════════════════════════════════════════════════════
# TestImFullCrossValidation (3)
# ══════════════════════════════════════════════════════════════════════════════


class TestImFullCrossValidation:
    """재무 데이터 내부 교차 검증 — 회귀 방지."""

    def test_segment_revenue_sum_equals_total_revenue(
        self, full_im_data: IMDocumentData
    ) -> None:
        """세그먼트 매출 합계 = 총매출 (모든 공통 연도, ±1 허용)."""
        fs = full_im_data.financial_statements
        sr = full_im_data.segment_revenue
        assert sr is not None, "segment_revenue가 None"
        common_years = set(fs.revenue.keys())
        for segment_data in sr.segments.values():
            common_years &= set(segment_data.keys())
        assert len(common_years) >= 3, (
            f"공통 연도 {len(common_years)}개 (3개 이상 기대)"
        )
        for year in sorted(common_years):
            total = sum(seg[year] for seg in sr.segments.values())
            assert abs(total - fs.revenue[year]) < 1, (
                f"{year}: 세그먼트 합계 {total:,.0f} ≠ 총매출 {fs.revenue[year]:,.0f}"
            )

    def test_balance_sheet_equation(self, full_im_data: IMDocumentData) -> None:
        """총자산 = 총부채 + 자기자본 (모든 공통 연도, ±1 허용)."""
        fs = full_im_data.financial_statements
        common_years = (
            set(fs.total_assets.keys())
            & set(fs.total_liabilities.keys())
            & set(fs.total_equity.keys())
        )
        assert len(common_years) >= 3, (
            f"공통 연도 {len(common_years)}개 (3개 이상 기대)"
        )
        for year in sorted(common_years):
            assets = fs.total_assets[year]
            rhs = fs.total_liabilities[year] + fs.total_equity[year]
            assert abs(assets - rhs) < 1, (
                f"{year}: 총자산 {assets:,.0f} ≠ 총부채({fs.total_liabilities[year]:,.0f})"
                f" + 자기자본({fs.total_equity[year]:,.0f}) = {rhs:,.0f}"
            )

    def test_deal_old_shares_consistent_with_stake_pct(
        self, full_im_data: IMDocumentData
    ) -> None:
        """old_shares = stake_pct × 총발행주식수 (±1주 허용)."""
        ds = full_im_data.deal_structure
        assert ds is not None, "deal_structure가 None"
        assert ds.old_shares is not None, "old_shares가 None"
        total_shares = sum(s.share_count for s in full_im_data.shareholders)
        expected = round(ds.stake_pct * total_shares)
        assert abs(ds.old_shares - expected) <= 1, (
            f"old_shares={ds.old_shares:,.0f} ≠ "
            f"stake_pct({ds.stake_pct:.0%}) × 총주식수({total_shares:,}) = {expected:,}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestImFullEdgeCases (2)
# ══════════════════════════════════════════════════════════════════════════════


class TestImFullEdgeCases:
    """경계/부정 케이스 테스트."""

    def test_pipeline_minimal_data_does_not_raise(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """최소 필드만 있는 IMDocumentData로 파이프라인 실행 시 예외 없이 PipelineResult 반환.

        continue_on_error=True 이므로 섹션 실패는 허용 —
        파이프라인 자체가 crash 되어서는 안 된다.
        """
        from src.design_renderer.pipeline import IMPipeline

        minimal = IMDocumentData(
            project_name="Minimal",
            company_name_kr="테스트",
            im_style=IMStyle.TITAN,
        )
        minimal.compute_derived_metrics()
        out = tmp_path_factory.mktemp("minimal_out") / "minimal.pptx"
        result = IMPipeline(continue_on_error=True).generate(minimal, pptx_path=out)
        assert result is not None, "PipelineResult가 None"

    def test_get_full_im_data_idempotent(self) -> None:
        """get_full_im_data() 두 번 호출 시 핵심 필드 동일 (부작용 없음)."""
        data1 = get_full_im_data()
        data2 = get_full_im_data()
        assert data1.project_name == data2.project_name
        assert data1.im_style == data2.im_style
        assert data1.company_name_kr == data2.company_name_kr
        assert data1.financial_statements.revenue == data2.financial_statements.revenue
