"""Tests for Ralph Loop core modules (ported from deal-mgmt).

Convergence, ProgressTracker, GateResult 코어 모듈의 정상 동작을 검증한다.
"""

import pytest

from app.ralph.convergence import (
    ConvergenceChecker,
    ConvergenceConfig,
    ConvergenceVerdict,
)
from app.ralph.gates.base import DimensionScore, GateResult, GateVerdict
from app.ralph.progress_tracker import ProgressTracker

# ── Convergence Tests ─────────────────────────────────────────────


class TestConvergenceConfig:
    def test_defaults(self):
        cfg = ConvergenceConfig()
        assert cfg.pass_threshold == 4.0
        assert cfg.max_iterations_per_section == 3
        assert cfg.max_cost_usd == 20.0
        assert cfg.improvement_threshold == 0.5

    def test_custom_values(self):
        cfg = ConvergenceConfig(pass_threshold=3.5, max_iterations_per_section=5)
        assert cfg.pass_threshold == 3.5
        assert cfg.max_iterations_per_section == 5


class TestConvergenceChecker:
    def setup_method(self):
        self.checker = ConvergenceChecker(ConvergenceConfig())

    def _make_gate_result(
        self,
        score: float,
        passed: bool = False,
        critical_flags: list[str] | None = None,
    ) -> GateResult:
        return GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS if passed else GateVerdict.CONDITIONAL_PASS,
            weighted_score=score,
            critical_flags=critical_flags or [],
        )

    def test_passed_verdict(self):
        tracker = ProgressTracker()
        gr = self._make_gate_result(4.5, passed=True)
        verdict = self.checker.check_section("test", gr, tracker)
        assert verdict.converged is True
        assert verdict.reason == "passed"

    def test_critical_flag_verdict(self):
        tracker = ProgressTracker()
        gr = self._make_gate_result(
            4.5, passed=True, critical_flags=["NUMERICAL_MISMATCH"]
        )
        verdict = self.checker.check_section("test", gr, tracker)
        assert verdict.converged is True
        assert verdict.reason == "critical_flag"

    def test_budget_exceeded_verdict(self):
        tracker = ProgressTracker()
        tracker._total_cost_usd = 25.0  # Exceed budget
        gr = self._make_gate_result(3.5)
        verdict = self.checker.check_section("test", gr, tracker)
        assert verdict.converged is True
        assert verdict.reason == "budget_exceeded"

    def test_max_iterations_verdict(self):
        tracker = ProgressTracker()
        # Record 3 iterations to hit max
        for i in range(3):
            tracker.record("test", i + 1, self._make_gate_result(3.0 + i * 0.3))
        gr = self._make_gate_result(3.5)
        verdict = self.checker.check_section("test", gr, tracker)
        assert verdict.converged is True
        assert verdict.reason == "max_iterations"

    def test_deteriorated_verdict(self):
        tracker = ProgressTracker()
        tracker.record("test", 1, self._make_gate_result(3.5))
        tracker.record("test", 2, self._make_gate_result(3.0))
        gr = self._make_gate_result(3.0)
        verdict = self.checker.check_section("test", gr, tracker)
        assert verdict.converged is True
        assert verdict.reason == "deteriorated"

    def test_continue_verdict(self):
        tracker = ProgressTracker()
        gr = self._make_gate_result(3.0)
        verdict = self.checker.check_section("test", gr, tracker)
        assert verdict.converged is False


# ── ProgressTracker Tests ─────────────────────────────────────────


class TestProgressTracker:
    def _make_gate_result(
        self,
        score: float,
        issues: list[str] | None = None,
        suggestions: list[str] | None = None,
    ) -> GateResult:
        return GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS if score >= 4.0 else GateVerdict.CONDITIONAL_PASS,
            weighted_score=score,
            issues=issues or [],
            suggestions=suggestions or [],
        )

    def test_initial_state(self):
        tracker = ProgressTracker()
        d = tracker.to_dict()
        assert d["records"] == {}
        assert d["total_cost_usd"] == 0.0

    def test_record_and_get_score_history(self):
        tracker = ProgressTracker()
        tracker.record("sec_1", 1, self._make_gate_result(3.5))
        tracker.record("sec_1", 2, self._make_gate_result(4.1))

        history = tracker.get_score_history("sec_1")
        assert len(history) == 2
        assert history[0] == 3.5
        assert history[1] == 4.1

    def test_mark_passed(self):
        tracker = ProgressTracker()
        tracker.record("sec_1", 1, self._make_gate_result(4.5))
        tracker.mark_passed("sec_1")
        assert tracker.is_section_passed("sec_1") is True

    def test_get_feedback(self):
        tracker = ProgressTracker()
        tracker.record(
            "sec_1",
            1,
            self._make_gate_result(
                3.0, issues=["Fix placeholder"], suggestions=["Add evidence"]
            ),
        )
        feedback = tracker.get_feedback("sec_1")
        assert "Fix placeholder" in feedback
        assert "Add evidence" in feedback

    def test_serialization_roundtrip(self):
        tracker = ProgressTracker()
        tracker.record("sec_1", 1, self._make_gate_result(4.0))
        d = tracker.to_dict()
        restored = ProgressTracker.from_dict(d)
        assert restored.get_score_history("sec_1") == [4.0]

    def test_total_cost_tracking(self):
        tracker = ProgressTracker()
        gr = GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS,
            weighted_score=4.0,
            cost_usd=0.05,
        )
        tracker.record("sec_1", 1, gr)
        tracker.record("sec_1", 2, gr)
        assert tracker.total_cost_usd == pytest.approx(0.10, abs=0.001)

    def test_get_all_critical_flags(self):
        tracker = ProgressTracker()
        gr = GateResult(
            gate_name="test",
            verdict=GateVerdict.FAIL,
            weighted_score=2.0,
            critical_flags=["NUMERICAL_MISMATCH"],
        )
        tracker.record("sec_1", 1, gr)
        flags = tracker.get_all_critical_flags()
        assert "NUMERICAL_MISMATCH" in flags


# ── GateResult Tests ──────────────────────────────────────────────


class TestGateResult:
    def test_passed_property(self):
        result = GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS,
            weighted_score=4.5,
        )
        assert result.passed is True

    def test_not_passed_with_critical_flags(self):
        result = GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS,
            weighted_score=4.5,
            critical_flags=["NUMERICAL_MISMATCH"],
        )
        assert result.passed is False

    def test_not_passed_with_fail_verdict(self):
        result = GateResult(
            gate_name="test",
            verdict=GateVerdict.FAIL,
            weighted_score=2.5,
        )
        assert result.passed is False


class TestDimensionScore:
    def test_frozen_dataclass(self):
        ds = DimensionScore(
            name="completeness",
            label="완전성",
            score=4.5,
            weight=0.2,
            feedback="Good coverage",
        )
        assert ds.score == 4.5
        assert ds.weight == 0.2
        with pytest.raises(AttributeError):
            ds.score = 3.0  # type: ignore[misc]
