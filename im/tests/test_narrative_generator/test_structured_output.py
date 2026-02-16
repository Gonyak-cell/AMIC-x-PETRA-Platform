"""구조화 출력 파싱 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

수치 클레임 추출(금액, 퍼센트), 내러티브 응답 파싱을 테스트한다.
"""

from __future__ import annotations

import pytest

from src.narrative_generator.engine.structured_output import (
    NumericClaim,
    SectionNarrative,
    extract_numeric_claims,
    parse_narrative_response,
)


# ---------------------------------------------------------------------------
# TestExtractNumericClaims
# ---------------------------------------------------------------------------


class TestExtractNumericClaims:
    """extract_numeric_claims 함수 테스트."""

    def test_extract_amount_claims(self) -> None:
        """금액 패턴('매출 1,500억원')이 올바르게 추출되는지 확인한다."""
        text = "당사의 매출은 1,500억원으로 전년 대비 크게 성장하였습니다."
        claims = extract_numeric_claims(text)

        amount_claims = [c for c in claims if c.metric_type == "amount"]
        assert len(amount_claims) >= 1

        claim = amount_claims[0]
        assert isinstance(claim, NumericClaim)
        assert claim.value == 1500 * 1e8  # 1,500억원 = 1500 * 10^8
        assert claim.unit == "억원"
        assert "1,500억원" in claim.raw_text

    def test_extract_percentage_claims(self) -> None:
        """퍼센트 패턴('15.2%')이 올바르게 추출되는지 확인한다."""
        text = "영업이익률은 15.2%를 기록하며 전년 대비 2.3%p 개선되었습니다."
        claims = extract_numeric_claims(text)

        pct_claims = [c for c in claims if c.metric_type == "percentage"]
        assert len(pct_claims) >= 1

        # 15.2% 클레임 확인
        values = [c.value for c in pct_claims]
        assert 15.2 in values

        # 2.3%p 클레임도 추출되어야 함
        raw_texts = [c.raw_text for c in pct_claims]
        assert any("15.2%" in rt for rt in raw_texts)

    @pytest.mark.parametrize(
        "text, expected_types",
        [
            ("매출 500억원, 성장률 12.5%, 5.2배", {"amount", "percentage", "multiple"}),
            ("임직원 1,200명, 고객사 350개", {"count"}),
        ],
        ids=["혼합_수치", "건수_수치"],
    )
    def test_extract_mixed_claims(self, text: str, expected_types: set[str]) -> None:
        """다양한 수치 유형이 혼합된 텍스트에서 올바르게 추출하는지 확인한다."""
        claims = extract_numeric_claims(text)
        found_types = {c.metric_type for c in claims}
        assert expected_types.issubset(found_types)


# ---------------------------------------------------------------------------
# TestParseNarrativeResponse
# ---------------------------------------------------------------------------


class TestParseNarrativeResponse:
    """parse_narrative_response 함수 테스트."""

    def test_parse_strips_markdown_and_extracts_claims(self) -> None:
        """마크다운이 제거되고 수치 클레임이 추출되는지 확인한다."""
        raw_response = (
            "## Executive Summary\n\n"
            "**테스트기업**은 매출 1,500억원, 영업이익률 18.7%를 기록하며 "
            "견조한 성장세를 유지하고 있습니다.\n\n"
            "- 3개년 매출 CAGR 22.5%\n"
            "- EBITDA 350억원\n"
        )

        result = parse_narrative_response(raw_response, "executive_summary")

        assert isinstance(result, SectionNarrative)
        assert result.section_id == "executive_summary"

        # 마크다운 헤더 '##' 제거 확인
        assert "##" not in result.text
        # 볼드 마커 '**' 제거 확인
        assert "**" not in result.text

        # 수치 클레임 추출 확인
        assert len(result.key_claims) >= 1

        # 메타데이터 존재 확인
        assert "original_length" in result.metadata
        assert "cleaned_length" in result.metadata
