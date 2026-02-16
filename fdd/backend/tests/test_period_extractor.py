"""Period extractor 단위 테스트.

TB 파일의 기간 탐지 유틸리티(period_extractor)를 검증한다.
"""

from datetime import date
from decimal import Decimal

from app.services.ingestion.period_extractor import (
    detect_tb_period,
    extract_period_from_filename,
    extract_period_from_headers,
    extract_period_from_sheet_name,
)

# ── 파일명 기반 탐지 ────────────────────────────────────


class TestExtractPeriodFromFilename:
    def test_yyyymm_dash(self):
        r = extract_period_from_filename("2025-01 TB.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 1, 31)
        assert r.source == "filename"
        assert r.confidence == Decimal("0.8000")

    def test_yyyymm_no_separator(self):
        r = extract_period_from_filename("TB_202503.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 3, 31)

    def test_yyyymm_slash(self):
        r = extract_period_from_filename("TB_2025/06.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 6, 30)

    def test_yyyymm_dot(self):
        r = extract_period_from_filename("시산표_2025.12.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 12, 31)

    def test_korean_year_month(self):
        r = extract_period_from_filename("시산표_2025년01월.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 1, 31)

    def test_korean_year_month_no_leading_zero(self):
        r = extract_period_from_filename("시산표_2025년3월.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 3, 31)

    def test_english_month_year(self):
        r = extract_period_from_filename("TB Jan 2025.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 1, 31)

    def test_english_full_month(self):
        r = extract_period_from_filename("Trial Balance February 2025.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 2, 28)

    def test_quarter_q_first(self):
        r = extract_period_from_filename("TB Q1 2025.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 3, 31)

    def test_quarter_q_after(self):
        r = extract_period_from_filename("TB_3Q2025.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 9, 30)

    def test_no_date_info(self):
        r = extract_period_from_filename("Trial_Balance.xlsx")
        assert r is None

    def test_leap_year_february(self):
        r = extract_period_from_filename("TB_202402.xlsx")
        assert r is not None
        assert r.period_date == date(2024, 2, 29)

    def test_no_extension(self):
        r = extract_period_from_filename("TB_202501")
        assert r is not None
        assert r.period_date == date(2025, 1, 31)

    def test_year_month_name(self):
        r = extract_period_from_filename("2025_March_TB.xlsx")
        assert r is not None
        assert r.period_date == date(2025, 3, 31)


# ── 시트명 기반 탐지 ────────────────────────────────────


class TestExtractPeriodFromSheetName:
    def test_yyyymm(self):
        r = extract_period_from_sheet_name("202501")
        assert r is not None
        assert r.period_date == date(2025, 1, 31)
        assert r.source == "sheet_name"
        assert r.confidence == Decimal("0.7500")

    def test_korean_month(self):
        r = extract_period_from_sheet_name("2025년 6월")
        assert r is not None
        assert r.period_date == date(2025, 6, 30)

    def test_english_month(self):
        r = extract_period_from_sheet_name("Jan 2025")
        assert r is not None
        assert r.period_date == date(2025, 1, 31)

    def test_no_date(self):
        r = extract_period_from_sheet_name("Sheet1")
        assert r is None

    def test_quarter(self):
        r = extract_period_from_sheet_name("Q4 2025")
        assert r is not None
        assert r.period_date == date(2025, 12, 31)


# ── 헤더 기반 탐지 ──────────────────────────────────────


class TestExtractPeriodFromHeaders:
    def test_as_of_full_date(self):
        headers = ["Account", "Name", "Trial Balance as of January 31, 2025", "Balance"]
        r = extract_period_from_headers(headers)
        assert r is not None
        assert r.period_date == date(2025, 1, 31)
        assert r.source == "header_row"
        assert r.confidence == Decimal("0.7000")

    def test_as_of_iso_date(self):
        headers = ["Account", "as of 2025-06-30", "Balance"]
        r = extract_period_from_headers(headers)
        assert r is not None
        assert r.period_date == date(2025, 6, 30)

    def test_yyyymm_in_header(self):
        headers = ["계정코드", "계정명", "202501 잔액"]
        r = extract_period_from_headers(headers)
        assert r is not None
        assert r.period_date == date(2025, 1, 31)

    def test_korean_in_header(self):
        headers = ["계정코드", "2025년 3월 시산표"]
        r = extract_period_from_headers(headers)
        assert r is not None
        assert r.period_date == date(2025, 3, 31)

    def test_no_date_in_headers(self):
        headers = ["Account Code", "Account Name", "Debit", "Credit", "Balance"]
        r = extract_period_from_headers(headers)
        assert r is None


# ── 통합 탐지 (detect_tb_period) ────────────────────────


class TestDetectTBPeriod:
    def test_user_specified_takes_priority(self):
        user_date = date(2025, 3, 15)
        r = detect_tb_period(
            filename="TB_202501.xlsx",
            sheet_name="Sheet1",
            headers=["Account"],
            user_period_date=user_date,
        )
        assert r is not None
        assert r.period_date == user_date
        assert r.source == "user_specified"
        assert r.confidence == Decimal("1.0000")

    def test_filename_over_sheet_name(self):
        r = detect_tb_period(
            filename="TB_202501.xlsx",
            sheet_name="202503",
            headers=["Account"],
        )
        assert r is not None
        assert r.period_date == date(2025, 1, 31)
        assert r.source == "filename"

    def test_sheet_name_when_no_filename_match(self):
        r = detect_tb_period(
            filename="Trial_Balance.xlsx",
            sheet_name="202503",
            headers=["Account"],
        )
        assert r is not None
        assert r.period_date == date(2025, 3, 31)
        assert r.source == "sheet_name"

    def test_header_when_no_other_match(self):
        r = detect_tb_period(
            filename="TB.xlsx",
            sheet_name="Sheet1",
            headers=["as of 2025-09-30"],
        )
        assert r is not None
        assert r.period_date == date(2025, 9, 30)
        assert r.source == "header_row"

    def test_deal_period_fallback(self):
        r = detect_tb_period(
            filename="TB.xlsx",
            sheet_name="Sheet1",
            headers=["Account"],
            deal_period_end=date(2025, 12, 31),
        )
        assert r is not None
        assert r.period_date == date(2025, 12, 31)
        assert r.source == "deal_period"
        assert r.confidence == Decimal("0.3000")

    def test_none_when_no_info(self):
        r = detect_tb_period(
            filename="data.xlsx",
            sheet_name="Sheet1",
            headers=["col1", "col2"],
        )
        assert r is None

    def test_user_specified_over_deal_fallback(self):
        r = detect_tb_period(
            filename="TB.xlsx",
            sheet_name="Sheet1",
            headers=["Account"],
            deal_period_end=date(2025, 12, 31),
            user_period_date=date(2025, 6, 30),
        )
        assert r.period_date == date(2025, 6, 30)
        assert r.source == "user_specified"
