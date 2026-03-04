"""Report Builder 골든 테스트 — Sprint 7.

Report IR 생성과 블록 빌더 함수들의 골든 케이스를 테스트합니다.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.renderers.report_builder import (
    AlignType,
    AppendixBlock,
    AppendixItem,
    # Block Types
    BlockType,
    ChartBlock,
    ChartData,
    ChartType,
    ClaimBlock,
    # Blocks
    CoverBlock,
    EvidenceRef,
    IssueBlock,
    IssueItem,
    KPIBlock,
    MethodologyBlock,
    MethodologyItem,
    # IR
    ReportIR,
    ReportMetadata,
    RiskLevel,
    ScopeBlock,
    ScopeItem,
    TableBlock,
    TableColumn,
    TextBlock,
    build_claim_block,
    build_issue_block,
    build_issue_summary_table_block,
    build_kpi_block,
    build_methodology_block,
    build_net_debt_schedule_block,
    build_nwc_definition_table_block,
    build_nwc_peg_table_block,
    build_nwc_trend_table_block,
    build_qoe_adjustments_table_block,
    # Builders
    build_qoe_table_block,
    build_scope_block,
    build_text_block,
    build_waterfall_chart_block,
    # Serialization
    report_ir_to_dict,
)

# =============================================================================
# Golden Test: Block Types
# =============================================================================


class TestBlockTypesGolden:
    """블록 타입 골든 테스트."""

    def test_all_block_types_exist(self) -> None:
        """모든 필수 블록 타입이 존재해야 함."""
        required_types = [
            "cover",
            "kpi",
            "table",
            "chart",
            "text",
            "claim",
            "issue",
            "methodology",
            "scope",
            "appendix",
        ]
        for bt in required_types:
            assert bt in [b.value for b in BlockType], f"Missing block type: {bt}"

    def test_chart_types_complete(self) -> None:
        """필수 차트 타입이 존재해야 함."""
        required = ["waterfall", "bar", "line", "pie"]
        for ct in required:
            assert ct in [c.value for c in ChartType], f"Missing chart type: {ct}"


# =============================================================================
# Golden Test: Cover Block
# =============================================================================


class TestCoverBlockGolden:
    """CoverBlock 골든 테스트."""

    def test_cover_full_data(self) -> None:
        """전체 필드가 포함된 Cover 블록."""
        block = CoverBlock(
            deal_name="Project Alpha Acquisition",
            deal_type="Buy-Side FDD",
            target_name="Alpha Corp",
            date=date(2026, 3, 15),
            prepared_by="Due Diligence Team",
            confidentiality="STRICTLY CONFIDENTIAL",
            logo_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA",
        )
        assert block.type == BlockType.COVER
        assert block.deal_name == "Project Alpha Acquisition"
        assert block.target_name == "Alpha Corp"

    def test_cover_minimal(self) -> None:
        """최소 필드만 포함된 Cover 블록."""
        block = CoverBlock(deal_name="Minimal Deal")
        assert block.deal_name == "Minimal Deal"
        assert block.confidentiality == "CONFIDENTIAL"  # default


# =============================================================================
# Golden Test: KPI Block
# =============================================================================


class TestKPIBlockGolden:
    """KPIBlock 골든 테스트."""

    def test_kpi_fdd_summary(self) -> None:
        """FDD Executive Summary KPI."""
        block = build_kpi_block(
            title="Financial Highlights",
            kpis=[
                ("Revenue", "125,000", "백만원"),
                ("Adjusted EBITDA", "18,750", "백만원"),
                ("EBITDA Margin", "15.0%", None),
                ("Net Debt", "45,000", "백만원"),
            ],
            columns=4,
        )
        assert block.type == BlockType.KPI
        assert len(block.kpis) == 4
        assert block.kpis[0]["label"] == "Revenue"
        assert block.kpis[2]["unit"] is None

    def test_kpi_3column_layout(self) -> None:
        """3열 레이아웃."""
        block = build_kpi_block(
            title="Key Metrics",
            kpis=[
                ("Metric1", "100", "단위"),
                ("Metric2", "200", "단위"),
                ("Metric3", "300", "단위"),
            ],
            columns=3,
        )
        assert block.columns == 3


# =============================================================================
# Golden Test: Table Blocks (6종)
# =============================================================================


class TestTableBlocksGolden:
    """TableBlock 6종 골든 테스트."""

    def test_qoe_bridge_table(self) -> None:
        """QoE Bridge 테이블."""
        bridge_data = [
            {"category": "Revenue", "FY2024": "100,000", "FY2025": "120,000"},
            {"category": "COGS", "FY2024": "(70,000)", "FY2025": "(84,000)"},
            {"category": "Gross Profit", "FY2024": "30,000", "FY2025": "36,000"},
            {"category": "SG&A", "FY2024": "(15,000)", "FY2025": "(18,000)"},
            {"category": "EBITDA", "FY2024": "15,000", "FY2025": "18,000"},
        ]
        block = build_qoe_table_block("QoE Bridge", bridge_data, ["FY2024", "FY2025"])
        assert block.type == BlockType.TABLE
        assert block.title == "QoE Bridge"
        assert len(block.columns) == 3
        assert len(block.rows) == 5

    def test_qoe_adjustments_table(self) -> None:
        """QoE 조정 상세 테이블."""
        adjustments = [
            {
                "category": "Non-recurring",
                "description": "법적 합의금",
                "amount": "1,500",
                "status": "approved",
                "evidence": "Yes",
            },
            {
                "category": "Non-operating",
                "description": "자산 처분익",
                "amount": "(500)",
                "status": "approved",
                "evidence": "Yes",
            },
            {
                "category": "Normalization",
                "description": "대표이사 급여 조정",
                "amount": "800",
                "status": "proposed",
                "evidence": "No",
            },
        ]
        block = build_qoe_adjustments_table_block("QoE Adjustments", adjustments)
        assert len(block.columns) == 5
        assert len(block.rows) == 3

    def test_nwc_definition_table(self) -> None:
        """NWC 정의 테이블."""
        items = [
            {
                "account": "매출채권",
                "classification": "above_the_line",
                "balance": "15,000",
                "included": "Yes",
            },
            {
                "account": "재고자산",
                "classification": "above_the_line",
                "balance": "8,000",
                "included": "Yes",
            },
            {
                "account": "매입채무",
                "classification": "above_the_line",
                "balance": "(10,000)",
                "included": "Yes",
            },
            {
                "account": "현금",
                "classification": "excluded",
                "balance": "5,000",
                "included": "No",
            },
        ]
        block = build_nwc_definition_table_block("NWC Definition", items)
        assert len(block.columns) == 4
        assert len(block.rows) == 4

    def test_nwc_trend_table(self) -> None:
        """NWC 월별 트렌드 테이블."""
        months = ["2024-10", "2024-11", "2024-12"]
        trend_data = [
            {
                "item": "Current Assets",
                "2024-10": "50,000",
                "2024-11": "52,000",
                "2024-12": "55,000",
            },
            {
                "item": "Current Liabilities",
                "2024-10": "(30,000)",
                "2024-11": "(31,000)",
                "2024-12": "(32,000)",
            },
            {
                "item": "NWC",
                "2024-10": "20,000",
                "2024-11": "21,000",
                "2024-12": "23,000",
            },
        ]
        block = build_nwc_trend_table_block("NWC Trend", trend_data, months)
        assert len(block.columns) == 4  # item + 3 months
        assert len(block.rows) == 3

    def test_nwc_peg_table(self) -> None:
        """NWC Peg 시나리오 테이블."""
        scenarios = [
            {
                "method": "Average (12M)",
                "target_nwc": "21,000",
                "adjustment": "(2,000)",
                "notes": "Recommended",
            },
            {
                "method": "Median (12M)",
                "target_nwc": "20,500",
                "adjustment": "(2,500)",
                "notes": "",
            },
            {
                "method": "Latest Month",
                "target_nwc": "23,000",
                "adjustment": "0",
                "notes": "",
            },
            {
                "method": "Buyer Proposed",
                "target_nwc": "18,000",
                "adjustment": "(5,000)",
                "notes": "Under discussion",
            },
        ]
        block = build_nwc_peg_table_block("NWC Peg Scenarios", scenarios)
        assert len(block.columns) == 4
        assert len(block.rows) == 4

    def test_net_debt_schedule(self) -> None:
        """Net Debt 스케줄 테이블."""
        items = [
            {
                "item": "Bank Loan A",
                "type": "debt",
                "balance": "30,000",
                "adjustment": "0",
                "adjusted": "30,000",
            },
            {
                "item": "Bank Loan B",
                "type": "debt",
                "balance": "20,000",
                "adjustment": "0",
                "adjusted": "20,000",
            },
            {
                "item": "Lease Liabilities",
                "type": "debt_like",
                "balance": "5,000",
                "adjustment": "0",
                "adjusted": "5,000",
            },
            {
                "item": "Cash",
                "type": "cash",
                "balance": "(8,000)",
                "adjustment": "0",
                "adjusted": "(8,000)",
            },
            {
                "item": "Short-term Deposits",
                "type": "cash_like",
                "balance": "(2,000)",
                "adjustment": "0",
                "adjusted": "(2,000)",
            },
        ]
        block = build_net_debt_schedule_block("Net Debt Schedule", items)
        assert len(block.columns) == 5
        assert len(block.rows) == 5

    def test_issue_summary_table(self) -> None:
        """이슈 요약 테이블."""
        issues = [
            {
                "id": "ISS-001",
                "category": "QoE",
                "severity": "high",
                "title": "비경상 항목 미분류",
                "status": "open",
            },
            {
                "id": "ISS-002",
                "category": "NWC",
                "severity": "medium",
                "title": "재고 평가 방법 변경",
                "status": "in_review",
            },
            {
                "id": "ISS-003",
                "category": "Debt",
                "severity": "low",
                "title": "리스 계약 확인 필요",
                "status": "resolved",
            },
        ]
        block = build_issue_summary_table_block("Issue Summary", issues)
        assert len(block.columns) == 5
        assert len(block.rows) == 3


# =============================================================================
# Golden Test: Chart Block
# =============================================================================


class TestChartBlockGolden:
    """ChartBlock 골든 테스트."""

    def test_waterfall_ebitda_bridge(self) -> None:
        """EBITDA 워터폴 차트."""
        block = build_waterfall_chart_block(
            title="EBITDA Bridge (FY2025)",
            categories=[
                "Reported EBITDA",
                "Non-recurring",
                "Non-operating",
                "Normalization",
                "Adjusted EBITDA",
            ],
            values=[
                Decimal("15000"),
                Decimal("1500"),
                Decimal("-500"),
                Decimal("800"),
                Decimal("16800"),
            ],
        )
        assert block.chart_type == ChartType.WATERFALL
        assert len(block.data.categories) == 5
        assert block.data.values[0] == Decimal("15000")

    def test_chart_with_prerendered_image(self) -> None:
        """사전 렌더링된 이미지 포함."""
        block = ChartBlock(
            chart_type=ChartType.WATERFALL,
            title="Pre-rendered Chart",
            image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )
        assert block.image_base64 is not None
        assert block.data is None


# =============================================================================
# Golden Test: Text Block
# =============================================================================


class TestTextBlockGolden:
    """TextBlock 골든 테스트."""

    def test_key_findings_block(self) -> None:
        """Key Findings 텍스트 블록."""
        block = build_text_block(
            content="분석 결과 주요 발견사항은 다음과 같습니다.",
            title="Key Findings",
            bullet_points=[
                "비경상 항목으로 150억원 조정",
                "운전자본 평균 210억원 수준",
                "순차입금 450억원 확인",
            ],
            risk_level=RiskLevel.MEDIUM,
        )
        assert block.type == BlockType.TEXT
        assert block.risk_level == RiskLevel.MEDIUM
        assert len(block.bullet_points) == 3


# =============================================================================
# Golden Test: Claim Block
# =============================================================================


class TestClaimBlockGolden:
    """ClaimBlock 골든 테스트."""

    def test_verified_claim(self) -> None:
        """근거가 있는 Claim."""
        block = build_claim_block(
            claim_text="FY2025 매출은 전년 대비 20% 성장하였습니다.",
            evidence_refs=[
                ("ev-001", "TB", "tb-row-42", "Trial Balance - Revenue"),
                ("ev-002", "GL", "gl-entry-1234", "General Ledger Detail"),
            ],
            risk_level=RiskLevel.LOW,
            category="QoE",
        )
        assert block.type == BlockType.CLAIM
        assert block.verified is True
        assert len(block.evidence_refs) == 2

    def test_unverified_claim(self) -> None:
        """근거가 없는 Claim."""
        block = build_claim_block(
            claim_text="해당 항목은 경영진 추정치에 의존합니다.",
            evidence_refs=None,
            risk_level=RiskLevel.HIGH,
        )
        assert block.verified is False


# =============================================================================
# Golden Test: Issue Block
# =============================================================================


class TestIssueBlockGolden:
    """IssueBlock 골든 테스트."""

    def test_issue_log_block(self) -> None:
        """이슈 로그 블록."""
        issues = [
            {
                "issue_id": "ISS-001",
                "category": "QoE",
                "severity": "critical",
                "title": "중대한 오류 발견",
                "status": "open",
            },
            {
                "issue_id": "ISS-002",
                "category": "DATA",
                "severity": "high",
                "title": "데이터 누락",
                "status": "open",
            },
        ]
        block = build_issue_block(issues, title="Issue Log", show_resolved=False)
        assert block.type == BlockType.ISSUE
        assert len(block.issues) == 2
        assert block.issues[0].severity == "critical"


# =============================================================================
# Golden Test: Scope Block
# =============================================================================


class TestScopeBlockGolden:
    """ScopeBlock 골든 테스트."""

    def test_scope_definitions_block(self) -> None:
        """범위/정의 블록."""
        scope_items = [
            ("period", "Analysis Period", "FY2024 - FY2025 (24 months)"),
            ("entity", "Target Entity", "Alpha Corporation"),
            ("currency", "Reporting Currency", "KRW (백만원)"),
            ("basis", "Accounting Basis", "K-IFRS"),
        ]
        definitions = {
            "EBITDA": "Earnings Before Interest, Taxes, Depreciation, and Amortization",
            "NWC": "Net Working Capital = Current Assets - Current Liabilities (excl. cash and debt)",
            "Net Debt": "Total Debt - Cash and Cash Equivalents",
        }
        block = build_scope_block(scope_items, definitions, "Scope & Definitions")
        assert block.type == BlockType.SCOPE
        assert len(block.scope_items) == 4
        assert len(block.definitions) == 3


# =============================================================================
# Golden Test: Methodology Block
# =============================================================================


class TestMethodologyBlockGolden:
    """MethodologyBlock 골든 테스트."""

    def test_methodology_block(self) -> None:
        """방법론 블록."""
        steps = [
            (1, "Data Collection", "경영진 제공 Trial Balance, GL, 보조원장 수령"),
            (2, "Account Mapping", "표준 CoA에 원장 계정 매핑"),
            (3, "QoE Analysis", "Reported EBITDA 계산 및 조정항목 식별"),
            (4, "NWC Analysis", "운전자본 항목 분류 및 Target NWC 산정"),
            (5, "Net Debt Analysis", "순차입금 및 Debt-like 항목 분석"),
        ]
        limitations = [
            "본 분석은 경영진 제공 자료에 기반하며 독립적 감사는 수행하지 않음",
            "미래 전망은 경영진 추정에 의존",
        ]
        block = build_methodology_block(steps, limitations=limitations)
        assert block.type == BlockType.METHODOLOGY
        assert len(block.steps) == 5
        assert len(block.limitations) == 2


# =============================================================================
# Golden Test: Full Report IR
# =============================================================================


class TestReportIRGolden:
    """ReportIR 전체 골든 테스트."""

    def test_full_fdd_report(self) -> None:
        """전체 FDD 보고서 IR."""
        ir = ReportIR(
            metadata=ReportMetadata(
                deal_id="deal-2026-001",
                deal_name="Project Alpha",
                generated_at="2026-02-06T12:00:00Z",
                version="1.0",
                engine_versions={"qoe": "0.1.0", "nwc": "0.1.0", "debt": "0.1.0"},
            ),
            sections=[
                # Cover
                CoverBlock(deal_name="Project Alpha", target_name="Alpha Corp"),
                # Scope
                build_scope_block(
                    [("period", "Period", "FY2025")],
                    {"EBITDA": "Earnings Before..."},
                ),
                # KPIs
                build_kpi_block("Summary", [("EBITDA", "15,000", "백만원")]),
                # QoE Table
                build_qoe_table_block(
                    "QoE", [{"category": "Revenue", "FY2025": "100,000"}], ["FY2025"]
                ),
                # Chart
                build_waterfall_chart_block(
                    "EBITDA Bridge",
                    ["Start", "End"],
                    [Decimal("10000"), Decimal("15000")],
                ),
                # Claims
                build_claim_block(
                    "매출 성장 확인", [("ev-1", "TB", "row-1", "TB Row")]
                ),
                # Issues
                build_issue_block(
                    [
                        {
                            "issue_id": "1",
                            "category": "QoE",
                            "severity": "high",
                            "title": "Issue",
                            "status": "open",
                        }
                    ]
                ),
                # Methodology
                build_methodology_block([(1, "Step 1", "Description")]),
                # Text
                build_text_block("분석 완료", title="Conclusion"),
            ],
        )

        assert len(ir.sections) == 9
        assert ir.metadata.deal_name == "Project Alpha"

        # Serialize and verify
        result = report_ir_to_dict(ir)
        assert "metadata" in result
        assert "sections" in result
        assert len(result["sections"]) == 9


class TestSerializationGolden:
    """직렬화 골든 테스트."""

    def test_decimal_serialization(self) -> None:
        """Decimal은 문자열로 직렬화."""
        block = ChartBlock(
            chart_type=ChartType.BAR,
            title="Test",
            data=ChartData(
                categories=["A", "B"],
                values=[Decimal("123456.7890"), Decimal("-999.9999")],
            ),
        )
        ir = ReportIR(sections=[block])
        result = report_ir_to_dict(ir)

        values = result["sections"][0]["data"]["values"]
        assert values[0] == "123456.7890"
        assert values[1] == "-999.9999"

    def test_date_serialization(self) -> None:
        """Date는 ISO 문자열로 직렬화."""
        block = CoverBlock(deal_name="Test", date=date(2026, 12, 31))
        ir = ReportIR(sections=[block])
        result = report_ir_to_dict(ir)

        assert result["sections"][0]["date"] == "2026-12-31"

    def test_enum_serialization(self) -> None:
        """Enum은 value로 직렬화."""
        block = TextBlock(
            content="Test",
            risk_level=RiskLevel.CRITICAL
            if hasattr(RiskLevel, "CRITICAL")
            else RiskLevel.HIGH,
        )
        ir = ReportIR(sections=[block])
        result = report_ir_to_dict(ir)

        assert result["sections"][0]["risk_level"] == "high"
        assert result["sections"][0]["type"] == "text"

    def test_none_handling(self) -> None:
        """None 값 처리."""
        block = ClaimBlock(claim_text="Test")
        ir = ReportIR(sections=[block])
        result = report_ir_to_dict(ir)

        assert result["sections"][0]["risk_level"] is None
        assert result["sections"][0]["category"] is None
