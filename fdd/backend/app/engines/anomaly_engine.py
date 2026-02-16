"""이상치 탐지 엔진 — FDD-601.

순수 함수만 포함. DB 접근 절대 금지.
모든 금액: Decimal. float 절대 금지.

리스크 스코어 가중치:
- Z-Score: 30% (카테고리별 표준편차 이탈)
- Amount Patterns: 25% (라운드 넘버, 이상 금액)
- Timing: 20% (월말 집중, 주말 전표)
- Keywords: 15% (비경상 키워드)
- Benford's Law: 10% (첫째 자리 분포 편차)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

ENGINE_VERSION = "0.1.0"

# Quantize constant — 4 decimal places
Q4 = Decimal("0.0001")

# Risk score weights
WEIGHT_ZSCORE = Decimal("0.30")
WEIGHT_AMOUNT_PATTERN = Decimal("0.25")
WEIGHT_TIMING = Decimal("0.20")
WEIGHT_KEYWORD = Decimal("0.15")
WEIGHT_BENFORD = Decimal("0.10")

# Threshold constants
DEFAULT_ZSCORE_THRESHOLD = Decimal("3.0")
ANOMALY_SCORE_THRESHOLD = Decimal("50.0")


# ── Data Types ───────────────────────────────────────────


@dataclass(frozen=True)
class EvidenceLinkData:
    """Evidence link data (엔진 → 서비스 출력용, DB 저장 전)."""

    target_type: str
    source_type: str  # "TB" or "GL"
    source_id: str
    source_detail: dict[str, Any] | None = None
    transaction_id: str | None = None


@dataclass(frozen=True)
class RiskFactorData:
    """개별 리스크 요인 데이터."""

    factor_type: str  # zscore, benford, timing, amount_pattern, keyword
    score_contribution: Decimal  # 가중치 적용 후 점수 (0-100 스케일 내 기여분)
    raw_score: Decimal  # 가중치 적용 전 원시 점수 (0-100)
    description: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class AnomalyScoreResult:
    """이상치 점수 결과."""

    entry_id: str
    risk_score: Decimal  # 0-100
    risk_factors: tuple[RiskFactorData, ...]  # frozen=True용 tuple
    is_anomaly: bool
    entry_data: dict[str, Any] | None = None


@dataclass
class ZScoreResult:
    """Z-Score 분석 결과."""

    entry_id: str
    amount: Decimal
    category: str
    mean: Decimal
    std_dev: Decimal
    zscore: Decimal
    is_outlier: bool


@dataclass
class BenfordResult:
    """Benford's Law 분석 결과."""

    observed_distribution: dict[str, Decimal]
    expected_distribution: dict[str, Decimal]
    chi_squared: Decimal
    deviation_score: Decimal  # 0-100 스케일


@dataclass
class TimingAnomalyResult:
    """타이밍 이상치 결과."""

    entry_id: str
    timing_type: str  # "month_end", "weekend", "quarter_end", "year_end"
    score: Decimal
    description: str


@dataclass
class AmountPatternResult:
    """금액 패턴 이상치 결과."""

    entry_id: str
    pattern_type: str  # "round_number", "threshold_clustering", "unusual_ratio"
    score: Decimal
    description: str


# ── Keywords (qoe_engine 재사용) ─────────────────────────

# 비경상 키워드
_NON_RECURRING_KEYWORDS: list[str] = [
    "소송",
    "구조조정",
    "일회성",
    "정리",
    "폐기",
    "처분손",
    "화재",
    "재해",
    "벌금",
    "과태료",
    "합의금",
    "위약금",
    "restructuring",
    "litigation",
    "one-time",
    "one-off",
    "write-off",
    "impairment",
    "severance",
    "settlement",
]

# 정상화 키워드 (오너/관계사)
_NORMALIZATION_KEYWORDS: list[str] = [
    "관계사",
    "특수관계",
    "임원",
    "대표이사",
    "오너",
    "related party",
    "owner",
    "director",
    "executive compensation",
]

# 모든 리스크 키워드 (비경상 + 정상화)
_ALL_RISK_KEYWORDS: list[str] = _NON_RECURRING_KEYWORDS + _NORMALIZATION_KEYWORDS

# Benford's Law 기대 분포 (첫째 자리 1-9)
_BENFORD_EXPECTED: dict[str, Decimal] = {
    "1": Decimal("0.301"),
    "2": Decimal("0.176"),
    "3": Decimal("0.125"),
    "4": Decimal("0.097"),
    "5": Decimal("0.079"),
    "6": Decimal("0.067"),
    "7": Decimal("0.058"),
    "8": Decimal("0.051"),
    "9": Decimal("0.046"),
}


def _q(amount: Decimal) -> Decimal:
    """NUMERIC(18,4) 정밀도로 반올림."""
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


def _safe_decimal(value: Any) -> Decimal:
    """안전하게 Decimal로 변환."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


# ── Z-Score 이상치 탐지 (30%) ───────────────────────────


def calculate_zscore_anomalies(
    entries: list[dict[str, Any]],
    threshold: Decimal = DEFAULT_ZSCORE_THRESHOLD,
) -> list[ZScoreResult]:
    """카테고리별 Z-Score 이상치를 탐지한다.

    Args:
        entries: GL/전표 데이터 리스트. 각 dict는 entry_id, amount, category 포함.
        threshold: Z-Score 임계값 (기본 3.0)

    Returns:
        Z-Score 결과 리스트 (이상치 여부 포함)
    """
    if not entries:
        return []

    # 카테고리별 그룹화
    by_category: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        cat = str(entry.get("category", "UNCATEGORIZED"))
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(entry)

    results: list[ZScoreResult] = []

    for category, cat_entries in by_category.items():
        amounts = [abs(_safe_decimal(e.get("amount", 0))) for e in cat_entries]

        if len(amounts) < 2:
            # 데이터 부족 — Z-Score 계산 불가
            for e in cat_entries:
                results.append(
                    ZScoreResult(
                        entry_id=str(e.get("entry_id", "")),
                        amount=_safe_decimal(e.get("amount", 0)),
                        category=category,
                        mean=Decimal("0"),
                        std_dev=Decimal("0"),
                        zscore=Decimal("0"),
                        is_outlier=False,
                    )
                )
            continue

        # 평균 및 표준편차 계산
        n = Decimal(str(len(amounts)))
        mean = _q(sum(amounts) / n)

        variance = sum((a - mean) ** 2 for a in amounts) / n
        # Decimal sqrt 근사 (math.sqrt 사용 후 변환)
        std_dev = _q(Decimal(str(math.sqrt(float(variance)))))

        for e, amt in zip(cat_entries, amounts, strict=True):
            if std_dev == Decimal("0"):
                zscore = Decimal("0")
            else:
                zscore = _q(abs(amt - mean) / std_dev)

            is_outlier = zscore >= threshold

            results.append(
                ZScoreResult(
                    entry_id=str(e.get("entry_id", "")),
                    amount=_safe_decimal(e.get("amount", 0)),
                    category=category,
                    mean=mean,
                    std_dev=std_dev,
                    zscore=zscore,
                    is_outlier=is_outlier,
                )
            )

    return results


def zscore_to_risk_score(zscore: Decimal, threshold: Decimal) -> Decimal:
    """Z-Score를 0-100 리스크 점수로 변환.

    threshold 미만: 0점
    threshold 이상: (zscore - threshold + 1) * 25, 최대 100
    """
    if zscore < threshold:
        return Decimal("0")
    excess = zscore - threshold + Decimal("1")
    score = _q(excess * Decimal("25"))
    return min(score, Decimal("100"))


# ── Benford's Law (10%) ──────────────────────────────────


def calculate_benford_deviation(amounts: list[Decimal]) -> BenfordResult:
    """Benford's Law 편차를 계산한다.

    첫째 자리 분포가 Benford 기대 분포에서 얼마나 벗어났는지 측정.

    Args:
        amounts: 금액 리스트 (Decimal)

    Returns:
        BenfordResult with observed/expected distributions and deviation score
    """
    if not amounts:
        return BenfordResult(
            observed_distribution={str(i): Decimal("0") for i in range(1, 10)},
            expected_distribution=_BENFORD_EXPECTED,
            chi_squared=Decimal("0"),
            deviation_score=Decimal("0"),
        )

    # 첫째 자리 추출 (0과 음수 제외)
    first_digits: list[str] = []
    for amt in amounts:
        abs_amt = abs(amt)
        if abs_amt == Decimal("0"):
            continue
        # 첫째 자리 추출
        s = str(abs_amt).lstrip("-").replace(".", "").lstrip("0")
        if s:
            first_digits.append(s[0])

    if len(first_digits) < 10:
        # 데이터 부족 — 신뢰할 수 있는 분석 불가
        return BenfordResult(
            observed_distribution={str(i): Decimal("0") for i in range(1, 10)},
            expected_distribution=_BENFORD_EXPECTED,
            chi_squared=Decimal("0"),
            deviation_score=Decimal("0"),
        )

    # 관측 분포 계산
    total = Decimal(str(len(first_digits)))
    observed: dict[str, Decimal] = {}
    for digit in range(1, 10):
        count = Decimal(str(first_digits.count(str(digit))))
        observed[str(digit)] = _q(count / total)

    # Chi-squared 계산
    chi_squared = Decimal("0")
    for digit in range(1, 10):
        d = str(digit)
        obs = observed.get(d, Decimal("0"))
        exp = _BENFORD_EXPECTED[d]
        if exp > Decimal("0"):
            chi_squared += _q(((obs - exp) ** 2) / exp)

    # Chi-squared를 0-100 스코어로 변환
    # 경험적 임계값: chi_squared > 0.5 → 의심스러움
    deviation_score = min(_q(chi_squared * Decimal("100")), Decimal("100"))

    return BenfordResult(
        observed_distribution=observed,
        expected_distribution=_BENFORD_EXPECTED,
        chi_squared=_q(chi_squared),
        deviation_score=deviation_score,
    )


# ── Timing 이상치 (20%) ────────────────────────────────


def detect_timing_anomalies(
    entries: list[dict[str, Any]],
) -> list[TimingAnomalyResult]:
    """타이밍 기반 이상치를 탐지한다.

    감지 패턴:
    - month_end: 월말 (28-31일) 전표 집중
    - weekend: 주말 전표
    - quarter_end: 분기말 (3, 6, 9, 12월 말)
    - year_end: 연말 (12/28-31)

    Args:
        entries: GL/전표 데이터 (entry_date 필드 필요)

    Returns:
        타이밍 이상치 리스트
    """
    results: list[TimingAnomalyResult] = []

    for entry in entries:
        entry_id = str(entry.get("entry_id", ""))
        entry_date = str(entry.get("entry_date", ""))

        if not entry_date or len(entry_date) < 10:
            continue

        try:
            # YYYY-MM-DD 형식 파싱
            year = int(entry_date[:4])
            month = int(entry_date[5:7])
            day = int(entry_date[8:10])
        except (ValueError, IndexError):
            continue

        # 연말 (12/28-31) — 가장 높은 리스크
        if month == 12 and day >= 28:
            results.append(
                TimingAnomalyResult(
                    entry_id=entry_id,
                    timing_type="year_end",
                    score=Decimal("80"),
                    description=f"연말 전표 ({entry_date})",
                )
            )
            continue  # 가장 구체적인 패턴이므로 하위 패턴 스킵

        # 분기말 (3, 6, 9, 12월 말) — 중간 리스크
        if month in (3, 6, 9, 12) and day >= 28:
            results.append(
                TimingAnomalyResult(
                    entry_id=entry_id,
                    timing_type="quarter_end",
                    score=Decimal("60"),
                    description=f"분기말 전표 ({entry_date})",
                )
            )
            continue

        # 월말 (28-31일)
        if day >= 28:
            results.append(
                TimingAnomalyResult(
                    entry_id=entry_id,
                    timing_type="month_end",
                    score=Decimal("40"),
                    description=f"월말 전표 ({entry_date})",
                )
            )
            continue

        # 주말 (ISO weekday: 6=토, 7=일)
        # 간단한 요일 계산 (Zeller's congruence 변형)
        try:
            import datetime

            dt = datetime.date(year, month, day)
            weekday = dt.isoweekday()  # 1=월 ~ 7=일
            if weekday >= 6:
                results.append(
                    TimingAnomalyResult(
                        entry_id=entry_id,
                        timing_type="weekend",
                        score=Decimal("50"),
                        description=f"주말 전표 ({entry_date}, {'토' if weekday == 6 else '일'})",
                    )
                )
        except ValueError:
            pass

    return results


# ── Amount Pattern 이상치 (25%) ──────────────────────────


def detect_amount_pattern_anomalies(
    entries: list[dict[str, Any]],
    revenue: Decimal,
) -> list[AmountPatternResult]:
    """금액 패턴 기반 이상치를 탐지한다.

    감지 패턴:
    - round_number: 정확한 라운드 넘버 (1M, 10M, 100M 등)
    - threshold_clustering: 결재 한도 근처 금액 클러스터링
    - unusual_ratio: 매출 대비 비정상적 비율

    Args:
        entries: GL/전표 데이터
        revenue: 총 매출액 (비율 계산 기준)

    Returns:
        금액 패턴 이상치 리스트
    """
    results: list[AmountPatternResult] = []
    abs_revenue = abs(revenue) if revenue != Decimal("0") else Decimal("1")

    # 라운드 넘버 패턴 (정확한 백만원/천만원/억원 단위)
    round_numbers = [
        Decimal("1000000"),  # 1M
        Decimal("5000000"),  # 5M
        Decimal("10000000"),  # 10M
        Decimal("50000000"),  # 50M
        Decimal("100000000"),  # 100M
        Decimal("500000000"),  # 500M
        Decimal("1000000000"),  # 1B
    ]

    for entry in entries:
        entry_id = str(entry.get("entry_id", ""))
        amount = abs(_safe_decimal(entry.get("amount", 0)))

        if amount == Decimal("0"):
            continue

        # 라운드 넘버 체크
        for rn in round_numbers:
            if amount == rn:
                results.append(
                    AmountPatternResult(
                        entry_id=entry_id,
                        pattern_type="round_number",
                        score=Decimal("60"),
                        description=f"정확한 라운드 넘버: {amount:,.0f}",
                    )
                )
                break

        # 결재 한도 근처 클러스터링 (5%, 10%, 50% 임계값)
        # 일반적 결재 한도: 1억, 5억, 10억
        approval_thresholds = [
            Decimal("100000000"),  # 1억
            Decimal("500000000"),  # 5억
            Decimal("1000000000"),  # 10억
        ]
        for threshold in approval_thresholds:
            # 한도의 95-99% 범위
            lower = _q(threshold * Decimal("0.95"))
            upper = threshold
            if lower <= amount < upper:
                results.append(
                    AmountPatternResult(
                        entry_id=entry_id,
                        pattern_type="threshold_clustering",
                        score=Decimal("70"),
                        description=f"결재 한도 근처: {amount:,.0f} (한도 {threshold:,.0f})",
                    )
                )
                break

        # 매출 대비 비율 체크 (단일 전표가 매출의 5% 이상)
        ratio = _q(amount / abs_revenue)
        if ratio >= Decimal("0.05"):
            pct = _q(ratio * Decimal("100"))
            results.append(
                AmountPatternResult(
                    entry_id=entry_id,
                    pattern_type="unusual_ratio",
                    score=Decimal("50") + min(_q(pct * Decimal("2")), Decimal("50")),
                    description=f"매출 대비 {pct:.2f}%",
                )
            )

    return results


# ── Keyword 탐지 (15%) ──────────────────────────────────


def detect_keyword_risks(
    entries: list[dict[str, Any]],
) -> list[tuple[str, str, Decimal]]:
    """키워드 기반 리스크를 탐지한다.

    Args:
        entries: GL/전표 데이터 (description, account_name 필드)

    Returns:
        (entry_id, matched_keyword, score) 튜플 리스트
    """
    results: list[tuple[str, str, Decimal]] = []

    for entry in entries:
        entry_id = str(entry.get("entry_id", ""))
        description = str(entry.get("description", "")).lower()
        account_name = str(entry.get("account_name", "")).lower()
        combined = f"{description} {account_name}"

        for kw in _ALL_RISK_KEYWORDS:
            if kw.lower() in combined:
                # 비경상 키워드 = 높은 점수, 정상화 키워드 = 중간 점수
                score = (
                    Decimal("70")
                    if kw in _NON_RECURRING_KEYWORDS
                    else Decimal("50")
                )
                results.append((entry_id, kw, score))
                break  # 첫 번째 매칭만

    return results


# ── Composite Risk Score (통합) ───────────────────────────


def calculate_composite_risk_score(
    entry: dict[str, Any],
    zscore_result: ZScoreResult | None = None,
    benford_deviation: Decimal = Decimal("0"),
    timing_result: TimingAnomalyResult | None = None,
    amount_pattern_result: AmountPatternResult | None = None,
    keyword_result: tuple[str, str, Decimal] | None = None,
) -> tuple[AnomalyScoreResult, list[EvidenceLinkData]]:
    """개별 전표의 통합 리스크 점수를 계산한다.

    각 요인별 가중치 적용:
    - Z-Score: 30%
    - Amount Patterns: 25%
    - Timing: 20%
    - Keywords: 15%
    - Benford's Law: 10%

    Args:
        entry: 원본 전표 데이터
        zscore_result: Z-Score 분석 결과
        benford_deviation: Benford 편차 점수 (0-100)
        timing_result: 타이밍 이상치 결과
        amount_pattern_result: 금액 패턴 결과
        keyword_result: (entry_id, keyword, score) 또는 None

    Returns:
        (AnomalyScoreResult, evidence links)
    """
    entry_id = str(entry.get("entry_id", ""))
    factors: list[RiskFactorData] = []
    total_score = Decimal("0")

    # Z-Score (30%)
    if zscore_result and zscore_result.is_outlier:
        raw = zscore_to_risk_score(zscore_result.zscore, DEFAULT_ZSCORE_THRESHOLD)
        contrib = _q(raw * WEIGHT_ZSCORE)
        factors.append(
            RiskFactorData(
                factor_type="zscore",
                score_contribution=contrib,
                raw_score=raw,
                description=f"Z-Score {zscore_result.zscore:.2f} (카테고리: {zscore_result.category})",
                details={
                    "zscore": str(zscore_result.zscore),
                    "mean": str(zscore_result.mean),
                    "std_dev": str(zscore_result.std_dev),
                },
            )
        )
        total_score += contrib

    # Amount Pattern (25%)
    if amount_pattern_result:
        raw = amount_pattern_result.score
        contrib = _q(raw * WEIGHT_AMOUNT_PATTERN)
        factors.append(
            RiskFactorData(
                factor_type="amount_pattern",
                score_contribution=contrib,
                raw_score=raw,
                description=amount_pattern_result.description,
                details={"pattern_type": amount_pattern_result.pattern_type},
            )
        )
        total_score += contrib

    # Timing (20%)
    if timing_result:
        raw = timing_result.score
        contrib = _q(raw * WEIGHT_TIMING)
        factors.append(
            RiskFactorData(
                factor_type="timing",
                score_contribution=contrib,
                raw_score=raw,
                description=timing_result.description,
                details={"timing_type": timing_result.timing_type},
            )
        )
        total_score += contrib

    # Keyword (15%)
    if keyword_result:
        _, kw, raw = keyword_result
        contrib = _q(raw * WEIGHT_KEYWORD)
        factors.append(
            RiskFactorData(
                factor_type="keyword",
                score_contribution=contrib,
                raw_score=raw,
                description=f"리스크 키워드 감지: {kw}",
                details={"keyword": kw},
            )
        )
        total_score += contrib

    # Benford (10%)
    if benford_deviation > Decimal("0"):
        raw = benford_deviation
        contrib = _q(raw * WEIGHT_BENFORD)
        factors.append(
            RiskFactorData(
                factor_type="benford",
                score_contribution=contrib,
                raw_score=raw,
                description=f"Benford 편차 점수: {benford_deviation:.2f}",
                details={"deviation_score": str(benford_deviation)},
            )
        )
        total_score += contrib

    total_score = min(_q(total_score), Decimal("100"))
    is_anomaly = total_score >= ANOMALY_SCORE_THRESHOLD

    result = AnomalyScoreResult(
        entry_id=entry_id,
        risk_score=total_score,
        risk_factors=tuple(factors),
        is_anomaly=is_anomaly,
        entry_data=entry,
    )

    # Evidence links
    evidence: list[EvidenceLinkData] = []
    if is_anomaly:
        evidence.append(
            EvidenceLinkData(
                target_type="anomaly_detection",
                source_type="GL",
                source_id=entry_id,
                source_detail={
                    "risk_score": str(total_score),
                    "factor_count": len(factors),
                    "factors": [f.factor_type for f in factors],
                },
                transaction_id=entry_id,
            )
        )

    return result, evidence


# ── Batch Processing ─────────────────────────────────────


def analyze_entries_for_anomalies(
    entries: list[dict[str, Any]],
    revenue: Decimal = Decimal("0"),
) -> tuple[list[AnomalyScoreResult], list[EvidenceLinkData]]:
    """전표 리스트의 이상치를 일괄 분석한다.

    Args:
        entries: GL/전표 데이터 리스트
        revenue: 총 매출액 (금액 패턴 분석용)

    Returns:
        (이상치 점수 결과 리스트, evidence links)
    """
    if not entries:
        return [], []

    # 사전 분석 수행
    zscore_results = calculate_zscore_anomalies(entries)
    zscore_map: dict[str, ZScoreResult] = {r.entry_id: r for r in zscore_results}

    amounts = [abs(_safe_decimal(e.get("amount", 0))) for e in entries]
    benford_result = calculate_benford_deviation(amounts)

    timing_results = detect_timing_anomalies(entries)
    timing_map: dict[str, TimingAnomalyResult] = {r.entry_id: r for r in timing_results}

    amount_pattern_results = detect_amount_pattern_anomalies(entries, revenue)
    amount_map: dict[str, AmountPatternResult] = {}
    for r in amount_pattern_results:
        if r.entry_id not in amount_map or r.score > amount_map[r.entry_id].score:
            amount_map[r.entry_id] = r  # 가장 높은 점수만 유지

    keyword_results = detect_keyword_risks(entries)
    keyword_map: dict[str, tuple[str, str, Decimal]] = {
        r[0]: r for r in keyword_results
    }

    # 각 전표별 통합 점수 계산
    all_results: list[AnomalyScoreResult] = []
    all_evidence: list[EvidenceLinkData] = []

    for entry in entries:
        entry_id = str(entry.get("entry_id", ""))
        result, evidence = calculate_composite_risk_score(
            entry=entry,
            zscore_result=zscore_map.get(entry_id),
            benford_deviation=benford_result.deviation_score,
            timing_result=timing_map.get(entry_id),
            amount_pattern_result=amount_map.get(entry_id),
            keyword_result=keyword_map.get(entry_id),
        )
        all_results.append(result)
        all_evidence.extend(evidence)

    # 리스크 점수 내림차순 정렬
    all_results.sort(key=lambda r: r.risk_score, reverse=True)

    return all_results, all_evidence
