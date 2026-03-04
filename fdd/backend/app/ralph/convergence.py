"""수렴 판정 — Ralph Loop 반복 중단 조건."""

from __future__ import annotations

from dataclasses import dataclass

from app.ralph.gates.base import GateResult
from app.ralph.progress_tracker import ProgressTracker


@dataclass
class ConvergenceConfig:
    """수렴 조건 설정."""

    pass_threshold: float = 4.0  # 5점 만점 중 통과 기준
    improvement_threshold: float = 0.5  # 이 이하 개선시 수렴으로 판정
    max_iterations_per_section: int = 3  # 섹션당 최대 반복 횟수
    max_iterations_total: int = 30  # 전체 최대 반복 횟수
    max_cost_usd: float = 20.0  # 비용 한도


@dataclass
class ConvergenceVerdict:
    """수렴 판정 결과."""

    converged: bool
    reason: str  # "passed" | "deteriorated" | "diminishing_returns" | "max_iterations" | "budget_exceeded" | "critical_flag"


class ConvergenceChecker:
    """Ralph Loop 수렴 조건을 판정한다.

    수렴 조건 (하나라도 충족 시 해당 섹션 반복 중단):
    1. 모든 게이트 결과가 pass_threshold 이상 → "passed"
    2. 반복 간 점수 개선이 improvement_threshold 미만 → "diminishing_returns"
    3. 섹션당 반복 횟수 초과 → "max_iterations"
    4. 총 비용 초과 → "budget_exceeded"
    5. CRITICAL Red Flag 탐지 → "critical_flag" (인간 검토 필요)
    """

    def __init__(self, config: ConvergenceConfig | None = None) -> None:
        self._config = config or ConvergenceConfig()

    def check_section(
        self,
        section_id: str,
        gate_result: GateResult,
        tracker: ProgressTracker,
    ) -> ConvergenceVerdict:
        """단일 섹션에 대한 수렴 판정."""
        cfg = self._config

        # 1. CRITICAL Red Flag → 즉시 중단 (인간 검토)
        if gate_result.critical_flags:
            return ConvergenceVerdict(
                converged=True,
                reason="critical_flag",
            )

        # 2. 통과 기준 달성
        if gate_result.passed and gate_result.weighted_score >= cfg.pass_threshold:
            return ConvergenceVerdict(converged=True, reason="passed")

        # 3. 비용 초과
        if tracker.total_cost_usd >= cfg.max_cost_usd:
            return ConvergenceVerdict(converged=True, reason="budget_exceeded")

        # 4. 반복 횟수 초과
        history = tracker.get_score_history(section_id)
        if len(history) >= cfg.max_iterations_per_section:
            return ConvergenceVerdict(converged=True, reason="max_iterations")

        # 5. 점수 하락 또는 수확 체감
        if len(history) >= 2:
            improvement = history[-1] - history[-2]
            if improvement < 0:
                return ConvergenceVerdict(converged=True, reason="deteriorated")
            if improvement < cfg.improvement_threshold:
                return ConvergenceVerdict(converged=True, reason="diminishing_returns")

        return ConvergenceVerdict(converged=False, reason="")

    def check_total_budget(self, tracker: ProgressTracker) -> bool:
        """총 비용이 한도를 초과했는지 확인."""
        return tracker.total_cost_usd >= self._config.max_cost_usd
