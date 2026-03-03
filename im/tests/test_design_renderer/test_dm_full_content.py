"""Phase 4 검증 테스트 — DM 완전한 콘텐츠 (32 tests).

get_full_dm_data()가 반환하는 IMDocumentData(DM 스타일)의 완성도를 검증한다.
기존 test_dm_pipeline.py(렌더러 메커닉스)와 비중복 — 여기서는 콘텐츠 품질과
완전한 데이터에 대한 E2E 파이프라인 검증을 수행한다.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from src.design_renderer.im_document import (
    DM_SECTIONS,
    IMDocumentData,
    IMStyle,
)
from src.design_renderer.sample_data.dm_full import get_full_dm_data
from src.design_renderer.sample_data.im_full import get_full_im_data
from src.design_renderer.sample_data.narratives_dm import get_dm_narrative_section_ids
from src.design_renderer.sample_data.tm_full import get_full_tm_data

if TYPE_CHECKING:
    from src.design_renderer.pipeline import PipelineResult

# ── 공통 상수 ──────────────────────────────────────────────────────────────────

KOREAN_RE = re.compile(r"[가-힣]")
PLACEHOLDER_RE = re.compile(r"(TODO|TBD|\{\{|\[INSERT\])", re.IGNORECASE)
NUMBER_RE = re.compile(r"\d[\d,.]*")

# DM 분석적 톤 용어 — 전체 섹션 매칭 기대
DM_ANALYTICAL_TERMS = [
    "분석",
    "리스크",
    "평가",
    "전략",
    "검토",
    "우려",
    "판단",
    "추정",
    "산출",
    "전망",
    "가정",
    "변동성",
    "민감도",
    "위협",
]


# ── 픽스처 ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def full_dm_data() -> IMDocumentData:
    """모듈 전체에서 공유하는 DM 데이터."""
    return get_full_dm_data()


# ══════════════════════════════════════════════════════════════════════════════
# TestDmFullDataCompleteness (10)
# ══════════════════════════════════════════════════════════════════════════════


class TestDmFullDataCompleteness:
    """DM 데이터 완성도 검증."""

    def test_full_dm_data_is_dm_style(self, full_dm_data: IMDocumentData) -> None:
        """im_style == DM."""
        assert full_dm_data.im_style == IMStyle.DM

    def test_dm_sections_count(self, full_dm_data: IMDocumentData) -> None:
        """len(sections) == len(DM_SECTIONS)."""
        expected = len(DM_SECTIONS)
        assert len(full_dm_data.sections) == expected, (
            f"섹션 {len(full_dm_data.sections)}개 ({expected}개 기대): "
            f"{full_dm_data.sections}"
        )

    def test_dm_sections_match_dm_preset(self, full_dm_data: IMDocumentData) -> None:
        """sections 내용이 DM_SECTIONS 프리셋과 일치."""
        assert full_dm_data.sections == DM_SECTIONS, (
            f"DM 섹션 불일치:\n  actual:   {full_dm_data.sections}\n"
            f"  expected: {DM_SECTIONS}"
        )

    def test_dm_financial_statements_populated(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """3년+ revenue + EBITDA."""
        fs = full_dm_data.financial_statements
        assert len(fs.revenue) >= 3, f"매출 {len(fs.revenue)}개 연도 (3개 이상 기대)"
        assert len(fs.ebitda) >= 3, f"EBITDA {len(fs.ebitda)}개 연도 (3개 이상 기대)"

    def test_dm_deal_structure_populated(self, full_dm_data: IMDocumentData) -> None:
        """seller, valuation_method, valuation_low/high 존재."""
        ds = full_dm_data.deal_structure
        assert ds is not None, "deal_structure가 None"
        assert ds.seller.strip() != "", "seller 비어있음"
        assert ds.valuation_method is not None and ds.valuation_method.strip() != "", (
            "valuation_method 비어있음"
        )
        assert ds.valuation_low is not None, "valuation_low 미설정"
        assert ds.valuation_high is not None, "valuation_high 미설정"

    def test_dm_market_data_populated(self, full_dm_data: IMDocumentData) -> None:
        """tam, competitors >= 1, industry_trends >= 1."""
        md = full_dm_data.market_data
        assert md is not None, "market_data가 None"
        assert md.tam is not None and md.tam > 0, "tam 미설정"
        assert len(md.competitors) >= 1, (
            f"경쟁사 {len(md.competitors)}개 (1개 이상 기대)"
        )
        assert len(md.industry_trends) >= 1, (
            f"산업 트렌드 {len(md.industry_trends)}개 (1개 이상 기대)"
        )

    def test_dm_investment_highlights_minimum_3(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """investment_highlights >= 3."""
        assert len(full_dm_data.investment_highlights) >= 3, (
            f"투자 하이라이트 {len(full_dm_data.investment_highlights)}개 (3개 이상 기대)"
        )

    def test_dm_company_overview_basic_fields(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """headquarters, key_products, employee_count 설정됨."""
        co = full_dm_data.company_overview
        assert co is not None, "company_overview가 None"
        assert co.headquarters.strip() != "", "headquarters 비어있음"
        assert len(co.key_products) >= 1, "key_products 비어있음"
        assert co.employee_count is not None and co.employee_count > 0, (
            "employee_count 미설정"
        )

    def test_dm_valuation_data_populated(self, full_dm_data: IMDocumentData) -> None:
        """valuation_data에 EV, EV/EBITDA, IRR/MOIC 시나리오 존재."""
        vd = full_dm_data.valuation_data
        assert vd is not None, "valuation_data가 None"
        assert len(vd.ev) >= 1, f"EV {len(vd.ev)}개 연도 (1개 이상 기대)"
        assert len(vd.ev_ebitda) >= 1, "EV/EBITDA 배수 미설정"
        assert len(vd.irr_scenarios) >= 1, "IRR 시나리오 미설정"
        assert len(vd.moic_scenarios) >= 1, "MOIC 시나리오 미설정"

    def test_dm_contacts_populated(self, full_dm_data: IMDocumentData) -> None:
        """연락처 2명 이상, name·email 비어있지 않음."""
        assert len(full_dm_data.contacts) >= 2, (
            f"연락처 {len(full_dm_data.contacts)}명 (2명 이상 기대)"
        )
        for i, c in enumerate(full_dm_data.contacts):
            assert c.name.strip() != "", f"contacts[{i}] name 비어있음"
            assert c.email.strip() != "", f"contacts[{i}] email 비어있음"


# ══════════════════════════════════════════════════════════════════════════════
# TestDmFullNarratives (6)
# ══════════════════════════════════════════════════════════════════════════════


class TestDmFullNarratives:
    """DM 내러티브 품질 검증."""

    def test_dm_narratives_cover_6_sections(self, full_dm_data: IMDocumentData) -> None:
        """6개 DM_SECTION_IDS 키 존재."""
        expected_ids = set(get_dm_narrative_section_ids())
        actual_ids = set(full_dm_data.narratives.keys())
        missing = expected_ids - actual_ids
        assert not missing, f"누락된 DM 내러티브 섹션: {missing}"

    def test_dm_narrative_minimum_length(self, full_dm_data: IMDocumentData) -> None:
        """각 DM 내러티브 >= 200자."""
        for section_id, text in full_dm_data.narratives.items():
            assert len(text) >= 200, (
                f"'{section_id}' 내러티브 {len(text)}자 (200자 이상 기대)"
            )

    def test_dm_narratives_korean_text(self, full_dm_data: IMDocumentData) -> None:
        """모든 DM 내러티브에 한국어 포함."""
        for section_id, text in full_dm_data.narratives.items():
            assert KOREAN_RE.search(text), f"'{section_id}' 내러티브에 한국어 없음"

    def test_dm_narratives_no_placeholders(self, full_dm_data: IMDocumentData) -> None:
        """플레이스홀더 텍스트 없음."""
        for section_id, text in full_dm_data.narratives.items():
            match = PLACEHOLDER_RE.search(text)
            assert match is None, (
                f"'{section_id}' 내러티브에 플레이스홀더 발견: '{match.group()}'"
            )

    def test_dm_narrative_analytical_tone(self, full_dm_data: IMDocumentData) -> None:
        """전체 내러티브에 분석 용어 포함."""
        expected_count = len(get_dm_narrative_section_ids())
        sections_with_analytical = 0
        for text in full_dm_data.narratives.values():
            if any(term in text for term in DM_ANALYTICAL_TERMS):
                sections_with_analytical += 1
        assert sections_with_analytical >= expected_count, (
            f"분석적 톤 내러티브 {sections_with_analytical}개 "
            f"({expected_count}개 전체 기대)"
        )

    def test_dm_risk_narrative_identifies_risks(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """dm_risk_assessment에 2+종 리스크 유형 언급."""
        risk_text = full_dm_data.narratives.get("dm_risk_assessment", "")
        risk_types = ["시장 리스크", "운영 리스크", "재무 리스크", "규제 리스크"]
        found = [rt for rt in risk_types if rt in risk_text]
        assert len(found) >= 2, (
            f"리스크 유형 {len(found)}개 발견 (2개 이상 기대): {found}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestDmFullCharts (2)
# ══════════════════════════════════════════════════════════════════════════════


class TestDmFullCharts:
    """DM 차트 데이터 검증."""

    def test_dm_charts_count_minimum_5(self, full_dm_data: IMDocumentData) -> None:
        """전체 ChartData 5+개."""
        total = sum(len(v) for v in full_dm_data.charts.values())
        assert total >= 5, f"차트 {total}개 (5개 이상 기대)"

    def test_dm_chart_data_non_empty(self, full_dm_data: IMDocumentData) -> None:
        """모든 ChartData에 title, data 비어있지 않음."""
        for section_id, chart_list in full_dm_data.charts.items():
            for i, chart in enumerate(chart_list):
                assert chart.title.strip() != "", f"[{section_id}][{i}] title 비어있음"
                assert len(chart.data) > 0, f"[{section_id}][{i}] data 비어있음"


# ══════════════════════════════════════════════════════════════════════════════
# TestDmFullPipeline (4)
# ══════════════════════════════════════════════════════════════════════════════


class TestDmFullPipeline:
    """DM 완전한 데이터에 대한 E2E 파이프라인 검증."""

    @pytest.fixture(scope="class")
    def pipeline_result(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> PipelineResult:
        """파이프라인 실행 결과 (클래스 전체에서 공유)."""
        from src.design_renderer.pipeline import IMPipeline

        data = get_full_dm_data()
        out_dir = tmp_path_factory.mktemp("dm_full_output")
        pptx_path = out_dir / "test_dm_full.pptx"

        pipeline = IMPipeline(continue_on_error=True)
        return pipeline.generate(data, pptx_path=pptx_path)

    def test_dm_full_pipeline_success(self, pipeline_result: PipelineResult) -> None:
        """pipeline.generate() 성공."""
        assert pipeline_result.success is True, (
            f"파이프라인 실패: errors={pipeline_result.errors}"
        )

    def test_dm_full_slide_count_8(self, pipeline_result: PipelineResult) -> None:
        """slides >= 8."""
        count = pipeline_result.total_pptx_slides
        assert count >= 8, f"슬라이드 {count}개 (8개 이상 기대)"

    def test_dm_full_zero_errors(self, pipeline_result: PipelineResult) -> None:
        """errors 없음."""
        assert pipeline_result.errors == [], (
            f"에러 {len(pipeline_result.errors)}건: {pipeline_result.errors}"
        )

    def test_dm_full_no_failed_sections(self, pipeline_result: PipelineResult) -> None:
        """failed_sections 없음."""
        failed = pipeline_result.failed_sections
        assert len(failed) == 0, (
            f"실패 섹션 {len(failed)}개: {[(f.section_id, f.error) for f in failed]}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestDmFullDerivedMetrics (2)
# ══════════════════════════════════════════════════════════════════════════════


class TestDmFullDerivedMetrics:
    """DM 파생 지표 검증."""

    def test_dm_derived_metrics_computed(self, full_dm_data: IMDocumentData) -> None:
        """compute_derived_metrics() 후 None 아님."""
        assert full_dm_data.derived_metrics is not None, (
            "derived_metrics가 None (compute_derived_metrics 미호출?)"
        )

    def test_dm_operating_margin_latest_positive(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """영업이익률 > 0."""
        assert full_dm_data.derived_metrics is not None
        margin = full_dm_data.derived_metrics.get("operating_margin_latest")
        assert margin is not None, "operating_margin_latest 미계산"
        assert margin > 0, f"operating_margin_latest={margin:.4f} (양수 기대)"


# ══════════════════════════════════════════════════════════════════════════════
# TestDmContentQuality (8)
# ══════════════════════════════════════════════════════════════════════════════


class TestDmContentQuality:
    """DM 콘텐츠 품질 및 독립성 검증."""

    def test_dm_valuation_narrative_has_method(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """dm_valuation에 밸류에이션 방법론 언급 (EV/EBITDA, DCF 등)."""
        val_text = full_dm_data.narratives.get("dm_valuation", "")
        methods = ["EV/EBITDA", "DCF", "PER", "PBR", "PSR"]
        found = [m for m in methods if m in val_text]
        assert len(found) >= 1, f"밸류에이션 방법론 {len(found)}개 발견 (1개 이상 기대)"

    def test_dm_deal_structure_narrative_has_terms(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """'지분', '매각', '인수' 등 거래 용어 참조."""
        deal_text = full_dm_data.narratives.get("dm_deal_structure", "")
        deal_terms = ["지분", "매각", "인수", "거래", "클로징"]
        found = [t for t in deal_terms if t in deal_text]
        assert len(found) >= 2, (
            f"거래 용어 {len(found)}개 발견 (2개 이상 기대): {found}"
        )

    def test_dm_summary_narrative_is_concise(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """200~2000자."""
        summary_text = full_dm_data.narratives.get("dm_summary", "")
        length = len(summary_text)
        assert 200 <= length <= 2000, f"dm_summary {length}자 (200~2000자 기대)"

    def test_dm_data_independent_from_tm(self) -> None:
        """im_style=DM, TM과 별도 객체."""
        dm_data = get_full_dm_data()
        tm_data = get_full_tm_data()
        assert dm_data is not tm_data, "DM과 TM이 동일 객체"
        assert dm_data.im_style != tm_data.im_style, (
            f"DM im_style={dm_data.im_style} == TM im_style={tm_data.im_style}"
        )
        assert dm_data.im_style == IMStyle.DM
        # narratives 키도 다른지 확인
        dm_keys = set(dm_data.narratives.keys())
        tm_keys = set(tm_data.narratives.keys())
        assert dm_keys != tm_keys, "DM과 TM의 narrative 키가 동일 — 별도 콘텐츠여야 함"

    def test_dm_data_independent_from_im(self) -> None:
        """im_style=DM, IM과 별도 객체."""
        dm_data = get_full_dm_data()
        im_data = get_full_im_data()
        assert dm_data is not im_data, "DM과 IM이 동일 객체"
        assert dm_data.im_style != im_data.im_style, (
            f"DM im_style={dm_data.im_style} == IM im_style={im_data.im_style}"
        )
        # narratives 키도 다른지 확인
        dm_keys = set(dm_data.narratives.keys())
        im_keys = set(im_data.narratives.keys())
        assert dm_keys != im_keys, "DM과 IM의 narrative 키가 동일 — 별도 콘텐츠여야 함"

    def test_dm_investment_thesis_references_financials(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """dm_investment_thesis에 재무 지표 1+개 참조."""
        thesis_text = full_dm_data.narratives.get("dm_investment_thesis", "")
        financial_terms = [
            "매출",
            "영업이익",
            "EBITDA",
            "CAGR",
            "이익률",
            "현금흐름",
            "IRR",
            "MOIC",
        ]
        found = [t for t in financial_terms if t in thesis_text]
        assert len(found) >= 1, f"재무 지표 참조 {len(found)}개 발견 (1개 이상 기대)"

    def test_dm_valuation_numbers_consistent_with_data(
        self, full_dm_data: IMDocumentData
    ) -> None:
        """dm_valuation 내러티브 핵심 수치가 재무 데이터와 정합."""
        val_text = full_dm_data.narratives.get("dm_valuation", "")
        fs = full_dm_data.financial_statements
        # EBITDA 2025E: 46,080백만원 → 약 461억원 (내러티브에 "461" 존재해야 함)
        ebitda_billions = round(fs.ebitda["2025E"] / 100)
        assert str(ebitda_billions) in val_text, (
            f"dm_valuation에 EBITDA {ebitda_billions}억원 근사치 미참조"
        )

    def test_dm_omits_non_dm_fields(self, full_dm_data: IMDocumentData) -> None:
        """DM은 management_team, shareholders 등을 포함하지 않아야 함."""
        assert len(full_dm_data.management_team) == 0, (
            f"DM에 management_team {len(full_dm_data.management_team)}명 혼입"
        )
        assert len(full_dm_data.shareholders) == 0, (
            f"DM에 shareholders {len(full_dm_data.shareholders)}명 혼입"
        )
        assert full_dm_data.growth_strategy is None, "DM에 growth_strategy 혼입"
        assert full_dm_data.segment_revenue is None, "DM에 segment_revenue 혼입"
        assert len(full_dm_data.key_customers) == 0, (
            f"DM에 key_customers {len(full_dm_data.key_customers)}개 혼입"
        )
