"""FDD Ralph Service — 2-Pass 보고서 품질 개선 오케스트레이션.

Pass 1 (Draft): build_report_ir() → Ralph Loop → Refined IR
Pass 2 (Final): checklist corrections → Ralph Loop → Final Refined IR
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ralph_session import FddRalphSession, FddRalphSessionStatus
from app.ralph.convergence import ConvergenceConfig
from app.ralph.gates.base import QualityGate
from app.ralph.gates.fdd_llm_judge_gate import FDDLLMJudgeGate
from app.ralph.gates.fdd_programmatic_gate import FDDProgrammaticGate
from app.ralph.generators.fdd_report_generator import FDDReportGenerator
from app.ralph.learning.pattern_aggregator import PatternAggregator
from app.ralph.orchestrator import LoopConfig, LoopStatus, RalphLoopOrchestrator
from app.renderers.report_builder import ReportIR, report_ir_to_dict

logger = logging.getLogger(__name__)

# PRD 로드
_PRD_PATH = Path(__file__).parent.parent / "ralph" / "prds" / "fdd_report.json"


def _load_prd() -> dict[str, Any]:
    """FDD Report PRD를 로드한다."""
    if _PRD_PATH.exists():
        return json.loads(_PRD_PATH.read_text(encoding="utf-8"))
    return {"document_type": "fdd_report", "sections": {}}


class FDDRalphService:
    """FDD 2-Pass Ralph Loop 서비스."""

    def __init__(self, db: Session) -> None:
        self._db = db

    async def run_draft_pass(
        self,
        deal_id: UUID,
        report_ir: ReportIR,
        config: dict[str, Any] | None = None,
        actor: str = "",
        llm_call=None,
    ) -> tuple[dict[str, Any], FddRalphSession]:
        """Pass 1: 초안 보고서의 텍스트 품질을 개선한다.

        Args:
            deal_id: Deal UUID
            report_ir: 분석 엔진이 생성한 원본 Report IR
            config: Ralph Loop 설정 오버라이드
            actor: 실행자 이메일
            llm_call: LLM 호출 함수 (테스트용 주입 가능)

        Returns:
            (Refined IR dict, FddRalphSession)
        """
        prd = _load_prd()
        user_config = config or {}

        convergence = ConvergenceConfig(
            pass_threshold=user_config.get("pass_threshold", 4.0),
            max_iterations_per_section=user_config.get("max_iterations_per_section", 3),
            max_cost_usd=user_config.get("max_cost_usd", 20.0),
        )

        ir_dict = report_ir_to_dict(report_ir)

        # 학습 패턴 로드
        patterns = self._load_learned_patterns("draft")

        # LLM 호출 함수
        if llm_call is None:
            llm_call = self._create_llm_call()

        # Generator 초기화
        generator = FDDReportGenerator(
            report_ir_dict=ir_dict,
            llm_call=llm_call,
            learned_patterns=patterns,
        )

        # Gates 초기화
        gates: list[QualityGate] = [
            FDDProgrammaticGate(),
            FDDLLMJudgeGate(llm_call=llm_call),
        ]

        # 세션 생성
        session = FddRalphSession(
            deal_id=deal_id,
            pass_type="draft",
            status=FddRalphSessionStatus.PLANNING,
            prd=prd,
            config=user_config,
            learned_patterns=patterns,
            created_by=actor,
        )
        self._db.add(session)
        self._db.flush()

        # Orchestrator 실행
        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=gates,
            prd=prd,
            config=LoopConfig(
                convergence=convergence,
                gate1_first=True,
                skip_gate2_on_gate1_fail=True,
            ),
        )

        # source_data: 엔진 데이터 (교차 검증용)
        source_data = self._extract_source_data(ir_dict)
        result = await orchestrator.run(source_data)

        # 세션 업데이트
        session.status = result.status.value
        session.progress = result.progress
        session.total_iterations = result.total_iterations
        session.total_cost_usd = result.total_cost_usd
        session.final_score = result.final_score
        session.section_scores = result.section_scores
        session.critical_flags = result.critical_flags
        session.error_message = "; ".join(result.errors) if result.errors else None

        # Refined IR 구성
        if result.final_artifact:
            try:
                refined_ir = json.loads(result.final_artifact)
                session.refined_ir = refined_ir
            except json.JSONDecodeError:
                session.refined_ir = ir_dict  # fallback to original
        else:
            session.refined_ir = ir_dict

        self._db.commit()
        self._db.refresh(session)

        return session.refined_ir, session

    async def run_final_pass(
        self,
        deal_id: UUID,
        report_ir: ReportIR,
        checklist_id: UUID,
        actor: str = "",
        llm_call=None,
    ) -> tuple[dict[str, Any], FddRalphSession]:
        """Pass 2: 체크리스트 수정사항을 반영하여 최종 보고서를 개선한다.

        Args:
            deal_id: Deal UUID
            report_ir: 원본 Report IR
            checklist_id: 확정된 체크리스트 ID
            actor: 실행자 이메일
            llm_call: LLM 호출 함수

        Returns:
            (Refined IR dict, FddRalphSession)
        """
        prd = _load_prd()

        convergence = ConvergenceConfig(
            pass_threshold=4.0,
            max_iterations_per_section=2,
            max_cost_usd=5.0,
        )

        ir_dict = report_ir_to_dict(report_ir)

        # 체크리스트 corrections 추출
        corrections = self._extract_checklist_corrections(checklist_id)

        # 학습 패턴 로드
        patterns = self._load_learned_patterns("final")

        # LLM 호출 함수
        if llm_call is None:
            llm_call = self._create_llm_call()

        # Generator 초기화 (corrections 전달)
        generator = FDDReportGenerator(
            report_ir_dict=ir_dict,
            llm_call=llm_call,
            checklist_corrections=corrections,
            learned_patterns=patterns,
        )

        # Gates 초기화 (corrections 전달)
        gates: list[QualityGate] = [
            FDDProgrammaticGate(checklist_corrections=corrections),
            FDDLLMJudgeGate(llm_call=llm_call),
        ]

        # 세션 생성
        session = FddRalphSession(
            deal_id=deal_id,
            pass_type="final",
            status=FddRalphSessionStatus.PLANNING,
            checklist_id=checklist_id,
            prd=prd,
            config={"max_iterations_per_section": 2, "max_cost_usd": 5.0},
            learned_patterns=patterns,
            created_by=actor,
        )
        self._db.add(session)
        self._db.flush()

        # Orchestrator 실행
        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=gates,
            prd=prd,
            config=LoopConfig(
                convergence=convergence,
                gate1_first=True,
                skip_gate2_on_gate1_fail=True,
            ),
        )

        source_data = self._extract_source_data(ir_dict)
        source_data["checklist_corrections"] = corrections
        result = await orchestrator.run(source_data)

        # 세션 업데이트
        session.status = result.status.value
        session.progress = result.progress
        session.total_iterations = result.total_iterations
        session.total_cost_usd = result.total_cost_usd
        session.final_score = result.final_score
        session.section_scores = result.section_scores
        session.critical_flags = result.critical_flags
        session.error_message = "; ".join(result.errors) if result.errors else None

        if result.final_artifact:
            try:
                refined_ir = json.loads(result.final_artifact)
                session.refined_ir = refined_ir
            except json.JSONDecodeError:
                session.refined_ir = ir_dict
        else:
            session.refined_ir = ir_dict

        self._db.commit()
        self._db.refresh(session)

        return session.refined_ir, session

    # ── Private Helpers ──────────────────────────────────────────────────

    def _load_learned_patterns(self, pass_type: str) -> list[str]:
        """과거 세션에서 학습 패턴을 로드한다."""
        try:
            aggregator = PatternAggregator(self._db)
            return aggregator.get_learned_patterns(pass_type=pass_type)
        except Exception as e:
            logger.warning("Failed to load learned patterns: %s", e)
            return []

    def _extract_checklist_corrections(self, checklist_id: UUID) -> list[dict]:
        """확정된 체크리스트에서 CORRECTED/FLAGGED 항목을 추출한다."""
        from app.models.fdd_checklist import FddChecklist

        checklist = self._db.query(FddChecklist).filter(
            FddChecklist.id == checklist_id,
        ).first()

        if not checklist:
            return []

        corrections = []
        for item in checklist.items:
            status_val = item.status.value if item.status else ""
            if status_val in ("CORRECTED", "FLAGGED"):
                corrections.append({
                    "category": item.category.value if item.category else "",
                    "title": item.title,
                    "status": status_val,
                    "auto_finding": item.auto_finding or "",
                    "auto_amount": str(item.auto_amount) if item.auto_amount else "",
                    "user_correction": item.user_correction or "",
                    "user_amount": str(item.user_amount) if item.user_amount else "",
                    "severity": item.severity.value if item.severity else "",
                })

        return corrections

    def _extract_source_data(self, ir_dict: dict) -> dict[str, Any]:
        """Report IR에서 교차 검증용 소스 데이터를 추출한다."""
        source: dict[str, Any] = {}

        for section in ir_dict.get("sections", []):
            block_type = section.get("type", "")

            if block_type == "kpi":
                kpis = section.get("kpis", [])
                for kpi in kpis:
                    label = (kpi.get("label") or "").lower()
                    if "ebitda" in label:
                        source.setdefault("qoe", {})["adjusted_ebitda"] = kpi.get("value", "")
                    elif "nwc" in label or "working" in label:
                        source.setdefault("nwc", {})["total_nwc"] = kpi.get("value", "")
                    elif "debt" in label:
                        source.setdefault("debt", {})["net_debt"] = kpi.get("value", "")

            elif block_type == "table":
                title = (section.get("title") or "").lower()
                if "qoe" in title or "earning" in title:
                    source.setdefault("qoe", {})["table_data"] = section.get("rows", [])
                elif "nwc" in title or "working" in title:
                    source.setdefault("nwc", {})["table_data"] = section.get("rows", [])
                elif "debt" in title:
                    source.setdefault("debt", {})["table_data"] = section.get("rows", [])

            elif block_type == "issue":
                source["issues"] = [
                    {"title": i.get("title", ""), "severity": i.get("severity", "")}
                    for i in section.get("issues", [])
                ]

        return source

    def _create_llm_call(self):
        """LLM 호출 함수를 생성한다."""
        async def llm_call(
            system_prompt: str,
            user_prompt: str,
            temperature: float = 0.3,
            max_tokens: int = 2048,
        ) -> str:
            try:
                from app.services.llm.routing import create_fdd_model_router

                router = create_fdd_model_router()
                if not router.available_providers:
                    raise RuntimeError("No LLM providers available")

                response = router.generate(
                    "ralph_loop",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.text
            except ImportError:
                raise RuntimeError(
                    "LLM routing module not available. "
                    "Ralph Loop requires at least one LLM provider (OpenAI/Anthropic)."
                )

        return llm_call
