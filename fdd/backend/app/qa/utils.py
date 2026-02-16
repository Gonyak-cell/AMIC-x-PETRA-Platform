"""QA 공통 유틸리티 — Sprint 8.

모든 QA 모듈에서 공통으로 사용하는 유틸리티 함수.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

# Quantize constant — 4 decimal places
Q4 = Decimal("0.0001")

# Placeholder 패턴 (대소문자 모두 허용)
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}"),  # {{name}}, {{NAME}}, {{my_var_1}}
    re.compile(r"\{\{TABLE:([A-Za-z_][A-Za-z0-9_]*)\}\}"),  # {{TABLE:name}}
    re.compile(r"\{\{CHART:([A-Za-z_][A-Za-z0-9_]*)\}\}"),  # {{CHART:name}}
]

# 임계값 상수
TEXT_OVERFLOW_LIMIT = 500  # 텍스트 블록 최대 글자 수
CELL_OVERFLOW_LIMIT = 50  # 테이블 셀 최대 글자 수
DEFAULT_NUMERIC_TOLERANCE = Decimal("0.0001")  # 수치 비교 허용 오차


def safe_decimal(value: Any) -> Decimal | None:
    """안전하게 Decimal로 변환.

    Args:
        value: 변환할 값 (str, int, float, Decimal, None)

    Returns:
        Decimal 또는 None (변환 실패 시)
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        # float는 먼저 str로 변환 (부동소수점 오차 방지)
        if isinstance(value, float):
            return Decimal(str(value))
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def compare_decimals(
    expected: Decimal | str | None,
    actual: Decimal | str | None,
    tolerance: Decimal = DEFAULT_NUMERIC_TOLERANCE,
) -> bool:
    """두 수치 비교.

    Args:
        expected: 예상 값
        actual: 실제 값
        tolerance: 허용 오차 (기본 0.0001)

    Returns:
        tolerance 이내면 True
    """
    exp = safe_decimal(expected)
    act = safe_decimal(actual)

    if exp is None and act is None:
        return True
    if exp is None or act is None:
        return False

    return abs(exp - act) <= tolerance


def format_decimal_diff(expected: Decimal, actual: Decimal) -> str:
    """수치 차이를 포맷팅.

    Args:
        expected: 예상 값
        actual: 실제 값

    Returns:
        "Expected 100.00, got 99.99 (diff: -0.01)" 형태
    """
    diff = actual - expected
    sign = "+" if diff >= 0 else ""
    return f"Expected {expected}, got {actual} (diff: {sign}{diff})"


def extract_numeric_keys(row: dict[str, Any]) -> list[str]:
    """행에서 수치 필드 키를 추출.

    Args:
        row: 테이블 행 딕셔너리

    Returns:
        수치로 변환 가능한 필드 키 목록
    """
    numeric_keys = []
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, (int, float, Decimal)):
            numeric_keys.append(key)
        elif isinstance(value, str):
            # 숫자로 변환 가능한지 확인
            try:
                Decimal(value.replace(",", "").replace(" ", ""))
                numeric_keys.append(key)
            except (InvalidOperation, ValueError):
                pass
    return numeric_keys


def find_placeholders(text: str) -> list[tuple[str, str]]:
    """텍스트에서 placeholder 패턴 찾기.

    Args:
        text: 검사할 텍스트

    Returns:
        [(전체 매치, 변수명), ...] 목록
    """
    results = []
    for pattern in PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(text):
            results.append((match.group(0), match.group(1)))
    return results


def check_text_length(text: str, limit: int) -> bool:
    """텍스트 길이가 제한 이내인지 확인.

    Args:
        text: 검사할 텍스트
        limit: 최대 글자 수

    Returns:
        제한 이내면 True
    """
    return len(text) <= limit


def build_location_path(
    *parts: str,
    row_index: int | None = None,
    col_key: str | None = None,
) -> str:
    """위치 경로 문자열 생성.

    Args:
        *parts: 경로 부분들 (section, block 등)
        row_index: 행 인덱스 (선택)
        col_key: 컬럼 키 (선택)

    Returns:
        "section.qoe/block.bridge/row.3/col.amount" 형태
    """
    path_parts = [str(p) for p in parts if p]
    if row_index is not None:
        path_parts.append(f"row.{row_index}")
    if col_key is not None:
        path_parts.append(f"col.{col_key}")
    return "/".join(path_parts)


def normalize_for_comparison(value: Any) -> str:
    """비교를 위한 값 정규화.

    Args:
        value: 정규화할 값

    Returns:
        정규화된 문자열
    """
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value.quantize(Q4, rounding=ROUND_HALF_UP))
    if isinstance(value, float):
        return str(Decimal(str(value)).quantize(Q4, rounding=ROUND_HALF_UP))
    return str(value).strip()


def deep_get(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """중첩 딕셔너리에서 값 가져오기.

    Args:
        d: 딕셔너리
        *keys: 키 경로
        default: 기본값

    Returns:
        값 또는 기본값
    """
    result = d
    for key in keys:
        if not isinstance(result, dict):
            return default
        result = result.get(key, default)
        if result is default:
            return default
    return result


def count_blocks_by_type(ir_dict: dict[str, Any]) -> dict[str, int]:
    """Report IR에서 블록 타입별 개수 집계.

    Args:
        ir_dict: Report IR 딕셔너리

    Returns:
        {"table": 3, "chart": 2, ...} 형태
    """
    counts: dict[str, int] = {}
    sections = ir_dict.get("sections", [])
    for section in sections:
        block_type = section.get("type", "unknown")
        counts[block_type] = counts.get(block_type, 0) + 1
    return counts
