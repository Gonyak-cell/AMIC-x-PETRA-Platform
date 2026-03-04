"""Delta Engine - 정의 버전 간 변경 분석.

EPIC-15 FDD-1501: DealDefinition 버전 간 차이 계산 및 영향 분석.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"


class ImpactLevel(StrEnum):
    """변경 영향도."""

    LOW = "LOW"  # 수치 변동 < 1%
    MEDIUM = "MEDIUM"  # 수치 변동 1-5%
    HIGH = "HIGH"  # 수치 변동 5-20%
    CRITICAL = "CRITICAL"  # 수치 변동 > 20%


class ChangeType(StrEnum):
    """변경 유형."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass(frozen=True)
class DefinitionDelta:
    """정의 변경 내역."""

    field: str
    change_type: ChangeType
    old_value: Any
    new_value: Any
    impact_level: ImpactLevel
    description: str = ""


@dataclass(frozen=True)
class CalculationImpact:
    """계산 영향."""

    calculation_type: str  # QoE, NWC, NetDebt
    field: str
    old_value: Decimal
    new_value: Decimal
    delta: Decimal
    delta_percent: Decimal
    impact_level: ImpactLevel


@dataclass
class DeltaSummary:
    """Delta 요약."""

    total_changes: int = 0
    by_impact_level: dict[str, int] = field(default_factory=dict)
    key_metrics_affected: list[str] = field(default_factory=list)
    recommendation: str | None = None


@dataclass
class DeltaResult:
    """Delta 분석 결과."""

    old_version: int
    new_version: int
    definition_deltas: list[DefinitionDelta] = field(default_factory=list)
    calculation_impacts: list[CalculationImpact] = field(default_factory=list)
    summary: DeltaSummary = field(default_factory=DeltaSummary)


# =============================================================================
# Delta Calculation
# =============================================================================


def calculate_definition_delta(
    old_definition: dict[str, Any],
    new_definition: dict[str, Any],
) -> list[DefinitionDelta]:
    """정의 변경 내역 계산.

    두 DealDefinition의 definition_data를 비교하여 변경 내역을 반환합니다.

    Args:
        old_definition: 이전 버전 정의 데이터
        new_definition: 새 버전 정의 데이터

    Returns:
        변경 내역 리스트
    """
    deltas: list[DefinitionDelta] = []

    # 모든 필드 수집
    all_fields = set(old_definition.keys()) | set(new_definition.keys())

    for field_name in all_fields:
        old_value = old_definition.get(field_name)
        new_value = new_definition.get(field_name)

        if old_value == new_value:
            continue

        # 변경 유형 결정
        if old_value is None:
            change_type = ChangeType.ADDED
        elif new_value is None:
            change_type = ChangeType.REMOVED
        else:
            change_type = ChangeType.MODIFIED

        # 영향도 결정
        impact_level = _calculate_field_impact(field_name, old_value, new_value)

        # 설명 생성
        description = _generate_change_description(
            field_name, change_type, old_value, new_value
        )

        deltas.append(
            DefinitionDelta(
                field=field_name,
                change_type=change_type,
                old_value=old_value,
                new_value=new_value,
                impact_level=impact_level,
                description=description,
            )
        )

    return deltas


def _calculate_field_impact(
    field_name: str,
    old_value: Any,
    new_value: Any,
) -> ImpactLevel:
    """필드 변경 영향도 계산."""
    # 핵심 필드 - CRITICAL 영향
    critical_fields = {
        "cash",
        "debt",
        "nwc",
        "target_nwc",
        "debt_like",
        "cash_like",
    }

    if field_name in critical_fields:
        # 리스트/딕트 변경은 HIGH 이상
        if isinstance(old_value, (list, dict)) or isinstance(new_value, (list, dict)):
            old_len = len(old_value) if old_value else 0
            new_len = len(new_value) if new_value else 0
            if abs(new_len - old_len) > 3:
                return ImpactLevel.CRITICAL
            elif abs(new_len - old_len) > 1:
                return ImpactLevel.HIGH
            else:
                return ImpactLevel.MEDIUM

    # 숫자 값 변경
    if _is_numeric(old_value) and _is_numeric(new_value):
        try:
            old_num = Decimal(str(old_value))
            new_num = Decimal(str(new_value))

            if old_num == 0:
                if new_num != 0:
                    return ImpactLevel.HIGH
                return ImpactLevel.LOW

            percent_change = abs((new_num - old_num) / old_num * 100)

            if percent_change > 20:
                return ImpactLevel.CRITICAL
            elif percent_change > 5:
                return ImpactLevel.HIGH
            elif percent_change > 1:
                return ImpactLevel.MEDIUM
            else:
                return ImpactLevel.LOW
        except (ValueError, TypeError, ArithmeticError):
            pass

    # 기본값
    if field_name in critical_fields:
        return ImpactLevel.HIGH
    return ImpactLevel.MEDIUM


def _is_numeric(value: Any) -> bool:
    """값이 숫자인지 확인."""
    if value is None:
        return False
    if isinstance(value, (int, float, Decimal)):
        return True
    if isinstance(value, str):
        try:
            Decimal(value)
            return True
        except (ValueError, TypeError):
            return False
    return False


def _generate_change_description(
    field: str,
    change_type: ChangeType,
    old_value: Any,
    new_value: Any,
) -> str:
    """변경 설명 생성."""
    if change_type == ChangeType.ADDED:
        return f"'{field}' field added"
    elif change_type == ChangeType.REMOVED:
        return f"'{field}' field removed"
    else:
        # 리스트 변경
        if isinstance(old_value, list) and isinstance(new_value, list):
            old_len = len(old_value)
            new_len = len(new_value)
            if new_len > old_len:
                return f"'{field}': {new_len - old_len} items added"
            elif new_len < old_len:
                return f"'{field}': {old_len - new_len} items removed"
            else:
                return f"'{field}': items modified"

        # 딕셔너리 변경
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            added = set(new_value.keys()) - set(old_value.keys())
            removed = set(old_value.keys()) - set(new_value.keys())
            if added or removed:
                parts = []
                if added:
                    parts.append(f"{len(added)} keys added")
                if removed:
                    parts.append(f"{len(removed)} keys removed")
                return f"'{field}': {', '.join(parts)}"

        return f"'{field}' changed from '{old_value}' to '{new_value}'"


# =============================================================================
# Calculation Impact Analysis
# =============================================================================


def analyze_calculation_impact(
    deltas: list[DefinitionDelta],
    old_results: dict[str, Any],
    new_results: dict[str, Any],
) -> list[CalculationImpact]:
    """계산 영향 분석.

    정의 변경이 각 계산 결과에 미친 영향을 분석합니다.

    Args:
        deltas: 정의 변경 내역
        old_results: 이전 계산 결과 (QoE, NWC, NetDebt 등)
        new_results: 새 계산 결과

    Returns:
        계산 영향 리스트
    """
    impacts: list[CalculationImpact] = []

    # 계산 유형별 핵심 메트릭
    key_metrics = {
        "qoe": ["reported_ebitda", "adjusted_ebitda", "total_adjustments"],
        "nwc": [
            "current_assets",
            "current_liabilities",
            "net_working_capital",
            "target_nwc",
        ],
        "debt": ["gross_debt", "cash", "net_debt", "debt_like_items"],
    }

    for calc_type, metrics in key_metrics.items():
        old_calc = old_results.get(calc_type, {})
        new_calc = new_results.get(calc_type, {})

        for metric in metrics:
            old_value = old_calc.get(metric)
            new_value = new_calc.get(metric)

            if old_value is None and new_value is None:
                continue

            # Decimal로 변환
            try:
                old_decimal = (
                    Decimal(str(old_value)) if old_value is not None else Decimal(0)
                )
                new_decimal = (
                    Decimal(str(new_value)) if new_value is not None else Decimal(0)
                )
            except (ValueError, TypeError):
                continue

            delta = new_decimal - old_decimal

            # 변화율 계산
            if old_decimal != 0:
                delta_percent = (delta / abs(old_decimal)) * 100
            else:
                delta_percent = Decimal(100) if new_decimal != 0 else Decimal(0)

            # 영향도 결정
            abs_percent = abs(delta_percent)
            if abs_percent > 20:
                impact_level = ImpactLevel.CRITICAL
            elif abs_percent > 5:
                impact_level = ImpactLevel.HIGH
            elif abs_percent > 1:
                impact_level = ImpactLevel.MEDIUM
            else:
                impact_level = ImpactLevel.LOW

            if delta != 0:
                impacts.append(
                    CalculationImpact(
                        calculation_type=calc_type,
                        field=metric,
                        old_value=old_decimal,
                        new_value=new_decimal,
                        delta=delta,
                        delta_percent=delta_percent.quantize(Decimal("0.01")),
                        impact_level=impact_level,
                    )
                )

    return impacts


# =============================================================================
# Summary Generation
# =============================================================================


def generate_delta_summary(
    deltas: list[DefinitionDelta],
    impacts: list[CalculationImpact],
) -> DeltaSummary:
    """Delta 요약 생성.

    Args:
        deltas: 정의 변경 내역
        impacts: 계산 영향

    Returns:
        Delta 요약
    """
    # 영향도별 집계
    by_impact: dict[str, int] = {
        ImpactLevel.LOW: 0,
        ImpactLevel.MEDIUM: 0,
        ImpactLevel.HIGH: 0,
        ImpactLevel.CRITICAL: 0,
    }

    for delta in deltas:
        by_impact[delta.impact_level] = by_impact.get(delta.impact_level, 0) + 1

    # 영향받은 주요 메트릭
    key_metrics_affected = []
    for impact in impacts:
        if impact.impact_level in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
            metric_name = f"{impact.calculation_type}.{impact.field}"
            if metric_name not in key_metrics_affected:
                key_metrics_affected.append(metric_name)

    # 권고사항 생성
    recommendation = None
    critical_count = by_impact.get(ImpactLevel.CRITICAL, 0)
    high_count = by_impact.get(ImpactLevel.HIGH, 0)

    if critical_count > 0:
        recommendation = (
            f"CRITICAL changes detected ({critical_count}). "
            "Full review and stakeholder approval required before proceeding."
        )
    elif high_count > 0:
        recommendation = (
            f"HIGH impact changes detected ({high_count}). "
            "Review recommended before finalizing."
        )

    return DeltaSummary(
        total_changes=len(deltas),
        by_impact_level=by_impact,
        key_metrics_affected=key_metrics_affected,
        recommendation=recommendation,
    )


# =============================================================================
# Main Function
# =============================================================================


def calculate_delta(
    old_definition: dict[str, Any],
    new_definition: dict[str, Any],
    old_version: int,
    new_version: int,
    old_results: dict[str, Any] | None = None,
    new_results: dict[str, Any] | None = None,
) -> DeltaResult:
    """전체 Delta 분석 수행.

    Args:
        old_definition: 이전 버전 정의 데이터
        new_definition: 새 버전 정의 데이터
        old_version: 이전 버전 번호
        new_version: 새 버전 번호
        old_results: 이전 계산 결과 (선택)
        new_results: 새 계산 결과 (선택)

    Returns:
        DeltaResult
    """
    # 정의 변경 계산
    deltas = calculate_definition_delta(old_definition, new_definition)

    # 계산 영향 분석 (결과가 있는 경우)
    impacts: list[CalculationImpact] = []
    if old_results and new_results:
        impacts = analyze_calculation_impact(deltas, old_results, new_results)

    # 요약 생성
    summary = generate_delta_summary(deltas, impacts)

    return DeltaResult(
        old_version=old_version,
        new_version=new_version,
        definition_deltas=deltas,
        calculation_impacts=impacts,
        summary=summary,
    )
