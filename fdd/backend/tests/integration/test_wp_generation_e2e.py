"""E2E 테스트 — WP 생성 전체 파이프라인.

엔진(Phase 1~4) → Report IR → 교차검증 → Blueprint → 시트 구조 검증.
실제 DB/LLM 없이 순수 함수 조합으로 전체 흐름을 검증한다.
"""

import pytest
from decimal import Decimal

from app.engines.multiperiod_engine import (
    LineItemDef,
    compute_multiperiod_is,
)
from app.engines.revenue_engine import (
    compute_revenue_breakdown,
)
from app.engines.cost_engine import (
    compute_manufacturing_cost,
)
from app.engines.fcf_engine import (
    compute_fcf_bridge,
)
from app.engines.backlog_engine import (
    compute_backlog_summary,
)
from app.engines.qualitative_engine import (
    InterviewNote,
    structure_interviews,
    extract_themes,
)
from app.services.report.deal_profile import DealProfile, DealProfileResolver
from app.services.report.blueprint import WorkbookBlueprint
from app.services.report.validation import (
    run_cross_validation,
    run_full_validation,
)
from app.renderers.report_builder import (
    build_multiperiod_is_block,
    build_revenue_by_customer_block,
    build_cost_manufacturing_block,
    build_fcf_bridge_block,
    build_backlog_summary_block,
)


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def sample_deal_profile():
    """샘플 딜 프로파일 — 모든 조건 활성화."""
    return DealProfile(
        deal_type="completion_accounts",
        structure="multi_entity",
        industry="manufacturing",
        entity_count=3,
        has_foreign_subsidiary=True,
        has_backlog_data=True,
        has_interview_data=True,
        has_detailed_cost=True,
    )


@pytest.fixture
def sample_line_items():
    """샘플 손익계산서 행 정의."""
    return [
        LineItemDef(code="REV", name_ko="매출액", name_en="Revenue", category="REVENUE", statement_type="IS", display_order=1),
        LineItemDef(code="COGS", name_ko="매출원가", name_en="COGS", category="COGS", statement_type="IS", display_order=2),
        LineItemDef(code="GP", name_ko="매출총이익", name_en="Gross Profit", category="GROSS_PROFIT", statement_type="IS", display_order=3, is_subtotal=True),
        LineItemDef(code="SGA", name_ko="판관비", name_en="SG&A", category="SGA", statement_type="IS", display_order=4),
        LineItemDef(code="OI", name_ko="영업이익", name_en="Operating Income", category="OPERATING_INCOME", statement_type="IS", display_order=5, is_subtotal=True),
    ]


@pytest.fixture
def sample_amounts():
    """3년 다기간 손익 데이터."""
    return {
        "FY2022": {
            "REV": Decimal("1000.00"),
            "COGS": Decimal("600.00"),
            "GP": Decimal("400.00"),
            "SGA": Decimal("200.00"),
            "OI": Decimal("200.00"),
        },
        "FY2023": {
            "REV": Decimal("1200.00"),
            "COGS": Decimal("700.00"),
            "GP": Decimal("500.00"),
            "SGA": Decimal("220.00"),
            "OI": Decimal("280.00"),
        },
        "FY2024": {
            "REV": Decimal("1500.00"),
            "COGS": Decimal("850.00"),
            "GP": Decimal("650.00"),
            "SGA": Decimal("250.00"),
            "OI": Decimal("400.00"),
        },
    }


# ── E2E Tests ──────────────────────────────────────────────

class TestE2EEngineToIR:
    """엔진 → Report IR 블록 변환 E2E."""

    def test_multiperiod_is_to_block(self, sample_line_items, sample_amounts):
        """다기간 IS 엔진 → 블록 변환."""
        result, evidence = compute_multiperiod_is(sample_amounts, sample_line_items)

        assert len(result.rows) == 5
        assert abs(result.rows[0].periods["FY2024"]) == Decimal("1500.0000")

        # YoY 계산 검증
        rev_yoy = result.rows[0].yoy_changes.get("FY2024")
        assert rev_yoy is not None

        # CAGR — 기간 수/부호 조건에 따라 None일 수 있음
        # 3년 데이터이므로 산출 시도는 되었을 것

        # 블록 변환 — TableBlock dataclass
        block = build_multiperiod_is_block(result)
        assert block.type.value == "table"
        assert len(block.rows) == 5
        assert len(evidence) > 0

    def test_revenue_breakdown_to_block(self):
        """매출 breakdown 엔진 → 블록 변환."""
        entries = [
            {"customer_name": "A사", "amount": Decimal("500"), "period": "FY2024"},
            {"customer_name": "B사", "amount": Decimal("300"), "period": "FY2024"},
            {"customer_name": "C사", "amount": Decimal("200"), "period": "FY2024"},
        ]
        result, evidence = compute_revenue_breakdown(
            entries,
            dimension="customer",
            dimension_key="customer_name",
            periods=["FY2024"],
        )

        assert len(result.breakdown) == 3
        assert result.top_n_share > Decimal("0")

        block = build_revenue_by_customer_block(result)
        assert block.type.value == "table"
        assert len(block.rows) >= 3

    def test_cost_manufacturing_to_block(self):
        """제조원가 엔진 → 블록 변환."""
        cost_entries = [
            {"cost_category": "DIRECT_MATERIAL", "amount": "300", "period": "FY2024"},
            {"cost_category": "DIRECT_LABOR", "amount": "200", "period": "FY2024"},
            {"cost_category": "OVERHEAD", "amount": "100", "period": "FY2024"},
        ]
        result, evidence = compute_manufacturing_cost(
            cost_entries,
            revenue_by_period={"FY2024": Decimal("1500")},
        )

        assert result.total_cogs["FY2024"] == Decimal("600.0000")

        block = build_cost_manufacturing_block(result)
        assert block.type.value == "table"
        assert len(block.rows) >= 3

    def test_fcf_bridge_to_block(self):
        """FCF Bridge 엔진 → 블록 변환."""
        fcf_inputs = {
            "FY2024": {
                "ebitda": "500",
                "depreciation_amortization": "60",
                "delta_ar": "20",
                "delta_inventory": "10",
                "delta_ap": "5",
                "tax_paid": "80",
                "other_operating": "10",
                "capex": "120",
            },
        }
        result, evidence = compute_fcf_bridge(fcf_inputs)

        assert len(result.periods) == 1
        pd = result.periods["FY2024"]
        assert pd.ebitda == Decimal("500.0000")

        block = build_fcf_bridge_block(result)
        assert block.type.value == "table"

    def test_backlog_summary_to_block(self):
        """수주잔액 엔진 → 블록 변환."""
        orders = [
            {"customer_name": "X사", "amount": "500"},
            {"customer_name": "Y사", "amount": "300"},
        ]
        result, evidence = compute_backlog_summary(
            orders,
            revenue_total=Decimal("1000"),
            new_orders_total=Decimal("900"),
        )

        assert result.total_backlog == Decimal("800.0000")
        assert len(result.backlog_by_customer) == 2

        block = build_backlog_summary_block(result)
        assert block.type.value == "table"


class TestE2EBlueprintValidation:
    """Blueprint → 교차검증 E2E."""

    def test_full_blueprint(self, sample_deal_profile):
        """전체 프로파일 → Blueprint 생성 → 시트 수 검증."""
        bp = WorkbookBlueprint(sample_deal_profile)
        sheets = bp.build()

        assert bp.total_sheets() >= 35
        categories = bp.get_categories()
        assert "수주 분석" in categories
        assert "연결 분석" in categories
        assert "정성적 분석" in categories
        assert "비용 분석" in categories

    def test_locked_box_excludes_nwc_peg(self):
        """Locked Box → NWC Peg 제외, Leakage Check 포함."""
        profile = DealProfile(deal_type="locked_box")
        bp = WorkbookBlueprint(profile)
        ids = bp.get_sheet_ids()

        assert "leakage_check" in ids
        assert "nwc_peg" not in ids

    def test_minimal_profile(self):
        """최소 프로파일 → 조건부 시트 미포함."""
        bp = WorkbookBlueprint(DealProfile())
        ids = bp.get_sheet_ids()

        assert "backlog_summary" not in ids
        assert "entity_pl" not in ids
        assert "interview_notes" not in ids
        assert "cost_mfg" not in ids

        assert "index" in ids
        assert "cover" in ids
        assert "qoe_bridge" in ids

    def test_cross_validation_all_pass(self):
        """Report IR 교차검증 — 모든 규칙 통과."""
        report_ir = {
            "metadata": {"deal_id": "test-deal-001"},
            "sections": [
                {
                    "type": "table",
                    "title": "IS (Multi-period)",
                    "rows": [
                        {"label": "매출액", "amount": "1000.00"},
                        {"label": "매출원가", "amount": "600.00"},
                        {"label": "판관비", "amount": "200.00"},
                    ],
                },
                {
                    "type": "table",
                    "title": "QoE Bridge",
                    "rows": [
                        {"label": "Reported Revenue", "amount": "1000.00"},
                        {"label": "Reported EBITDA", "amount": "200.00"},
                        {"label": "Total Adjustments", "amount": "30.00"},
                        {"label": "Adjusted EBITDA", "amount": "230.00"},
                    ],
                },
                {
                    "type": "table",
                    "title": "Net Debt Schedule",
                    "rows": [
                        {"label": "Total Debt", "amount": "500.00"},
                        {"label": "Cash", "amount": "150.00"},
                        {"label": "Net Debt", "amount": "350.00"},
                    ],
                },
                {
                    "type": "table",
                    "title": "FCF Bridge",
                    "rows": [
                        {"label": "Operating Cash Flow", "amount": "180.00"},
                        {"label": "Total CAPEX", "amount": "80.00"},
                        {"label": "Free Cash Flow", "amount": "100.00"},
                    ],
                },
                {
                    "type": "table",
                    "title": "Revenue by Customer",
                    "rows": [],
                    "footer_rows": [
                        {"label": "합계", "amount": "1000.00"},
                    ],
                },
            ],
        }

        qa_result, findings = run_cross_validation(report_ir)
        assert qa_result.passed is True
        assert qa_result.error_count == 0

    def test_cross_validation_detects_mismatch(self):
        """교차검증 — 불일치 감지."""
        report_ir = {
            "sections": [
                {
                    "type": "table",
                    "title": "Net Debt Schedule",
                    "rows": [
                        {"label": "Total Debt", "amount": "500.00"},
                        {"label": "Cash", "amount": "150.00"},
                        {"label": "Net Debt", "amount": "999.00"},
                    ],
                },
            ],
        }

        qa_result, findings = run_cross_validation(report_ir)
        error_findings = [f for f in findings if f.severity.name == "ERROR"]
        assert len(error_findings) >= 1

    def test_full_validation_summary(self):
        """전체 검증 요약."""
        report_ir = {"sections": []}
        summary = run_full_validation(report_ir)

        assert summary["version"] == "0.1.0"
        assert "overall_passed" in summary
        assert "rules" in summary


class TestE2EQualitative:
    """정성적 분석 E2E."""

    def test_interview_to_themes(self):
        """인터뷰 → 구조화 → 테마 추출 파이프라인."""
        # structure_interviews / extract_themes는 list[dict] 입력
        raw_notes = [
            {
                "source": "CFO",
                "topic": "매출",
                "content": "매출이 최근 3년간 꾸준히 성장했습니다. 신규 고객 확보가 주요 요인입니다.",
            },
            {
                "source": "COO",
                "topic": "운영",
                "content": "생산능력이 한계에 가까워지고 있어 CAPEX 투자가 필요합니다. 최근 이직율이 높아 핵심인력 유출 우려가 있고, 소송 리스크도 존재합니다.",
            },
            {
                "source": "영업팀장",
                "topic": "수주",
                "content": "수주잔고가 충분하여 향후 2년간 매출 성장이 전망됩니다. 다만 특정 고객 의존도가 높습니다.",
            },
        ]

        # 구조화
        struct_result, struct_evidence = structure_interviews(raw_notes)
        assert len(struct_result.notes) == 3
        assert struct_result.total_notes == 3

        # 테마 추출 — 구조화된 InterviewNote 객체를 입력
        theme_result, theme_evidence = extract_themes(struct_result.notes)
        assert len(theme_result.themes) > 0

        # 리스크 플래그 확인
        all_flags = []
        for note in struct_result.notes:
            all_flags.extend(note.risk_flags)
        assert len(all_flags) > 0


class TestE2EProfileVariants:
    """다양한 DealProfile 변형 E2E."""

    @pytest.mark.parametrize("deal_type,expected_in,expected_not_in", [
        ("completion_accounts", ["nwc_peg"], ["leakage_check"]),
        ("locked_box", ["leakage_check"], ["nwc_peg"]),
        ("general", [], ["nwc_peg", "leakage_check"]),
    ])
    def test_deal_type_variants(self, deal_type, expected_in, expected_not_in):
        """거래구조별 시트 포함/제외."""
        profile = DealProfile(deal_type=deal_type)
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        for sheet_id in expected_in:
            assert sheet_id in ids, f"{sheet_id} should be in {deal_type}"
        for sheet_id in expected_not_in:
            assert sheet_id not in ids, f"{sheet_id} should not be in {deal_type}"

    @pytest.mark.parametrize("entity_count,has_consolidation", [
        (1, False),
        (2, True),
        (5, True),
    ])
    def test_entity_count_variants(self, entity_count, has_consolidation):
        """엔티티 수별 연결 시트 포함/제외."""
        profile = DealProfile(entity_count=entity_count)
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert ("entity_pl" in ids) == has_consolidation
