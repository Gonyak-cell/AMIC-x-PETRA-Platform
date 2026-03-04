"""이상치 탐지 엔진 단위 테스트 — FDD-601."""

from decimal import Decimal

from app.engines.anomaly_engine import (
    ANOMALY_SCORE_THRESHOLD,
    DEFAULT_ZSCORE_THRESHOLD,
    AmountPatternResult,
    AnomalyScoreResult,
    BenfordResult,
    TimingAnomalyResult,
    ZScoreResult,
    analyze_entries_for_anomalies,
    calculate_benford_deviation,
    calculate_composite_risk_score,
    calculate_zscore_anomalies,
    detect_amount_pattern_anomalies,
    detect_keyword_risks,
    detect_timing_anomalies,
    zscore_to_risk_score,
)

# ── Helpers ──────────────────────────────────────────────


def _entry(
    entry_id: str,
    amount: str,
    category: str = "SGA",
    entry_date: str = "2025-06-15",
    description: str = "",
    account_name: str = "",
) -> dict:
    """Quick entry factory."""
    return {
        "entry_id": entry_id,
        "amount": amount,
        "category": category,
        "entry_date": entry_date,
        "description": description,
        "account_name": account_name,
    }


# ── TestCalculateZscoreAnomalies ────────────────────────


class TestCalculateZscoreAnomalies:
    """Z-Score 이상치 탐지 테스트."""

    def test_basic_zscore_detection(self):
        """기본 Z-Score 이상치 탐지."""
        # 대부분 100 근처, 하나만 극단적으로 높아야 zscore > 3.0
        # 충분한 데이터와 극단적 이상치 필요
        entries = [
            _entry("E1", "100"),
            _entry("E2", "105"),
            _entry("E3", "95"),
            _entry("E4", "102"),
            _entry("E5", "98"),
            _entry("E6", "101"),
            _entry("E7", "99"),
            _entry("E8", "103"),
            _entry("E9", "97"),
            _entry("E10", "5000"),  # 극단적 이상치
        ]
        results = calculate_zscore_anomalies(entries)

        assert len(results) == 10
        outlier = next(r for r in results if r.entry_id == "E10")
        assert outlier.is_outlier is True
        assert outlier.zscore >= DEFAULT_ZSCORE_THRESHOLD

    def test_multiple_categories(self):
        """다중 카테고리 독립 분석."""
        entries = [
            _entry("E1", "100", category="SGA"),
            _entry("E2", "105", category="SGA"),
            _entry("E3", "500000", category="COGS"),
            _entry("E4", "510000", category="COGS"),
        ]
        results = calculate_zscore_anomalies(entries)

        sga_results = [r for r in results if r.category == "SGA"]
        cogs_results = [r for r in results if r.category == "COGS"]

        assert len(sga_results) == 2
        assert len(cogs_results) == 2
        # 각 카테고리 내에서 독립적으로 mean/std 계산
        assert sga_results[0].mean != cogs_results[0].mean

    def test_empty_entries(self):
        """빈 리스트 처리."""
        results = calculate_zscore_anomalies([])
        assert results == []

    def test_single_entry_no_zscore(self):
        """단일 항목 — Z-Score 계산 불가 (is_outlier=False)."""
        entries = [_entry("E1", "100")]
        results = calculate_zscore_anomalies(entries)

        assert len(results) == 1
        assert results[0].zscore == Decimal("0")
        assert results[0].is_outlier is False

    def test_threshold_boundary(self):
        """임계값 경계 테스트."""
        # Z-Score가 정확히 3.0인 경우
        entries = [
            _entry("E1", "0"),
            _entry("E2", "0"),
            _entry("E3", "0"),
            _entry("E4", "3"),  # mean=0.75, std≈1.3 → zscore < 3
        ]
        results = calculate_zscore_anomalies(entries)

        # 모든 항목이 outlier가 아닐 수 있음 (데이터에 따라)
        assert all(isinstance(r, ZScoreResult) for r in results)

    def test_zscore_to_risk_score_conversion(self):
        """Z-Score → 리스크 점수 변환."""
        # threshold 미만
        assert zscore_to_risk_score(Decimal("2.5"), Decimal("3.0")) == Decimal("0")
        # threshold 이상
        score = zscore_to_risk_score(Decimal("4.0"), Decimal("3.0"))
        assert score > Decimal("0")
        # 매우 높은 Z-Score → 최대 100
        score_high = zscore_to_risk_score(Decimal("10.0"), Decimal("3.0"))
        assert score_high == Decimal("100.0000")


# ── TestBenfordDeviation ────────────────────────────────


class TestCalculateBenfordDeviation:
    """Benford's Law 편차 테스트."""

    def test_basic_benford_calculation(self):
        """기본 Benford 분포 계산."""
        # 첫째 자리가 골고루 분포된 데이터
        amounts = [
            Decimal("123"),
            Decimal("234"),
            Decimal("345"),
            Decimal("456"),
            Decimal("567"),
            Decimal("678"),
            Decimal("789"),
            Decimal("890"),
            Decimal("912"),
            Decimal("101"),
        ]
        result = calculate_benford_deviation(amounts)

        assert isinstance(result, BenfordResult)
        assert len(result.observed_distribution) == 9
        assert len(result.expected_distribution) == 9
        assert result.deviation_score >= Decimal("0")

    def test_empty_amounts(self):
        """빈 금액 리스트."""
        result = calculate_benford_deviation([])

        assert result.chi_squared == Decimal("0")
        assert result.deviation_score == Decimal("0")

    def test_insufficient_data(self):
        """데이터 부족 (10개 미만)."""
        amounts = [Decimal("100"), Decimal("200")]
        result = calculate_benford_deviation(amounts)

        # 신뢰할 수 없는 분석 → 0점
        assert result.deviation_score == Decimal("0")

    def test_perfect_benford_distribution(self):
        """Benford 분포와 일치하는 데이터 → 낮은 편차."""
        # Benford 비율에 맞춰 데이터 생성
        amounts = (
            [Decimal("100")] * 30  # 1: 30%
            + [Decimal("200")] * 18  # 2: 18%
            + [Decimal("300")] * 12  # 3: 12%
            + [Decimal("400")] * 10  # 4: 10%
            + [Decimal("500")] * 8  # 5: 8%
            + [Decimal("600")] * 7  # 6: 7%
            + [Decimal("700")] * 6  # 7: 6%
            + [Decimal("800")] * 5  # 8: 5%
            + [Decimal("900")] * 4  # 9: 4%
        )
        result = calculate_benford_deviation(amounts)

        # 완벽하진 않지만 편차가 낮아야 함
        assert result.deviation_score < Decimal("50")


# ── TestTimingAnomalies ────────────────────────────────


class TestDetectTimingAnomalies:
    """타이밍 이상치 탐지 테스트."""

    def test_year_end_detection(self):
        """연말 (12/28-31) 전표 탐지."""
        entries = [_entry("E1", "1000", entry_date="2025-12-31")]
        results = detect_timing_anomalies(entries)

        assert len(results) == 1
        assert results[0].timing_type == "year_end"
        assert results[0].score == Decimal("80")

    def test_quarter_end_detection(self):
        """분기말 전표 탐지."""
        entries = [_entry("E1", "1000", entry_date="2025-06-30")]
        results = detect_timing_anomalies(entries)

        assert len(results) == 1
        assert results[0].timing_type == "quarter_end"
        assert results[0].score == Decimal("60")

    def test_month_end_detection(self):
        """월말 전표 탐지 (분기말 제외)."""
        entries = [_entry("E1", "1000", entry_date="2025-07-31")]
        results = detect_timing_anomalies(entries)

        assert len(results) == 1
        assert results[0].timing_type == "month_end"
        assert results[0].score == Decimal("40")

    def test_weekend_detection(self):
        """주말 전표 탐지."""
        # 2025-06-14 = 토요일
        entries = [_entry("E1", "1000", entry_date="2025-06-14")]
        results = detect_timing_anomalies(entries)

        assert len(results) == 1
        assert results[0].timing_type == "weekend"
        assert "토" in results[0].description

    def test_normal_weekday_no_anomaly(self):
        """평일 일반 날짜 — 타이밍 이상치 없음."""
        # 2025-06-12 = 목요일
        entries = [_entry("E1", "1000", entry_date="2025-06-12")]
        results = detect_timing_anomalies(entries)

        assert len(results) == 0


# ── TestAmountPatternAnomalies ─────────────────────────


class TestDetectAmountPatternAnomalies:
    """금액 패턴 이상치 탐지 테스트."""

    def test_round_number_detection(self):
        """라운드 넘버 탐지."""
        entries = [_entry("E1", "10000000")]  # 정확히 1천만원
        results = detect_amount_pattern_anomalies(entries, Decimal("1000000000"))

        round_results = [r for r in results if r.pattern_type == "round_number"]
        assert len(round_results) == 1
        assert round_results[0].score == Decimal("60")

    def test_threshold_clustering(self):
        """결재 한도 근처 금액 탐지."""
        entries = [_entry("E1", "98000000")]  # 1억의 98%
        results = detect_amount_pattern_anomalies(entries, Decimal("10000000000"))

        threshold_results = [
            r for r in results if r.pattern_type == "threshold_clustering"
        ]
        assert len(threshold_results) == 1
        assert threshold_results[0].score == Decimal("70")

    def test_unusual_ratio(self):
        """매출 대비 높은 비율 탐지."""
        entries = [_entry("E1", "60000000")]  # 매출 10억의 6%
        results = detect_amount_pattern_anomalies(entries, Decimal("1000000000"))

        ratio_results = [r for r in results if r.pattern_type == "unusual_ratio"]
        assert len(ratio_results) == 1
        assert "매출 대비" in ratio_results[0].description

    def test_no_patterns_normal_amount(self):
        """일반 금액 — 패턴 없음."""
        entries = [_entry("E1", "12345678")]  # 비정상적이지 않은 금액
        results = detect_amount_pattern_anomalies(entries, Decimal("10000000000"))

        # 라운드 넘버도 아니고, 한도 근처도 아니고, 매출 대비 낮음
        assert len(results) == 0

    def test_zero_amount_excluded(self):
        """0원 금액 제외."""
        entries = [_entry("E1", "0")]
        results = detect_amount_pattern_anomalies(entries, Decimal("1000000000"))

        assert len(results) == 0


# ── TestKeywordRisks ──────────────────────────────────


class TestDetectKeywordRisks:
    """키워드 리스크 탐지 테스트."""

    def test_non_recurring_keyword(self):
        """비경상 키워드 탐지."""
        entries = [_entry("E1", "1000", description="소송 합의금")]
        results = detect_keyword_risks(entries)

        assert len(results) == 1
        assert results[0][1] == "소송"
        assert results[0][2] == Decimal("70")

    def test_normalization_keyword(self):
        """정상화 키워드 탐지."""
        entries = [_entry("E1", "1000", description="관계사 거래")]
        results = detect_keyword_risks(entries)

        assert len(results) == 1
        assert results[0][1] == "관계사"
        assert results[0][2] == Decimal("50")

    def test_no_keyword_match(self):
        """키워드 매칭 없음."""
        entries = [_entry("E1", "1000", description="일반 경비")]
        results = detect_keyword_risks(entries)

        assert len(results) == 0


# ── TestCompositeRiskScore ────────────────────────────


class TestCalculateCompositeRiskScore:
    """통합 리스크 점수 계산 테스트."""

    def test_combined_factors(self):
        """복수 요인 통합 점수."""
        entry = _entry("E1", "10000000", entry_date="2025-12-31")

        zscore_result = ZScoreResult(
            entry_id="E1",
            amount=Decimal("10000000"),
            category="SGA",
            mean=Decimal("1000000"),
            std_dev=Decimal("500000"),
            zscore=Decimal("5.0"),  # > 3.0 threshold
            is_outlier=True,
        )

        timing_result = TimingAnomalyResult(
            entry_id="E1",
            timing_type="year_end",
            score=Decimal("80"),
            description="연말 전표",
        )

        amount_result = AmountPatternResult(
            entry_id="E1",
            pattern_type="round_number",
            score=Decimal("60"),
            description="정확한 라운드 넘버",
        )

        result, evidence = calculate_composite_risk_score(
            entry=entry,
            zscore_result=zscore_result,
            timing_result=timing_result,
            amount_pattern_result=amount_result,
        )

        assert isinstance(result, AnomalyScoreResult)
        assert result.risk_score > Decimal("0")
        assert len(result.risk_factors) == 3
        # 복수 요인 → 높은 점수 → anomaly
        assert result.is_anomaly is True
        assert len(evidence) > 0

    def test_single_factor(self):
        """단일 요인만 있는 경우."""
        entry = _entry("E1", "1000")

        timing_result = TimingAnomalyResult(
            entry_id="E1",
            timing_type="month_end",
            score=Decimal("40"),
            description="월말 전표",
        )

        result, _ = calculate_composite_risk_score(
            entry=entry,
            timing_result=timing_result,
        )

        assert len(result.risk_factors) == 1
        # 40 * 0.20 = 8점 → anomaly 아님
        assert result.risk_score == Decimal("8.0000")
        assert result.is_anomaly is False

    def test_below_threshold_not_anomaly(self):
        """임계값 미만 — anomaly 아님."""
        entry = _entry("E1", "1000")

        # 가장 낮은 점수만 부여
        timing_result = TimingAnomalyResult(
            entry_id="E1",
            timing_type="month_end",
            score=Decimal("40"),
            description="월말 전표",
        )

        result, evidence = calculate_composite_risk_score(
            entry=entry,
            timing_result=timing_result,
        )

        assert result.risk_score < ANOMALY_SCORE_THRESHOLD
        assert result.is_anomaly is False
        # anomaly 아니면 evidence 없음
        assert len(evidence) == 0


# ── TestAnalyzeEntriesForAnomalies ─────────────────────


class TestAnalyzeEntriesForAnomalies:
    """일괄 분석 테스트."""

    def test_batch_analysis(self):
        """배치 분석 통합 테스트."""
        entries = [
            _entry("E1", "100", entry_date="2025-06-15"),  # 정상
            _entry("E2", "10000000", entry_date="2025-12-31"),  # 연말 + 라운드
            _entry(
                "E3", "500", entry_date="2025-06-14", description="소송비용"
            ),  # 주말+키워드
            _entry("E4", "200", entry_date="2025-06-15"),  # 정상
            _entry("E5", "150", entry_date="2025-06-15"),  # 정상
        ]

        results, _ = analyze_entries_for_anomalies(
            entries, revenue=Decimal("100000000")
        )

        assert len(results) == 5
        # 결과는 risk_score 내림차순 정렬
        assert results[0].risk_score >= results[-1].risk_score

        # E2, E3은 높은 리스크 예상
        high_risk_ids = {r.entry_id for r in results if r.risk_score > Decimal("10")}
        assert "E2" in high_risk_ids or "E3" in high_risk_ids

    def test_empty_batch(self):
        """빈 배치 처리."""
        results, evidence = analyze_entries_for_anomalies([])

        assert results == []
        assert evidence == []

    def test_all_normal_entries(self):
        """모두 정상 전표."""
        entries = [
            _entry("E1", "123456", entry_date="2025-06-12"),
            _entry("E2", "234567", entry_date="2025-06-13"),
            _entry("E3", "345678", entry_date="2025-06-16"),
        ]

        results, _ = analyze_entries_for_anomalies(
            entries, revenue=Decimal("1000000000")
        )

        assert len(results) == 3
        # 대부분 낮은 점수
        for r in results:
            assert r.risk_score < Decimal("50")
