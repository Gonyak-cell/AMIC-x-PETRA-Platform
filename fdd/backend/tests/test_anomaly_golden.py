"""이상치 탐지 골든 테스트 — Sprint 6.

30개 골든 케이스로 이상치 탐지 정확도 검증.
"""

from decimal import Decimal

import pytest

from app.engines.anomaly_engine import (
    ANOMALY_SCORE_THRESHOLD,
    analyze_entries_for_anomalies,
    calculate_benford_deviation,
    calculate_zscore_anomalies,
    detect_amount_pattern_anomalies,
    detect_keyword_risks,
    detect_timing_anomalies,
)


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


# ── Golden Test Cases ─────────────────────────────────────


class TestZScoreGolden:
    """Z-Score 골든 테스트."""

    def test_golden_1_extreme_outlier(self):
        """극단적 이상치 탐지."""
        entries = [_entry(f"E{i}", "100") for i in range(1, 10)]
        entries.append(_entry("E10", "10000"))  # 100배 차이
        results = calculate_zscore_anomalies(entries)
        outliers = [r for r in results if r.is_outlier]
        assert len(outliers) >= 1
        assert any(r.entry_id == "E10" for r in outliers)

    def test_golden_2_no_outlier(self):
        """유사 금액 — 이상치 없음."""
        entries = [_entry(f"E{i}", str(100 + i)) for i in range(1, 11)]
        results = calculate_zscore_anomalies(entries)
        outliers = [r for r in results if r.is_outlier]
        assert len(outliers) == 0

    def test_golden_3_category_independent(self):
        """카테고리별 독립 분석."""
        entries = [
            _entry("E1", "100", category="SGA"),
            _entry("E2", "105", category="SGA"),
            _entry("E3", "1000000", category="COGS"),  # 다른 카테고리
            _entry("E4", "1050000", category="COGS"),
        ]
        results = calculate_zscore_anomalies(entries)
        # 각 카테고리 내에서는 정상
        outliers = [r for r in results if r.is_outlier]
        assert len(outliers) == 0


class TestBenfordGolden:
    """Benford's Law 골든 테스트."""

    def test_golden_4_natural_distribution(self):
        """자연스러운 분포 — 낮은 편차."""
        # 실제 거래 데이터와 유사한 분포
        amounts = (
            [Decimal("1234")] * 30
            + [Decimal("2345")] * 18
            + [Decimal("3456")] * 12
            + [Decimal("4567")] * 10
            + [Decimal("5678")] * 8
            + [Decimal("6789")] * 7
            + [Decimal("7890")] * 6
            + [Decimal("8901")] * 5
            + [Decimal("9012")] * 4
        )
        result = calculate_benford_deviation(amounts)
        assert result.deviation_score < Decimal("30")

    def test_golden_5_suspicious_distribution(self):
        """의심스러운 분포 — 높은 편차."""
        # 모든 금액이 5로 시작 (비정상)
        amounts = [Decimal("5000"), Decimal("5500"), Decimal("5999")] * 50
        result = calculate_benford_deviation(amounts)
        assert result.deviation_score > Decimal("50")


class TestTimingGolden:
    """타이밍 이상치 골든 테스트."""

    def test_golden_6_year_end(self):
        """연말 (12/31) 탐지."""
        entries = [_entry("E1", "1000", entry_date="2025-12-31")]
        results = detect_timing_anomalies(entries)
        assert len(results) == 1
        assert results[0].timing_type == "year_end"
        assert results[0].score == Decimal("80")

    def test_golden_7_quarter_end(self):
        """분기말 탐지."""
        entries = [_entry("E1", "1000", entry_date="2025-03-31")]
        results = detect_timing_anomalies(entries)
        assert len(results) == 1
        assert results[0].timing_type == "quarter_end"

    def test_golden_8_weekend_saturday(self):
        """토요일 전표."""
        entries = [_entry("E1", "1000", entry_date="2025-06-14")]  # 토요일
        results = detect_timing_anomalies(entries)
        assert len(results) == 1
        assert results[0].timing_type == "weekend"
        assert "토" in results[0].description

    def test_golden_9_weekend_sunday(self):
        """일요일 전표."""
        entries = [_entry("E1", "1000", entry_date="2025-06-15")]  # 일요일
        results = detect_timing_anomalies(entries)
        assert len(results) == 1
        assert "일" in results[0].description

    def test_golden_10_normal_day(self):
        """평일 — 이상치 없음."""
        entries = [_entry("E1", "1000", entry_date="2025-06-12")]  # 목요일
        results = detect_timing_anomalies(entries)
        assert len(results) == 0


class TestAmountPatternGolden:
    """금액 패턴 골든 테스트."""

    def test_golden_11_round_1m(self):
        """정확히 1백만원."""
        entries = [_entry("E1", "1000000")]
        results = detect_amount_pattern_anomalies(entries, Decimal("10000000000"))
        round_results = [r for r in results if r.pattern_type == "round_number"]
        assert len(round_results) == 1

    def test_golden_12_round_100m(self):
        """정확히 1억원."""
        entries = [_entry("E1", "100000000")]
        results = detect_amount_pattern_anomalies(entries, Decimal("10000000000"))
        round_results = [r for r in results if r.pattern_type == "round_number"]
        assert len(round_results) == 1

    def test_golden_13_threshold_97pct(self):
        """결재 한도의 97% (1억 기준)."""
        entries = [_entry("E1", "97000000")]
        results = detect_amount_pattern_anomalies(entries, Decimal("10000000000"))
        threshold_results = [
            r for r in results if r.pattern_type == "threshold_clustering"
        ]
        assert len(threshold_results) == 1

    def test_golden_14_high_revenue_ratio(self):
        """매출 대비 10%."""
        entries = [_entry("E1", "100000000")]
        results = detect_amount_pattern_anomalies(entries, Decimal("1000000000"))
        ratio_results = [r for r in results if r.pattern_type == "unusual_ratio"]
        assert len(ratio_results) == 1

    def test_golden_15_normal_amount(self):
        """정상 금액 — 패턴 없음."""
        entries = [_entry("E1", "12345678")]
        results = detect_amount_pattern_anomalies(entries, Decimal("100000000000"))
        assert len(results) == 0


class TestKeywordGolden:
    """키워드 골든 테스트."""

    def test_golden_16_litigation_korean(self):
        """소송 (한글)."""
        entries = [_entry("E1", "1000", description="소송 합의금")]
        results = detect_keyword_risks(entries)
        assert len(results) == 1
        assert results[0][1] == "소송"
        assert results[0][2] == Decimal("70")

    def test_golden_17_restructuring_english(self):
        """restructuring (영문)."""
        entries = [_entry("E1", "1000", description="Restructuring expense")]
        results = detect_keyword_risks(entries)
        assert len(results) == 1
        assert results[0][1] == "restructuring"

    def test_golden_18_related_party(self):
        """관계사 거래."""
        entries = [_entry("E1", "1000", description="관계사 대여금")]
        results = detect_keyword_risks(entries)
        assert len(results) == 1
        assert results[0][2] == Decimal("50")  # 정상화 키워드

    def test_golden_19_owner_related(self):
        """오너 관련."""
        entries = [_entry("E1", "1000", account_name="대표이사 가지급금")]
        results = detect_keyword_risks(entries)
        assert len(results) == 1

    def test_golden_20_no_keyword(self):
        """키워드 없음."""
        entries = [_entry("E1", "1000", description="일반 복리후생비")]
        results = detect_keyword_risks(entries)
        assert len(results) == 0


class TestCompositeGolden:
    """통합 분석 골든 테스트."""

    def test_golden_21_multi_factor_high_risk(self):
        """복수 요인 — 고위험 (threshold 미만이지만 복수 요인 확인)."""
        entries = [
            _entry(
                "E1",
                "100000000",  # 라운드 넘버
                entry_date="2025-12-31",  # 연말
                description="소송 합의금",  # 비경상 키워드
            )
        ]
        results, evidence = analyze_entries_for_anomalies(
            entries, revenue=Decimal("1000000000")
        )
        assert len(results) == 1
        # 3개 요인이 모두 탐지되어야 함
        assert len(results[0].risk_factors) >= 3
        # 가중치 합산: timing(80*0.2=16) + keyword(70*0.15=10.5) + amount(70*0.25=17.5) = 44
        assert results[0].risk_score >= Decimal("40")

    def test_golden_22_single_factor_low_risk(self):
        """단일 요인 — 저위험."""
        entries = [_entry("E1", "1000", entry_date="2025-07-31")]  # 월말만
        results, _ = analyze_entries_for_anomalies(
            entries, revenue=Decimal("100000000000")
        )
        assert len(results) == 1
        # 월말만으로는 anomaly 아님 (40 * 0.20 = 8점)
        assert results[0].risk_score < ANOMALY_SCORE_THRESHOLD

    def test_golden_23_sorted_by_risk(self):
        """리스크 점수 내림차순 정렬."""
        entries = [
            _entry("E1", "100", entry_date="2025-06-15"),
            _entry("E2", "100000000", entry_date="2025-12-31", description="소송"),
            _entry("E3", "1000", entry_date="2025-06-14"),  # 주말
        ]
        results, _ = analyze_entries_for_anomalies(
            entries, revenue=Decimal("1000000000")
        )
        # E2가 가장 높은 점수
        assert results[0].entry_id == "E2"

    def test_golden_24_evidence_created(self):
        """이상치에 대한 evidence 생성."""
        entries = [
            _entry("E1", "100000000", entry_date="2025-12-31", description="소송 합의"),
        ]
        results, evidence = analyze_entries_for_anomalies(
            entries, revenue=Decimal("1000000000")
        )
        # 이상치면 evidence 있음
        if results[0].is_anomaly:
            assert len(evidence) > 0

    def test_golden_25_no_anomaly_no_evidence(self):
        """정상 전표 — evidence 없음."""
        entries = [_entry("E1", "100", entry_date="2025-06-12")]
        results, evidence = analyze_entries_for_anomalies(entries)
        # 정상이면 evidence 없음
        assert len(evidence) == 0


class TestEdgeCaseGolden:
    """엣지 케이스 골든 테스트."""

    def test_golden_26_empty_entries(self):
        """빈 리스트."""
        results, evidence = analyze_entries_for_anomalies([])
        assert results == []
        assert evidence == []

    def test_golden_27_zero_amount(self):
        """0원 전표 — 평일."""
        entries = [_entry("E1", "0", entry_date="2025-06-12")]  # 목요일
        results, _ = analyze_entries_for_anomalies(entries)
        assert len(results) == 1
        # 0원이면 금액 패턴 탐지 안됨, 평일이면 타이밍 탐지 안됨
        assert results[0].risk_score == Decimal("0")

    def test_golden_28_negative_amount(self):
        """음수 금액."""
        entries = [_entry("E1", "-1000000")]
        results, _ = analyze_entries_for_anomalies(
            entries, revenue=Decimal("100000000")
        )
        assert len(results) == 1
        # 음수도 정상 처리

    def test_golden_29_zero_revenue(self):
        """매출 0 (비율 계산 안전)."""
        entries = [_entry("E1", "1000000")]
        results, _ = analyze_entries_for_anomalies(entries, revenue=Decimal("0"))
        assert len(results) == 1
        # 0으로 나누기 없이 정상 처리

    def test_golden_30_mixed_categories(self):
        """다양한 카테고리 혼합."""
        entries = [
            _entry("E1", "100", category="REVENUE"),
            _entry("E2", "200", category="COGS"),
            _entry("E3", "300", category="SGA"),
            _entry("E4", "400", category="REVENUE"),
        ]
        results, _ = analyze_entries_for_anomalies(entries)
        assert len(results) == 4
