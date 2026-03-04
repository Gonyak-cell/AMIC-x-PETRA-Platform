"""ReportValidationEngine 단위 테스트."""

from decimal import Decimal

import pytest

from app.services.report.validation import (
    CROSS_TOLERANCE,
    ValidationResult,
    run_cross_validation,
    run_full_validation,
    validate_commentary_direction,
    validate_debt_net,
    validate_fcf_bridge_math,
    validate_is_qoe_revenue,
    validate_qoe_ebitda_bridge,
    validate_revenue_breakdown_total,
)


def _make_section(
    title: str, rows: list[dict], footer_rows: list[dict] | None = None
) -> dict:
    """테스트용 섹션 팩토리."""
    section = {"type": "table", "title": title, "rows": rows}
    if footer_rows:
        section["footer_rows"] = footer_rows
    return section


class TestValidateISQoERevenue:
    def test_matching_revenue(self):
        sections = [
            _make_section(
                "IS (Multi-period)",
                [
                    {"label": "매출액", "amount": "1000.00"},
                ],
            ),
            _make_section(
                "QoE Bridge",
                [
                    {"label": "Reported Revenue", "amount": "1000.00"},
                ],
            ),
        ]
        result = validate_is_qoe_revenue(sections)
        assert result.passed is True

    def test_mismatched_revenue(self):
        sections = [
            _make_section(
                "IS (Multi-period)",
                [
                    {"label": "매출액", "amount": "1000.00"},
                ],
            ),
            _make_section(
                "QoE Bridge",
                [
                    {"label": "Reported Revenue", "amount": "900.00"},
                ],
            ),
        ]
        result = validate_is_qoe_revenue(sections)
        assert result.passed is False

    def test_within_tolerance(self):
        sections = [
            _make_section(
                "Income Statement",
                [
                    {"label": "Revenue", "amount": "1000.00"},
                ],
            ),
            _make_section(
                "QoE Bridge",
                [
                    {"label": "Revenue", "amount": "1000.50"},
                ],
            ),
        ]
        result = validate_is_qoe_revenue(sections)
        assert result.passed is True

    def test_missing_data_skips(self):
        sections = [
            _make_section(
                "QoE Bridge",
                [
                    {"label": "Revenue", "amount": "1000.00"},
                ],
            ),
        ]
        result = validate_is_qoe_revenue(sections)
        assert result.passed is True
        assert "스킵" in result.message


class TestValidateQoEBridge:
    def test_bridge_matches(self):
        sections = [
            _make_section(
                "QoE Bridge",
                [
                    {"label": "Reported EBITDA", "amount": "500.00"},
                    {"label": "Total Adjustments", "amount": "50.00"},
                    {"label": "Adjusted EBITDA", "amount": "550.00"},
                ],
            ),
        ]
        result = validate_qoe_ebitda_bridge(sections)
        assert result.passed is True

    def test_bridge_mismatch(self):
        sections = [
            _make_section(
                "QoE Bridge",
                [
                    {"label": "Reported EBITDA", "amount": "500.00"},
                    {"label": "Total Adjustments", "amount": "50.00"},
                    {"label": "Adjusted EBITDA", "amount": "600.00"},
                ],
            ),
        ]
        result = validate_qoe_ebitda_bridge(sections)
        assert result.passed is False


class TestValidateDebtNet:
    def test_net_debt_correct(self):
        sections = [
            _make_section(
                "Net Debt Schedule",
                [
                    {"label": "Total Debt", "amount": "300.00"},
                    {"label": "Cash", "amount": "100.00"},
                    {"label": "Net Debt", "amount": "200.00"},
                ],
            ),
        ]
        result = validate_debt_net(sections)
        assert result.passed is True

    def test_net_debt_wrong(self):
        sections = [
            _make_section(
                "Net Debt Schedule",
                [
                    {"label": "Total Debt", "amount": "300.00"},
                    {"label": "Cash", "amount": "100.00"},
                    {"label": "Net Debt", "amount": "250.00"},
                ],
            ),
        ]
        result = validate_debt_net(sections)
        assert result.passed is False


class TestValidateFCFBridge:
    def test_fcf_correct(self):
        sections = [
            _make_section(
                "FCF Bridge",
                [
                    {"label": "Operating Cash Flow", "amount": "400.00"},
                    {"label": "Total CAPEX", "amount": "100.00"},
                    {"label": "Free Cash Flow", "amount": "300.00"},
                ],
            ),
        ]
        result = validate_fcf_bridge_math(sections)
        assert result.passed is True

    def test_fcf_mismatch(self):
        sections = [
            _make_section(
                "FCF Bridge",
                [
                    {"label": "OCF", "amount": "400.00"},
                    {"label": "Total CAPEX", "amount": "100.00"},
                    {"label": "FCF", "amount": "350.00"},
                ],
            ),
        ]
        result = validate_fcf_bridge_math(sections)
        assert result.passed is False


class TestValidateRevenueBreakdown:
    def test_revenue_total_matches(self):
        sections = [
            _make_section(
                "IS (Multi-period)",
                [
                    {"label": "매출액", "amount": "1000.00"},
                ],
            ),
            _make_section(
                "Revenue by Customer",
                [],
                footer_rows=[
                    {"label": "합계", "amount": "1000.00"},
                ],
            ),
        ]
        result = validate_revenue_breakdown_total(sections)
        assert result.passed is True

    def test_revenue_total_mismatch(self):
        sections = [
            _make_section(
                "IS (Multi-period)",
                [
                    {"label": "매출액", "amount": "1000.00"},
                ],
            ),
            _make_section(
                "Revenue by Customer",
                [],
                footer_rows=[
                    {"label": "Total", "amount": "800.00"},
                ],
            ),
        ]
        result = validate_revenue_breakdown_total(sections)
        assert result.passed is False


class TestValidateCommentaryDirection:
    def test_increase_matches(self):
        result = validate_commentary_direction(
            "매출액이 전년 대비 증가하였습니다.",
            "Revenue",
            Decimal("0.10"),
        )
        assert result.passed is True

    def test_decrease_matches(self):
        result = validate_commentary_direction(
            "Operating income decreased significantly.",
            "OI",
            Decimal("-0.15"),
        )
        assert result.passed is True

    def test_direction_mismatch(self):
        result = validate_commentary_direction(
            "매출이 전년 대비 감소하였습니다.",
            "Revenue",
            Decimal("0.10"),  # 실제는 증가
        )
        assert result.passed is False

    def test_no_direction_words(self):
        result = validate_commentary_direction(
            "매출 실적이 양호합니다.",
            "Revenue",
            Decimal("0.10"),
        )
        assert result.passed is True


class TestRunCrossValidation:
    def test_all_pass(self):
        report_ir = {
            "sections": [
                _make_section(
                    "IS (Multi-period)",
                    [
                        {"label": "매출액", "amount": "1000.00"},
                    ],
                ),
                _make_section(
                    "QoE Bridge",
                    [
                        {"label": "Reported Revenue", "amount": "1000.00"},
                        {"label": "Reported EBITDA", "amount": "500.00"},
                        {"label": "Total Adjustments", "amount": "50.00"},
                        {"label": "Adjusted EBITDA", "amount": "550.00"},
                    ],
                ),
                _make_section(
                    "Net Debt Schedule",
                    [
                        {"label": "Total Debt", "amount": "300.00"},
                        {"label": "Cash", "amount": "100.00"},
                        {"label": "Net Debt", "amount": "200.00"},
                    ],
                ),
                _make_section(
                    "FCF Bridge",
                    [
                        {"label": "Operating Cash Flow", "amount": "400.00"},
                        {"label": "Total CAPEX", "amount": "100.00"},
                        {"label": "Free Cash Flow", "amount": "300.00"},
                    ],
                ),
                _make_section(
                    "Revenue by Customer",
                    [],
                    footer_rows=[
                        {"label": "합계", "amount": "1000.00"},
                    ],
                ),
            ],
        }
        qa_result, findings = run_cross_validation(report_ir)
        assert qa_result.passed is True
        assert qa_result.error_count == 0

    def test_some_failures(self):
        report_ir = {
            "sections": [
                _make_section(
                    "Net Debt Schedule",
                    [
                        {"label": "Total Debt", "amount": "300.00"},
                        {"label": "Cash", "amount": "100.00"},
                        {"label": "Net Debt", "amount": "999.00"},
                    ],
                ),
            ],
        }
        qa_result, findings = run_cross_validation(report_ir)
        assert qa_result.error_count >= 1


class TestRunFullValidation:
    def test_returns_summary(self):
        report_ir = {"sections": []}
        summary = run_full_validation(report_ir)
        assert "version" in summary
        assert "overall_passed" in summary
        assert "rules" in summary
        assert isinstance(summary["rules"], list)
