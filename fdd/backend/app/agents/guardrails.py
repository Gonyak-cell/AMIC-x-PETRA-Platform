"""AI Guardrails — Sprint 6.

LLM 출력의 할루시네이션 탐지 및 금액 교차검증 함수.

규칙:
1. LLM이 언급한 금액은 반드시 소스 데이터에 존재해야 함
2. LLM이 언급한 전표 ID는 반드시 소스 데이터에 존재해야 함
3. LLM 제안 합계와 엔진 계산 합계는 일치해야 함
4. 존재하지 않는 계정 코드 참조는 할루시네이션
5. 낮은 신뢰도 제안은 필터링
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_amounts_exist(
    llm_output: dict[str, Any],
    source_entries: list[dict[str, Any]],
    amount_field: str = "amount",
) -> list[str]:
    """LLM이 언급한 금액이 소스 데이터에 존재하는지 검증한다.

    Args:
        llm_output: LLM 출력 딕셔너리
        source_entries: 소스 전표 리스트
        amount_field: 금액 필드명

    Returns:
        검증 오류 목록
    """
    errors: list[str] = []

    # 소스 금액 수집 (문자열 변환하여 비교)
    source_amounts: set[str] = set()
    for entry in source_entries:
        amt = entry.get(amount_field)
        if amt is not None:
            # Decimal과 문자열 모두 처리
            source_amounts.add(str(amt).strip())

    # LLM 출력에서 금액 추출
    llm_amounts = _extract_amounts_from_output(llm_output)

    for amt in llm_amounts:
        amt_str = str(amt).strip()
        if amt_str not in source_amounts:
            errors.append(f"금액 {amt_str}이 소스 데이터에 존재하지 않음 (할루시네이션 의심)")

    return errors


def validate_entry_ids_exist(
    llm_output: dict[str, Any],
    source_entries: list[dict[str, Any]],
    id_field: str = "entry_id",
) -> list[str]:
    """LLM이 언급한 전표 ID가 소스 데이터에 존재하는지 검증한다.

    Args:
        llm_output: LLM 출력 딕셔너리
        source_entries: 소스 전표 리스트
        id_field: ID 필드명

    Returns:
        검증 오류 목록
    """
    errors: list[str] = []

    # 소스 ID 수집
    source_ids: set[str] = set()
    for entry in source_entries:
        entry_id = entry.get(id_field)
        if entry_id:
            source_ids.add(str(entry_id))

    # LLM 출력에서 entry_id 추출
    llm_ids = _extract_entry_ids_from_output(llm_output)

    for eid in llm_ids:
        if eid not in source_ids:
            errors.append(f"전표 ID {eid}가 소스 데이터에 존재하지 않음 (할루시네이션 의심)")

    return errors


def validate_totals_match(
    llm_suggested_total: Decimal,
    engine_calculated_total: Decimal,
    tolerance: Decimal = Decimal("0.01"),
) -> list[str]:
    """LLM 제안 합계와 엔진 계산 합계를 교차검증한다.

    Args:
        llm_suggested_total: LLM이 제안한 합계
        engine_calculated_total: 엔진이 계산한 합계
        tolerance: 허용 오차 (기본 0.01)

    Returns:
        검증 오류 목록
    """
    errors: list[str] = []

    diff = abs(llm_suggested_total - engine_calculated_total)
    if diff > tolerance:
        errors.append(
            f"합계 불일치: LLM={llm_suggested_total}, "
            f"Engine={engine_calculated_total}, 차이={diff}"
        )

    return errors


def check_hallucination_patterns(
    llm_output: dict[str, Any],
    known_account_codes: set[str],
) -> list[str]:
    """존재하지 않는 계정 코드 참조를 탐지한다.

    Args:
        llm_output: LLM 출력 딕셔너리
        known_account_codes: 알려진 계정 코드 집합

    Returns:
        할루시네이션 오류 목록
    """
    errors: list[str] = []

    # LLM 출력에서 계정 코드 추출
    llm_codes = _extract_account_codes_from_output(llm_output)

    for code in llm_codes:
        if code not in known_account_codes:
            errors.append(f"계정 코드 {code}가 존재하지 않음 (할루시네이션)")

    return errors


def enforce_confidence_threshold(
    llm_output: dict[str, Any],
    min_confidence: Decimal = Decimal("0.30"),
) -> dict[str, Any]:
    """낮은 신뢰도 제안을 필터링한다.

    Args:
        llm_output: LLM 출력 딕셔너리
        min_confidence: 최소 신뢰도 (기본 0.30)

    Returns:
        필터링된 출력 딕셔너리
    """
    filtered = llm_output.copy()

    # analysis_results 필터링 (QoE Analyzer용)
    if "analysis_results" in filtered:
        filtered["analysis_results"] = [
            item
            for item in filtered["analysis_results"]
            if Decimal(str(item.get("confidence", 0))) >= min_confidence
        ]

    # mapping_suggestions 필터링 (CoA Mapper용)
    if "mapping_suggestions" in filtered:
        filtered["mapping_suggestions"] = [
            item
            for item in filtered["mapping_suggestions"]
            if Decimal(str(item.get("confidence", 0))) >= min_confidence
        ]

    return filtered


def validate_no_calculations(
    llm_output: dict[str, Any],
) -> list[str]:
    """LLM이 계산을 시도했는지 검사한다.

    LLM은 판단만 수행해야 하며, 계산은 엔진이 수행한다.
    계산 시도의 징후를 탐지한다.

    Returns:
        검증 오류 목록
    """
    errors: list[str] = []

    # 계산 관련 키워드 탐지
    calculation_keywords = [
        "calculated",
        "computed",
        "sum is",
        "total is",
        "합계는",
        "계산하면",
        "계산 결과",
    ]

    output_str = str(llm_output).lower()
    for kw in calculation_keywords:
        if kw in output_str:
            errors.append(
                f"LLM이 계산을 시도한 것으로 보임 (키워드: {kw}). "
                "계산은 엔진만 수행해야 함."
            )
            break

    return errors


def validate_narrative_claims(
    narrative_text: str,
    known_values: dict[str, str],
) -> list[str]:
    """LLM 생성 내러티브의 수치 주장을 엔진 계산값과 교차검증한다.

    내러티브에 등장하는 숫자가 known_values에 있는 값과 일치하는지 확인.
    내러티브에 없는 수치를 날조했는지 탐지.

    Args:
        narrative_text: LLM이 생성한 내러티브 텍스트
        known_values: {레이블: 값} — 엔진에서 계산된 값 (예: {"EBITDA": "1,234"})

    Returns:
        검증 경고 목록
    """
    import re

    warnings: list[str] = []

    # 내러티브에서 숫자 패턴 추출 (쉼표 포함 숫자, 소수점 포함)
    number_pattern = re.compile(r"[\d,]+\.?\d*")
    narrative_numbers = set(number_pattern.findall(narrative_text))

    # 알려진 값에서 숫자 추출
    known_numbers: set[str] = set()
    for value in known_values.values():
        nums = number_pattern.findall(str(value))
        known_numbers.update(nums)

    # 내러티브에 있지만 알려진 값에 없는 큰 숫자 탐지
    for num_str in narrative_numbers:
        clean = num_str.replace(",", "")
        try:
            num = Decimal(clean)
        except Exception:
            logger.debug("Skipping unparseable narrative number: %s", num_str)
            continue

        # 작은 숫자(100 미만)는 무시 — 백분율, 횟수 등
        if abs(num) < 100:
            continue

        # 알려진 숫자에 있는지 확인
        found = False
        for known in known_numbers:
            known_clean = known.replace(",", "")
            try:
                if Decimal(known_clean) == num:
                    found = True
                    break
            except Exception:
                logger.debug("Skipping unparseable known value: %s", known)
                continue

        if not found:
            warnings.append(
                f"내러티브에 '{num_str}'이 등장하지만 엔진 계산값에 없음 (할루시네이션 의심)"
            )

    return warnings


# ── Internal Helpers ─────────────────────────────────────


def _extract_amounts_from_output(output: dict[str, Any]) -> list[str]:
    """LLM 출력에서 금액 값들을 추출한다."""
    amounts: list[str] = []

    def _recursive_extract(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ("amount", "suggested_amount", "total"):
                    if value is not None:
                        amounts.append(str(value))
                else:
                    _recursive_extract(value)
        elif isinstance(obj, list):
            for item in obj:
                _recursive_extract(item)

    _recursive_extract(output)
    return amounts


def _extract_entry_ids_from_output(output: dict[str, Any]) -> list[str]:
    """LLM 출력에서 entry_id 값들을 추출한다."""
    ids: list[str] = []

    def _recursive_extract(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ("entry_id", "source_entry_id"):
                    if value is not None:
                        ids.append(str(value))
                else:
                    _recursive_extract(value)
        elif isinstance(obj, list):
            for item in obj:
                _recursive_extract(item)

    _recursive_extract(output)
    return ids


def _extract_account_codes_from_output(output: dict[str, Any]) -> list[str]:
    """LLM 출력에서 계정 코드 값들을 추출한다."""
    codes: list[str] = []

    def _recursive_extract(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in (
                    "account_code",
                    "source_account_code",
                    "suggested_target_code",
                ):
                    if value is not None:
                        codes.append(str(value))
                else:
                    _recursive_extract(value)
        elif isinstance(obj, list):
            for item in obj:
                _recursive_extract(item)

    _recursive_extract(output)
    return codes


# ── Phase 4: 추가 검증 함수 ─────────────────────────────


def validate_percentage_claims(
    text: str,
    known_percentages: dict[str, str],
    tolerance: Decimal = Decimal("2.0"),
) -> list[str]:
    """LLM 텍스트 내 백분율 주장이 실제 값과 일치하는지 검증.

    Args:
        text: LLM 생성 텍스트
        known_percentages: {"metric_name": "45.5"} 형태의 실제 값
        tolerance: 허용 오차 (%, 기본 2.0)

    Returns:
        경고 메시지 목록
    """
    import re

    warnings = []
    # 텍스트에서 "N%" 또는 "N.N%" 패턴 추출
    pct_pattern = re.compile(r"(\d+\.?\d*)\s*%")
    matches = pct_pattern.findall(text)

    for match_str in matches:
        try:
            claimed_pct = Decimal(match_str)
        except Exception:
            continue

        # 알려진 값과 비교
        for metric, actual_str in known_percentages.items():
            try:
                actual = Decimal(str(actual_str))
            except Exception:
                continue

            # 근접한 값이면 검증 (±tolerance 이내에서 차이 체크)
            diff = abs(claimed_pct - actual)
            if diff <= tolerance * 2 and diff > tolerance:
                warnings.append(
                    f"PCT_MISMATCH: Claimed {claimed_pct}% for {metric}, actual {actual}%"
                )

    return warnings


def validate_trend_direction(
    text: str,
    known_trends: dict[str, str],
) -> list[str]:
    """LLM 텍스트 내 증가/감소 방향이 실제 YoY와 일치하는지 검증.

    Args:
        text: LLM 생성 텍스트
        known_trends: {"metric": "increase"} 또는 {"metric": "decrease"}

    Returns:
        경고 메시지 목록
    """
    warnings = []
    increase_words = {"증가", "상승", "성장", "확대", "호전", "increase", "growth", "rise", "grew"}
    decrease_words = {"감소", "하락", "축소", "악화", "위축", "decrease", "decline", "drop", "fell"}

    text_lower = text.lower()

    for metric, direction in known_trends.items():
        metric_lower = metric.lower()
        if metric_lower not in text_lower:
            continue

        # 메트릭 주변 텍스트에서 방향 감지
        idx = text_lower.index(metric_lower)
        context = text_lower[max(0, idx - 50):idx + len(metric_lower) + 50]

        text_says_increase = any(w in context for w in increase_words)
        text_says_decrease = any(w in context for w in decrease_words)

        if direction == "increase" and text_says_decrease and not text_says_increase:
            warnings.append(
                f"TREND_MISMATCH: Text says '{metric}' decreased, but actual trend is increase"
            )
        elif direction == "decrease" and text_says_increase and not text_says_decrease:
            warnings.append(
                f"TREND_MISMATCH: Text says '{metric}' increased, but actual trend is decrease"
            )

    return warnings
