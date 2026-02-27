"""Ralph Loop 진행 상태 추적기 — 반복별 점수, 피드백, 비용 기록."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.ralph.gates.base import GateResult


@dataclass
class IterationRecord:
    """단일 반복의 기록."""

    iteration: int
    section_id: str
    timestamp: str
    gate_results: list[dict] = field(default_factory=list)
    weighted_score: float = 0.0
    passed: bool = False
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "section_id": self.section_id,
            "timestamp": self.timestamp,
            "gate_results": self.gate_results,
            "weighted_score": self.weighted_score,
            "passed": self.passed,
            "cost_usd": self.cost_usd,
        }


class ProgressTracker:
    """Ralph Loop 진행 상태를 추적한다.

    - 섹션별 반복 기록 (점수 추이, 피드백, 비용)
    - 수렴 판정을 위한 이전 반복 피드백 제공
    - DB JSONB에 직렬화 가능
    """

    def __init__(self) -> None:
        self._records: dict[str, list[IterationRecord]] = {}
        self._passed_sections: set[str] = set()
        self._total_cost_usd: float = 0.0

    def record(
        self,
        section_id: str,
        iteration: int,
        *gate_results: GateResult,
    ) -> None:
        """반복 결과를 기록한다."""
        gate_dicts = []
        cost = 0.0
        best_score = 0.0

        for gr in gate_results:
            gate_dicts.append({
                "gate_name": gr.gate_name,
                "verdict": gr.verdict,
                "weighted_score": gr.weighted_score,
                "issues": gr.issues,
                "suggestions": gr.suggestions,
                "critical_flags": gr.critical_flags,
                "cost_usd": gr.cost_usd,
                "duration_ms": gr.duration_ms,
                "dimensions": [
                    {"name": d.name, "label": d.label, "score": d.score, "weight": d.weight, "feedback": d.feedback}
                    for d in gr.dimensions
                ],
            })
            cost += gr.cost_usd
            best_score = max(best_score, gr.weighted_score)

        rec = IterationRecord(
            iteration=iteration,
            section_id=section_id,
            timestamp=datetime.now(UTC).isoformat(),
            gate_results=gate_dicts,
            weighted_score=best_score,
            passed=all(gr.passed for gr in gate_results),
            cost_usd=cost,
        )

        self._records.setdefault(section_id, []).append(rec)
        self._total_cost_usd += cost

    def mark_passed(self, section_id: str) -> None:
        self._passed_sections.add(section_id)

    def is_section_passed(self, section_id: str) -> bool:
        return section_id in self._passed_sections

    def get_feedback(self, section_id: str) -> list[str]:
        """이전 반복들의 피드백을 수집한다 (Fresh Context용)."""
        records = self._records.get(section_id, [])
        if not records:
            return []
        # 가장 최근 반복의 피드백만 전달 (context 최소화)
        last = records[-1]
        feedback: list[str] = []
        for gr in last.gate_results:
            feedback.extend(gr.get("issues", []))
            feedback.extend(gr.get("suggestions", []))
        return feedback

    def get_score_history(self, section_id: str) -> list[float]:
        """섹션의 점수 추이를 반환한다 (수렴 판정용)."""
        return [r.weighted_score for r in self._records.get(section_id, [])]

    def get_all_critical_flags(self) -> list[str]:
        """모든 섹션의 critical_flags를 수집한다."""
        flags: list[str] = []
        for recs in self._records.values():
            for rec in recs:
                for gr in rec.gate_results:
                    flags.extend(gr.get("critical_flags", []))
        return flags

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost_usd

    @property
    def passed_count(self) -> int:
        return len(self._passed_sections)

    def to_dict(self) -> dict:
        """DB JSONB 직렬화."""
        return {
            "records": {
                sid: [r.to_dict() for r in recs]
                for sid, recs in self._records.items()
            },
            "passed_sections": sorted(self._passed_sections),
            "total_cost_usd": self._total_cost_usd,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProgressTracker:
        """DB JSONB에서 복원."""
        tracker = cls()
        for sid, recs in data.get("records", {}).items():
            tracker._records[sid] = [
                IterationRecord(**{k: v for k, v in r.items()})
                for r in recs
            ]
        tracker._passed_sections = set(data.get("passed_sections", []))
        tracker._total_cost_usd = data.get("total_cost_usd", 0.0)
        return tracker
