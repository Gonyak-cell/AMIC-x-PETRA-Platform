"""한국어 금융 용어 브릿지 단위 테스트.

> 마지막 수정: 2026-02-11 15:00:00

to_korean, to_english, get_term, get_industry_terms 함수를 테스트한다.
"""

from __future__ import annotations

import pytest

from src.narrative_generator.korean_finance.terminology import (
    TermCategory,
    TermEntry,
    get_industry_terms,
    get_term,
    to_english,
    to_korean,
)


# ---------------------------------------------------------------------------
# TestToKorean
# ---------------------------------------------------------------------------


class TestToKorean:
    """to_korean 함수 테스트."""

    @pytest.mark.parametrize(
        "input_term, expected_substring",
        [
            ("EBITDA", "EBITDA"),
            ("EBITDA", "상각전영업이익"),
            ("ebitda", "EBITDA"),
            ("ROE", "자기자본이익률"),
        ],
        ids=["약어_EBITDA", "한국어_포함", "소문자_키", "약어_ROE"],
    )
    def test_to_korean_with_abbreviation(
        self, input_term: str, expected_substring: str
    ) -> None:
        """영문 약어/키를 한국어로 변환할 때 약어와 한국어가 모두 포함되는지 확인한다."""
        result = to_korean(input_term)
        assert expected_substring in result

    def test_to_korean_unknown_term_returns_original(self) -> None:
        """미등록 용어는 원본 그대로 반환한다."""
        unknown = "UnknownFinancialTerm"
        assert to_korean(unknown) == unknown


# ---------------------------------------------------------------------------
# TestToEnglish
# ---------------------------------------------------------------------------


class TestToEnglish:
    """to_english 함수 테스트."""

    def test_to_english_returns_english(self) -> None:
        """한국어 '영업이익률'을 영문 'Operating Profit Margin'으로 변환한다."""
        result = to_english("영업이익률")
        assert result == "Operating Profit Margin"

    def test_to_english_unknown_term_returns_original(self) -> None:
        """미등록 한국어 용어는 원본 그대로 반환한다."""
        unknown = "알수없는용어"
        assert to_english(unknown) == unknown


# ---------------------------------------------------------------------------
# TestGetTerm
# ---------------------------------------------------------------------------


class TestGetTerm:
    """get_term 함수 테스트."""

    def test_get_term_returns_term_entry(self) -> None:
        """등록된 키로 TermEntry를 조회한다."""
        entry = get_term("revenue")

        assert entry is not None
        assert isinstance(entry, TermEntry)
        assert entry.korean == "매출액"
        assert entry.english == "Revenue"
        assert entry.category == TermCategory.INCOME_STATEMENT

    def test_get_term_unknown_returns_none(self) -> None:
        """미등록 키는 None을 반환한다."""
        assert get_term("nonexistent_key") is None


# ---------------------------------------------------------------------------
# TestGetIndustryTerms
# ---------------------------------------------------------------------------


class TestGetIndustryTerms:
    """get_industry_terms 함수 테스트."""

    def test_get_industry_terms_tech(self) -> None:
        """tech 산업 용어 목록이 비어있지 않고 올바른 카테고리인지 확인한다."""
        terms = get_industry_terms("tech")

        assert len(terms) > 0
        assert all(isinstance(t, TermEntry) for t in terms)
        assert all(t.category == TermCategory.INDUSTRY_TECH for t in terms)

        # 대표 용어 존재 확인
        abbreviations = {t.abbreviation for t in terms if t.abbreviation}
        assert "ARR" in abbreviations
        assert "MRR" in abbreviations

    def test_get_industry_terms_logistics(self) -> None:
        """logistics 산업 용어 목록이 30개 이상이고 올바른 카테고리인지 확인한다."""
        terms = get_industry_terms("logistics")

        assert len(terms) >= 30
        assert all(isinstance(t, TermEntry) for t in terms)
        assert all(t.category == TermCategory.INDUSTRY_LOGISTICS for t in terms)

    def test_get_industry_terms_logistics_has_key_terms(self) -> None:
        """logistics 산업 용어에 핵심 약어(OTD, TMS, WMS, 3PL)가 포함."""
        terms = get_industry_terms("logistics")
        abbreviations = {t.abbreviation for t in terms if t.abbreviation}
        assert "OTD" in abbreviations
        assert "TMS" in abbreviations
        assert "WMS" in abbreviations
        assert "3PL" in abbreviations

    def test_term_category_industry_logistics_exists(self) -> None:
        """TermCategory.INDUSTRY_LOGISTICS가 존재한다."""
        assert hasattr(TermCategory, "INDUSTRY_LOGISTICS")
        assert TermCategory.INDUSTRY_LOGISTICS.value == "industry_logistics"

    def test_get_industry_terms_unknown_returns_empty(self) -> None:
        """미등록 산업은 빈 리스트를 반환한다."""
        assert get_industry_terms("unknown_industry") == []
