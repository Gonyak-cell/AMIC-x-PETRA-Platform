"""Delta Engine Tests - 정의 버전 간 변경 분석 테스트.

EPIC-15 FDD-1501: Delta Engine 테스트.
"""

from decimal import Decimal

import pytest

from app.engines.delta_engine import (
    CalculationImpact,
    ChangeType,
    DefinitionDelta,
    DeltaResult,
    DeltaSummary,
    ImpactLevel,
    analyze_calculation_impact,
    calculate_definition_delta,
    calculate_delta,
    generate_delta_summary,
)

# =============================================================================
# DefinitionDelta Tests
# =============================================================================


class TestCalculateDefinitionDelta:
    """calculate_definition_delta tests."""

    def test_no_changes(self):
        """변경 없음."""
        old_def = {"cash": {"include": ["1110"], "exclude": []}}
        new_def = {"cash": {"include": ["1110"], "exclude": []}}

        deltas = calculate_definition_delta(old_def, new_def)
        assert len(deltas) == 0

    def test_field_added(self):
        """필드 추가."""
        old_def = {"cash": {"include": []}}
        new_def = {"cash": {"include": []}, "debt": {"include": ["2110"]}}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert deltas[0].field == "debt"
        assert deltas[0].change_type == ChangeType.ADDED
        assert deltas[0].new_value == {"include": ["2110"]}

    def test_field_removed(self):
        """필드 제거."""
        old_def = {"cash": {"include": []}, "debt": {"include": ["2110"]}}
        new_def = {"cash": {"include": []}}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert deltas[0].field == "debt"
        assert deltas[0].change_type == ChangeType.REMOVED
        assert deltas[0].old_value == {"include": ["2110"]}

    def test_field_modified(self):
        """필드 수정."""
        old_def = {"cash": {"include": ["1110"]}}
        new_def = {"cash": {"include": ["1110", "1120"]}}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert deltas[0].field == "cash"
        assert deltas[0].change_type == ChangeType.MODIFIED

    def test_multiple_changes(self):
        """다중 변경."""
        old_def = {
            "cash": {"include": ["1110"]},
            "debt": {"include": ["2110"]},
        }
        new_def = {
            "cash": {"include": ["1110", "1120"]},  # Modified
            "nwc": {"include": []},  # Added
            # debt removed
        }

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 3
        change_types = {d.change_type for d in deltas}
        assert ChangeType.ADDED in change_types
        assert ChangeType.REMOVED in change_types
        assert ChangeType.MODIFIED in change_types

    def test_list_item_added(self):
        """리스트 항목 추가."""
        old_def = {"debt_like": [{"item": "A", "category": "lease"}]}
        new_def = {
            "debt_like": [
                {"item": "A", "category": "lease"},
                {"item": "B", "category": "pension"},
            ]
        }

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert "1 items added" in deltas[0].description

    def test_list_item_removed(self):
        """리스트 항목 제거."""
        old_def = {
            "debt_like": [
                {"item": "A", "category": "lease"},
                {"item": "B", "category": "pension"},
            ]
        }
        new_def = {"debt_like": [{"item": "A", "category": "lease"}]}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert "1 items removed" in deltas[0].description


# =============================================================================
# Impact Level Tests
# =============================================================================


class TestImpactLevel:
    """Impact level calculation tests."""

    def test_critical_field_change(self):
        """핵심 필드 변경 - MEDIUM 이상 (리스트 4개 추가)."""
        old_def = {"cash": {"include": []}}
        new_def = {"cash": {"include": ["1110", "1120", "1130", "1140"]}}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        # 4개 항목 변경은 MEDIUM (>3이면 HIGH)
        assert deltas[0].impact_level in (ImpactLevel.MEDIUM, ImpactLevel.HIGH, ImpactLevel.CRITICAL)

    def test_numeric_change_low(self):
        """숫자 변경 < 1% - LOW."""
        old_def = {"value": "100"}
        new_def = {"value": "100.5"}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert deltas[0].impact_level == ImpactLevel.LOW

    def test_numeric_change_medium(self):
        """숫자 변경 1-5% - MEDIUM."""
        old_def = {"value": "100"}
        new_def = {"value": "103"}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert deltas[0].impact_level == ImpactLevel.MEDIUM

    def test_numeric_change_high(self):
        """숫자 변경 5-20% - HIGH."""
        old_def = {"value": "100"}
        new_def = {"value": "115"}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert deltas[0].impact_level == ImpactLevel.HIGH

    def test_numeric_change_critical(self):
        """숫자 변경 > 20% - CRITICAL."""
        old_def = {"value": "100"}
        new_def = {"value": "150"}

        deltas = calculate_definition_delta(old_def, new_def)

        assert len(deltas) == 1
        assert deltas[0].impact_level == ImpactLevel.CRITICAL


# =============================================================================
# Calculation Impact Tests
# =============================================================================


class TestAnalyzeCalculationImpact:
    """analyze_calculation_impact tests."""

    def test_no_impact(self):
        """영향 없음."""
        deltas: list[DefinitionDelta] = []
        old_results = {"qoe": {"adjusted_ebitda": "10000"}}
        new_results = {"qoe": {"adjusted_ebitda": "10000"}}

        impacts = analyze_calculation_impact(deltas, old_results, new_results)
        assert len(impacts) == 0

    def test_qoe_impact(self):
        """QoE 영향."""
        deltas: list[DefinitionDelta] = []
        old_results = {"qoe": {"adjusted_ebitda": "10000"}}
        new_results = {"qoe": {"adjusted_ebitda": "12500"}}  # 25% change

        impacts = analyze_calculation_impact(deltas, old_results, new_results)

        assert len(impacts) == 1
        impact = impacts[0]
        assert impact.calculation_type == "qoe"
        assert impact.field == "adjusted_ebitda"
        assert impact.old_value == Decimal("10000")
        assert impact.new_value == Decimal("12500")
        assert impact.delta == Decimal("2500")
        assert impact.delta_percent == Decimal("25.00")
        assert impact.impact_level == ImpactLevel.CRITICAL  # >20%

    def test_nwc_impact(self):
        """NWC 영향."""
        deltas: list[DefinitionDelta] = []
        old_results = {"nwc": {"net_working_capital": "5000"}}
        new_results = {"nwc": {"net_working_capital": "5200"}}

        impacts = analyze_calculation_impact(deltas, old_results, new_results)

        assert len(impacts) == 1
        impact = impacts[0]
        assert impact.calculation_type == "nwc"
        assert impact.delta_percent == Decimal("4.00")
        assert impact.impact_level == ImpactLevel.MEDIUM

    def test_debt_impact(self):
        """Net Debt 영향."""
        deltas: list[DefinitionDelta] = []
        old_results = {"debt": {"net_debt": "8000"}}
        new_results = {"debt": {"net_debt": "8800"}}

        impacts = analyze_calculation_impact(deltas, old_results, new_results)

        assert len(impacts) == 1
        assert impacts[0].calculation_type == "debt"
        assert impacts[0].impact_level == ImpactLevel.HIGH

    def test_multiple_impacts(self):
        """다중 계산 영향."""
        deltas: list[DefinitionDelta] = []
        old_results = {
            "qoe": {"adjusted_ebitda": "10000"},
            "nwc": {"net_working_capital": "5000"},
            "debt": {"net_debt": "8000"},
        }
        new_results = {
            "qoe": {"adjusted_ebitda": "12000"},
            "nwc": {"net_working_capital": "5500"},
            "debt": {"net_debt": "7500"},
        }

        impacts = analyze_calculation_impact(deltas, old_results, new_results)

        assert len(impacts) == 3
        calc_types = {i.calculation_type for i in impacts}
        assert calc_types == {"qoe", "nwc", "debt"}


# =============================================================================
# Delta Summary Tests
# =============================================================================


class TestGenerateDeltaSummary:
    """generate_delta_summary tests."""

    def test_empty_summary(self):
        """빈 요약."""
        summary = generate_delta_summary([], [])

        assert summary.total_changes == 0
        assert summary.recommendation is None

    def test_summary_with_critical(self):
        """CRITICAL 변경 포함 요약."""
        deltas = [
            DefinitionDelta(
                field="cash",
                change_type=ChangeType.MODIFIED,
                old_value={},
                new_value={},
                impact_level=ImpactLevel.CRITICAL,
            ),
        ]
        impacts: list[CalculationImpact] = []

        summary = generate_delta_summary(deltas, impacts)

        assert summary.total_changes == 1
        assert summary.by_impact_level[ImpactLevel.CRITICAL] == 1
        assert "CRITICAL" in summary.recommendation
        assert "approval required" in summary.recommendation

    def test_summary_with_high(self):
        """HIGH 변경 포함 요약."""
        deltas = [
            DefinitionDelta(
                field="debt",
                change_type=ChangeType.ADDED,
                old_value=None,
                new_value={},
                impact_level=ImpactLevel.HIGH,
            ),
        ]
        impacts: list[CalculationImpact] = []

        summary = generate_delta_summary(deltas, impacts)

        assert summary.by_impact_level[ImpactLevel.HIGH] == 1
        assert "HIGH impact" in summary.recommendation

    def test_summary_key_metrics(self):
        """주요 메트릭 영향."""
        deltas: list[DefinitionDelta] = []
        impacts = [
            CalculationImpact(
                calculation_type="qoe",
                field="adjusted_ebitda",
                old_value=Decimal("10000"),
                new_value=Decimal("12500"),
                delta=Decimal("2500"),
                delta_percent=Decimal("25.00"),
                impact_level=ImpactLevel.CRITICAL,
            ),
        ]

        summary = generate_delta_summary(deltas, impacts)

        assert "qoe.adjusted_ebitda" in summary.key_metrics_affected


# =============================================================================
# Full Delta Calculation Tests
# =============================================================================


class TestCalculateDelta:
    """calculate_delta full pipeline tests."""

    def test_calculate_delta_basic(self):
        """기본 Delta 계산."""
        old_def = {"cash": {"include": ["1110"]}}
        new_def = {"cash": {"include": ["1110", "1120"]}}

        result = calculate_delta(
            old_definition=old_def,
            new_definition=new_def,
            old_version=1,
            new_version=2,
        )

        assert result.old_version == 1
        assert result.new_version == 2
        assert len(result.definition_deltas) == 1
        assert result.summary.total_changes == 1

    def test_calculate_delta_with_results(self):
        """계산 결과 포함 Delta."""
        old_def = {"cash": {"include": []}}
        new_def = {"cash": {"include": ["1110"]}}
        old_results = {"qoe": {"adjusted_ebitda": "10000"}}
        new_results = {"qoe": {"adjusted_ebitda": "12000"}}

        result = calculate_delta(
            old_definition=old_def,
            new_definition=new_def,
            old_version=1,
            new_version=2,
            old_results=old_results,
            new_results=new_results,
        )

        assert len(result.definition_deltas) == 1
        assert len(result.calculation_impacts) == 1

    def test_calculate_delta_no_changes(self):
        """변경 없는 Delta."""
        old_def = {"cash": {"include": ["1110"]}}
        new_def = {"cash": {"include": ["1110"]}}

        result = calculate_delta(
            old_definition=old_def,
            new_definition=new_def,
            old_version=1,
            new_version=2,
        )

        assert len(result.definition_deltas) == 0
        assert result.summary.total_changes == 0

    def test_calculate_delta_complex(self):
        """복잡한 Delta 시나리오."""
        old_def = {
            "cash": {"include": ["1110"], "exclude": []},
            "debt": {"include": ["2110"], "exclude": []},
            "nwc": {"include": ["1200", "1300"], "exclude": ["1310"]},
            "target_nwc": {"method": "6M_AVG", "value": None},
            "debt_like": [
                {"item": "Lease liability", "category": "lease", "rationale": "IFRS16"},
            ],
        }
        new_def = {
            "cash": {"include": ["1110", "1120"], "exclude": []},  # Modified
            "debt": {"include": ["2110", "2120"], "exclude": []},  # Modified
            "nwc": {"include": ["1200", "1300"], "exclude": []},  # Modified
            "target_nwc": {"method": "12M_AVG", "value": "5000"},  # Modified
            "debt_like": [
                {"item": "Lease liability", "category": "lease", "rationale": "IFRS16"},
                {"item": "Pension", "category": "pension", "rationale": "PBO"},  # Added
            ],
            "cash_like": [{"item": "Restricted cash", "category": "restricted"}],  # Added
        }
        old_results = {
            "qoe": {"adjusted_ebitda": "10000", "total_adjustments": "500"},
            "nwc": {"net_working_capital": "3000", "target_nwc": "3500"},
            "debt": {"net_debt": "8000", "gross_debt": "10000"},
        }
        new_results = {
            "qoe": {"adjusted_ebitda": "10500", "total_adjustments": "600"},
            "nwc": {"net_working_capital": "3200", "target_nwc": "5000"},
            "debt": {"net_debt": "8500", "gross_debt": "11000"},
        }

        result = calculate_delta(
            old_definition=old_def,
            new_definition=new_def,
            old_version=1,
            new_version=2,
            old_results=old_results,
            new_results=new_results,
        )

        assert len(result.definition_deltas) >= 4  # 여러 필드 변경
        assert len(result.calculation_impacts) >= 3  # 여러 메트릭 영향
        assert result.summary.total_changes >= 4


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_definitions(self):
        """빈 정의."""
        result = calculate_delta({}, {}, 1, 2)
        assert len(result.definition_deltas) == 0

    def test_none_values(self):
        """None 값 처리."""
        old_def = {"field": None}
        new_def = {"field": "value"}

        deltas = calculate_definition_delta(old_def, new_def)
        assert len(deltas) == 1
        assert deltas[0].old_value is None

    def test_nested_dict_change(self):
        """중첩 딕셔너리 변경."""
        old_def = {"nested": {"level1": {"level2": "old"}}}
        new_def = {"nested": {"level1": {"level2": "new"}}}

        deltas = calculate_definition_delta(old_def, new_def)
        assert len(deltas) == 1

    def test_zero_base_percentage(self):
        """0에서 변경 시 퍼센트 계산."""
        old_results = {"qoe": {"adjusted_ebitda": "0"}}
        new_results = {"qoe": {"adjusted_ebitda": "1000"}}

        impacts = analyze_calculation_impact([], old_results, new_results)

        assert len(impacts) == 1
        assert impacts[0].delta_percent == Decimal("100.00")
