"""SaaS 산업별 재무 지표 계산기 단위 테스트.

ARR, MRR, NRR, Gross/Net Churn, LTV, CAC, LTV/CAC, Rule of 40,
CAC Payback 등 SaaS 핵심 KPI 계산을 검증합니다.

> 마지막 수정: 2026-02-11 15:00:00
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.saas import (
    SaaSMetrics,
    calculate_arr,
    calculate_cac,
    calculate_cac_payback,
    calculate_gross_churn,
    calculate_ltv,
    calculate_ltv_cac_ratio,
    calculate_mrr,
    calculate_net_churn,
    calculate_nrr,
    calculate_rule_of_40,
    calculate_saas_metrics,
)


# ---------------------------------------------------------------------------
# calculate_arr 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateArr:
    """calculate_arr 함수 테스트."""

    def test_basic_arr(self) -> None:
        """연간 구독 매출이 그대로 ARR로 반환된다."""
        result = calculate_arr(
            subscription_revenue={"2023": Decimal("120000"), "2024": Decimal("150000")},
        )
        assert result == {"2023": Decimal("120000"), "2024": Decimal("150000")}

    def test_none_value_excluded(self) -> None:
        """구독 매출이 None인 연도는 제외된다."""
        result = calculate_arr(
            subscription_revenue={"2023": Decimal("120000"), "2024": None},
        )
        assert result == {"2023": Decimal("120000")}
        assert "2024" not in result

    def test_empty_input(self) -> None:
        """빈 입력은 빈 딕셔너리를 반환한다."""
        result = calculate_arr(subscription_revenue={})
        assert result == {}


# ---------------------------------------------------------------------------
# calculate_mrr 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateMrr:
    """calculate_mrr 함수 테스트."""

    def test_basic_mrr(self) -> None:
        """MRR = 연간 구독 매출 / 12."""
        result = calculate_mrr(
            subscription_revenue={"2023": Decimal("120000")},
        )
        assert result == {"2023": Decimal("10000")}

    def test_none_excluded(self) -> None:
        """None인 연도는 제외된다."""
        result = calculate_mrr(
            subscription_revenue={"2023": Decimal("120000"), "2024": None},
        )
        assert "2024" not in result


# ---------------------------------------------------------------------------
# calculate_nrr 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateNrr:
    """calculate_nrr 함수 테스트."""

    def test_basic_nrr(self) -> None:
        """NRR = (기초ARR + 확장 - 축소 - 이탈) / 기초ARR × 100."""
        result = calculate_nrr(
            beginning_arr={"2023": Decimal("100000")},
            expansion={"2023": Decimal("20000")},
            contraction={"2023": Decimal("5000")},
            churned={"2023": Decimal("3000")},
        )
        # (100000 + 20000 - 5000 - 3000) / 100000 * 100 = 112.0
        assert result["2023"] == pytest.approx(112.0)

    def test_net_expansion_above_100(self) -> None:
        """확장이 축소+이탈보다 크면 NRR > 100%."""
        result = calculate_nrr(
            beginning_arr={"2023": Decimal("100000")},
            expansion={"2023": Decimal("30000")},
            contraction={"2023": Decimal("2000")},
            churned={"2023": Decimal("1000")},
        )
        assert result["2023"] > 100.0

    def test_zero_beginning_arr_excluded(self) -> None:
        """기초ARR이 0이면 해당 연도 제외."""
        result = calculate_nrr(
            beginning_arr={"2023": Decimal("0")},
            expansion={"2023": Decimal("20000")},
            contraction={"2023": Decimal("5000")},
            churned={"2023": Decimal("3000")},
        )
        assert "2023" not in result

    def test_none_inputs_excluded(self) -> None:
        """구성요소 중 None이 있으면 해당 연도 제외."""
        result = calculate_nrr(
            beginning_arr={"2023": Decimal("100000")},
            expansion={"2023": None},
            contraction={"2023": Decimal("5000")},
            churned={"2023": Decimal("3000")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_gross_churn 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateGrossChurn:
    """calculate_gross_churn 함수 테스트."""

    def test_basic_gross_churn(self) -> None:
        """Gross Churn = (이탈 + 축소) / 기초ARR × 100."""
        result = calculate_gross_churn(
            churned_revenue={"2023": Decimal("5000")},
            contraction_revenue={"2023": Decimal("3000")},
            beginning_arr={"2023": Decimal("100000")},
        )
        # (5000 + 3000) / 100000 * 100 = 8.0
        assert result["2023"] == pytest.approx(8.0)

    def test_zero_beginning_arr_excluded(self) -> None:
        """기초ARR이 0이면 제외."""
        result = calculate_gross_churn(
            churned_revenue={"2023": Decimal("5000")},
            contraction_revenue={"2023": Decimal("3000")},
            beginning_arr={"2023": Decimal("0")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_net_churn 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateNetChurn:
    """calculate_net_churn 함수 테스트."""

    def test_positive_net_churn(self) -> None:
        """이탈+축소 > 확장이면 양수 Net Churn."""
        result = calculate_net_churn(
            churned_revenue={"2023": Decimal("5000")},
            contraction_revenue={"2023": Decimal("3000")},
            expansion_revenue={"2023": Decimal("2000")},
            beginning_arr={"2023": Decimal("100000")},
        )
        # (5000 + 3000 - 2000) / 100000 * 100 = 6.0
        assert result["2023"] == pytest.approx(6.0)

    def test_negative_net_churn_healthy(self) -> None:
        """확장 > 이탈+축소이면 음수 Net Churn (건전한 SaaS)."""
        result = calculate_net_churn(
            churned_revenue={"2023": Decimal("2000")},
            contraction_revenue={"2023": Decimal("1000")},
            expansion_revenue={"2023": Decimal("10000")},
            beginning_arr={"2023": Decimal("100000")},
        )
        # (2000 + 1000 - 10000) / 100000 * 100 = -7.0
        assert result["2023"] == pytest.approx(-7.0)


# ---------------------------------------------------------------------------
# calculate_ltv 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateLtv:
    """calculate_ltv 함수 테스트."""

    def test_basic_ltv(self) -> None:
        """LTV = ARPU × 매출총이익률 / Churn Rate."""
        result = calculate_ltv(
            arpu={"2023": Decimal("1000")},
            gross_margin_pct={"2023": Decimal("0.80")},
            churn_rate={"2023": Decimal("0.05")},
        )
        # 1000 * 0.80 / 0.05 = 16000
        assert result["2023"] == Decimal("16000")

    def test_zero_churn_excluded(self) -> None:
        """Churn Rate가 0이면 제외 (무한대 방지)."""
        result = calculate_ltv(
            arpu={"2023": Decimal("1000")},
            gross_margin_pct={"2023": Decimal("0.80")},
            churn_rate={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_none_churn_excluded(self) -> None:
        """Churn Rate가 None이면 제외."""
        result = calculate_ltv(
            arpu={"2023": Decimal("1000")},
            gross_margin_pct={"2023": Decimal("0.80")},
            churn_rate={"2023": None},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_cac 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateCac:
    """calculate_cac 함수 테스트."""

    def test_basic_cac(self) -> None:
        """CAC = 영업마케팅비 / 신규고객수."""
        result = calculate_cac(
            sales_marketing_cost={"2023": Decimal("500000")},
            new_customers={"2023": Decimal("100")},
        )
        assert result["2023"] == Decimal("5000")

    def test_zero_customers_excluded(self) -> None:
        """신규고객수가 0이면 제외."""
        result = calculate_cac(
            sales_marketing_cost={"2023": Decimal("500000")},
            new_customers={"2023": Decimal("0")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_ltv_cac_ratio 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateLtvCacRatio:
    """calculate_ltv_cac_ratio 함수 테스트."""

    def test_basic_ratio(self) -> None:
        """LTV/CAC = LTV / CAC."""
        result = calculate_ltv_cac_ratio(
            ltv={"2023": Decimal("15000")},
            cac={"2023": Decimal("5000")},
        )
        assert result["2023"] == pytest.approx(3.0)

    def test_zero_cac_excluded(self) -> None:
        """CAC가 0이면 제외."""
        result = calculate_ltv_cac_ratio(
            ltv={"2023": Decimal("15000")},
            cac={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_mismatched_years(self) -> None:
        """LTV와 CAC에 공통 연도만 계산."""
        result = calculate_ltv_cac_ratio(
            ltv={"2023": Decimal("15000"), "2024": Decimal("18000")},
            cac={"2023": Decimal("5000")},
        )
        assert "2023" in result
        assert "2024" not in result


# ---------------------------------------------------------------------------
# calculate_rule_of_40 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateRuleOf40:
    """calculate_rule_of_40 함수 테스트."""

    def test_basic_rule_of_40(self) -> None:
        """Rule of 40 = 매출성장률 + 영업이익률."""
        result = calculate_rule_of_40(
            revenue_growth_rate={"2023": 30.0},
            operating_margin={"2023": 15.0},
        )
        assert result["2023"] == pytest.approx(45.0)

    def test_negative_margin_high_growth(self) -> None:
        """음수 영업이익률이라도 성장률로 보상 가능."""
        result = calculate_rule_of_40(
            revenue_growth_rate={"2023": 60.0},
            operating_margin={"2023": -15.0},
        )
        assert result["2023"] == pytest.approx(45.0)

    def test_missing_year_excluded(self) -> None:
        """한쪽에만 있는 연도는 제외."""
        result = calculate_rule_of_40(
            revenue_growth_rate={"2023": 30.0, "2024": 25.0},
            operating_margin={"2023": 15.0},
        )
        assert "2023" in result
        assert "2024" not in result


# ---------------------------------------------------------------------------
# calculate_cac_payback 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateCacPayback:
    """calculate_cac_payback 함수 테스트."""

    def test_basic_payback(self) -> None:
        """CAC Payback = CAC / (고객당MRR × 총이익률)."""
        result = calculate_cac_payback(
            cac={"2023": Decimal("6000")},
            mrr_per_customer={"2023": Decimal("500")},
            gross_margin_pct={"2023": Decimal("0.80")},
        )
        # 6000 / (500 * 0.80) = 6000 / 400 = 15.0 개월
        assert result["2023"] == pytest.approx(15.0)

    def test_zero_margin_excluded(self) -> None:
        """총이익률이 0이면 제외."""
        result = calculate_cac_payback(
            cac={"2023": Decimal("6000")},
            mrr_per_customer={"2023": Decimal("500")},
            gross_margin_pct={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_zero_mrr_excluded(self) -> None:
        """고객당 MRR이 0이면 제외."""
        result = calculate_cac_payback(
            cac={"2023": Decimal("6000")},
            mrr_per_customer={"2023": Decimal("0")},
            gross_margin_pct={"2023": Decimal("0.80")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_saas_metrics 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateSaaSMetrics:
    """calculate_saas_metrics 통합 테스트."""

    @pytest.fixture
    def full_saas_data(self) -> dict:
        """전체 SaaS 테스트 데이터."""
        return {
            "revenue": {"2023": Decimal("200000"), "2024": Decimal("260000")},
            "subscription_revenue": {
                "2023": Decimal("180000"),
                "2024": Decimal("240000"),
            },
            "beginning_arr": {"2023": Decimal("150000"), "2024": Decimal("180000")},
            "expansion_revenue": {"2023": Decimal("25000"), "2024": Decimal("35000")},
            "contraction_revenue": {"2023": Decimal("3000"), "2024": Decimal("4000")},
            "churned_revenue": {"2023": Decimal("5000"), "2024": Decimal("6000")},
            "sales_marketing_cost": {
                "2023": Decimal("80000"),
                "2024": Decimal("100000"),
            },
            "new_customers": {"2023": Decimal("50"), "2024": Decimal("60")},
            "arpu": {"2023": Decimal("3600"), "2024": Decimal("4000")},
            "gross_margin_pct": {"2023": Decimal("0.75"), "2024": Decimal("0.78")},
            "revenue_growth_rate": {"2023": 25.0, "2024": 30.0},
            "operating_margin": {"2023": 10.0, "2024": 12.0},
        }

    def test_all_metrics_calculated(self, full_saas_data: dict) -> None:
        """모든 입력 제공 시 10개 지표 모두 계산된다."""
        result = calculate_saas_metrics(**full_saas_data)

        assert isinstance(result, SaaSMetrics)
        assert len(result.arr) == 2
        assert len(result.mrr) == 2
        assert len(result.nrr) == 2
        assert len(result.gross_churn_rate) == 2
        assert len(result.net_churn_rate) == 2
        assert len(result.ltv) > 0
        assert len(result.cac) == 2
        assert len(result.ltv_cac_ratio) > 0
        assert len(result.rule_of_40) == 2
        assert len(result.cac_payback_months) > 0

    def test_minimal_data_graceful(self) -> None:
        """필수 입력만 제공 시 ARR/MRR만 계산, 나머지는 빈 dict."""
        result = calculate_saas_metrics(
            revenue={"2023": Decimal("200000")},
            subscription_revenue={"2023": Decimal("180000")},
        )
        assert isinstance(result, SaaSMetrics)
        assert result.arr == {"2023": Decimal("180000")}
        assert result.mrr == {"2023": Decimal("15000")}
        assert result.nrr == {}
        assert result.gross_churn_rate == {}
        assert result.net_churn_rate == {}
        assert result.ltv == {}
        assert result.cac == {}
        assert result.ltv_cac_ratio == {}
        assert result.rule_of_40 == {}
        assert result.cac_payback_months == {}

    def test_dataclass_is_frozen(self) -> None:
        """SaaSMetrics는 frozen 데이터클래스이다."""
        result = calculate_saas_metrics(
            revenue={"2023": Decimal("200000")},
            subscription_revenue={"2023": Decimal("180000")},
        )
        with pytest.raises(AttributeError):
            result.arr = {}  # type: ignore[misc]

    def test_nrr_values_correct(self, full_saas_data: dict) -> None:
        """NRR 값이 정확히 계산되는지 확인한다."""
        result = calculate_saas_metrics(**full_saas_data)
        # 2023: (150000 + 25000 - 3000 - 5000) / 150000 * 100 = 111.33...
        assert result.nrr["2023"] == pytest.approx(
            (150000 + 25000 - 3000 - 5000) / 150000 * 100, rel=1e-4
        )

    def test_rule_of_40_values_correct(self, full_saas_data: dict) -> None:
        """Rule of 40 값이 정확히 계산되는지 확인한다."""
        result = calculate_saas_metrics(**full_saas_data)
        # 2023: 25.0 + 10.0 = 35.0
        assert result.rule_of_40["2023"] == pytest.approx(35.0)
        # 2024: 30.0 + 12.0 = 42.0
        assert result.rule_of_40["2024"] == pytest.approx(42.0)
