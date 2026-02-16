"""Report Builder 테스트.

Report IR dataclasses와 빌더 함수들을 테스트합니다.
"""

from decimal import Decimal
from datetime import date

import pytest

from app.renderers.report_builder import (
    AlignType,
    BlockType,
    ChartBlock,
    ChartData,
    ChartType,
    CoverBlock,
    KPIBlock,
    Position,
    ReportIR,
    ReportMetadata,
    RiskLevel,
    Size,
    TableBlock,
    TableColumn,
    TextBlock,
    build_kpi_block,
    build_qoe_table_block,
    build_text_block,
    build_waterfall_chart_block,
    report_ir_to_dict,
)


class TestBlockTypes:
    """블록 타입 Enum 테스트."""

    def test_block_type_values(self) -> None:
        assert BlockType.COVER.value == "cover"
        assert BlockType.KPI.value == "kpi"
        assert BlockType.TABLE.value == "table"
        assert BlockType.CHART.value == "chart"
        assert BlockType.TEXT.value == "text"

    def test_chart_type_values(self) -> None:
        assert ChartType.WATERFALL.value == "waterfall"
        assert ChartType.BAR.value == "bar"
        assert ChartType.LINE.value == "line"
        assert ChartType.PIE.value == "pie"

    def test_align_type_values(self) -> None:
        assert AlignType.LEFT.value == "left"
        assert AlignType.CENTER.value == "center"
        assert AlignType.RIGHT.value == "right"

    def test_risk_level_values(self) -> None:
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"


class TestPositionAndSize:
    """Position, Size dataclass 테스트."""

    def test_position_defaults(self) -> None:
        pos = Position()
        assert pos.x == 0.5
        assert pos.y == 1.5

    def test_position_custom(self) -> None:
        pos = Position(x=1.0, y=2.0)
        assert pos.x == 1.0
        assert pos.y == 2.0

    def test_size_defaults(self) -> None:
        size = Size()
        assert size.w == 9.0
        assert size.h == 4.0

    def test_size_custom(self) -> None:
        size = Size(w=8.0, h=5.0)
        assert size.w == 8.0
        assert size.h == 5.0


class TestCoverBlock:
    """CoverBlock 테스트."""

    def test_cover_block_type(self) -> None:
        block = CoverBlock()
        assert block.type == BlockType.COVER

    def test_cover_block_with_data(self) -> None:
        block = CoverBlock(
            deal_name="Project Alpha",
            deal_type="Acquisition",
            target_name="Target Corp",
            date=date(2026, 2, 6),
            prepared_by="FDD Team",
            confidentiality="STRICTLY CONFIDENTIAL",
        )
        assert block.deal_name == "Project Alpha"
        assert block.deal_type == "Acquisition"
        assert block.target_name == "Target Corp"
        assert block.date == date(2026, 2, 6)
        assert block.prepared_by == "FDD Team"
        assert block.confidentiality == "STRICTLY CONFIDENTIAL"


class TestKPIBlock:
    """KPIBlock 테스트."""

    def test_kpi_block_type(self) -> None:
        block = KPIBlock()
        assert block.type == BlockType.KPI

    def test_kpi_block_with_data(self) -> None:
        kpis = [
            {"label": "Revenue", "value": "10,000", "unit": "백만원"},
            {"label": "EBITDA", "value": "2,500", "unit": "백만원"},
            {"label": "Margin", "value": "25%", "unit": None},
        ]
        block = KPIBlock(title="Financial Summary", kpis=kpis, columns=3)
        assert block.title == "Financial Summary"
        assert len(block.kpis) == 3
        assert block.columns == 3


class TestTableBlock:
    """TableBlock 테스트."""

    def test_table_block_type(self) -> None:
        block = TableBlock()
        assert block.type == BlockType.TABLE

    def test_table_block_with_columns_and_rows(self) -> None:
        columns = [
            TableColumn(key="category", header="Category", width=2.0, align=AlignType.LEFT),
            TableColumn(key="fy2024", header="FY2024", width=1.5, align=AlignType.RIGHT, format="currency"),
            TableColumn(key="fy2025", header="FY2025", width=1.5, align=AlignType.RIGHT, format="currency"),
        ]
        rows = [
            {"category": "Revenue", "fy2024": "10,000", "fy2025": "12,000"},
            {"category": "COGS", "fy2024": "(7,000)", "fy2025": "(8,400)"},
        ]
        block = TableBlock(
            title="QoE Bridge",
            columns=columns,
            rows=rows,
            zebra_stripe=True,
        )
        assert block.title == "QoE Bridge"
        assert len(block.columns) == 3
        assert len(block.rows) == 2
        assert block.zebra_stripe is True


class TestChartBlock:
    """ChartBlock 테스트."""

    def test_chart_block_type(self) -> None:
        block = ChartBlock()
        assert block.type == BlockType.CHART

    def test_chart_block_waterfall(self) -> None:
        data = ChartData(
            categories=["Reported", "One-off", "Non-operating", "Adjusted"],
            values=[Decimal("1000"), Decimal("200"), Decimal("-50"), None],
        )
        block = ChartBlock(
            chart_type=ChartType.WATERFALL,
            title="EBITDA Bridge",
            data=data,
        )
        assert block.chart_type == ChartType.WATERFALL
        assert block.title == "EBITDA Bridge"
        assert len(block.data.categories) == 4
        assert block.data.values[0] == Decimal("1000")

    def test_chart_block_with_image(self) -> None:
        block = ChartBlock(
            chart_type=ChartType.WATERFALL,
            title="EBITDA Bridge",
            image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )
        assert block.image_base64 is not None
        assert block.data is None


class TestTextBlock:
    """TextBlock 테스트."""

    def test_text_block_type(self) -> None:
        block = TextBlock()
        assert block.type == BlockType.TEXT

    def test_text_block_with_content(self) -> None:
        block = TextBlock(
            title="Key Findings",
            content="Analysis reveals significant one-off adjustments.",
            bullet_points=[
                "Legal settlement: 150M KRW",
                "Restructuring costs: 80M KRW",
            ],
            risk_level=RiskLevel.MEDIUM,
        )
        assert block.title == "Key Findings"
        assert "one-off adjustments" in block.content
        assert len(block.bullet_points) == 2
        assert block.risk_level == RiskLevel.MEDIUM


class TestReportIR:
    """ReportIR 테스트."""

    def test_report_ir_empty(self) -> None:
        ir = ReportIR()
        assert ir.metadata.deal_id == ""
        assert ir.sections == []

    def test_report_ir_with_sections(self) -> None:
        metadata = ReportMetadata(
            deal_id="deal-123",
            deal_name="Project Alpha",
            generated_at="2026-02-06T12:00:00Z",
            version="1.0",
            engine_versions={"qoe": "0.1.0", "nwc": "0.1.0"},
        )
        sections = [
            CoverBlock(deal_name="Project Alpha", target_name="Target Corp"),
            KPIBlock(title="Summary", kpis=[{"label": "EBITDA", "value": "2,500", "unit": "백만원"}]),
        ]
        ir = ReportIR(metadata=metadata, sections=sections)

        assert ir.metadata.deal_id == "deal-123"
        assert len(ir.sections) == 2
        assert ir.sections[0].type == BlockType.COVER
        assert ir.sections[1].type == BlockType.KPI


class TestBuilderFunctions:
    """빌더 함수 테스트."""

    def test_build_qoe_table_block(self) -> None:
        bridge_data = [
            {"category": "Revenue", "FY2024": "10,000", "FY2025": "12,000"},
            {"category": "COGS", "FY2024": "(7,000)", "FY2025": "(8,400)"},
            {"category": "Gross Profit", "FY2024": "3,000", "FY2025": "3,600"},
        ]
        block = build_qoe_table_block(
            title="QoE Analysis",
            bridge_data=bridge_data,
            fiscal_years=["FY2024", "FY2025"],
        )
        assert block.title == "QoE Analysis"
        assert len(block.columns) == 3  # category + 2 years
        assert block.columns[0].key == "category"
        assert block.columns[1].key == "FY2024"
        assert block.columns[2].key == "FY2025"

    def test_build_waterfall_chart_block(self) -> None:
        block = build_waterfall_chart_block(
            title="EBITDA Bridge",
            categories=["Reported", "One-off", "Adjusted"],
            values=[Decimal("1000"), Decimal("200"), Decimal("1200")],
        )
        assert block.chart_type == ChartType.WATERFALL
        assert block.title == "EBITDA Bridge"
        assert len(block.data.categories) == 3
        assert block.size.w == 9.0
        assert block.size.h == 4.5

    def test_build_waterfall_chart_block_with_image(self) -> None:
        block = build_waterfall_chart_block(
            title="EBITDA Bridge",
            categories=["Reported", "Adjusted"],
            values=[Decimal("1000"), Decimal("1200")],
            image_base64="base64data",
        )
        assert block.image_base64 == "base64data"

    def test_build_kpi_block(self) -> None:
        block = build_kpi_block(
            title="KPIs",
            kpis=[
                ("Revenue", "10,000", "백만원"),
                ("EBITDA", "2,500", "백만원"),
                ("Margin", "25%", None),
            ],
            columns=3,
        )
        assert block.title == "KPIs"
        assert len(block.kpis) == 3
        assert block.kpis[0]["label"] == "Revenue"
        assert block.kpis[0]["value"] == "10,000"
        assert block.kpis[0]["unit"] == "백만원"
        assert block.kpis[2]["unit"] is None

    def test_build_text_block(self) -> None:
        block = build_text_block(
            content="Important findings.",
            title="Findings",
            bullet_points=["Point 1", "Point 2"],
            risk_level=RiskLevel.HIGH,
        )
        assert block.title == "Findings"
        assert block.content == "Important findings."
        assert len(block.bullet_points) == 2
        assert block.risk_level == RiskLevel.HIGH


class TestSerialization:
    """report_ir_to_dict 직렬화 테스트."""

    def test_serialize_simple_ir(self) -> None:
        ir = ReportIR(
            metadata=ReportMetadata(deal_id="123", deal_name="Test Deal"),
            sections=[CoverBlock(deal_name="Test Deal")],
        )
        result = report_ir_to_dict(ir)

        assert result["metadata"]["deal_id"] == "123"
        assert result["metadata"]["deal_name"] == "Test Deal"
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "cover"

    def test_serialize_decimal_values(self) -> None:
        data = ChartData(
            categories=["A", "B"],
            values=[Decimal("1000.5"), Decimal("2000.75")],
        )
        block = ChartBlock(
            chart_type=ChartType.BAR,
            title="Test",
            data=data,
        )
        ir = ReportIR(sections=[block])
        result = report_ir_to_dict(ir)

        # Decimal이 문자열로 직렬화되어야 함
        assert result["sections"][0]["data"]["values"][0] == "1000.5"
        assert result["sections"][0]["data"]["values"][1] == "2000.75"

    def test_serialize_date_values(self) -> None:
        block = CoverBlock(
            deal_name="Test",
            date=date(2026, 2, 6),
        )
        ir = ReportIR(sections=[block])
        result = report_ir_to_dict(ir)

        # date가 ISO 문자열로 직렬화되어야 함
        assert result["sections"][0]["date"] == "2026-02-06"

    def test_serialize_enum_values(self) -> None:
        block = TextBlock(
            content="Test",
            risk_level=RiskLevel.HIGH,
        )
        ir = ReportIR(sections=[block])
        result = report_ir_to_dict(ir)

        # Enum이 value로 직렬화되어야 함
        assert result["sections"][0]["risk_level"] == "high"
        assert result["sections"][0]["type"] == "text"

    def test_serialize_full_report(self) -> None:
        """전체 보고서 직렬화 테스트."""
        ir = ReportIR(
            metadata=ReportMetadata(
                deal_id="deal-001",
                deal_name="Project Alpha",
                generated_at="2026-02-06T12:00:00Z",
                version="1.0",
                engine_versions={"qoe": "0.1.0"},
            ),
            sections=[
                CoverBlock(
                    deal_name="Project Alpha",
                    target_name="Target Corp",
                    date=date(2026, 2, 6),
                ),
                build_kpi_block(
                    title="Summary",
                    kpis=[("EBITDA", "2,500", "백만원")],
                ),
                build_waterfall_chart_block(
                    title="EBITDA Bridge",
                    categories=["Reported", "Adjusted"],
                    values=[Decimal("1000"), Decimal("1200")],
                ),
                build_text_block(
                    content="Analysis complete.",
                    risk_level=RiskLevel.LOW,
                ),
            ],
        )
        result = report_ir_to_dict(ir)

        # 전체 구조 검증
        assert "metadata" in result
        assert "sections" in result
        assert len(result["sections"]) == 4
        assert result["sections"][0]["type"] == "cover"
        assert result["sections"][1]["type"] == "kpi"
        assert result["sections"][2]["type"] == "chart"
        assert result["sections"][3]["type"] == "text"
