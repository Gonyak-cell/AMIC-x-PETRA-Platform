"""Narrative Engine 테스트 — FDD-1201, FDD-1202.

테스트 ID 규칙: T-NARRATIVE-{번호}
"""

from decimal import Decimal

import pytest

from app.services.narrative import (
    NARRATIVE_VERSION,
    NarrativeTemplate,
    generate_debt_narrative,
    generate_executive_summary,
    generate_narrative,
    generate_nwc_narrative,
    generate_qoe_narrative,
    load_narrative_template,
)
from app.services.narrative.engine import (
    BUILTIN_TEMPLATES,
    _format_currency,
    _format_percentage,
)


class TestNarrativeVersion:
    """T-NARRATIVE-01: 버전 정보 테스트."""

    def test_version_exists(self):
        """버전 문자열 존재."""
        assert NARRATIVE_VERSION is not None
        assert isinstance(NARRATIVE_VERSION, str)

    def test_version_format(self):
        """버전 포맷 (SemVer)."""
        parts = NARRATIVE_VERSION.split(".")
        assert len(parts) == 3


class TestBuiltinTemplates:
    """T-NARRATIVE-02: 내장 템플릿 테스트."""

    def test_qoe_summary_template(self):
        """QoE 요약 템플릿 존재."""
        assert "qoe_summary" in BUILTIN_TEMPLATES
        template = BUILTIN_TEMPLATES["qoe_summary"]
        assert template.category == "qoe"
        assert "EBITDA" in template.text

    def test_nwc_summary_template(self):
        """NWC 요약 템플릿 존재."""
        assert "nwc_summary" in BUILTIN_TEMPLATES
        template = BUILTIN_TEMPLATES["nwc_summary"]
        assert template.category == "nwc"

    def test_debt_summary_template(self):
        """Debt 요약 템플릿 존재."""
        assert "debt_summary" in BUILTIN_TEMPLATES
        template = BUILTIN_TEMPLATES["debt_summary"]
        assert template.category == "debt"

    def test_executive_summary_template(self):
        """Executive Summary 템플릿 존재."""
        assert "executive_summary" in BUILTIN_TEMPLATES
        template = BUILTIN_TEMPLATES["executive_summary"]
        assert template.category == "summary"


class TestLoadTemplate:
    """T-NARRATIVE-03: 템플릿 로드 테스트."""

    def test_load_builtin_template(self):
        """내장 템플릿 로드."""
        template = load_narrative_template("qoe_summary")
        assert isinstance(template, NarrativeTemplate)
        assert template.name == "qoe_summary"

    def test_load_nonexistent_template(self):
        """존재하지 않는 템플릿."""
        with pytest.raises(ValueError, match="not found"):
            load_narrative_template("nonexistent_template")


class TestFormatHelpers:
    """T-NARRATIVE-04: 포맷 헬퍼 테스트."""

    def test_format_currency_decimal(self):
        """Decimal 금액 포맷."""
        result = _format_currency(Decimal("1234567"))
        assert result == "1,234,567"

    def test_format_currency_negative(self):
        """음수 금액 포맷."""
        result = _format_currency(Decimal("-500000"))
        assert result == "-500,000"

    def test_format_currency_none(self):
        """None 금액 포맷."""
        result = _format_currency(None)
        assert result == "-"

    def test_format_percentage(self):
        """백분율 포맷."""
        result = _format_percentage(15.5)
        assert result == "15.5%"


class TestGenerateNarrative:
    """T-NARRATIVE-05: 서술문 생성 테스트."""

    def test_basic_narrative(self):
        """기본 서술문 생성."""
        result = generate_narrative(
            "qoe_summary",
            {
                "period": "FY2025",
                "reported_ebitda": "1,000,000",
                "adjusted_ebitda": "1,200,000",
                "adjustment_count": 3,
                "adjustments": [
                    {
                        "category": "Non-recurring",
                        "amount": "100,000",
                        "description": "Legal settlement",
                    },
                ],
                "adjustment_ratio": 20.0,
            },
        )
        assert "FY2025" in result
        assert "1,000,000" in result
        assert "1,200,000" in result

    def test_narrative_with_missing_optional(self):
        """선택적 변수 없는 서술문."""
        result = generate_narrative(
            "qoe_summary",
            {
                "period": "FY2025",
                "reported_ebitda": "1,000,000",
                "adjusted_ebitda": "1,000,000",
                "adjustment_count": 0,
                "adjustments": [],
                "adjustment_ratio": 0.0,
            },
        )
        assert "FY2025" in result
        # 조정 비율이 낮으면 추가 검토 문구 없음
        assert "추가 검토" not in result


class TestGenerateQoENarrative:
    """T-NARRATIVE-06: QoE 서술문 생성 테스트."""

    def test_qoe_narrative_basic(self):
        """기본 QoE 서술문."""
        result = generate_qoe_narrative(
            period="FY2025",
            reported_ebitda=Decimal("1000000000"),
            adjusted_ebitda=Decimal("1200000000"),
            adjustments=[
                {
                    "category": "Non-recurring",
                    "amount": "100,000,000",
                    "description": "일회성 비용",
                },
                {
                    "category": "Non-operating",
                    "amount": "50,000,000",
                    "description": "비영업 수익",
                },
            ],
        )
        assert "FY2025" in result
        assert "Reported EBITDA" in result
        assert "Adjusted EBITDA" in result

    def test_qoe_narrative_no_adjustments(self):
        """조정 없는 QoE 서술문."""
        result = generate_qoe_narrative(
            period="FY2025",
            reported_ebitda="1000000000",
            adjusted_ebitda="1000000000",
            adjustments=[],
        )
        assert "0건" in result or "0개" in result or "조정" in result

    def test_qoe_narrative_high_adjustment_ratio(self):
        """높은 조정 비율 경고."""
        result = generate_qoe_narrative(
            period="FY2025",
            reported_ebitda=Decimal("1000"),
            adjusted_ebitda=Decimal("1500"),  # 50% 조정
            adjustments=[
                {
                    "category": "Non-recurring",
                    "amount": "500",
                    "description": "큰 조정",
                },
            ],
        )
        assert "검토" in result or "높" in result


class TestGenerateNWCNarrative:
    """T-NARRATIVE-07: NWC 서술문 생성 테스트."""

    def test_nwc_narrative_basic(self):
        """기본 NWC 서술문."""
        result = generate_nwc_narrative(
            period="2025-12-31",
            total_nwc=Decimal("500000000"),
            current_assets=Decimal("1000000000"),
            current_liabilities=Decimal("500000000"),
        )
        assert "500,000,000" in result
        assert "유동자산" in result
        assert "유동부채" in result

    def test_nwc_narrative_with_peg(self):
        """Peg 포함 NWC 서술문."""
        result = generate_nwc_narrative(
            period="2025-12-31",
            total_nwc=Decimal("500000000"),
            current_assets=Decimal("1000000000"),
            current_liabilities=Decimal("500000000"),
            peg_method="Average",
            target_nwc=Decimal("450000000"),
            adjustment=Decimal("-50000000"),
        )
        assert "Average" in result
        assert "Target NWC" in result


class TestGenerateDebtNarrative:
    """T-NARRATIVE-08: Net Debt 서술문 생성 테스트."""

    def test_debt_narrative_basic(self):
        """기본 Net Debt 서술문."""
        result = generate_debt_narrative(
            period="2025-12-31",
            net_debt=Decimal("300000000"),
            total_debt=Decimal("500000000"),
            cash=Decimal("200000000"),
        )
        assert "300,000,000" in result
        assert "차입금" in result
        assert "현금" in result

    def test_debt_narrative_with_debt_like(self):
        """Debt-like 항목 포함 서술문."""
        result = generate_debt_narrative(
            period="2025-12-31",
            net_debt=Decimal("350000000"),
            total_debt=Decimal("500000000"),
            cash=Decimal("200000000"),
            debt_like_items=[
                {"name": "리스부채", "amount": "30,000,000", "reason": "IFRS 16"},
                {"name": "선수금", "amount": "20,000,000"},
            ],
        )
        assert "Debt-like" in result
        assert "리스부채" in result

    def test_debt_narrative_with_ifrs16(self):
        """IFRS 16 영향 포함 서술문."""
        result = generate_debt_narrative(
            period="2025-12-31",
            net_debt=Decimal("350000000"),
            total_debt=Decimal("500000000"),
            cash=Decimal("200000000"),
            ifrs16_impact=Decimal("50000000"),
        )
        assert "IFRS 16" in result
        assert "50,000,000" in result


class TestGenerateExecutiveSummary:
    """T-NARRATIVE-09: Executive Summary 생성 테스트."""

    def test_executive_summary_basic(self):
        """기본 Executive Summary."""
        result = generate_executive_summary(
            deal_name="Project Alpha",
            target_name="Target Corp",
            analysis_period="FY2025",
            qoe_summary="Adjusted EBITDA is 1.2B KRW.",
            nwc_summary="NWC is 500M KRW.",
            debt_summary="Net Debt is 300M KRW.",
        )
        assert "Project Alpha" in result
        assert "Target Corp" in result
        assert "Quality of Earnings" in result
        assert "Net Working Capital" in result
        assert "Net Debt" in result

    def test_executive_summary_with_findings(self):
        """발견사항 포함 Executive Summary."""
        result = generate_executive_summary(
            deal_name="Project Beta",
            target_name="Beta Inc.",
            analysis_period="FY2025",
            qoe_summary="EBITDA 1B",
            nwc_summary="NWC 400M",
            debt_summary="Net Debt 200M",
            key_findings=[
                "Non-recurring items identified",
                "Working capital seasonality observed",
            ],
            risk_factors=[
                "Customer concentration risk",
                "Pending litigation",
            ],
        )
        assert "Key Findings" in result
        assert "Risk Factors" in result
        assert "Non-recurring" in result
        assert "litigation" in result


class TestKoreanNarratives:
    """T-NARRATIVE-10: 한글 서술문 테스트."""

    def test_korean_qoe(self):
        """한글 QoE 서술문."""
        result = generate_qoe_narrative(
            period="2025년 12월",
            reported_ebitda=Decimal("10000000000"),  # 100억
            adjusted_ebitda=Decimal("12000000000"),  # 120억
            adjustments=[
                {
                    "category": "일회성",
                    "amount": "2,000,000,000",
                    "description": "법적 합의금",
                },
            ],
        )
        assert "2025년 12월" in result
        # 한글 숫자 포맷 확인
        assert "10,000,000,000" in result or "100억" in result

    def test_korean_special_characters(self):
        """특수 문자 포함 서술문."""
        result = generate_nwc_narrative(
            period="2025년 (Q4)",
            total_nwc=Decimal("500000000"),
            current_assets=Decimal("1000000000"),
            current_liabilities=Decimal("500000000"),
        )
        assert "2025년 (Q4)" in result
