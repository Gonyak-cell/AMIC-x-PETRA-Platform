"""수주잔액 분석 엔진 단위 테스트."""

from decimal import Decimal

import pytest

from app.engines.backlog_engine import (
    BacklogAgingResult,
    BacklogSummaryResult,
    MonthlyNewOrderResult,
    NegativeMarginResult,
    compute_backlog_aging,
    compute_backlog_summary,
    compute_monthly_new_orders,
    detect_negative_margin_orders,
)

# ── Backlog Summary ─────────────────────────────────────


class TestComputeBacklogSummary:
    def test_basic_summary(self):
        """기본 수주잔액 집계."""
        entries = [
            {"customer_name": "A사", "amount": "30000"},
            {"customer_name": "B사", "amount": "20000"},
            {"customer_name": "A사", "amount": "10000"},
        ]
        result, evidence = compute_backlog_summary(entries)

        assert result.total_backlog == Decimal("60000.0000")
        assert len(result.backlog_by_customer) == 2
        # A사 40000 > B사 20000 순
        assert result.backlog_by_customer[0].customer_name == "A사"
        assert result.backlog_by_customer[0].amount == Decimal("40000.0000")
        assert result.order_count == 3

    def test_customer_share(self):
        """거래처별 비중 계산."""
        entries = [
            {"customer_name": "A사", "amount": "60000"},
            {"customer_name": "B사", "amount": "40000"},
        ]
        result, _ = compute_backlog_summary(entries)

        assert result.backlog_by_customer[0].share_pct == Decimal("60.00")
        assert result.backlog_by_customer[1].share_pct == Decimal("40.00")

    def test_book_to_bill(self):
        """Book-to-Bill ratio 계산."""
        entries = [
            {"customer_name": "A사", "amount": "50000"},
        ]
        result, _ = compute_backlog_summary(
            entries,
            revenue_total=Decimal("100000"),
            new_orders_total=Decimal("120000"),
        )

        assert result.book_to_bill_ratio == Decimal("1.20")

    def test_backlog_coverage(self):
        """수주 커버리지 (개월수) 계산."""
        entries = [
            {"customer_name": "A사", "amount": "100000"},
        ]
        result, _ = compute_backlog_summary(
            entries,
            revenue_total=Decimal("120000"),
            revenue_months=12,
        )

        # 커버리지 = 100000 / (120000/12) = 100000 / 10000 = 10.00개월
        assert result.backlog_coverage_months == Decimal("10.00")

    def test_hhi_calculation(self):
        """HHI 집중도 지수 계산."""
        # 2개 균등 → (50)^2 + (50)^2 = 5000
        entries = [
            {"customer_name": "A사", "amount": "50000"},
            {"customer_name": "B사", "amount": "50000"},
        ]
        result, _ = compute_backlog_summary(entries)

        assert result.concentration_index == Decimal("5000.00")

    def test_top_n_share(self):
        """Top N 비중 계산."""
        entries = [
            {"customer_name": f"고객{i}", "amount": str(10000 - i * 100)}
            for i in range(10)
        ]
        result, _ = compute_backlog_summary(entries, top_n=5)

        # Top 5 합산 비중 > 50%
        assert result.top_n_share > Decimal("50")

    def test_concentration_warning(self):
        """집중도 경고 생성."""
        # 1개 거래처 100%
        entries = [
            {"customer_name": "독점사", "amount": "100000"},
        ]
        result, _ = compute_backlog_summary(entries)

        assert result.top_n_share == Decimal("100.00")
        assert any("BACKLOG_CONCENTRATION" in w for w in result.warnings)

    def test_low_btb_warning(self):
        """낮은 Book-to-Bill 경고."""
        entries = [
            {"customer_name": "A사", "amount": "50000"},
        ]
        result, _ = compute_backlog_summary(
            entries,
            revenue_total=Decimal("100000"),
            new_orders_total=Decimal("80000"),
        )

        assert result.book_to_bill_ratio == Decimal("0.80")
        assert any("BACKLOG_LOW_BTB" in w for w in result.warnings)

    def test_empty_entries(self):
        """빈 입력 처리."""
        result, _ = compute_backlog_summary([])

        assert result.total_backlog == Decimal("0")
        assert any("BACKLOG_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        """Evidence 링크 생성 확인."""
        entries = [{"customer_name": "A사", "amount": "50000"}]
        _, evidence = compute_backlog_summary(entries)

        assert len(evidence) >= 1
        assert evidence[0].target_type == "backlog_summary"


# ── Backlog Aging ────────────────────────────────────────


class TestComputeBacklogAging:
    def test_basic_aging(self):
        """기본 Aging 구간 배정."""
        entries = [
            {"amount": "30000", "remaining_months": 1},  # 0-3M
            {"amount": "20000", "remaining_months": 4},  # 3-6M
            {"amount": "10000", "remaining_months": 8},  # 6-12M
            {"amount": "5000", "remaining_months": 15},  # 12M+
        ]
        result, _ = compute_backlog_aging(entries)

        assert result.total_backlog == Decimal("65000.0000")
        assert len(result.buckets) == 4
        assert result.buckets[0].bucket == "0-3M"
        assert result.buckets[0].amount == Decimal("30000.0000")

    def test_overdue_detection(self):
        """납기 초과 감지."""
        entries = [
            {"amount": "30000", "remaining_months": 2},
            {"amount": "20000", "remaining_months": -1},  # 납기 초과
            {"amount": "10000", "remaining_months": -3},  # 납기 초과
        ]
        result, _ = compute_backlog_aging(entries)

        assert result.overdue_amount == Decimal("30000.0000")
        assert result.overdue_share_pct == Decimal("50.00")

    def test_overdue_warning(self):
        """높은 납기 초과율 경고."""
        entries = [
            {"amount": "30000", "remaining_months": 2},
            {"amount": "20000", "remaining_months": -1},
        ]
        result, _ = compute_backlog_aging(entries)

        assert result.overdue_share_pct == Decimal("40.00")
        assert any("AGING_HIGH_OVERDUE" in w for w in result.warnings)

    def test_long_term_warning(self):
        """장기 수주 경고 (6M+ > 30%)."""
        entries = [
            {"amount": "20000", "remaining_months": 1},
            {"amount": "40000", "remaining_months": 9},   # 6-12M
            {"amount": "30000", "remaining_months": 18},  # 12M+
        ]
        result, _ = compute_backlog_aging(entries)

        assert any("AGING_LONG_TERM" in w for w in result.warnings)

    def test_empty_entries(self):
        """빈 입력."""
        result, _ = compute_backlog_aging([])
        assert result.total_backlog == Decimal("0")
        assert any("AGING_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        """Evidence 링크."""
        entries = [{"amount": "50000", "remaining_months": 2}]
        _, evidence = compute_backlog_aging(entries)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "backlog_aging"


# ── Negative Margin Detection ────────────────────────────


class TestDetectNegativeMarginOrders:
    def test_basic_detection(self):
        """기본 역마진 감지."""
        entries = [
            {
                "order_id": "ORD-001",
                "customer_name": "A사",
                "amount": "10000",
                "estimated_cost": "12000",
            },
            {
                "order_id": "ORD-002",
                "customer_name": "B사",
                "amount": "20000",
                "estimated_cost": "18000",
            },
        ]
        result, _ = detect_negative_margin_orders(entries)

        assert result.negative_count == 1
        assert result.negative_margin_orders[0].order_id == "ORD-001"
        assert result.negative_margin_orders[0].margin == Decimal("-20.00")

    def test_loss_calculation(self):
        """역마진 손실 합계."""
        entries = [
            {"order_id": "ORD-001", "amount": "10000", "estimated_cost": "12000"},
            {"order_id": "ORD-002", "amount": "8000", "estimated_cost": "10000"},
        ]
        result, _ = detect_negative_margin_orders(entries)

        assert result.negative_count == 2
        assert result.total_negative_amount == Decimal("18000.0000")
        assert result.total_negative_loss == Decimal("4000.0000")

    def test_no_cost_data(self):
        """원가 미기재 항목 건너뛰기."""
        entries = [
            {"order_id": "ORD-001", "amount": "10000"},
        ]
        result, _ = detect_negative_margin_orders(entries)
        assert result.negative_count == 0

    def test_many_negative_warning(self):
        """많은 역마진 수주 경고."""
        entries = [
            {"order_id": f"ORD-{i:03d}", "amount": "10000", "estimated_cost": "12000"}
            for i in range(7)
        ]
        result, _ = detect_negative_margin_orders(entries)
        assert any("MARGIN_MANY_NEGATIVE" in w for w in result.warnings)

    def test_evidence_generated(self):
        """역마진별 Evidence."""
        entries = [
            {"order_id": "ORD-001", "amount": "10000", "estimated_cost": "15000"},
        ]
        _, evidence = detect_negative_margin_orders(entries)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "negative_margin"


# ── Monthly New Orders ───────────────────────────────────


class TestComputeMonthlyNewOrders:
    def test_basic_monthly(self):
        """기본 월별 집계."""
        entries = [
            {"order_month": "2024-01", "amount": "10000"},
            {"order_month": "2024-02", "amount": "15000"},
            {"order_month": "2024-01", "amount": "5000"},
        ]
        result, _ = compute_monthly_new_orders(entries)

        assert result.months == ["2024-01", "2024-02"]
        assert result.amounts["2024-01"] == Decimal("15000.0000")
        assert result.amounts["2024-02"] == Decimal("15000.0000")

    def test_cumulative(self):
        """누적 계산."""
        entries = [
            {"order_month": "2024-01", "amount": "10000"},
            {"order_month": "2024-02", "amount": "20000"},
            {"order_month": "2024-03", "amount": "15000"},
        ]
        result, _ = compute_monthly_new_orders(entries)

        assert result.cumulative["2024-01"] == Decimal("10000.0000")
        assert result.cumulative["2024-02"] == Decimal("30000.0000")
        assert result.cumulative["2024-03"] == Decimal("45000.0000")

    def test_yoy_growth(self):
        """전년 동월 대비 YoY."""
        entries = [
            {"order_month": "2024-01", "amount": "12000"},
            {"order_month": "2024-02", "amount": "18000"},
        ]
        prior = [
            {"order_month": "2023-01", "amount": "10000"},
            {"order_month": "2023-02", "amount": "15000"},
        ]
        result, _ = compute_monthly_new_orders(entries, prior_year_entries=prior)

        assert result.yoy_growth["2024-01"] == Decimal("20.00")
        assert result.yoy_growth["2024-02"] == Decimal("20.00")

    def test_declining_warning(self):
        """3개월 연속 감소 경고."""
        entries = [
            {"order_month": "2024-01", "amount": "30000"},
            {"order_month": "2024-02", "amount": "20000"},
            {"order_month": "2024-03", "amount": "10000"},
        ]
        result, _ = compute_monthly_new_orders(entries)
        assert any("ORDERS_DECLINING" in w for w in result.warnings)

    def test_empty_entries(self):
        """빈 입력."""
        result, _ = compute_monthly_new_orders([])
        assert result.months == []
        assert any("ORDERS_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        """Evidence 링크."""
        entries = [{"order_month": "2024-01", "amount": "10000"}]
        _, evidence = compute_monthly_new_orders(entries)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "monthly_new_orders"
