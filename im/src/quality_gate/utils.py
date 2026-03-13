"""한국어 재무 수치 파싱 유틸리티.

deal-mgmt/app/ralph/korean_finance_dict.py의 parse_korean_number를 복제.
PPTXProgrammaticGate에서 테이블 합계 정합성 검증에 사용한다.
"""

from __future__ import annotations

import re

_PAREN_NEG_RE = re.compile(r"^\(([0-9,.]+)\)$")
_CURRENCY_RE = re.compile(r"[₩\\$€,원달러]")
_PERCENT_RE = re.compile(r"([0-9,.]+)\s*%")
_NUMBER_RE = re.compile(r"^-?[0-9,.]+$")


def parse_korean_number(text: str) -> float | None:
    """한국어 재무 수치 문자열을 float으로 파싱한다.

    지원 형식:
    - 괄호 음수: "(500)" → -500
    - 통화 기호: "₩1,234", "$1,234", "1,234원"
    - 퍼센트: "12.5%"
    - 천단위 쉼표: "1,234,567"
    """
    s = text.strip()
    if not s or s == "-":
        return None

    # 괄호 음수
    m = _PAREN_NEG_RE.match(s)
    if m:
        return -float(m.group(1).replace(",", ""))

    # 통화/기호 제거
    s = _CURRENCY_RE.sub("", s).strip()

    # 퍼센트
    m = _PERCENT_RE.match(s)
    if m:
        return float(m.group(1).replace(",", "")) / 100.0

    # 일반 숫자
    s = s.replace(",", "")
    if _NUMBER_RE.match(s):
        return float(s)

    return None
