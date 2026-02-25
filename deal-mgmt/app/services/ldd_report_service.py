"""LDD(법률실사) 보고서 서비스 — docxtpl 기반 .docx 생성 및 CRUD.

Ralph Loop 2회 적용 워크플로우:
1. create_ldd_report_from_vdr() → Ralph Loop #1 (초안)
2. 사용자 체크리스트 리뷰 (ldd_review_service.py)
3. finalize_ldd_report() → Ralph Loop #2 (최종 Refine)
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import LDDIssueLevel, LDDItemStatus, LDDReportStatus, LDDReportType
from app.models.ldd_report import LDDReport
from app.models.ldd_vdr_reference import LddVdrReference
from app.schemas.ldd_report import (
    DEFAULT_LDD_SECTIONS,
    LDDFinalizeRequest,
    LDDReportCreate,
    LDDReportCreateAuto,
    LDDReportCreateFromVdr,
    LDDSectionsUpdate,
)

logger = logging.getLogger(__name__)

TEMPLATE_DIR     = Path(__file__).resolve().parent.parent.parent / "templates" / "ldd"
OUTPUT_DIR       = Path(__file__).resolve().parent.parent.parent / "generated" / "ldd"
_PROJECT_ROOT    = Path(__file__).resolve().parent.parent.parent
TEMPLATE_VERSION = "1.0"


def _validate_source_dir(source_dir: str) -> None:
    """source_dir가 프로젝트 루트 하위인지 검증한다 (Path Traversal 방어)."""
    try:
        resolved = Path(source_dir).resolve()
        resolved.relative_to(_PROJECT_ROOT)
    except (ValueError, OSError):
        raise ValueError(
            f"source_dir은 프로젝트 디렉토리 내부여야 합니다: {source_dir}"
        )


# ── 집계 계산 ─────────────────────────────────────────────────────────────────

def _compute_counts(sections: list[dict]) -> dict:
    """섹션 데이터로부터 이슈 카운트를 계산한다."""
    total = issue = red = amber = green = ok = na = pending = rfi = 0

    for section in sections:
        for item in section.get("items", []):
            total += 1
            status = item.get("status", "PENDING")
            level  = item.get("issue_level")

            if status == LDDItemStatus.OK:
                ok += 1
            elif status == LDDItemStatus.ISSUE:
                issue += 1
                if level == LDDIssueLevel.CRITICAL:
                    red += 1
                elif level in (LDDIssueLevel.HIGH, LDDIssueLevel.MEDIUM):
                    amber += 1
                elif level == LDDIssueLevel.LOW:
                    green += 1
            elif status == LDDItemStatus.NA:
                na += 1
            else:
                pending += 1

            if item.get("rfi_required"):
                rfi += 1

    return {
        "total_items":   total,
        "issue_count":   issue,
        "red_count":     red,
        "amber_count":   amber,
        "green_count":   green,
        "ok_count":      ok,
        "na_count":      na,
        "pending_count": pending,
        "rfi_count":     rfi,
    }


def _merge_ai_results(
    sections: list[dict],
    ai_sections: dict,
    *,
    include_ai_meta: bool = True,
    approved_items: set[str] | None = None,
) -> list[dict]:
    """Ralph Loop AI 결과를 기존 섹션에 병합한다.

    Args:
        sections: 기본 섹션 데이터 (변경됨 — in-place)
        ai_sections: AI가 반환한 섹션별 항목 딕셔너리
        include_ai_meta: confidence, evidence_refs 등 AI 메타데이터 포함 여부
        approved_items: 사용자 승인된 item_id 집합. 해당 항목은 AI 결과 대신
                        user_override 값만 적용한다 (finalize 시 사용).
    """
    for section in sections:
        section_type = section["section_type"]
        if section_type not in ai_sections:
            continue
        ai_items = ai_sections[section_type]
        for item in section["items"]:
            item_id = item.get("item_id", "")

            # 승인된 항목: user_override만 적용 (AI 결과 무시)
            if approved_items and item_id in approved_items:
                if item.get("user_override_status"):
                    item["status"] = item["user_override_status"]
                if item.get("user_override_level"):
                    item["issue_level"] = item["user_override_level"]
                continue

            for ai_item in ai_items:
                if ai_item.get("item_id") != item_id:
                    continue
                item["status"] = ai_item.get("status", item.get("status", "PENDING"))
                item["issue_level"] = ai_item.get("issue_level", item.get("issue_level"))
                item["description"] = ai_item.get("description", item.get("description", ""))
                item["deal_impact"] = ai_item.get("deal_impact", item.get("deal_impact", ""))
                item["recommendation"] = ai_item.get("recommendation", item.get("recommendation", ""))
                item["rfi_required"] = ai_item.get("rfi_required", item.get("rfi_required", False))
                item["rfi_number"] = ai_item.get("rfi_number", item.get("rfi_number", ""))
                if include_ai_meta:
                    item["confidence"] = ai_item.get("confidence", item.get("confidence", 0.0))
                    item["evidence_refs"] = ai_item.get("evidence_refs", item.get("evidence_refs", []))
                break
    return sections


def _compute_risk_colors(sections: list[dict]) -> list[dict]:
    """각 항목의 risk_color를 이슈레벨 기반으로 자동 계산한다."""
    _level_to_color = {
        LDDIssueLevel.CRITICAL: "RED",
        LDDIssueLevel.HIGH:     "AMBER",
        LDDIssueLevel.MEDIUM:   "AMBER",
        LDDIssueLevel.LOW:      "GREEN",
    }
    for section in sections:
        for item in section.get("items", []):
            level = item.get("issue_level")
            if item.get("status") == LDDItemStatus.ISSUE and level:
                item["risk_color"] = _level_to_color.get(level, "")
            else:
                item["risk_color"] = ""
    return sections


# ── docxtpl 렌더링 컨텍스트 빌드 ─────────────────────────────────────────────

def _build_context(report: LDDReport) -> dict:
    """docxtpl에 전달할 컨텍스트 딕셔너리를 생성한다."""
    sections = report.sections or []

    # 전체 이슈 목록 (ISSUE 항목만)
    all_issues = []
    red_issues = []
    sections_with_issues = []

    for section in sections:
        section_title = section.get("title", "")
        sec_issues = []
        for item in section.get("items", []):
            if item.get("status") == LDDItemStatus.ISSUE:
                enriched = {**item, "section_title": section_title}
                all_issues.append(enriched)
                level = item.get("issue_level", "")
                if level in (LDDIssueLevel.CRITICAL, LDDIssueLevel.HIGH, LDDIssueLevel.MEDIUM):
                    sec_issues.append(item)
                    if level == LDDIssueLevel.CRITICAL:
                        red_issues.append(enriched)

        if sec_issues:
            sections_with_issues.append({
                "title":  section_title,
                "issues": sec_issues,
            })

    ctx = {
        "title":          report.title,
        "target_company": report.target_company or "",
        "dd_period":      report.dd_period or "",
        "law_firm":       report.law_firm or "",
        "prepared_by":    report.prepared_by or "",
        "report_date":    date.today().strftime("%Y년 %m월 %d일"),
        "total_items":    report.total_items,
        "issue_count":    report.issue_count,
        "red_count":      report.red_count,
        "amber_count":    report.amber_count,
        "green_count":    report.green_count,
        "ok_count":       report.ok_count,
        "na_count":       report.na_count,
        "pending_count":  report.pending_count,
        "rfi_count":      report.rfi_count,
        "sections":       sections,
        "all_issues":     all_issues,
        "red_issues":     red_issues,
        "sections_with_issues": sections_with_issues,
        # VDR 연동 메타데이터
        "vdr_source":     report.vdr_source,
        "draft_score":    report.draft_score,
        "final_score":    report.final_score,
    }
    return ctx


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def list_ldd_reports(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[LDDReport]:
    q = (
        select(LDDReport)
        .where(LDDReport.transaction_id == transaction_id)
        .order_by(LDDReport.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def list_all_ldd_reports(db: AsyncSession) -> list[LDDReport]:
    """모든 거래의 LDD 보고서를 조회한다 (전체 목록)."""
    q = select(LDDReport).order_by(LDDReport.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
) -> LDDReport:
    q = select(LDDReport).where(
        LDDReport.id == report_id,
        LDDReport.transaction_id == transaction_id,
    )
    result = await db.execute(q)
    report = result.scalar_one_or_none()
    if not report:
        raise DocumentNotFoundError("LDD 보고서를 찾을 수 없습니다.")
    return report


async def create_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: LDDReportCreate,
    created_by_email: str | None = None,
) -> LDDReport:
    # 섹션 기본값 적용
    sections_data = (
        [s.model_dump() for s in body.sections]
        if body.sections
        else DEFAULT_LDD_SECTIONS
    )
    sections_data = _compute_risk_colors(sections_data)
    counts = _compute_counts(sections_data)

    report = LDDReport(
        transaction_id   = transaction_id,
        report_type      = body.report_type,
        title            = body.title,
        target_company   = body.target_company,
        dd_period        = body.dd_period,
        law_firm         = body.law_firm,
        prepared_by      = body.prepared_by,
        sections         = sections_data,
        template_version = TEMPLATE_VERSION,
        created_by_email = created_by_email,
        status           = LDDReportStatus.DRAFT,
        **counts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # 즉시 렌더링
    report = await generate_ldd_report(db, report)
    return report


async def update_ldd_sections(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LDDSectionsUpdate,
) -> LDDReport:
    """섹션 데이터를 업데이트하고 보고서를 재렌더링한다."""
    report = await get_ldd_report(db, transaction_id, report_id)

    sections_data = [s.model_dump() for s in body.sections]
    sections_data = _compute_risk_colors(sections_data)
    counts = _compute_counts(sections_data)

    report.sections = sections_data
    for k, v in counts.items():
        setattr(report, k, v)

    # 기존 파일 삭제
    if report.file_path:
        try:
            Path(report.file_path).unlink(missing_ok=True)
        except OSError:
            pass
    report.file_path = None
    report.file_name = None
    report.file_size_bytes = None

    return await generate_ldd_report(db, report)


async def delete_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
) -> None:
    report = await get_ldd_report(db, transaction_id, report_id)

    if report.file_path:
        try:
            Path(report.file_path).unlink(missing_ok=True)
        except OSError:
            pass

    await db.delete(report)
    await db.commit()


# ── docxtpl 렌더링 ────────────────────────────────────────────────────────────

async def generate_ldd_report(
    db: AsyncSession,
    report: LDDReport,
) -> LDDReport:
    """
    asyncio.to_thread을 통해 블로킹 docxtpl 렌더링을 수행한다.
    FULL → ldd_full_template.docx
    REDFLAG → ldd_redflag_template.docx
    """
    template_name = f"ldd_{report.report_type.lower()}_template.docx"
    template_path = TEMPLATE_DIR / template_name

    if not template_path.exists():
        report.status = LDDReportStatus.FAILED
        report.error_message = (
            f"템플릿 파일을 찾을 수 없습니다: {template_name}. "
            "'uv run python scripts/create_ldd_template.py'를 실행하세요."
        )
        await db.commit()
        await db.refresh(report)
        return report

    report_id   = report.id
    report_type = report.report_type
    context     = _build_context(report)

    def _render() -> tuple[str, str, int]:
        """동기 렌더링 — 별도 스레드에서 실행."""
        from docxtpl import DocxTemplate

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tpl = DocxTemplate(str(template_path))
        tpl.render(context)
        fname = f"LDD_{report_type}_{report_id}.docx"
        out   = OUTPUT_DIR / fname
        tpl.save(str(out))
        return fname, str(out), out.stat().st_size

    # GENERATING 상태로 먼저 저장
    report.status = LDDReportStatus.GENERATING
    await db.commit()

    try:
        fname, fpath, fsize = await asyncio.to_thread(_render)
        report.status          = LDDReportStatus.READY
        report.file_name       = fname
        report.file_path       = fpath
        report.file_size_bytes = fsize
        report.error_message   = None
    except Exception as exc:
        report.status        = LDDReportStatus.FAILED
        report.error_message = str(exc)

    await db.commit()
    await db.refresh(report)
    return report


async def create_ldd_report_auto(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: LDDReportCreateAuto,
    created_by_email: str | None = None,
) -> LDDReport:
    """Ralph Loop 기반 LDD 보고서 자동 생성.

    1. source_dir 스캔 → 파일 분류
    2. 섹션별 AI 분석 (Ralph Loop)
    3. 결과를 기존 LDDReport에 채워넣기
    4. docxtpl 렌더링
    """
    from app.core.config import settings
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.docx_gate import DOCXProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.ldd.section_analyzer import LDDDocumentGenerator, LDDSectionAnalyzer
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.parsers.file_classifier import parse_and_classify, scan_directory

    # 1. 실사자료 스캔 및 파싱 (경로 검증)
    _validate_source_dir(body.source_dir)
    file_list = scan_directory(body.source_dir)
    if not file_list:
        # 자료 없으면 빈 보고서로 생성
        return await create_ldd_report(
            db, transaction_id,
            LDDReportCreate(
                title=body.title,
                report_type=body.report_type,
                target_company=body.target_company,
                dd_period=body.dd_period,
                law_firm=body.law_firm,
                prepared_by=body.prepared_by,
            ),
            created_by_email,
        )

    # 2. 파일 파싱 + DDRL 섹션 매핑
    from app.ralph.parsers.base import ParsedFile
    source_map: dict[str, list[ParsedFile]] = {}
    for file_info in file_list:
        parsed = parse_and_classify(file_info["path"])
        for section in parsed.ddrl_sections:
            source_map.setdefault(section, []).append(parsed)

    # 3. LLM 클라이언트 + 학습 패턴 + 분석기 설정
    llm_client = RalphLLMClient.from_settings(settings)
    llm_call = llm_client.call if llm_client.is_available else None

    learned_patterns: list[str] = []
    try:
        from app.ralph.learning.pattern_aggregator import PatternAggregator
        agg = PatternAggregator(db)
        learned_patterns = await agg.get_learned_patterns("LDD")
    except Exception as exc:
        logging.getLogger(__name__).warning("학습 패턴 조회 실패 (무시): %s", exc)

    analyzer = LDDSectionAnalyzer(llm_call=llm_call, learned_patterns=learned_patterns)
    generator = LDDDocumentGenerator(analyzer, DEFAULT_LDD_SECTIONS)
    generator.set_source_map(source_map)

    # 4. 품질 게이트 조립
    gates = [DOCXProgrammaticGate()]
    if llm_call:
        gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="ldd"))

    # 5. Ralph Loop 실행
    from app.ralph.prd_manager import load_prd

    convergence_config = ConvergenceConfig(
        max_iterations_per_section=body.max_iterations,
        max_cost_usd=body.max_cost_usd,
    )
    prd = load_prd(body.report_type if body.report_type in ("ldd_full", "ldd_redflag") else "ldd_full")
    orchestrator = RalphLoopOrchestrator(
        generator=generator,
        gates=gates,
        prd=prd,
        config=LoopConfig(convergence=convergence_config),
    )

    loop_result = await orchestrator.run(source_data={"source_dir": body.source_dir})

    # 5. 결과를 LDD 섹션 형식으로 변환
    sections_data = list(DEFAULT_LDD_SECTIONS)
    if loop_result.final_artifact:
        try:
            report_data = json.loads(loop_result.final_artifact)
            ai_sections = report_data.get("sections", {})
            _merge_ai_results(sections_data, ai_sections, include_ai_meta=True)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Ralph Loop 결과 파싱 실패: %s", e)

    sections_data = _compute_risk_colors(sections_data)
    counts = _compute_counts(sections_data)

    # 6. DB 저장
    report = LDDReport(
        transaction_id=transaction_id,
        report_type=body.report_type,
        title=body.title,
        target_company=body.target_company,
        dd_period=body.dd_period,
        law_firm=body.law_firm,
        prepared_by=body.prepared_by,
        sections=sections_data,
        template_version=TEMPLATE_VERSION,
        created_by_email=created_by_email,
        status=LDDReportStatus.DRAFT,
        **counts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # 7. DOCX 렌더링
    report = await generate_ldd_report(db, report)
    return report


# ── VDR 기반 워크플로우 ──────────────────────────────────────────────────────


async def _insert_vdr_references(
    db: AsyncSession,
    report_id: uuid.UUID,
    sections: list[dict],
    vdr_name_to_id: dict[str, uuid.UUID],
) -> None:
    """AI 분석 결과의 evidence_refs를 VDR 문서 UUID로 변환하여 링크 테이블에 저장."""
    import re

    for section in sections:
        section_type = section.get("section_type", "")
        for item in section.get("items", []):
            item_id = item.get("item_id", "")
            for ref in item.get("evidence_refs", []):
                vdr_doc_id: uuid.UUID | None = None

                # [VDR:uuid]filename 형식에서 UUID 추출
                match = re.match(r"\[VDR:([0-9a-f-]{36})\]", ref)
                if match:
                    try:
                        vdr_doc_id = uuid.UUID(match.group(1))
                    except ValueError:
                        pass

                # UUID 못 찾으면 파일명으로 매칭
                if not vdr_doc_id:
                    vdr_doc_id = vdr_name_to_id.get(ref)

                # 부분 매칭 시도 (파일명 일부 일치)
                if not vdr_doc_id:
                    for name, vid in vdr_name_to_id.items():
                        if ref in name or name in ref:
                            vdr_doc_id = vid
                            break

                if vdr_doc_id:
                    link = LddVdrReference(
                        ldd_report_id=report_id,
                        item_id=item_id,
                        vdr_document_id=vdr_doc_id,
                        section_type=section_type,
                        relevance_score=item.get("confidence", 0.0),
                        evidence_snippet=item.get("description", "")[:500] if item.get("description") else None,
                    )
                    db.add(link)

    await db.flush()


async def create_ldd_report_from_vdr(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: LDDReportCreateFromVdr,
    created_by_email: str | None = None,
) -> LDDReport:
    """Ralph Loop #1: VDR 문서 기반 초안 보고서 생성.

    1. LDDReport 생성 (status=ANALYZING)
    2. VDR 문서 텍스트 추출 (캐시 활용)
    3. 섹션별 소스 매핑
    4. Ralph Loop #1 실행
    5. 결과 → sections JSONB 매핑
    6. evidence_refs → VDR 참조 링크 생성
    7. 상태 → REVIEW
    """
    from app.core.config import settings
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.docx_gate import DOCXProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.ldd.section_analyzer import LDDDocumentGenerator, LDDSectionAnalyzer
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.text_extraction_service import TextExtractionService, build_source_map

    now = datetime.now(timezone.utc)

    # 1. LDDReport 레코드 생성
    sections_data = copy.deepcopy(DEFAULT_LDD_SECTIONS)
    counts = _compute_counts(sections_data)

    report = LDDReport(
        transaction_id=transaction_id,
        report_type=body.report_type,
        title=body.title,
        target_company=body.target_company,
        dd_period=body.dd_period,
        law_firm=body.law_firm,
        prepared_by=body.prepared_by,
        sections=sections_data,
        template_version=TEMPLATE_VERSION,
        created_by_email=created_by_email,
        status=LDDReportStatus.ANALYZING,
        vdr_source=True,
        analysis_started_at=now,
        **counts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    try:
        # 2. VDR 문서 텍스트 추출
        extractor = TextExtractionService()
        source_files = await extractor.extract_from_vdr_documents(
            db, transaction_id, folder_ids=body.folder_ids,
        )

        if not source_files:
            report.status = LDDReportStatus.REVIEW
            report.analysis_completed_at = datetime.now(timezone.utc)
            report.review_started_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(report)
            return report

        # 3. 섹션별 소스 매핑
        vdr_source_map = build_source_map(source_files)

        # VDR 파일명 → UUID 역매핑 (evidence 매칭용)
        vdr_name_to_id: dict[str, uuid.UUID] = {}
        for vsf in source_files:
            vdr_name_to_id[vsf.original_name] = vsf.vdr_document_id
            vdr_name_to_id[f"[VDR:{vsf.vdr_document_id}]{vsf.original_name}"] = vsf.vdr_document_id

        # ParsedFile source_map 변환 (VDR 메타데이터를 source_path에 포함)
        parsed_source_map: dict[str, list] = {}
        for section_type, vsf_list in vdr_source_map.items():
            parsed_list = []
            for vsf in vsf_list:
                p = copy.copy(vsf.parsed)
                p.source_path = f"[VDR:{vsf.vdr_document_id}]{vsf.original_name}"
                parsed_list.append(p)
            parsed_source_map[section_type] = parsed_list

        # 4. LLM 클라이언트 + 학습 패턴
        llm_client = RalphLLMClient.from_settings(settings)
        llm_call = llm_client.call if llm_client.is_available else None

        learned_patterns: list[str] = []
        try:
            from app.ralph.learning.pattern_aggregator import PatternAggregator
            agg = PatternAggregator(db)
            learned_patterns = await agg.get_learned_patterns("LDD")
        except Exception as exc:
            logger.warning("학습 패턴 조회 실패 (무시): %s", exc)

        # ── 멀티 LLM 파이프라인 분기 ──
        use_multi_llm = (
            body.use_multi_llm if body.use_multi_llm is not None
            else settings.LDD_MULTI_LLM_ENABLED
        )

        if use_multi_llm and llm_client.is_available:
            # ★ 멀티 LLM 7단계 파이프라인 ★
            from app.ralph.generators.ldd.pipeline import LDDMultiLLMPipeline
            from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig
            from app.ralph.routing.ldd_router import LDDModelRouter

            router = LDDModelRouter(llm_client)
            pipeline_config = LDDPipelineConfig(
                stage3_risk_dual=settings.LDD_STAGE3_DUAL_RISK,
                stage4_gap_detection=settings.LDD_STAGE4_GAP_DETECTION,
                stage5_jurisdiction=settings.LDD_STAGE5_JURISDICTION,
                stage7_qa=settings.LDD_STAGE7_QA,
                risk_gap_auto_resolve=settings.LDD_RISK_GAP_AUTO_RESOLVE,
                max_cost_usd=settings.LDD_MAX_COST_USD,
                max_iterations=body.draft_max_iterations,
                deal_type=getattr(body, "deal_type", ""),
                industry=getattr(body, "industry", ""),
                is_cross_border=getattr(body, "is_cross_border", False),
            )

            pipeline = LDDMultiLLMPipeline(
                llm_client=llm_client,
                router=router,
                config=pipeline_config,
                source_map=parsed_source_map,
                sections_config=copy.deepcopy(DEFAULT_LDD_SECTIONS),
                learned_patterns=learned_patterns,
            )

            vdr_doc_names = list(vdr_name_to_id.keys())
            pipeline_result = await pipeline.run(vdr_document_names=vdr_doc_names)

            # 파이프라인 결과 → LDD 섹션 형식 변환
            sections_data = copy.deepcopy(DEFAULT_LDD_SECTIONS)
            if pipeline_result.sections:
                _merge_ai_results(sections_data, pipeline_result.sections, include_ai_meta=True)

            sections_data = _compute_risk_colors(sections_data)
            counts = _compute_counts(sections_data)

            # VDR 참조 링크 생성
            await _insert_vdr_references(db, report.id, sections_data, vdr_name_to_id)

            # 결과 저장 (멀티 LLM 메타데이터 포함)
            report.sections = sections_data
            for k, v in counts.items():
                setattr(report, k, v)

            report.dual_risk_summary = pipeline_result.dual_risk_summary
            report.gap_detection = pipeline_result.gap_detection
            report.jurisdiction_analysis = pipeline_result.jurisdiction_analysis
            report.qa_result = pipeline_result.qa_result
            report.pipeline_stages = pipeline_result.stages
            report.draft_score = (
                pipeline_result.qa_result.get("overall_score")
                if pipeline_result.qa_result else None
            )
            report.status = LDDReportStatus.REVIEW
            report.analysis_completed_at = datetime.now(timezone.utc)
            report.review_started_at = datetime.now(timezone.utc)

        else:
            # ── 기존 단일 LLM 워크플로우 (하위 호환) ──
            analyzer = LDDSectionAnalyzer(llm_call=llm_call, learned_patterns=learned_patterns)
            generator = LDDDocumentGenerator(analyzer, copy.deepcopy(DEFAULT_LDD_SECTIONS))
            generator.set_source_map(parsed_source_map)

            # 5. 품질 게이트 + Ralph Loop #1
            gates: list = [DOCXProgrammaticGate()]
            if llm_call:
                gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="ldd"))

            convergence_config = ConvergenceConfig(
                max_iterations_per_section=body.draft_max_iterations,
                max_cost_usd=body.max_cost_usd * 0.6,  # 전체 예산의 60%를 초안에 배정
            )
            prd_key = f"ldd_{body.report_type.lower()}"  # "FULL" → "ldd_full", "REDFLAG" → "ldd_redflag"
            prd = load_prd(prd_key)

            orchestrator = RalphLoopOrchestrator(
                generator=generator,
                gates=gates,
                prd=prd,
                config=LoopConfig(convergence=convergence_config),
            )

            # 5b. RalphSession 레코드 생성 (학습 패턴 축적용)
            from app.models.ralph_session import RalphSession, RalphSessionStatus
            ralph_session = RalphSession(
                id=uuid.UUID(orchestrator.session_id),
                transaction_id=transaction_id,
                doc_type="LDD",  # get_learned_patterns("LDD") 쿼리와 일치
                status=RalphSessionStatus.PLANNING,
                prd=prd,
                config={
                    "max_iterations": body.draft_max_iterations,
                    "max_cost_usd": body.max_cost_usd * 0.6,
                },
                learned_patterns=learned_patterns or None,
                created_by_email=created_by_email,
            )
            db.add(ralph_session)
            await db.flush()

            loop_result = await orchestrator.run(source_data={"transaction_id": str(transaction_id)})

            # 5c. RalphSession 결과 업데이트
            ralph_session.status = loop_result.status.value
            ralph_session.progress = loop_result.progress
            ralph_session.total_iterations = loop_result.total_iterations
            ralph_session.total_cost_usd = loop_result.total_cost_usd
            ralph_session.final_score = loop_result.final_score
            ralph_session.section_scores = loop_result.section_scores
            ralph_session.critical_flags = loop_result.critical_flags
            ralph_session.error_message = (
                "; ".join(loop_result.errors) if loop_result.errors else None
            )

            # 6. 결과를 LDD 섹션 형식으로 변환
            sections_data = copy.deepcopy(DEFAULT_LDD_SECTIONS)
            if loop_result.final_artifact:
                try:
                    report_data = json.loads(loop_result.final_artifact)
                    ai_sections = report_data.get("sections", {})
                    _merge_ai_results(sections_data, ai_sections, include_ai_meta=True)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Ralph Loop #1 결과 파싱 실패: %s", e)

            sections_data = _compute_risk_colors(sections_data)
            counts = _compute_counts(sections_data)

            # 7. VDR 참조 링크 생성
            await _insert_vdr_references(db, report.id, sections_data, vdr_name_to_id)

            # 8. 결과 저장
            report.sections = sections_data
            for k, v in counts.items():
                setattr(report, k, v)

            report.draft_ralph_session_id = (
                uuid.UUID(loop_result.session_id) if loop_result.session_id else None
            )
            report.draft_score = loop_result.final_score
            report.status = LDDReportStatus.REVIEW
            report.analysis_completed_at = datetime.now(timezone.utc)
            report.review_started_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(report)
        return report

    except Exception as exc:
        logger.exception("LDD 보고서 생성 실패: %s", exc)
        # RalphSession 실패 상태 업데이트 (생성 이후 실패한 경우만)
        try:
            ralph_session.status = RalphSessionStatus.FAILED
            ralph_session.error_message = str(exc)[:500]
        except NameError:
            pass  # ralph_session 또는 멀티 LLM 모드에서 실패한 경우
        report.status = LDDReportStatus.FAILED
        report.error_message = str(exc)
        report.analysis_completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(report)
        return report


async def finalize_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LDDFinalizeRequest,
) -> LDDReport:
    """Ralph Loop #2: 사용자 피드백 반영 최종 보고서 Refine.

    1. 상태 검증 (REVIEW만 허용)
    2. 사용자 피드백 수집
    3. Ralph Loop #2 (승인 항목 스킵, 반려/수정 항목만 재분석)
    4. DOCX 렌더링
    5. 상태 → READY
    """
    from app.core.config import settings
    from app.core.exceptions import WorkflowError
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.docx_gate import DOCXProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.ldd.finalize_generator import LDDFinalizeGenerator
    from app.ralph.generators.ldd.section_analyzer import LDDSectionAnalyzer
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.text_extraction_service import TextExtractionService, build_source_map

    report = await get_ldd_report(db, transaction_id, report_id)

    if report.status != LDDReportStatus.REVIEW:
        raise WorkflowError(
            f"최종 확정은 REVIEW 상태에서만 가능합니다 (현재: {report.status})"
        )

    report.status = LDDReportStatus.FINALIZING
    report.finalize_started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        # 1. 사용자 피드백 수집
        sections = copy.deepcopy(report.sections or [])
        user_feedback: dict[str, str] = {}
        approved_items: set[str] = set()

        for section in sections:
            for item in section.get("items", []):
                item_id = item.get("item_id", "")
                if item.get("user_approved") is True:
                    approved_items.add(item_id)
                elif item.get("user_approved") is False:
                    parts = []
                    if item.get("user_comment"):
                        parts.append(f"사용자 피드백: {item['user_comment']}")
                    if item.get("user_override_status"):
                        parts.append(f"사용자가 status를 {item['user_override_status']}로 변경 요청")
                    if item.get("user_override_level"):
                        parts.append(f"사용자가 issue_level을 {item['user_override_level']}로 변경 요청")
                    user_feedback[item_id] = "; ".join(parts) if parts else "사용자 반려 — 재분석 필요"

        # 2. VDR 소스 재로딩 (VDR 기반인 경우)
        parsed_source_map: dict[str, list] = {}
        if report.vdr_source:
            extractor = TextExtractionService()
            source_files = await extractor.extract_from_vdr_documents(db, transaction_id)
            if source_files:
                vdr_source_map = build_source_map(source_files)
                for section_type, vsf_list in vdr_source_map.items():
                    parsed_list = []
                    for vsf in vsf_list:
                        p = copy.copy(vsf.parsed)
                        p.source_path = f"[VDR:{vsf.vdr_document_id}]{vsf.original_name}"
                        parsed_list.append(p)
                    parsed_source_map[section_type] = parsed_list

        # 3. LLM 클라이언트
        llm_client = RalphLLMClient.from_settings(settings)
        llm_call = llm_client.call if llm_client.is_available else None

        learned_patterns: list[str] = []
        try:
            from app.ralph.learning.pattern_aggregator import PatternAggregator
            agg = PatternAggregator(db)
            learned_patterns = await agg.get_learned_patterns("LDD")
        except Exception as exc:
            logger.warning("학습 패턴 조회 실패 (무시): %s", exc)

        analyzer = LDDSectionAnalyzer(llm_call=llm_call, learned_patterns=learned_patterns)

        # 4. LDDFinalizeGenerator (승인 항목 스킵)
        generator = LDDFinalizeGenerator(
            analyzer=analyzer,
            sections_config=sections,
            user_feedback=user_feedback,
            approved_items=approved_items,
        )
        generator.set_source_map(parsed_source_map)

        # 5. 품질 게이트 + Ralph Loop #2
        # user_reviews: 반려된 항목 정보를 게이트에 전달하여 반영 검증
        user_reviews = {
            item_id: {"approved": False, "feedback": fb}
            for item_id, fb in user_feedback.items()
        }
        for item_id in approved_items:
            if item_id not in user_reviews:
                user_reviews[item_id] = {"approved": True, "feedback": ""}

        gates: list = [DOCXProgrammaticGate(user_reviews=user_reviews)]
        if llm_call:
            gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="ldd"))

        convergence_config = ConvergenceConfig(
            max_iterations_per_section=min(body.max_iterations, 3),
            max_cost_usd=min(body.max_cost_usd, 10.0),
        )
        prd = load_prd("ldd_full")

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=gates,
            prd=prd,
            config=LoopConfig(convergence=convergence_config),
        )

        # 5b. RalphSession 레코드 생성 (학습 패턴 축적용)
        from app.models.ralph_session import RalphSession, RalphSessionStatus
        ralph_session = RalphSession(
            id=uuid.UUID(orchestrator.session_id),
            transaction_id=transaction_id,
            doc_type="LDD",  # get_learned_patterns("LDD") 쿼리와 일치
            status=RalphSessionStatus.PLANNING,
            prd=prd,
            config={
                "max_iterations": min(body.max_iterations, 3),
                "max_cost_usd": min(body.max_cost_usd, 10.0),
                "pass": "finalize",
            },
            learned_patterns=learned_patterns or None,
            created_by_email=report.created_by_email,
        )
        db.add(ralph_session)
        await db.flush()

        loop_result = await orchestrator.run(source_data={"transaction_id": str(transaction_id)})

        # 5c. RalphSession 결과 업데이트
        ralph_session.status = loop_result.status.value
        ralph_session.progress = loop_result.progress
        ralph_session.total_iterations = loop_result.total_iterations
        ralph_session.total_cost_usd = loop_result.total_cost_usd
        ralph_session.final_score = loop_result.final_score
        ralph_session.section_scores = loop_result.section_scores
        ralph_session.critical_flags = loop_result.critical_flags
        ralph_session.error_message = (
            "; ".join(loop_result.errors) if loop_result.errors else None
        )

        # 6. 결과 반영
        if loop_result.final_artifact:
            try:
                report_data = json.loads(loop_result.final_artifact)
                ai_sections = report_data.get("sections", {})
                _merge_ai_results(
                    sections, ai_sections,
                    include_ai_meta=True,
                    approved_items=approved_items,
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Ralph Loop #2 결과 파싱 실패: %s", e)

        sections = _compute_risk_colors(sections)
        counts = _compute_counts(sections)

        report.sections = sections
        for k, v in counts.items():
            setattr(report, k, v)

        report.final_ralph_session_id = (
            uuid.UUID(loop_result.session_id) if loop_result.session_id else None
        )
        report.final_score = loop_result.final_score
        report.finalize_completed_at = datetime.now(timezone.utc)

        # 7. DOCX 렌더링
        report = await generate_ldd_report(db, report)
        return report

    except Exception as exc:
        logger.exception("Ralph Loop #2 실패: %s", exc)
        # RalphSession 실패 상태 업데이트 (생성 이후 실패한 경우만)
        try:
            ralph_session.status = RalphSessionStatus.FAILED
            ralph_session.error_message = str(exc)[:500]
        except NameError:
            pass  # ralph_session 생성 이전에 실패한 경우
        report.status = LDDReportStatus.FAILED
        report.error_message = str(exc)
        report.finalize_completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(report)
        return report


async def regenerate_ldd_report(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    report_id: uuid.UUID,
) -> LDDReport:
    """기존 섹션 데이터로 보고서를 재렌더링한다."""
    report = await get_ldd_report(db, transaction_id, report_id)

    if report.file_path:
        try:
            Path(report.file_path).unlink(missing_ok=True)
        except OSError:
            pass
    report.file_path       = None
    report.file_name       = None
    report.file_size_bytes = None

    return await generate_ldd_report(db, report)
