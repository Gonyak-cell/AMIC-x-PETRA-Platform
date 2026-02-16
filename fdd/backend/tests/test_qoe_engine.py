"""QoE 엔진 순수 함수 단위 테스트 — FDD-501/502/503."""

from decimal import Decimal

from app.engines.qoe_engine import (
    AdjustmentCandidateData,
    CategoryTotal,
    build_qoe_bridge,
    calculate_reported_ebitda,
    detect_adjustment_candidates,
)

# ── Helpers ──────────────────────────────────────────────


def _cat(category: str, total: str, count: int = 1) -> CategoryTotal:
    """Quick CategoryTotal factory."""
    return CategoryTotal(
        category=category,
        total=Decimal(total),
        account_count=count,
        accounts=[{"code": f"{category}-001", "name": category, "amount": total}],
    )


# ── TestCalculateReportedEBITDA ──────────────────────────


class TestCalculateReportedEBITDA:
    """Reported EBITDA 계산 테스트."""

    def test_basic_positive_ebitda(self):
        """기본 양수 EBITDA: Revenue 100M - COGS 60M - SGA 20M = EBITDA 20M."""
        totals = [
            _cat("REVENUE", "-100000000"),  # 대변(음수)
            _cat("COGS", "60000000"),  # 차변(양수)
            _cat("SGA", "20000000"),  # 차변(양수)
            _cat("DEPRECIATION_AMORTIZATION", "5000000"),
        ]
        result, _evidence = calculate_reported_ebitda(totals)

        assert result.revenue == Decimal("100000000.0000")
        assert result.cogs == Decimal("60000000.0000")
        assert result.gross_profit == Decimal("40000000.0000")
        assert result.sga == Decimal("20000000.0000")
        assert result.depreciation_amortization == Decimal("5000000.0000")
        assert result.operating_income == Decimal("15000000.0000")
        # EBITDA = OI + D&A = 15M + 5M = 20M
        assert result.reported_ebitda == Decimal("20000000.0000")
        assert len(result.warnings) == 0

    def test_ebitda_with_da_addback(self):
        """D&A add-back 확인: EBITDA = Operating Income + D&A."""
        totals = [
            _cat("REVENUE", "-50000000"),
            _cat("COGS", "30000000"),
            _cat("SGA", "10000000"),
            _cat("DEPRECIATION_AMORTIZATION", "8000000"),
        ]
        result, _ = calculate_reported_ebitda(totals)

        oi = (
            Decimal("50000000")
            - Decimal("30000000")
            - Decimal("10000000")
            - Decimal("8000000")
        )
        assert result.operating_income == oi.quantize(Decimal("0.0001"))
        assert result.reported_ebitda == (oi + Decimal("8000000")).quantize(
            Decimal("0.0001")
        )

    def test_negative_ebitda_warning(self):
        """음수 EBITDA → 경고 포함."""
        totals = [
            _cat("REVENUE", "-10000000"),
            _cat("COGS", "8000000"),
            _cat("SGA", "5000000"),
        ]
        result, _ = calculate_reported_ebitda(totals)

        assert result.reported_ebitda < Decimal("0")
        assert any("QOE_NEGATIVE_EBITDA" in w for w in result.warnings)

    def test_zero_revenue(self):
        """매출 0일 때 정상 동작."""
        totals = [
            _cat("SGA", "1000000"),
        ]
        result, _ = calculate_reported_ebitda(totals)

        assert result.revenue == Decimal("0.0000")
        assert result.reported_ebitda == Decimal("-1000000.0000")

    def test_other_operating_income(self):
        """기타영업수익 반영 확인."""
        totals = [
            _cat("REVENUE", "-100000000"),
            _cat("COGS", "60000000"),
            _cat("SGA", "20000000"),
            _cat("DEPRECIATION_AMORTIZATION", "5000000"),
            _cat("OTHER_OPERATING_INCOME", "-3000000"),  # 대변(음수) → 양수
        ]
        result, _ = calculate_reported_ebitda(totals)

        # GP = 100M - 60M = 40M
        # OI = 40M - 20M - 5M + 3M = 18M
        # EBITDA = 18M + 5M = 23M
        assert result.other_operating == Decimal("3000000.0000")
        assert result.operating_income == Decimal("18000000.0000")
        assert result.reported_ebitda == Decimal("23000000.0000")

    def test_sign_convention_revenue_credit(self):
        """TB 매출 대변(음수) → P&L 양수 변환 확인."""
        totals = [_cat("REVENUE", "-50000000")]
        result, _ = calculate_reported_ebitda(totals)
        assert result.revenue == Decimal("50000000.0000")

    def test_sign_convention_cogs_debit(self):
        """TB COGS 차변(양수) → 그대로 유지."""
        totals = [_cat("COGS", "30000000")]
        result, _ = calculate_reported_ebitda(totals)
        assert result.cogs == Decimal("30000000.0000")

    def test_empty_categories(self):
        """카테고리 없을 때 모든 값 0."""
        result, evidence = calculate_reported_ebitda([])

        assert result.revenue == Decimal("0.0000")
        assert result.cogs == Decimal("0.0000")
        assert result.reported_ebitda == Decimal("0.0000")
        assert len(evidence) == 0

    def test_evidence_links_generated(self):
        """계정별 EvidenceLink 생성 확인."""
        totals = [
            CategoryTotal(
                category="REVENUE",
                total=Decimal("-50000000"),
                account_count=2,
                accounts=[
                    {"code": "4100", "name": "매출", "amount": "-30000000"},
                    {"code": "4200", "name": "용역매출", "amount": "-20000000"},
                ],
            ),
        ]
        _, evidence = calculate_reported_ebitda(totals)
        assert len(evidence) == 2
        assert evidence[0].target_type == "qoe_calculation"
        assert evidence[0].source_type == "TB"

    def test_decimal_precision(self):
        """소수점 4자리 정밀도 보장."""
        totals = [_cat("REVENUE", "-12345678.9012")]
        result, _ = calculate_reported_ebitda(totals)
        assert result.revenue == Decimal("12345678.9012")


# ── TestDetectAdjustmentCandidates ───────────────────────


class TestDetectAdjustmentCandidates:
    """조정 후보 감지 테스트."""

    def test_keyword_litigation(self):
        """소송 키워드 감지."""
        gl = [
            {
                "entry_id": "GL-001",
                "account_code": "9100",
                "account_name": "소송비용",
                "amount": "50000000",
                "description": "소송 합의금",
                "entry_date": "2025-06-15",
            },
        ]
        candidates = detect_adjustment_candidates(gl, set(), Decimal("1000000000"))
        assert len(candidates) == 1
        assert candidates[0].category == "NON_RECURRING"
        assert candidates[0].detection_method == "keyword"
        assert "소송" in candidates[0].description

    def test_keyword_restructuring(self):
        """구조조정 키워드 감지."""
        gl = [
            {
                "entry_id": "GL-002",
                "account_code": "9200",
                "account_name": "경비",
                "amount": "30000000",
                "description": "구조조정 관련 비용",
                "entry_date": "2025-03-01",
            },
        ]
        candidates = detect_adjustment_candidates(gl, set(), Decimal("1000000000"))
        assert len(candidates) == 1
        assert candidates[0].category == "NON_RECURRING"

    def test_owner_related_keyword(self):
        """관계사/오너 키워드 → NORMALIZATION."""
        gl = [
            {
                "entry_id": "GL-003",
                "account_code": "8100",
                "account_name": "관계사 거래",
                "amount": "20000000",
                "description": "특수관계자 거래",
                "entry_date": "2025-04-01",
            },
        ]
        candidates = detect_adjustment_candidates(gl, set(), Decimal("1000000000"))
        assert len(candidates) == 1
        assert candidates[0].category == "NORMALIZATION"

    def test_non_operating_account(self):
        """비영업 매핑 계정 감지."""
        gl = [
            {
                "entry_id": "GL-004",
                "account_code": "NON-001",
                "account_name": "외환차손",
                "amount": "15000000",
                "description": "외환차손",
                "entry_date": "2025-05-01",
            },
        ]
        candidates = detect_adjustment_candidates(
            gl, {"NON-001"}, Decimal("1000000000")
        )
        assert len(candidates) == 1
        assert candidates[0].category == "NON_OPERATING"
        assert candidates[0].detection_method == "non_operating"

    def test_year_end_large_entry(self):
        """연말 대규모 전표 감지."""
        gl = [
            {
                "entry_id": "GL-005",
                "account_code": "5100",
                "account_name": "잡비",
                "amount": "100000000",
                "description": "기말 대체 분개",
                "entry_date": "2025-12-31",
            },
        ]
        # Materiality = max(100M * 1%, 1M) = 1M. 5x = 5M. 100M >= 5M → match
        candidates = detect_adjustment_candidates(gl, set(), Decimal("100000000"))
        assert len(candidates) == 1
        assert candidates[0].detection_method == "year_end"

    def test_below_materiality_excluded(self):
        """중요성 기준 미달 항목은 제외."""
        gl = [
            {
                "entry_id": "GL-006",
                "account_code": "5100",
                "account_name": "소송비용",
                "amount": "500000",
                "description": "소송비용",
                "entry_date": "2025-01-01",
            },
        ]
        # Materiality = max(1B * 1%, 1M) = 10M. 500K < 10M → excluded
        candidates = detect_adjustment_candidates(gl, set(), Decimal("1000000000"))
        assert len(candidates) == 0

    def test_dedup_by_entry_id(self):
        """동일 entry_id 중복 감지 방지."""
        gl = [
            {
                "entry_id": "GL-007",
                "account_code": "9100",
                "account_name": "소송비용",
                "amount": "50000000",
                "description": "소송 합의금 대표이사",
                "entry_date": "2025-06-15",
            },
        ]
        candidates = detect_adjustment_candidates(gl, {"9100"}, Decimal("1000000000"))
        # "소송" matches first (NON_RECURRING), should not also match "대표이사" or non_operating
        assert len(candidates) == 1

    def test_no_candidates_empty_gl(self):
        """GL 없으면 후보 0건."""
        candidates = detect_adjustment_candidates([], set(), Decimal("100000000"))
        assert len(candidates) == 0

    def test_sorted_by_confidence_desc(self):
        """confidence DESC 정렬 확인."""
        gl = [
            {
                "entry_id": "GL-A",
                "account_code": "NON-001",
                "account_name": "이자수익",
                "amount": "20000000",
                "description": "이자수익",
                "entry_date": "2025-03-01",
            },
            {
                "entry_id": "GL-B",
                "account_code": "9100",
                "account_name": "소송비용",
                "amount": "30000000",
                "description": "소송비용",
                "entry_date": "2025-04-01",
            },
        ]
        candidates = detect_adjustment_candidates(
            gl, {"NON-001"}, Decimal("1000000000")
        )
        assert len(candidates) == 2
        # non_operating=80 > keyword=70
        assert candidates[0].confidence_score >= candidates[1].confidence_score


# ── TestBuildQoEBridge ───────────────────────────────────


class TestBuildQoEBridge:
    """QoE Bridge 구축 테스트."""

    def test_no_adjustments(self):
        """조정 없을 때 Adjusted = Reported."""
        bridge = build_qoe_bridge(Decimal("20000000.0000"), [])
        assert bridge.adjusted_ebitda == Decimal("20000000.0000")
        assert bridge.total_adjustments == Decimal("0.0000")
        assert bridge.balance_check_error == Decimal("0.0000")

    def test_single_positive_adjustment(self):
        """단일 양수 조정: Adjusted = Reported + Adj."""
        adj = AdjustmentCandidateData(
            category="NON_RECURRING",
            description="소송비용 제거",
            amount=Decimal("5000000.0000"),
            detection_method="keyword",
            confidence_score=Decimal("70.00"),
        )
        bridge = build_qoe_bridge(Decimal("20000000.0000"), [adj])
        assert bridge.adjusted_ebitda == Decimal("25000000.0000")
        assert bridge.total_adjustments == Decimal("5000000.0000")
        assert bridge.balance_check_error == Decimal("0.0000")

    def test_single_negative_adjustment(self):
        """단일 음수 조정 (차감)."""
        adj = AdjustmentCandidateData(
            category="NORMALIZATION",
            description="과다 임원 급여",
            amount=Decimal("-3000000.0000"),
            detection_method="keyword",
            confidence_score=Decimal("60.00"),
        )
        bridge = build_qoe_bridge(Decimal("20000000.0000"), [adj])
        assert bridge.adjusted_ebitda == Decimal("17000000.0000")
        assert bridge.balance_check_error == Decimal("0.0000")

    def test_multiple_mixed_adjustments(self):
        """복수 조정 (양수 + 음수 혼합)."""
        adjs = [
            AdjustmentCandidateData(
                category="NON_RECURRING",
                description="소송비",
                amount=Decimal("5000000.0000"),
                detection_method="keyword",
                confidence_score=Decimal("70.00"),
            ),
            AdjustmentCandidateData(
                category="NON_OPERATING",
                description="이자수익 제거",
                amount=Decimal("-2000000.0000"),
                detection_method="non_operating",
                confidence_score=Decimal("80.00"),
            ),
            AdjustmentCandidateData(
                category="NORMALIZATION",
                description="오너 급여 정상화",
                amount=Decimal("1000000.0000"),
                detection_method="keyword",
                confidence_score=Decimal("60.00"),
            ),
        ]
        bridge = build_qoe_bridge(Decimal("20000000.0000"), adjs)

        # Total = 5M - 2M + 1M = 4M
        assert bridge.total_adjustments == Decimal("4000000.0000")
        assert bridge.adjusted_ebitda == Decimal("24000000.0000")
        assert bridge.balance_check_error == Decimal("0.0000")

    def test_balance_check_always_zero(self):
        """밸런스 에러는 항상 0.0000."""
        for val in ["0.0000", "99999999.9999", "-12345678.1234"]:
            bridge = build_qoe_bridge(Decimal(val), [])
            assert bridge.balance_check_error == Decimal("0.0000")

    def test_large_amounts_precision(self):
        """대규모 금액에서도 정밀도 유지."""
        adj = AdjustmentCandidateData(
            category="NON_RECURRING",
            description="대규모 조정",
            amount=Decimal("123456789012.3456"),
            detection_method="manual",
            confidence_score=Decimal("100.00"),
        )
        bridge = build_qoe_bridge(Decimal("987654321098.7654"), [adj])
        expected = Decimal("1111111110111.1110")
        assert bridge.adjusted_ebitda == expected
        assert bridge.balance_check_error == Decimal("0.0000")
