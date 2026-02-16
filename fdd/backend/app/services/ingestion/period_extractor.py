"""TB 파일에서 기간 정보를 추출하는 유틸리티.

TB(시산표) 파일은 행별 날짜 없이 기간 스냅샷을 나타내므로,
파일명·시트명·헤더에서 기간을 추출하여 entry_date로 사용한다.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PeriodDetectionResult:
    """기간 탐지 결과."""

    period_date: date
    source: str  # "user_specified" | "filename" | "sheet_name" | "header_row" | "deal_period"
    confidence: Decimal
    raw_text: str


# ── 월 이름 매핑 ────────────────────────────────────────

_MONTH_NAMES: dict[str, int] = {
    # English
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}  # fmt: skip

# Korean month: "1월"~"12월"
for _m in range(1, 13):
    _MONTH_NAMES[f"{_m}월"] = _m

# ── 정규식 패턴 ─────────────────────────────────────────

# YYYY-MM, YYYY/MM, YYYY.MM, YYYYMM
_RE_YYYYMM = re.compile(r"(20\d{2})[-/.]?(0[1-9]|1[0-2])")

# Korean: 2025년 01월, 2025년 1월
_RE_KR_YEAR_MONTH = re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월")

# English month + year: "Jan 2025", "January 2025"
_RE_MONTH_YEAR = re.compile(
    r"(?:^|[\s_\-])"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s_\-.,]*"
    r"(20\d{2})"
    r"(?:[\s_\-.]|$)",
    re.IGNORECASE,
)

# Year + month name: "2025 Jan", "2025-January"
_RE_YEAR_MONTH = re.compile(
    r"(20\d{2})"
    r"[\s_\-.,]+"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:[\s_\-.]|$)",
    re.IGNORECASE,
)

# Quarter: Q1 2025, 1Q2025, 1Q 2025
_RE_QUARTER = re.compile(
    r"(?:Q([1-4])\s*(20\d{2})|([1-4])Q\s*(20\d{2}))", re.IGNORECASE
)

# "as of DATE" pattern in headers
_RE_AS_OF = re.compile(
    r"as\s+of\s+"
    r"(\w+\s+\d{1,2},?\s+\d{4}|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})",
    re.IGNORECASE,
)

# Full date in header: YYYY-MM-DD, YYYY/MM/DD
_RE_FULL_DATE = re.compile(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})")


def _last_day(year: int, month: int) -> date:
    """월의 마지막 날짜를 반환한다."""
    return date(year, month, calendar.monthrange(year, month)[1])


def _quarter_end(year: int, quarter: int) -> date:
    """분기 마지막 날짜를 반환한다."""
    month = quarter * 3
    return _last_day(year, month)


def _parse_yyyymm(text: str) -> date | None:
    """YYYYMM 패턴에서 월말 날짜를 추출한다."""
    m = _RE_YYYYMM.search(text)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 2000 <= year <= 2099 and 1 <= month <= 12:
            return _last_day(year, month)
    return None


def _parse_kr_year_month(text: str) -> date | None:
    """한국어 연월 패턴 (2025년 01월)에서 월말 날짜를 추출한다."""
    m = _RE_KR_YEAR_MONTH.search(text)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 2000 <= year <= 2099 and 1 <= month <= 12:
            return _last_day(year, month)
    return None


def _parse_month_year(text: str) -> date | None:
    """영문 월+연도 패턴 (Jan 2025)에서 월말 날짜를 추출한다."""
    for pattern in (_RE_MONTH_YEAR, _RE_YEAR_MONTH):
        m = pattern.search(text)
        if m:
            groups = m.groups()
            if pattern is _RE_MONTH_YEAR:
                month_str, year_str = groups[0], groups[1]
            else:
                year_str, month_str = groups[0], groups[1]
            month = _MONTH_NAMES.get(month_str.lower())
            year = int(year_str)
            if month and 2000 <= year <= 2099:
                return _last_day(year, month)
    return None


def _parse_quarter(text: str) -> date | None:
    """분기 패턴 (Q1 2025, 1Q2025)에서 분기말 날짜를 추출한다."""
    m = _RE_QUARTER.search(text)
    if m:
        if m.group(1):
            quarter, year = int(m.group(1)), int(m.group(2))
        else:
            quarter, year = int(m.group(3)), int(m.group(4))
        if 1 <= quarter <= 4 and 2000 <= year <= 2099:
            return _quarter_end(year, quarter)
    return None


def _parse_as_of(text: str) -> date | None:
    """'as of DATE' 패턴에서 날짜를 추출한다."""
    m = _RE_AS_OF.search(text)
    if not m:
        return None
    date_str = m.group(1)
    # Try YYYY-MM-DD
    dm = _RE_FULL_DATE.search(date_str)
    if dm:
        year, month, day = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        if 2000 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return date(year, month, day)
            except ValueError:
                return None
    # Try "Month DD, YYYY" e.g. "January 31, 2025"
    parts = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", date_str)
    if parts:
        month = _MONTH_NAMES.get(parts.group(1).lower())
        day, year = int(parts.group(2)), int(parts.group(3))
        if month and 2000 <= year <= 2099:
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None


# ── 소스별 탐지 함수 ────────────────────────────────────


def extract_period_from_filename(filename: str) -> PeriodDetectionResult | None:
    """파일명에서 기간을 추출한다."""
    text = filename.rsplit(".", 1)[0] if "." in filename else filename

    for parser in (
        _parse_kr_year_month,
        _parse_yyyymm,
        _parse_month_year,
        _parse_quarter,
    ):
        result = parser(text)
        if result:
            return PeriodDetectionResult(
                period_date=result,
                source="filename",
                confidence=Decimal("0.8000"),
                raw_text=filename,
            )
    return None


def extract_period_from_sheet_name(sheet_name: str) -> PeriodDetectionResult | None:
    """시트명에서 기간을 추출한다."""
    for parser in (
        _parse_kr_year_month,
        _parse_yyyymm,
        _parse_month_year,
        _parse_quarter,
    ):
        result = parser(sheet_name)
        if result:
            return PeriodDetectionResult(
                period_date=result,
                source="sheet_name",
                confidence=Decimal("0.7500"),
                raw_text=sheet_name,
            )
    return None


def extract_period_from_headers(headers: list[str]) -> PeriodDetectionResult | None:
    """헤더 행 텍스트에서 기간을 추출한다."""
    joined = " ".join(h for h in headers if h)

    # "as of" 패턴 우선
    result = _parse_as_of(joined)
    if result:
        return PeriodDetectionResult(
            period_date=result,
            source="header_row",
            confidence=Decimal("0.7000"),
            raw_text=joined[:200],
        )

    # 일반 날짜 패턴
    for parser in (
        _parse_kr_year_month,
        _parse_yyyymm,
        _parse_month_year,
        _parse_quarter,
    ):
        result = parser(joined)
        if result:
            return PeriodDetectionResult(
                period_date=result,
                source="header_row",
                confidence=Decimal("0.7000"),
                raw_text=joined[:200],
            )
    return None


def detect_tb_period(
    filename: str,
    sheet_name: str,
    headers: list[str],
    deal_period_end: date | None = None,
    user_period_date: date | None = None,
) -> PeriodDetectionResult | None:
    """TB 파일의 기간을 다중 전략으로 탐지한다.

    우선순위:
    1. user_period_date (사용자 지정, confidence=1.0)
    2. 파일명 패턴 (confidence=0.80)
    3. 시트명 패턴 (confidence=0.75)
    4. 헤더 텍스트 (confidence=0.70)
    5. deal.reference_date 폴백 (confidence=0.30)
    """
    if user_period_date is not None:
        return PeriodDetectionResult(
            period_date=user_period_date,
            source="user_specified",
            confidence=Decimal("1.0000"),
            raw_text=str(user_period_date),
        )

    result = extract_period_from_filename(filename)
    if result:
        return result

    result = extract_period_from_sheet_name(sheet_name)
    if result:
        return result

    result = extract_period_from_headers(headers)
    if result:
        return result

    if deal_period_end is not None:
        return PeriodDetectionResult(
            period_date=deal_period_end,
            source="deal_period",
            confidence=Decimal("0.3000"),
            raw_text=str(deal_period_end),
        )

    return None
