"""Ralph Loop 오케스트레이터 — 3단계 반복 개선 아키텍처.

Phase 1: 구조 기획 (아웃라인 생성)
Phase 2: 섹션별 생성-평가 (섹션당 반복)
Phase 3: 통합 검증 (최종 조합)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol

from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig
from app.ralph.gates.base import GateResult, QualityGate
from app.ralph.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


# ── 프로토콜 ──────────────────────────────────────────────────────────────────


class DocumentGenerator(Protocol):
    """문서 생성기 인터페이스.

    FDD Report IR Generator 등이 이 인터페이스를 구현한다.
    """

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict[str, Any],
        source_data: dict[str, Any],
        feedback: list[str] | None = None,
    ) -> str:
        """섹션 콘텐츠를 생성하고 결과를 반환한다."""
        ...

    async def generate_outline(
        self,
        source_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """전체 문서 아웃라인(섹션 목록)을 생성한다."""
        ...

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str,
    ) -> str:
        """개별 섹션 산출물을 하나의 최종 문서로 조합한다."""
        ...


# ── 결과 모델 ─────────────────────────────────────────────────────────────────


class LoopStatus(StrEnum):
    PLANNING = "PLANNING"         # Phase 1: 구조 기획 중
    GENERATING = "GENERATING"     # Phase 2: 섹션별 생성-평가 중
    VALIDATING = "VALIDATING"     # Phase 3: 통합 검증 중
    COMPLETED = "COMPLETED"       # 완료
    FAILED = "FAILED"             # 실패
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"  # 비용 초과


@dataclass
class LoopResult:
    """Ralph Loop 최종 결과."""

    session_id: str
    status: LoopStatus
    output_path: str | None = None
    final_artifact: str | None = None  # assemble_document 결과 (JSON 문자열)
    total_iterations: int = 0
    total_cost_usd: float = 0.0
    final_score: float = 0.0
    section_scores: dict[str, float] = field(default_factory=dict)
    progress: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    critical_flags: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


@dataclass
class LoopConfig:
    """Ralph Loop 설정."""

    convergence: ConvergenceConfig = field(default_factory=ConvergenceConfig)
    gate1_first: bool = True              # Gate 1 먼저 실행 (비용 최적화)
    skip_gate2_on_gate1_fail: bool = True  # Gate 1 실패시 Gate 2 건너뜀
    output_dir: str = ""                  # 최종 출력 디렉토리


# ── 오케스트레이터 ─────────────────────────────────────────────────────────────


class RalphLoopOrchestrator:
    """Ralph Loop 3단계 오케스트레이터.

    사용법::

        orchestrator = RalphLoopOrchestrator(
            generator=FDDReportGenerator(...),
            gates=[FDDProgrammaticGate(), FDDLLMJudgeGate(...)],
            prd=load_prd("fdd_report"),
        )
        result = await orchestrator.run(source_data)
    """

    def __init__(
        self,
        generator: DocumentGenerator,
        gates: list[QualityGate],
        prd: dict[str, Any],
        config: LoopConfig | None = None,
    ) -> None:
        self._generator = generator
        self._gates = gates
        self._prd = prd
        self._config = config or LoopConfig()
        self._tracker = ProgressTracker()
        self._convergence = ConvergenceChecker(self._config.convergence)
        self._session_id = str(uuid.uuid4())
        self._total_iterations = 0

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def progress(self) -> ProgressTracker:
        return self._tracker

    async def run(self, source_data: dict[str, Any]) -> LoopResult:
        """3단계 Ralph Loop를 실행한다."""
        started = datetime.now(timezone.utc).isoformat()
        errors: list[str] = []
        critical_flags: list[str] = []

        try:
            # Phase 1: 구조 기획
            logger.info("[Ralph Loop %s] Phase 1: 구조 기획 시작", self._session_id[:8])
            outline = await self._phase1_plan(source_data)

            # Phase 2: 섹션별 생성-평가
            logger.info("[Ralph Loop %s] Phase 2: 섹션별 생성-평가 시작 (%d 섹션)", self._session_id[:8], len(outline))
            section_artifacts = await self._phase2_iterate(outline, source_data)

            # Phase 3: 통합 검증
            logger.info("[Ralph Loop %s] Phase 3: 통합 검증 시작", self._session_id[:8])
            final_artifact = await self._phase3_validate(section_artifacts, source_data)
            output_path = final_artifact

            # 최종 결과 집계
            section_scores = {}
            for sid in [s.get("id", "") for s in outline]:
                history = self._tracker.get_score_history(sid)
                section_scores[sid] = history[-1] if history else 0.0

            critical_flags.extend(self._tracker.get_all_critical_flags())

            final_score = sum(section_scores.values()) / max(len(section_scores), 1)

            status = LoopStatus.COMPLETED
            if critical_flags:
                status = LoopStatus.FAILED

            return LoopResult(
                session_id=self._session_id,
                status=status,
                output_path=output_path,
                final_artifact=final_artifact,
                total_iterations=self._total_iterations,
                total_cost_usd=self._tracker.total_cost_usd,
                final_score=round(final_score, 3),
                section_scores=section_scores,
                progress=self._tracker.to_dict(),
                errors=errors,
                critical_flags=critical_flags,
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as exc:
            logger.exception("[Ralph Loop %s] 실행 실패", self._session_id[:8])
            return LoopResult(
                session_id=self._session_id,
                status=LoopStatus.FAILED,
                total_iterations=self._total_iterations,
                total_cost_usd=self._tracker.total_cost_usd,
                progress=self._tracker.to_dict(),
                errors=[str(exc)],
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

    # ── Phase 1: 구조 기획 ──────────────────────────────────────────────────

    async def _phase1_plan(self, source_data: dict[str, Any]) -> list[dict[str, Any]]:
        """전체 문서 아웃라인을 생성한다."""
        outline = await self._generator.generate_outline(source_data)
        return outline

    # ── Phase 2: 섹션별 생성-평가 ────────────────────────────────────────────

    async def _phase2_iterate(
        self,
        outline: list[dict[str, Any]],
        source_data: dict[str, Any],
    ) -> dict[str, str]:
        """각 섹션을 반복 개선한다."""
        section_artifacts: dict[str, str] = {}

        for section in outline:
            sid = section.get("id", "")
            if self._tracker.is_section_passed(sid):
                continue

            if self._convergence.check_total_budget(self._tracker):
                logger.warning("[Ralph Loop] 비용 한도 초과, 남은 섹션 건너뜀")
                break

            artifact_path = await self._iterate_section(sid, section, source_data)
            if artifact_path:
                section_artifacts[sid] = artifact_path

        return section_artifacts

    async def _iterate_section(
        self,
        section_id: str,
        section_criteria: dict[str, Any],
        source_data: dict[str, Any],
    ) -> str | None:
        """단일 섹션에 대해 생성-평가를 반복한다."""
        max_iter = self._config.convergence.max_iterations_per_section
        artifact_path: str | None = None

        for iteration in range(max_iter):
            self._total_iterations += 1

            # Fresh Context: 이전 반복의 피드백만 전달
            feedback = self._tracker.get_feedback(section_id)

            # 생성
            artifact_path = await self._generator.generate_section(
                section_id=section_id,
                section_criteria=section_criteria,
                source_data=source_data,
                feedback=feedback,
            )

            # 품질 게이트 평가
            gate_results: list[GateResult] = []
            for i, gate in enumerate(self._gates):
                # Gate 1 실패시 Gate 2 건너뜀 (비용 최적화)
                if (
                    i > 0
                    and self._config.skip_gate2_on_gate1_fail
                    and gate_results
                    and not gate_results[-1].passed
                ):
                    break

                result = await gate.evaluate(
                    artifact_path=artifact_path,
                    prd_section=section_criteria,
                    source_data=source_data,
                )
                gate_results.append(result)

            # 기록
            self._tracker.record(section_id, iteration, *gate_results)

            # 수렴 판정 (마지막 게이트 결과 기준)
            last_result = gate_results[-1] if gate_results else None
            if last_result:
                verdict = self._convergence.check_section(
                    section_id, last_result, self._tracker,
                )
                if verdict.converged:
                    logger.info(
                        "[Ralph Loop] 섹션 %s 수렴 (사유: %s, 반복: %d, 점수: %.2f)",
                        section_id, verdict.reason, iteration + 1,
                        last_result.weighted_score,
                    )
                    if verdict.reason == "passed":
                        self._tracker.mark_passed(section_id)
                    break

        return artifact_path

    # ── Phase 3: 통합 검증 ──────────────────────────────────────────────────

    async def _phase3_validate(
        self,
        section_artifacts: dict[str, str],
        source_data: dict[str, Any],
    ) -> str | None:
        """전체 문서를 조합하고 통합 검증한다."""
        if not section_artifacts:
            return None

        output_path = await self._generator.assemble_document(
            section_artifacts=section_artifacts,
            output_path=self._config.output_dir or "",
        )
        return output_path
