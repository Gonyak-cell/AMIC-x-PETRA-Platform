"""Financial Engine -- 단위 정규화 모듈 (T-F04).

한국 재무 데이터에서 사용되는 금액 단위(원, 천원, 백만원, 억원, 조원)를
감지하고 원(KRW) 단위로 정규화합니다.

주요 기능:
- 문자열에서 단위를 자동 감지하고 Decimal 변환
- 콤마, 괄호 음수, 공백 등 다양한 표기 처리
- 단위 간 변환 (예: 백만원 -> 억원)
- 배치 정규화

> 마지막 수정: 2026-02-09 16:02:30
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Final

from src.financial_engine.exceptions import NormalizationError, UnitConversionError


# ============================================================================
# 단위 스케일 정의
# ============================================================================


@dataclass(frozen=True)
class UnitScale:
    """금액 단위 스케일 정의.

    Attributes:
        name: 단위 이름 (예: "백만원").
        multiplier: 원 단위 대비 배율.
        patterns: 해당 단위를 감지하기 위한 정규식 패턴 목록.
    """

    name: str
    multiplier: Decimal
    patterns: list[str] = field(default_factory=list)

    def matches(self, text: str) -> bool:
        """주어진 텍스트가 이 단위 패턴에 매칭되는지 확인한다.

        Args:
            text: 검사할 문자열.

        Returns:
            패턴 매칭 여부.
        """
        for pattern in self.patterns:
            if re.search(pattern, text):
                return True
        return False


# 단위 스케일 목록 -- 큰 단위부터 정의하여 조원이 원보다 먼저 매칭되도록 한다.
UNIT_SCALES: Final[list[UnitScale]] = [
    UnitScale(
        name="조원",
        multiplier=Decimal("1000000000000"),
        patterns=[r"조\s*원", r"조$"],
    ),
    UnitScale(
        name="억원",
        multiplier=Decimal("100000000"),
        patterns=[r"억\s*원", r"억$"],
    ),
    UnitScale(
        name="백만원",
        multiplier=Decimal("1000000"),
        patterns=[r"백만\s*원", r"백만$"],
    ),
    UnitScale(
        name="천원",
        multiplier=Decimal("1000"),
        patterns=[r"천\s*원", r"천$"],
    ),
    UnitScale(
        name="원",
        multiplier=Decimal("1"),
        patterns=[r"(?<!조\s)(?<!억\s)(?<!백만\s)(?<!천\s)원$", r"(?<!조)(?<!억)(?<!백만)(?<!천)원$"],
    ),
]

# 이름으로 빠르게 조회하기 위한 매핑
_UNIT_BY_NAME: Final[dict[str, UnitScale]] = {scale.name: scale for scale in UNIT_SCALES}


def _get_unit_by_name(name: str) -> UnitScale:
    """이름으로 UnitScale을 조회한다.

    Args:
        name: 단위 이름 (예: "백만원", "억원").

    Returns:
        매칭되는 UnitScale.

    Raises:
        UnitConversionError: 해당 이름의 단위가 존재하지 않을 때.
    """
    scale = _UNIT_BY_NAME.get(name)
    if scale is None:
        raise UnitConversionError(
            value=name,
            source_unit=None,
            reason=f"알 수 없는 단위: '{name}'. "
            f"지원 단위: {', '.join(_UNIT_BY_NAME.keys())}",
        )
    return scale


# ============================================================================
# 내부 헬퍼
# ============================================================================

# 숫자 부분 추출 패턴: 부호, 정수, 소수점, 괄호 음수 등
_NUMERIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
    (?P<paren_neg>\()?\s*        # 괄호 음수 시작 (선택)
    (?P<sign>[+-])?\s*           # 부호 (선택)
    (?P<number>                  # 숫자 본체
        \d[\d,]*                 # 정수부 (콤마 포함 가능)
        (?:\.\d+)?               # 소수부 (선택)
    )
    \s*(?P<paren_close>\))?      # 괄호 음수 종료 (선택)
    """,
    re.VERBOSE,
)

# 단위 텍스트 추출 패턴 (숫자 뒤에 오는 한글 단위)
_UNIT_SUFFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:조\s*원|억\s*원|백만\s*원|천\s*원|원)"
)


def _clean_numeric_string(raw: str) -> tuple[Decimal, str]:
    """원시 문자열에서 숫자 값과 단위 접미사를 분리한다.

    Args:
        raw: 원시 입력 문자열 (예: "1,500백만원", "(3.5)억원").

    Returns:
        (숫자 Decimal 값, 단위 접미사 문자열) 튜플.
        단위가 없으면 접미사는 빈 문자열.

    Raises:
        NormalizationError: 숫자를 파싱할 수 없을 때.
    """
    text = raw.strip()
    if not text:
        raise NormalizationError(
            message="정규화 실패: 빈 문자열은 변환할 수 없습니다.",
            details={"value": raw},
        )

    match = _NUMERIC_PATTERN.search(text)
    if match is None:
        raise NormalizationError(
            message=f"정규화 실패: '{raw}'에서 숫자를 추출할 수 없습니다.",
            details={"value": raw},
        )

    number_str = match.group("number").replace(",", "")
    sign = match.group("sign")
    is_paren_neg = (
        match.group("paren_neg") is not None and match.group("paren_close") is not None
    )

    try:
        value = Decimal(number_str)
    except InvalidOperation as exc:
        raise NormalizationError(
            message=f"정규화 실패: '{number_str}'을(를) 숫자로 변환할 수 없습니다.",
            details={"value": raw, "extracted": number_str},
        ) from exc

    # 음수 처리: 명시적 마이너스 부호 또는 괄호 표기
    if sign == "-" or is_paren_neg:
        value = -value

    # 숫자 매칭 이후의 텍스트에서 단위 접미사 추출
    text[match.end() :].strip()
    # 숫자 앞의 텍스트는 무시하지만, 숫자 바로 뒤에 붙은 단위도 확인
    # (예: "1500백만원" -- 숫자 패턴이 "1500"까지만 매칭)
    # 전체 텍스트에서 단위 패턴을 찾는다
    unit_match = _UNIT_SUFFIX_PATTERN.search(text[match.start("number") :])
    unit_suffix = unit_match.group(0) if unit_match else ""

    return value, unit_suffix


# ============================================================================
# UnitNormalizer 클래스
# ============================================================================


class UnitNormalizer:
    """금액 단위 정규화기.

    한국 재무 데이터에서 사용되는 다양한 금액 표기를 원(KRW) 단위의
    Decimal 값으로 변환한다.

    Examples:
        >>> normalizer = UnitNormalizer()
        >>> normalizer.normalize("1,500백만원")
        Decimal('1500000000')
        >>> normalizer.normalize("3.5억원")
        Decimal('350000000')
        >>> normalizer.normalize("-1,500", source_unit="천원")
        Decimal('-1500000')
    """

    def __init__(self, *, default_unit: str = "원") -> None:
        """UnitNormalizer를 초기화한다.

        Args:
            default_unit: 단위를 감지할 수 없을 때 사용할 기본 단위.
                지원 단위: 원, 천원, 백만원, 억원, 조원.

        Raises:
            UnitConversionError: default_unit이 지원하지 않는 단위일 때.
        """
        self._default_unit: UnitScale = _get_unit_by_name(default_unit)

    def detect_unit(self, value: str) -> UnitScale | None:
        """문자열에서 금액 단위를 감지한다.

        큰 단위부터 순서대로 매칭하여 가장 먼저 매칭되는 단위를 반환한다.
        (예: "조원"이 "원"보다 먼저 검사됨)

        Args:
            value: 단위를 감지할 문자열.

        Returns:
            감지된 UnitScale. 단위를 찾을 수 없으면 None.
        """
        if not value or not value.strip():
            return None

        text = value.strip()
        for scale in UNIT_SCALES:
            if scale.matches(text):
                return scale
        return None

    def normalize(
        self,
        value: str | Decimal | int | float | None,
        *,
        source_unit: str | None = None,
    ) -> Decimal:
        """금액 값을 원(KRW) 단위 Decimal로 정규화한다.

        처리 흐름:
        1. None/빈 문자열 -> Decimal("0")
        2. 이미 Decimal/int/float -> source_unit 적용 후 반환
        3. 문자열 -> 숫자 추출 + 단위 감지 -> 원 단위로 변환

        Args:
            value: 정규화할 값. 문자열, 숫자, 또는 None.
            source_unit: 명시적 소스 단위. 지정 시 문자열 내 단위보다 우선.

        Returns:
            원(KRW) 단위의 Decimal 값.

        Raises:
            NormalizationError: 값을 파싱할 수 없을 때.
            UnitConversionError: source_unit이 알 수 없는 단위일 때.
        """
        # None 또는 빈 값 처리
        if value is None:
            return Decimal("0")

        if isinstance(value, (int, float)):
            value = Decimal(str(value))

        if isinstance(value, Decimal):
            unit = _get_unit_by_name(source_unit) if source_unit else self._default_unit
            return value * unit.multiplier

        # 문자열 처리
        if not isinstance(value, str):
            raise NormalizationError(
                message=f"정규화 실패: 지원하지 않는 타입 '{type(value).__name__}'.",
                details={"value": str(value), "type": type(value).__name__},
            )

        stripped = value.strip()
        if not stripped:
            return Decimal("0")

        # 숫자와 단위 접미사 분리
        numeric_value, unit_suffix = _clean_numeric_string(stripped)

        # 단위 결정: source_unit > 문자열 내 단위 > default_unit
        if source_unit is not None:
            unit = _get_unit_by_name(source_unit)
        elif unit_suffix:
            detected = self.detect_unit(unit_suffix)
            unit = detected if detected else self._default_unit
        else:
            unit = self._default_unit

        return numeric_value * unit.multiplier

    def normalize_batch(
        self,
        data: dict[str, str | Decimal | int | float | None],
        *,
        source_unit: str | None = None,
    ) -> dict[str, Decimal]:
        """여러 항목을 일괄 정규화한다.

        Args:
            data: {항목명: 값} 딕셔너리.
            source_unit: 모든 항목에 적용할 소스 단위 (선택).

        Returns:
            {항목명: 원 단위 Decimal 값} 딕셔너리.

        Raises:
            NormalizationError: 개별 값 정규화 실패 시.
                details에 실패한 키와 원본 값을 포함한다.
        """
        result: dict[str, Decimal] = {}
        errors: list[dict[str, str]] = []

        for key, val in data.items():
            try:
                result[key] = self.normalize(val, source_unit=source_unit)
            except (NormalizationError, UnitConversionError) as exc:
                errors.append({"key": key, "value": str(val), "error": exc.message})

        if errors:
            raise NormalizationError(
                message=f"배치 정규화 실패: {len(errors)}건의 항목에서 오류 발생.",
                details={"errors": errors, "successful_count": len(result)},
            )

        return result

    def convert(
        self,
        value: Decimal,
        *,
        from_unit: str,
        to_unit: str,
    ) -> Decimal:
        """금액을 한 단위에서 다른 단위로 변환한다.

        내부적으로 원(KRW) 단위를 거쳐 변환한다:
        source -> 원 -> target

        Args:
            value: 변환할 Decimal 값.
            from_unit: 소스 단위 이름 (예: "백만원").
            to_unit: 대상 단위 이름 (예: "억원").

        Returns:
            대상 단위의 Decimal 값.

        Raises:
            UnitConversionError: 알 수 없는 단위가 지정되었을 때.
        """
        source = _get_unit_by_name(from_unit)
        target = _get_unit_by_name(to_unit)

        if source.name == target.name:
            return value

        # 원 단위로 변환 후 대상 단위로 나눈다
        value_in_won = value * source.multiplier
        return value_in_won / target.multiplier
