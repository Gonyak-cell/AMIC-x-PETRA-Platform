"""LDD 7단계 멀티 LLM 파이프라인 오케스트레이터.

기존 LDDDocumentGenerator/LDDSectionAnalyzer를 확장하여
4개 멀티 LLM 구간(Stage 3/4/5/7)을 통합 조율한다.

멀티 LLM 미활성화 시 기존 단일 LLM 워크플로우로 폴백.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig
from app.ralph.parsers.base import ParsedFile

logger = logging.getLogger(__name__)


# ── 파이프라인 결과 ──────────────────────────────────────────────

@dataclass
class StageProgress:
    """개별 Stage 진행 상태."""

    stage: int
    name: str
    status: str = "pending"  # pending | running | completed | skipped
    progress_pct: int = 0


@dataclass
class PipelineResult:
    """10단계 파이프라인 전체 결과."""

    sections: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    executive_summary: str = ""
    dual_risk_summary: dict[str, Any] | None = None
    gap_detection: dict[str, Any] | None = None
    jurisdiction_analysis: dict[str, Any] | None = None
    narrative_sections: dict[str, list[dict]] | None = None
    appendices: dict[str, Any] | None = None
    qa_result: dict[str, Any] | None = None
    guardrail_result: dict[str, Any] | None = None
    cost_usd: float = 0.0
    stages: list[dict[str, Any]] = field(default_factory=list)


# ── 메인 파이프라인 ──────────────────────────────────────────────

class LDDMultiLLMPipeline:
    """LDD 10단계 멀티 LLM 파이프라인 오케스트레이터.

    기존 Ralph Loop과 독립적으로 실행.
    create_ldd_report_from_vdr() 안에서 호출.
    """

    def __init__(
        self,
        llm_client,
        router,
        config: LDDPipelineConfig,
        source_map: dict[str, list[ParsedFile]] | None = None,
        sections_config: list[dict] | None = None,
        learned_patterns: list[str] | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._router = router
        self._config = config
        self._source_map = source_map or {}
        self._sections_config = sections_config or []
        self._learned_patterns = learned_patterns or []
        self._stages: list[StageProgress] = [
            StageProgress(1, "문서 분류"),
            StageProgress(2, "조항 추출"),
            StageProgress(3, "듀얼 리스크 분석"),
            StageProgress(4, "누락 탐지"),
            StageProgress(5, "관할권 교차 분석"),
            StageProgress(6, "6블록 서술 생성"),
            StageProgress(7, "법률 인용 검증"),
            StageProgress(8, "별첨 데이터 수집"),
            StageProgress(9, "레포트 생성"),
            StageProgress(10, "최종 QA"),
        ]

    async def run(
        self,
        vdr_document_names: list[str] | None = None,
    ) -> PipelineResult:
        """10단계 파이프라인을 순차 실행한다.

        Stage 1~2: 기존 LDDSectionAnalyzer로 수행 (단일 LLM)
        Stage 3: DualRiskAnalyzer (멀티 LLM, opt-in)
        Stage 4: GapDetector (멀티 LLM, opt-in)
        Stage 5: JurisdictionAnalyzer (멀티 LLM, 크로스보더 시)
        Stage 6: NarrativeGenerator — 6블록 서술 생성 (opt-in)
        Stage 7: 법률 인용 검증 (레지스트리 대조)
        Stage 8: 별첨 데이터 수집 (체크리스트 기반)
        Stage 9: Executive Summary + 교차 검증 (단일 LLM)
        Stage 10: LDDReportQA (멀티 LLM, opt-in)
        """
        from app.ralph.generators.ldd.section_analyzer import LDDSectionAnalyzer

        result = PipelineResult()

        # ── Stage 1+2: 기존 분석기로 항목별 분석 ──
        self._update_stage(0, "running")
        self._update_stage(1, "running")

        analyzer = LDDSectionAnalyzer(
            llm_call=self._router.call_routed if self._router else (
                self._llm_client.call if self._llm_client and self._llm_client.is_available else None
            ),
            learned_patterns=self._learned_patterns,
        )

        section_results: dict[str, list[dict]] = {}
        for section_cfg in self._sections_config:
            section_type = section_cfg.get("section_type", "")
            items = section_cfg.get("items", [])
            source_files = self._source_map.get(section_type, [])

            analyzed_items: list[dict] = []
            for item in items:
                item_result = await analyzer.analyze_item(
                    item_id=item.get("item_id", ""),
                    item_name=item.get("name", ""),
                    section_type=section_type,
                    section_title=section_cfg.get("title", ""),
                    source_files=source_files,
                )
                item_result["item_id"] = item.get("item_id", "")
                item_result["name"] = item.get("name", "")
                analyzed_items.append(item_result)

            section_results[section_type] = analyzed_items

        self._update_stage(0, "completed", 10)
        self._update_stage(1, "completed", 25)

        # ── Stage 3: 듀얼 리스크 분석 ──
        dual_risk_summary: dict[str, Any] | None = None
        if self._config.stage3_risk_dual and self._router and not self._is_cost_exceeded():
            self._update_stage(2, "running")
            try:
                dual_risk_summary = await self._run_stage3_dual_risk(
                    section_results,
                )
                result.dual_risk_summary = dual_risk_summary
            except Exception as exc:
                logger.warning("Stage 3 듀얼 리스크 분석 실패 (폴백): %s", exc)
            self._update_stage(2, "completed", 50)
        else:
            self._update_stage(2, "skipped", 50)

        # ── Stage 4: 누락 탐지 ──
        if self._config.stage4_gap_detection and self._router and not self._is_cost_exceeded():
            self._update_stage(3, "running")
            try:
                gap_result = await self._run_stage4_gap_detection(
                    section_results, vdr_document_names or [],
                )
                result.gap_detection = {
                    "total_checklist": gap_result.total_checklist,
                    "total_freeform": gap_result.total_freeform,
                    "total_unique": gap_result.total_unique,
                    "duplicates_removed": gap_result.duplicates_removed,
                    "merged_gaps": [
                        {
                            "gap_id": g.gap_id,
                            "section_type": g.section_type,
                            "description": g.description,
                            "priority": g.priority,
                            "rationale": g.rationale,
                            "source": g.source,
                        }
                        for g in gap_result.merged_gaps
                    ],
                }
            except Exception as exc:
                logger.warning("Stage 4 누락 탐지 실패 (폴백): %s", exc)
                gap_result = None
            self._update_stage(3, "completed", 65)
        else:
            self._update_stage(3, "skipped", 65)
            gap_result = None

        # ── Stage 5: 관할권 교차 분석 (크로스보더 시) ──
        if self._config.stage5_jurisdiction and self._config.is_cross_border and self._router and not self._is_cost_exceeded():
            self._update_stage(4, "running")
            try:
                jurisdiction_result = await self._run_stage5_jurisdiction(
                    section_results,
                )
                result.jurisdiction_analysis = {
                    "total_points": jurisdiction_result.total_points,
                    "cross_points": [
                        {
                            "point_id": p.point_id,
                            "point_type": p.point_type,
                            "korean_aspect": p.korean_aspect,
                            "english_aspect": p.english_aspect,
                            "severity": p.severity,
                            "recommendation": p.recommendation,
                        }
                        for p in jurisdiction_result.cross_points
                    ],
                    "conflict_points": [
                        {
                            "point_id": p.point_id,
                            "point_type": p.point_type,
                            "korean_aspect": p.korean_aspect,
                            "english_aspect": p.english_aspect,
                            "severity": p.severity,
                            "recommendation": p.recommendation,
                        }
                        for p in jurisdiction_result.conflict_points
                    ],
                }
            except Exception as exc:
                logger.warning("Stage 5 관할권 교차 분석 실패 (폴백): %s", exc)
            self._update_stage(4, "completed", 75)
        else:
            self._update_stage(4, "skipped", 55)

        # ── Stage 6: 6블록 서술 생성 ──
        if self._config.stage6_narrative and not self._is_cost_exceeded():
            self._update_stage(5, "running")
            try:
                narrative_results = await self._run_stage6_narrative(section_results)
                result.narrative_sections = narrative_results
            except Exception as exc:
                logger.warning("Stage 6 서술 생성 실패 (폴백): %s", exc)
            self._update_stage(5, "completed", 70)
        else:
            self._update_stage(5, "skipped", 70)

        # ── Stage 7: 법률 인용 검증 ──
        if result.narrative_sections and not self._is_cost_exceeded():
            self._update_stage(6, "running")
            try:
                from app.ralph.generators.ldd.citation_verifier import CitationVerifier
                verifier = CitationVerifier()
                result.narrative_sections = verifier.verify_narrative_sections(
                    result.narrative_sections,
                )
                logger.info("Stage 7 법률 인용 검증 완료")
            except Exception as exc:
                logger.warning("Stage 7 인용 검증 실패 (폴백): %s", exc)
            self._update_stage(6, "completed", 73)
        else:
            self._update_stage(6, "skipped", 73)

        # ── Stage 8: 별첨 데이터 수집 ──
        try:
            from app.ralph.generators.ldd.appendix_generator import AppendixGenerator
            self._update_stage(7, "running")
            appendix_gen = AppendixGenerator()
            appendix_result = appendix_gen.generate(section_results)
            result.appendices = appendix_result.to_dict()
            logger.info(
                "Stage 8 별첨 생성 완료: %d개 테이블, %d개 행",
                appendix_result.non_empty_tables,
                appendix_result.total_rows,
            )
            self._update_stage(7, "completed", 75)
        except Exception as exc:
            logger.warning("Stage 8 별첨 생성 실패 (폴백): %s", exc)
            self._update_stage(7, "skipped", 75)

        # ── Guardrails 검증 ──
        try:
            guardrail_result = self._run_guardrails(
                section_results, gap_result, vdr_document_names or [],
            )
            result.guardrail_result = {
                "has_errors": guardrail_result.has_errors,
                "error_count": guardrail_result.error_count,
                "warning_count": guardrail_result.warning_count,
                "passed_rules": guardrail_result.passed_rules,
                "issues": [
                    {
                        "rule": i.rule,
                        "severity": i.severity,
                        "location": i.location,
                        "message": i.message,
                    }
                    for i in guardrail_result.issues
                ],
            }
        except Exception as exc:
            logger.warning("Guardrails 검증 실패 (무시): %s", exc)

        # ── Stage 9: Executive Summary ──
        self._update_stage(8, "running")
        try:
            exec_summary = await analyzer.generate_executive_summary(section_results)
            result.executive_summary = exec_summary
        except Exception as exc:
            logger.warning("Executive Summary 생성 실패: %s", exc)
            result.executive_summary = ""
        self._update_stage(8, "completed", 90)

        # ── Stage 10: 최종 QA ──
        if self._config.stage7_qa and self._router and not self._is_cost_exceeded():
            self._update_stage(9, "running")
            try:
                qa_result = await self._run_stage7_qa(section_results, exec_summary=result.executive_summary)
                result.qa_result = {
                    "overall_score": qa_result.overall_score,
                    "issues": [
                        {
                            "category": i.category,
                            "severity": i.severity,
                            "location": i.location,
                            "description": i.description,
                        }
                        for i in qa_result.issues
                    ],
                    "passed_checks": qa_result.passed_checks,
                    "summary": qa_result.summary,
                }
            except Exception as exc:
                logger.warning("Stage 10 QA 실패 (폴백): %s", exc)
            self._update_stage(9, "completed", 100)
        else:
            self._update_stage(9, "skipped", 100)

        # ── 서술 품질 게이트 (LLM 없이 밀리초 동작) ──
        if result.narrative_sections:
            try:
                from app.ralph.gates.narrative_gate import NarrativeQualityGate
                nq_gate = NarrativeQualityGate()
                nq_result = nq_gate.evaluate(result.narrative_sections)
                if result.qa_result is None:
                    result.qa_result = {}
                result.qa_result["narrative_quality"] = nq_result.to_dict()
                logger.info(
                    "서술 품질 게이트: %d/%d 통과 (점수 %.1f/5.0)",
                    nq_result.passed_items, nq_result.total_items, nq_result.overall_score,
                )
            except Exception as exc:
                logger.warning("서술 품질 게이트 실패 (무시): %s", exc)

        # ── 최종 결과 조립 ──
        result.sections = section_results
        result.cost_usd = (
            self._llm_client._cost_tracker.accumulated_usd
            if hasattr(self._llm_client, "_cost_tracker")
            else 0.0
        )
        result.stages = [
            {"stage": s.stage, "name": s.name, "status": s.status, "progress_pct": s.progress_pct}
            for s in self._stages
        ]

        return result

    # ── Stage 3: 듀얼 리스크 분석 ──

    async def _run_stage3_dual_risk(
        self,
        section_results: dict[str, list[dict]],
    ) -> dict[str, Any]:
        """Stage 3: 듀얼 관점 리스크 분석."""
        from app.ralph.generators.ldd.dual_risk_analyzer import DualRiskAnalyzer

        dual_analyzer = DualRiskAnalyzer(
            llm_client=self._llm_client,
            router=self._router,
            config=self._config,
        )

        summary: dict[str, Any] = {
            "total_analyzed": 0,
            "auto_resolved": 0,
            "needs_human_review": 0,
            "items": [],
        }

        # section_type → title 매핑
        title_map = {
            cfg.get("section_type", ""): cfg.get("title", "")
            for cfg in self._sections_config
        }

        for section_type, items in section_results.items():
            source_files = self._source_map.get(section_type, [])
            for item in items:
                if item.get("status") != "ISSUE":
                    continue

                try:
                    dual_result = await dual_analyzer.analyze_item_dual(
                        item_id=item.get("item_id", ""),
                        item_name=item.get("name", ""),
                        section_type=section_type,
                        section_title=title_map.get(section_type, ""),
                        source_files=source_files,
                    )

                    summary["total_analyzed"] += 1
                    if dual_result.comparison.auto_resolved:
                        summary["auto_resolved"] += 1
                        # 자동 해결 시 병합 결과로 업데이트
                        if dual_result.merged:
                            item.update(dual_result.merged)
                    else:
                        summary["needs_human_review"] += 1

                    summary["items"].append({
                        "item_id": dual_result.item_id,
                        "gap": dual_result.comparison.gap,
                        "auto_resolved": dual_result.comparison.auto_resolved,
                        "needs_human_review": dual_result.comparison.needs_human_review,
                        "final_level": dual_result.comparison.final_level,
                        "note": dual_result.comparison.note,
                    })

                except Exception as exc:
                    logger.warning(
                        "Stage 3 항목 %s 분석 실패: %s",
                        item.get("item_id", "?"), exc,
                    )

        return summary

    # ── Stage 4: 누락 탐지 ──

    async def _run_stage4_gap_detection(
        self,
        section_results: dict[str, list[dict]],
        document_names: list[str],
    ):
        """Stage 4: 누락 탐지 (최대 ROI)."""
        from app.ralph.generators.ldd.gap_detector import GapDetector

        detector = GapDetector(
            llm_client=self._llm_client,
            router=self._router,
            config=self._config,
        )

        return await detector.detect_gaps(
            analyzed_sections=section_results,
            document_names=document_names,
        )

    # ── Stage 5: 관할권 교차 분석 ──

    async def _run_stage5_jurisdiction(
        self,
        section_results: dict[str, list[dict]],
    ):
        """Stage 5: 관할권 교차 분석 (크로스보더 시)."""
        from app.ralph.generators.ldd.jurisdiction_analyzer import JurisdictionAnalyzer

        analyzer = JurisdictionAnalyzer(
            llm_client=self._llm_client,
            router=self._router,
        )

        # 키 조항 요약 생성
        key_clauses_parts: list[str] = []
        for section_type, items in section_results.items():
            issues = [i for i in items if i.get("status") == "ISSUE"]
            if issues:
                key_clauses_parts.append(f"## {section_type}")
                for issue in issues:
                    key_clauses_parts.append(
                        f"- [{issue.get('issue_level', '?')}] {issue.get('item_id', '')}: "
                        f"{issue.get('description', '')[:150]}"
                    )

        return await analyzer.analyze(
            key_clauses_summary="\n".join(key_clauses_parts),
            deal_summary=self._config.deal_summary or "(거래 요약 미제공)",
        )

    # ── Stage 6: 6블록 서술 생성 ──

    async def _run_stage6_narrative(
        self,
        section_results: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        """Stage 6: 항목별 6블록 서술 생성."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        # LLM 호출 함수 결정
        llm_call = (
            self._router.call_routed if self._router
            else (self._llm_client.call if self._llm_client and self._llm_client.is_available else None)
        )

        generator = NarrativeGenerator(
            llm_call=llm_call,
            learned_patterns=self._learned_patterns,
        )

        # 법률 컨텍스트 주입기 초기화
        try:
            from app.ralph.generators.ldd.legal_citations import CitationPromptInjector
            injector = CitationPromptInjector()
        except Exception:
            injector = None

        # section_type → title 매핑
        title_map = {
            cfg.get("section_type", ""): cfg.get("title", "")
            for cfg in self._sections_config
        }

        narrative_results: dict[str, list[dict]] = {}

        for section_type, items in section_results.items():
            source_files = self._source_map.get(section_type, [])
            section_dict = {
                "section_type": section_type,
                "title": title_map.get(section_type, ""),
                "items": items,
            }

            # 섹션별 법률 컨텍스트 주입
            legal_context = ""
            if injector:
                try:
                    legal_context = injector.build_legal_context(section_type)
                except Exception as exc:
                    logger.debug("법률 컨텍스트 주입 실패 (%s): %s", section_type, exc)

            results = await generator.generate_section_narratives(
                section=section_dict,
                source_files=source_files,
                legal_context=legal_context,
            )

            narrative_results[section_type] = [r.to_dict() for r in results]
            logger.info(
                "Stage 6 서술 생성 완료: %s (%d 항목, %d 블록)",
                section_type,
                len(results),
                sum(len(r.blocks) for r in results),
            )

        return narrative_results

    # ── Stage 10: 최종 QA ──

    async def _run_stage7_qa(
        self,
        section_results: dict[str, list[dict]],
        exec_summary: str = "",
    ):
        """Stage 7: 최종 QA."""
        from app.ralph.generators.ldd.report_qa import LDDReportQA

        qa = LDDReportQA(
            llm_client=self._llm_client,
            router=self._router,
        )

        report_data = {
            "sections": section_results,
            "executive_summary": exec_summary,
        }

        return await qa.evaluate(report_data)

    # ── Guardrails ──

    def _run_guardrails(
        self,
        section_results: dict[str, list[dict]],
        gap_result: Any | None,
        vdr_document_names: list[str],
    ):
        """Guardrails 검증 (동기)."""
        from app.ralph.generators.ldd.guardrails import LDDGuardrails

        # section_results → flat sections list 변환
        sections_list: list[dict] = []
        for section_type, items in section_results.items():
            sections_list.append({
                "section_type": section_type,
                "items": items,
            })

        guardrails = LDDGuardrails(
            vdr_document_ids=vdr_document_names,
            gap_detection_result=gap_result,
        )

        return guardrails.validate_all(sections_list)

    # ── Helper ──

    def _update_stage(self, index: int, status: str, progress_pct: int = 0) -> None:
        if 0 <= index < len(self._stages):
            self._stages[index].status = status
            if progress_pct:
                self._stages[index].progress_pct = progress_pct

    def _is_cost_exceeded(self) -> bool:
        """누적 비용이 한도를 초과했는지 확인한다."""
        if not hasattr(self._llm_client, "_cost_tracker"):
            return False
        accumulated = self._llm_client._cost_tracker.accumulated_usd
        if accumulated >= self._config.max_cost_usd:
            logger.warning(
                "비용 한도 초과 ($%.2f >= $%.2f) — 이후 Stage 스킵",
                accumulated, self._config.max_cost_usd,
            )
            return True
        return False
