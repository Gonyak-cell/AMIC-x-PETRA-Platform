"""구조화 출력 파싱 모듈 (T-N15).

> 마지막 수정: 2026-02-10 11:52:29

LLM 응답에서 내러티브 텍스트와 수치 클레임을 추출한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class NumericClaim:
    """내러티브에서 추출된 수치 주장.

    Attributes:
        raw_text: 원문 텍스트 (예: "매출 1,500억원").
        metric_type: 지표 유형 ("amount", "percentage", "multiple", "count").
        value: 파싱된 수치.
        unit: 단위 ("억원", "%", "배" 등).
        context: 주변 문맥 텍스트.
    """

    raw_text: str
    metric_type: str
    value: float
    unit: str = ""
    context: str = ""


@dataclass
class SectionNarrative:
    """구조화된 섹션 내러티브.

    Attributes:
        section_id: 섹션 식별자.
        text: 내러티브 본문 (plain text).
        key_claims: 추출된 수치 클레임 리스트.
        metadata: 추가 메타데이터.
    """

    section_id: str
    text: str
    key_claims: list[NumericClaim] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 수치 패턴 정규식
# ---------------------------------------------------------------------------

# 금액 패턴: "1,500억원", "150.3백만원", "2.5조원", "1,234원"
_AMOUNT_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(조원|억원|백만원|만원|원|조|억)")

# 퍼센트 패턴: "15.2%", "23.4%p", "-5.1%"
_PERCENT_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s*(%p|%)")

# 배수 패턴: "5.2배", "3.1x", "1.8X"
_MULTIPLE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(배|[xX])")

# 건수/개 패턴: "1,200명", "350개", "28건"
_COUNT_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})*)\s*(명|개|건|곳|사|호)")


# ---------------------------------------------------------------------------
# 클레임 추출
# ---------------------------------------------------------------------------


def extract_numeric_claims(text: str) -> list[NumericClaim]:
    """텍스트에서 수치 클레임을 추출한다.

    Args:
        text: 분석할 텍스트.

    Returns:
        NumericClaim 리스트.
    """
    claims: list[NumericClaim] = []

    # 금액 추출
    for match in _AMOUNT_PATTERN.finditer(text):
        value_str = match.group(1).replace(",", "")
        unit = match.group(2)
        raw_value = float(value_str)

        # 원 단위로 정규화
        multiplier = _UNIT_MULTIPLIERS.get(unit, 1)
        normalized_value = raw_value * multiplier

        context = _get_context(text, match.start(), match.end())
        claims.append(
            NumericClaim(
                raw_text=match.group(0),
                metric_type="amount",
                value=normalized_value,
                unit=unit,
                context=context,
            )
        )

    # 퍼센트 추출
    for match in _PERCENT_PATTERN.finditer(text):
        value = float(match.group(1))
        unit = match.group(2)
        context = _get_context(text, match.start(), match.end())
        claims.append(
            NumericClaim(
                raw_text=match.group(0),
                metric_type="percentage",
                value=value,
                unit=unit,
                context=context,
            )
        )

    # 배수 추출
    for match in _MULTIPLE_PATTERN.finditer(text):
        value = float(match.group(1))
        unit = match.group(2)
        context = _get_context(text, match.start(), match.end())
        claims.append(
            NumericClaim(
                raw_text=match.group(0),
                metric_type="multiple",
                value=value,
                unit=unit,
                context=context,
            )
        )

    # 건수 추출
    for match in _COUNT_PATTERN.finditer(text):
        value = float(match.group(1).replace(",", ""))
        unit = match.group(2)
        context = _get_context(text, match.start(), match.end())
        claims.append(
            NumericClaim(
                raw_text=match.group(0),
                metric_type="count",
                value=value,
                unit=unit,
                context=context,
            )
        )

    return claims


def parse_narrative_response(
    raw: str,
    section_id: str,
) -> SectionNarrative:
    """LLM 응답을 SectionNarrative로 파싱한다.

    Args:
        raw: LLM의 원문 응답.
        section_id: 섹션 식별자.

    Returns:
        SectionNarrative (텍스트 + 수치 클레임).
    """
    # 텍스트 정리: 불필요한 마크다운/헤더 제거
    text = _clean_response(raw)

    # 수치 클레임 추출
    claims = extract_numeric_claims(text)

    return SectionNarrative(
        section_id=section_id,
        text=text,
        key_claims=claims,
        metadata={"original_length": len(raw), "cleaned_length": len(text)},
    )


# ---------------------------------------------------------------------------
# 내부 유틸리티
# ---------------------------------------------------------------------------

_UNIT_MULTIPLIERS: dict[str, float] = {
    "원": 1,
    "만원": 1e4,
    "백만원": 1e6,
    "억원": 1e8,
    "억": 1e8,
    "조원": 1e12,
    "조": 1e12,
}


def _get_context(text: str, start: int, end: int, window: int = 30) -> str:
    """매치 주변의 컨텍스트 텍스트를 반환한다."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    return text[ctx_start:ctx_end].strip()


def _clean_response(raw: str) -> str:
    """LLM 응답 텍스트를 정리한다.

    마크다운 헤더, 볼드, 리스트 마커 등을 제거한다.
    """
    text = raw.strip()

    # 마크다운 헤더 제거 (## 등)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # 볼드/이탤릭 마커 제거
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)

    # 리스트 마커 제거 (- 또는 * 로 시작하는 줄)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)

    # 연속 줄바꿈 정리
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
