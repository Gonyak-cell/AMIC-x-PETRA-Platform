"""Tests for Excel Report Renderer.

생성된 .xlsx 파일을 openpyxl로 다시 읽어 데이터 정합성을 확인한다.
"""

from datetime import date
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from app.renderers.excel_renderer import render_excel_report
from app.renderers.report_builder import (
    AlignType,
    CoverBlock,
    IssueBlock,
    IssueItem,
    KPIBlock,
    ReportIR,
    ReportMetadata,
    ScopeBlock,
    ScopeItem,
    TableBlock,
    TableColumn,
    TextBlock,
)

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_ir() -> ReportIR:
    """최소 Report IR (표지만)."""
    return ReportIR(
        metadata=ReportMetadata(
            deal_id="test-deal-001",
            deal_name="Test Corp",
            version="1.0",
        ),
        sections=[
            CoverBlock(
                deal_name="Test Corp",
                target_name="Target Co., Ltd.",
                deal_type="Acquisition",
                date=date(2025, 12, 31),
                confidentiality="STRICTLY CONFIDENTIAL",
            ),
        ],
    )


@pytest.fixture
def full_ir() -> ReportIR:
    """전체 Report IR (Cover + KPI + Table + Issues)."""
    return ReportIR(
        metadata=ReportMetadata(
            deal_id="test-deal-002",
            deal_name="Full Deal Corp",
            version="2.0",
            engine_versions={"qoe": "0.1.0", "nwc": "0.1.0", "debt": "0.1.0"},
        ),
        sections=[
            # Cover
            CoverBlock(
                deal_name="Full Deal Corp",
                target_name="Target Industries",
                deal_type="Financial Due Diligence",
                date=date(2026, 1, 15),
            ),
            # KPI
            KPIBlock(
                title="Key Metrics",
                kpis=[
                    {"label": "Revenue", "value": "50,000", "unit": "백만원"},
                    {"label": "EBITDA", "value": "12,500", "unit": "백만원"},
                    {"label": "Net Debt", "value": "8,000", "unit": "백만원"},
                ],
            ),
            # Scope
            ScopeBlock(
                title="Scope",
                scope_items=[
                    ScopeItem(category="period", label="분석기간", value="2024.01-2025.12"),
                    ScopeItem(category="currency", label="통화", value="KRW"),
                ],
            ),
            # QoE Bridge Table
            TableBlock(
                title="QoE Bridge",
                columns=[
                    TableColumn(key="category", header="Category", width=2.5, align=AlignType.LEFT),
                    TableColumn(key="reported", header="Reported", format="currency"),
                    TableColumn(key="adjustments", header="Adjustments", format="currency"),
                    TableColumn(key="adjusted", header="Adjusted", format="currency"),
                ],
                rows=[
                    {"category": "Revenue", "reported": 50000, "adjustments": -500, "adjusted": 49500},
                    {"category": "COGS", "reported": -30000, "adjustments": 1000, "adjusted": -29000},
                    {"category": "SG&A", "reported": -8000, "adjustments": 200, "adjusted": -7800},
                ],
                footer_rows=[
                    {"category": "EBITDA", "reported": 12000, "adjustments": 700, "adjusted": 12700},
                ],
            ),
            # NWC Table
            TableBlock(
                title="NWC Definition",
                columns=[
                    TableColumn(key="account", header="Account", width=3.0, align=AlignType.LEFT),
                    TableColumn(key="balance", header="Balance", format="currency"),
                    TableColumn(key="classification", header="Classification"),
                ],
                rows=[
                    {"account": "매출채권", "balance": 5000, "classification": "Above Line"},
                    {"account": "재고자산", "balance": 3000, "classification": "Above Line"},
                    {"account": "매입채무", "balance": -4000, "classification": "Above Line"},
                ],
            ),
            # Net Debt Table
            TableBlock(
                title="Net Debt Schedule",
                columns=[
                    TableColumn(key="item", header="Item", width=3.0, align=AlignType.LEFT),
                    TableColumn(key="amount", header="Amount", format="currency"),
                    TableColumn(key="type", header="Type"),
                ],
                rows=[
                    {"item": "은행차입금", "amount": 10000, "type": "Debt"},
                    {"item": "리스부채", "amount": 2000, "type": "Debt-like"},
                    {"item": "현금", "amount": -3000, "type": "Cash"},
                    {"item": "단기금융상품", "amount": -1000, "type": "Cash-like"},
                ],
            ),
            # Issues
            IssueBlock(
                title="Issue Log",
                issues=[
                    IssueItem(
                        issue_id="ISS-001",
                        category="QoE_ADJUSTMENT",
                        severity="high",
                        title="비경상 항목 미분류",
                        description="2025년 일회성 컨설팅 비용 500백만원 미조정",
                        status="open",
                    ),
                    IssueItem(
                        issue_id="ISS-002",
                        category="TIMING",
                        severity="medium",
                        title="매출인식 시점 차이",
                        description="분기말 매출인식 시점 불일치",
                        status="open",
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def sample_checklist_data() -> list[dict]:
    """체크리스트 데이터 샘플."""
    return [
        {
            "category": "REVENUE_RECOGNITION",
            "title": "Revenue Recognition Review",
            "auto_finding": "매출 50,000백만원 확인",
            "auto_amount": "50000",
            "user_correction": "",
            "user_amount": "",
            "status": "CONFIRMED",
            "severity": "HIGH",
        },
        {
            "category": "COGS_CLASSIFICATION",
            "title": "COGS Classification Review",
            "auto_finding": "매출원가 분류 이상 없음",
            "auto_amount": "30000",
            "user_correction": "감가상각비 재분류 필요",
            "user_amount": "31000",
            "status": "CORRECTED",
            "severity": "HIGH",
        },
        {
            "category": "NON_RECURRING_ITEMS",
            "title": "Non-Recurring Items",
            "auto_finding": "3건 비경상 항목 자동 식별",
            "auto_amount": "1500",
            "user_correction": "",
            "user_amount": "",
            "status": "FLAGGED",
            "severity": "HIGH",
        },
    ]


# ── Tests ───────────────────────────────────────────────────────────────


class TestMinimalRender:
    def test_render_returns_bytes(self, minimal_ir: ReportIR):
        """렌더링 결과가 BytesIO를 반환한다."""
        result = render_excel_report(minimal_ir)
        assert result is not None
        assert result.getvalue()[:4] == b"PK\x03\x04"  # ZIP/XLSX 매직 바이트

    def test_cover_sheet_exists(self, minimal_ir: ReportIR):
        """Cover & Summary 시트가 생성된다."""
        result = render_excel_report(minimal_ir)
        wb = load_workbook(result)
        assert "Cover & Summary" in wb.sheetnames

    def test_cover_has_deal_name(self, minimal_ir: ReportIR):
        """Cover 시트에 딜 이름이 포함된다."""
        result = render_excel_report(minimal_ir)
        wb = load_workbook(result)
        ws = wb["Cover & Summary"]
        values = [cell.value for row in ws.iter_rows() for cell in row if cell.value]
        assert any("Test Corp" in str(v) for v in values)

    def test_cover_has_target_name(self, minimal_ir: ReportIR):
        result = render_excel_report(minimal_ir)
        wb = load_workbook(result)
        ws = wb["Cover & Summary"]
        values = [cell.value for row in ws.iter_rows() for cell in row if cell.value]
        assert any("Target Co" in str(v) for v in values)


class TestFullRender:
    def test_all_sheets_created(self, full_ir: ReportIR):
        """Cover + 테이블 시트 3개 + Issues = 5개 시트."""
        result = render_excel_report(full_ir)
        wb = load_workbook(result)
        assert "Cover & Summary" in wb.sheetnames
        assert "QoE Bridge" in wb.sheetnames
        assert "Issues" in wb.sheetnames
        # NWC, Net Debt 시트도 존재
        assert len(wb.sheetnames) >= 4

    def test_qoe_table_data(self, full_ir: ReportIR):
        """QoE Bridge 시트의 데이터 정합성 확인."""
        result = render_excel_report(full_ir)
        wb = load_workbook(result)
        ws = wb["QoE Bridge"]

        # 모든 셀 값 수집
        all_values = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    all_values.append(cell.value)

        # 헤더 확인
        assert "Category" in all_values
        assert "Reported" in all_values

        # 데이터 확인 (카테고리명)
        assert "Revenue" in all_values
        assert "COGS" in all_values
        assert "EBITDA" in all_values  # footer row

    def test_qoe_currency_values(self, full_ir: ReportIR):
        """QoE 테이블의 숫자 값이 올바르게 렌더링된다."""
        result = render_excel_report(full_ir)
        wb = load_workbook(result)
        ws = wb["QoE Bridge"]

        # 숫자 값 수집
        numeric_values = set()
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, (int, float)):
                    numeric_values.add(cell.value)

        assert 50000.0 in numeric_values or 50000 in numeric_values
        assert -30000.0 in numeric_values or -30000 in numeric_values

    def test_issues_sheet(self, full_ir: ReportIR):
        """Issues 시트의 이슈 데이터 확인."""
        result = render_excel_report(full_ir)
        wb = load_workbook(result)
        ws = wb["Issues"]

        all_values = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    all_values.append(str(cell.value))

        assert "ISS-001" in all_values
        assert "ISS-002" in all_values
        assert "high" in all_values
        assert "medium" in all_values

    def test_issue_severity_headers(self, full_ir: ReportIR):
        """Issues 시트에 올바른 헤더가 있다."""
        result = render_excel_report(full_ir)
        wb = load_workbook(result)
        ws = wb["Issues"]

        header_values = set()
        for row in ws.iter_rows(max_row=5):
            for cell in row:
                if cell.value:
                    header_values.add(str(cell.value))

        assert "Severity" in header_values
        assert "Category" in header_values


class TestChecklistSheet:
    def test_checklist_sheet_created(
        self, minimal_ir: ReportIR, sample_checklist_data: list[dict]
    ):
        """체크리스트 데이터 전달 시 Checklist 시트 생성."""
        result = render_excel_report(minimal_ir, checklist_data=sample_checklist_data)
        wb = load_workbook(result)
        assert "FDD Checklist" in wb.sheetnames

    def test_checklist_data_populated(
        self, minimal_ir: ReportIR, sample_checklist_data: list[dict]
    ):
        """체크리스트 시트에 데이터가 올바르게 채워진다."""
        result = render_excel_report(minimal_ir, checklist_data=sample_checklist_data)
        wb = load_workbook(result)
        ws = wb["FDD Checklist"]

        all_values = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    all_values.append(str(cell.value))

        # 카테고리
        assert "REVENUE_RECOGNITION" in all_values
        assert "COGS_CLASSIFICATION" in all_values

        # 상태
        assert "CONFIRMED" in all_values
        assert "CORRECTED" in all_values
        assert "FLAGGED" in all_values

    def test_no_checklist_sheet_when_none(self, minimal_ir: ReportIR):
        """체크리스트 데이터 없으면 시트 미생성."""
        result = render_excel_report(minimal_ir, checklist_data=None)
        wb = load_workbook(result)
        assert "FDD Checklist" not in wb.sheetnames

    def test_no_checklist_sheet_when_empty(self, minimal_ir: ReportIR):
        """빈 체크리스트 데이터면 시트 미생성."""
        result = render_excel_report(minimal_ir, checklist_data=[])
        wb = load_workbook(result)
        assert "FDD Checklist" not in wb.sheetnames

    def test_checklist_headers(
        self, minimal_ir: ReportIR, sample_checklist_data: list[dict]
    ):
        """체크리스트 시트 헤더 확인."""
        result = render_excel_report(minimal_ir, checklist_data=sample_checklist_data)
        wb = load_workbook(result)
        ws = wb["FDD Checklist"]

        header_values = set()
        for row in ws.iter_rows(max_row=5):
            for cell in row:
                if cell.value:
                    header_values.add(str(cell.value))

        assert "Category" in header_values
        assert "Title" in header_values
        assert "Auto Finding" in header_values
        assert "Status" in header_values
        assert "Severity" in header_values


class TestFileSave:
    def test_save_to_path(self, tmp_path, full_ir: ReportIR):
        """파일 경로로 저장 시 파일이 생성된다."""
        output_path = tmp_path / "test_report.xlsx"
        result = render_excel_report(full_ir, output_path=output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # 저장된 파일도 유효한 xlsx
        wb = load_workbook(output_path)
        assert "Cover & Summary" in wb.sheetnames

        # BytesIO도 반환
        assert result.getvalue()[:4] == b"PK\x03\x04"


class TestEdgeCases:
    def test_empty_report_ir(self):
        """빈 Report IR도 렌더링 가능."""
        ir = ReportIR()
        result = render_excel_report(ir)
        wb = load_workbook(result)
        assert "Cover & Summary" in wb.sheetnames

    def test_table_without_rows(self):
        """데이터 없는 테이블도 렌더링 가능."""
        ir = ReportIR(
            sections=[
                TableBlock(
                    title="Empty Table",
                    columns=[
                        TableColumn(key="a", header="Column A"),
                        TableColumn(key="b", header="Column B"),
                    ],
                    rows=[],
                ),
            ]
        )
        result = render_excel_report(ir)
        wb = load_workbook(result)
        assert len(wb.sheetnames) >= 2  # Cover + Empty Table

    def test_issue_block_no_issues(self):
        """이슈 없는 IssueBlock도 렌더링 가능."""
        ir = ReportIR(
            sections=[
                IssueBlock(title="No Issues", issues=[]),
            ]
        )
        result = render_excel_report(ir)
        wb = load_workbook(result)
        assert "Issues" in wb.sheetnames

    def test_multiple_table_blocks(self):
        """여러 테이블 블록이 각각 별도 시트로 생성된다."""
        ir = ReportIR(
            sections=[
                TableBlock(
                    title="QoE Adjustments",
                    columns=[TableColumn(key="a", header="A")],
                    rows=[{"a": "val1"}],
                ),
                TableBlock(
                    title="NWC Analysis",
                    columns=[TableColumn(key="b", header="B")],
                    rows=[{"b": "val2"}],
                ),
                TableBlock(
                    title="Net Debt Schedule",
                    columns=[TableColumn(key="c", header="C")],
                    rows=[{"c": "val3"}],
                ),
            ]
        )
        result = render_excel_report(ir)
        wb = load_workbook(result)
        # Cover + 3 tables
        assert len(wb.sheetnames) >= 4

    def test_long_sheet_name_truncated(self):
        """31자 초과 시트명은 잘린다."""
        ir = ReportIR(
            sections=[
                TableBlock(
                    title="A" * 50,  # 50자
                    columns=[TableColumn(key="x", header="X")],
                    rows=[{"x": 1}],
                ),
            ]
        )
        result = render_excel_report(ir)
        wb = load_workbook(result)
        # 모든 시트명이 31자 이하
        for name in wb.sheetnames:
            assert len(name) <= 31
