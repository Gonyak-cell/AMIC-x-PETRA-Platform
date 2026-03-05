"""Reports API endpoints."""

import asyncio
import io
import os
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.config import settings
from app.core.logging import get_logger
from app.database import get_db
from app.models.analysis_run import AnalysisRun
from app.models.audit import AuditAction, AuditLog
from app.models.report_version import ReportStatus, ReportVersion
from app.renderers.excel_renderer import render_excel_report
from app.renderers.report_builder import report_ir_to_dict
from app.renderers.word_renderer import render_word_report
from app.schemas.report import (
    ReportGenerateRequest,
    ReportPreviewResponse,
)
from app.schemas.report_version import (
    ReportVersionCreate,
    ReportVersionFinalize,
    ReportVersionRead,
)
from app.services.report.report_service import build_report_ir, generate_pptx

logger = get_logger(__name__)

router = APIRouter(prefix="/deals/{deal_id}/reports", tags=["reports"])


@router.post("/generate")
async def generate_report(
    deal_id: UUID,
    request: ReportGenerateRequest,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
):
    """FDD 보고서 생성.

    Args:
        deal_id: Deal UUID
        request: 보고서 생성 요청

    Returns:
        format=pptx: PPTX 파일 다운로드
        format=docx: DOCX 파일 다운로드
        format=json: Report IR JSON
    """
    # Report IR 생성 (이벤트 루프 블로킹 방지: threadpool에서 실행)
    report_ir = await asyncio.to_thread(
        partial(
            build_report_ir,
            db=db,
            deal_id=deal_id,
            include_qoe=request.include_qoe,
            include_nwc=request.include_nwc,
            include_debt=request.include_debt,
            include_issues=request.include_issues,
            include_financial_statements=request.include_financial_statements,
            include_trends=request.include_trends,
            include_sales_analysis=request.include_sales_analysis,
            include_multiperiod=request.include_multiperiod,
            include_revenue_deepdive=request.include_revenue_deepdive,
            include_cost_structure=request.include_cost_structure,
            include_fcf=request.include_fcf,
            include_backlog=request.include_backlog,
            include_consolidation_enhanced=request.include_consolidation_enhanced,
            use_llm_narratives=request.use_llm_narratives,
            use_template_slotfill=request.use_template_slotfill,
        )
    )

    # Ralph Loop Pass 1: Draft Refinement
    ir_dict = None
    if request.ralph_enabled:
        from app.services.ralph_service import FDDRalphService

        ralph_service = FDDRalphService(db)
        ralph_config = (
            request.ralph_config.model_dump() if request.ralph_config else None
        )
        refined_ir, _ralph_session = await ralph_service.run_draft_pass(
            deal_id=deal_id,
            report_ir=report_ir,
            config=ralph_config,
            actor=current_user.email,
        )
        ir_dict = refined_ir  # Ralph가 반환한 Refined IR dict 사용

    # Refined IR 텍스트를 ReportIR 객체에 패치 (docx/xlsx/pptx 렌더러에도 반영)
    if ir_dict:
        _patch_report_ir(report_ir, ir_dict)

    # QA 팩트체크 (활성화된 경우)
    qa_warnings: list[dict] = []
    if request.qa_enabled:
        import json as _json

        from app.agents.report_qa import ReportQAAgent
        from app.services.llm.routing import create_fdd_model_router

        try:
            router = create_fdd_model_router()
            qa_agent = ReportQAAgent(router=router)
            qa_context = {
                "deal_name": report_ir.metadata.deal_name,
                "report_ir_json": _json.dumps(
                    ir_dict if ir_dict else report_ir_to_dict(report_ir),
                    ensure_ascii=False,
                    default=str,
                ),
                "qoe_summary": None,
                "nwc_summary": None,
                "debt_summary": None,
            }
            qa_response = qa_agent.run(qa_context)
            if qa_response.success and qa_response.result:
                score = qa_response.result.get("overall_score", 5)
                if score < 3:
                    qa_warnings = qa_response.result.get("issues", [])
                # 최근 AnalysisRun에 QA 결과 저장
                latest_run = db.scalar(
                    select(AnalysisRun)
                    .where(AnalysisRun.deal_id == deal_id)
                    .order_by(AnalysisRun.created_at.desc())
                    .limit(1)
                )
                if latest_run:
                    latest_run.qa_result = qa_response.result
                    db.commit()
        except Exception as e:
            logger.warning("Report QA failed: %s", e)

    if request.format == "json":
        result = ir_dict if ir_dict else report_ir_to_dict(report_ir)
        if qa_warnings:
            result["qa_warnings"] = qa_warnings
        return result

    if request.format == "docx":
        # Word 문서 생성
        docx_buffer = render_word_report(report_ir)
        filename = f"FDD_Report_{report_ir.metadata.deal_name}.docx"

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    if request.format == "xlsx":
        # Excel 문서 생성
        # 체크리스트 데이터 로드 (있으면)
        checklist_data = None
        if request.checklist_id:
            from app.models.fdd_checklist import FddChecklist

            checklist = (
                db.query(FddChecklist)
                .filter(
                    FddChecklist.id == request.checklist_id,
                    FddChecklist.deal_id == deal_id,
                )
                .first()
            )
            if checklist:
                checklist_data = {
                    "items": [
                        {
                            "category": item.category.value,
                            "title": item.title,
                            "description": item.description,
                            "auto_finding": item.auto_finding or "",
                            "auto_amount": str(item.auto_amount)
                            if item.auto_amount
                            else "",
                            "user_correction": item.user_correction or "",
                            "user_amount": str(item.user_amount)
                            if item.user_amount
                            else "",
                            "status": item.status.value,
                            "severity": item.severity.value if item.severity else "",
                        }
                        for item in checklist.items
                    ]
                }

        xlsx_buffer = render_excel_report(
            report_ir,
            checklist_data=checklist_data["items"] if checklist_data else None,
        )
        filename = f"FDD_Report_{report_ir.metadata.deal_name}.xlsx"

        return StreamingResponse(
            xlsx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    # PPTX 생성 (기본값)
    pptx_bytes = await generate_pptx(
        report_ir, pptx_service_url=settings.pptx_service_url
    )
    filename = f"FDD_Report_{report_ir.metadata.deal_name}.pptx"

    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _patch_report_ir(report_ir, ir_dict: dict) -> None:
    """Ralph refined IR dict의 텍스트를 원본 ReportIR 객체에 in-place 패치한다.

    Renderers(docx/xlsx/pptx)는 ReportIR 객체를 받으므로, Ralph Loop이
    개선한 텍스트를 객체에 직접 반영해야 한다.
    """
    refined_sections = ir_dict.get("sections", [])
    for idx, section in enumerate(report_ir.sections):
        if idx >= len(refined_sections):
            break
        refined = refined_sections[idx]
        block_type = refined.get("type", "")

        if block_type == "text":
            if "content" in refined:
                section.content = refined["content"]
            if "bullet_points" in refined and isinstance(
                refined["bullet_points"], list
            ):
                section.bullet_points = refined["bullet_points"]

        elif block_type == "claim":
            if "claim_text" in refined:
                section.claim_text = refined["claim_text"]

        elif block_type == "issue":
            refined_issues = refined.get("issues", [])
            for i, issue in enumerate(section.issues):
                if i < len(refined_issues):
                    ri = refined_issues[i]
                    if "description" in ri:
                        issue.description = ri["description"]
                    if "recommendation" in ri:
                        issue.recommendation = ri["recommendation"]


@router.post("/generate-word")
def generate_word_report(
    deal_id: UUID,
    include_qoe: bool = True,
    include_nwc: bool = True,
    include_debt: bool = True,
    include_issues: bool = True,
    include_financial_statements: bool = True,
    include_trends: bool = True,
    include_sales_analysis: bool = True,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
):
    """Word(DOCX) 보고서 생성.

    Args:
        deal_id: Deal UUID
        include_qoe: QoE 섹션 포함
        include_nwc: NWC 섹션 포함
        include_debt: Net Debt 섹션 포함
        include_issues: Issue Log 포함
        include_financial_statements: 재무제표(IS/BS/CF) 포함
        include_trends: 다기간 트렌드 포함
        include_sales_analysis: 매출/원가 분석 포함

    Returns:
        DOCX 파일 다운로드
    """
    report_ir = build_report_ir(
        db=db,
        deal_id=deal_id,
        include_qoe=include_qoe,
        include_nwc=include_nwc,
        include_debt=include_debt,
        include_issues=include_issues,
        include_financial_statements=include_financial_statements,
        include_trends=include_trends,
        include_sales_analysis=include_sales_analysis,
    )

    docx_buffer = render_word_report(report_ir)
    filename = f"FDD_Report_{report_ir.metadata.deal_name}.docx"

    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/preview", response_model=ReportPreviewResponse)
def preview_report(
    deal_id: UUID,
    include_qoe: bool = True,
    include_nwc: bool = True,
    include_debt: bool = True,
    include_issues: bool = True,
    include_financial_statements: bool = True,
    include_trends: bool = True,
    include_sales_analysis: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """보고서 미리보기 (섹션 목록).

    Args:
        deal_id: Deal UUID

    Returns:
        섹션 목록 및 메타데이터
    """
    report_ir = build_report_ir(
        db=db,
        deal_id=deal_id,
        include_qoe=include_qoe,
        include_nwc=include_nwc,
        include_debt=include_debt,
        include_issues=include_issues,
        include_financial_statements=include_financial_statements,
        include_trends=include_trends,
        include_sales_analysis=include_sales_analysis,
    )

    ir_dict = report_ir_to_dict(report_ir)

    sections_preview = []
    for section in ir_dict["sections"]:
        sections_preview.append(
            {
                "type": section.get("type"),
                "title": section.get("title")
                or section.get("deal_name")
                or section.get("claim_text", "")[:50],
            }
        )

    return ReportPreviewResponse(
        deal_id=str(deal_id),
        deal_name=report_ir.metadata.deal_name,
        sections_count=len(report_ir.sections),
        sections=sections_preview,
    )


@router.get("/ir")
def get_report_ir(
    deal_id: UUID,
    include_qoe: bool = True,
    include_nwc: bool = True,
    include_debt: bool = True,
    include_issues: bool = True,
    include_financial_statements: bool = True,
    include_trends: bool = True,
    include_sales_analysis: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Report IR JSON 조회.

    Args:
        deal_id: Deal UUID

    Returns:
        Report IR JSON
    """
    report_ir = build_report_ir(
        db=db,
        deal_id=deal_id,
        include_qoe=include_qoe,
        include_nwc=include_nwc,
        include_debt=include_debt,
        include_issues=include_issues,
        include_financial_statements=include_financial_statements,
        include_trends=include_trends,
        include_sales_analysis=include_sales_analysis,
    )

    return report_ir_to_dict(report_ir)


# ── Report Versions ──────────────────────────────────────


@router.get("/versions", response_model=list[ReportVersionRead])
def list_report_versions(
    deal_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """List report versions for a deal.

    Args:
        deal_id: Deal UUID.

    Returns:
        List of report versions ordered by version descending.
    """
    stmt = (
        select(ReportVersion)
        .where(ReportVersion.deal_id == deal_id)
        .order_by(ReportVersion.version.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("/versions", response_model=ReportVersionRead, status_code=201)
async def create_report_version(
    deal_id: UUID,
    body: ReportVersionCreate,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
):
    """Create a new report version.

    Generates the report file and saves it to disk. The version number
    is auto-incremented. New versions start as DRAFT.

    Args:
        deal_id: Deal UUID.
        body: Report version creation options.

    Returns:
        Created report version record.
    """
    # Determine next version number
    latest_version = db.scalar(
        select(ReportVersion.version)
        .where(ReportVersion.deal_id == deal_id)
        .order_by(ReportVersion.version.desc())
        .limit(1)
    )
    next_version = (latest_version or 0) + 1

    # Build report IR (이벤트 루프 블로킹 방지: threadpool에서 실행)
    report_ir = await asyncio.to_thread(
        partial(
            build_report_ir,
            db=db,
            deal_id=deal_id,
            include_qoe=body.include_qoe,
            include_nwc=body.include_nwc,
            include_debt=body.include_debt,
            include_issues=body.include_issues,
            include_financial_statements=body.include_financial_statements,
            include_trends=body.include_trends,
            include_sales_analysis=body.include_sales_analysis,
        )
    )

    # Generate file
    file_dir = f"uploads/{deal_id}/reports"
    os.makedirs(file_dir, exist_ok=True)
    file_name = f"v{next_version}.{body.file_format}"
    file_path = f"{file_dir}/{file_name}"

    if body.file_format == "docx":
        docx_buffer = render_word_report(report_ir)
        Path(file_path).write_bytes(docx_buffer.getvalue())
    elif body.file_format == "xlsx":
        xlsx_buffer = render_excel_report(report_ir)
        Path(file_path).write_bytes(xlsx_buffer.getvalue())
    else:
        pptx_bytes = await generate_pptx(
            report_ir, pptx_service_url=settings.pptx_service_url
        )
        Path(file_path).write_bytes(pptx_bytes)

    # Create DB record
    report_version = ReportVersion(
        deal_id=deal_id,
        version=next_version,
        status=ReportStatus.DRAFT,
        file_path=file_path,
        file_format=body.file_format,
        options={
            "include_qoe": body.include_qoe,
            "include_nwc": body.include_nwc,
            "include_debt": body.include_debt,
            "include_issues": body.include_issues,
        },
        notes=body.notes,
        created_by=current_user.email,
    )
    db.add(report_version)
    db.flush()

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="report_version",
            entity_id=report_version.id,
            action=AuditAction.CREATE,
            actor=current_user.email,
            new_value={
                "version": next_version,
                "file_format": body.file_format,
                "status": ReportStatus.DRAFT.value,
            },
        )
    )

    db.commit()
    db.refresh(report_version)
    return report_version


@router.put("/versions/{version}/finalize", response_model=ReportVersionRead)
def finalize_report_version(
    deal_id: UUID,
    version: int,
    body: ReportVersionFinalize,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
):
    """Finalize a report version, marking it as FINAL.

    Args:
        deal_id: Deal UUID.
        version: Version number to finalize.
        body: Optional finalization notes.

    Returns:
        Updated report version.
    """
    stmt = select(ReportVersion).where(
        ReportVersion.deal_id == deal_id,
        ReportVersion.version == version,
    )
    report_version = db.scalar(stmt)
    if report_version is None:
        raise HTTPException(status_code=404, detail="Report version not found")

    if report_version.status == ReportStatus.FINAL:
        raise HTTPException(
            status_code=400,
            detail="Report version is already finalized",
        )

    old_status = report_version.status.value
    report_version.status = ReportStatus.FINAL
    report_version.finalized_at = datetime.now(UTC)
    if body.notes is not None:
        report_version.notes = body.notes

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="report_version",
            entity_id=report_version.id,
            action=AuditAction.APPROVE,
            actor=current_user.email,
            old_value={"status": old_status},
            new_value={"status": ReportStatus.FINAL.value},
        )
    )

    db.commit()
    db.refresh(report_version)
    return report_version


@router.get("/versions/{version}/download")
def download_report_version(
    deal_id: UUID,
    version: int,
    current_user: CurrentUser = require_permission(Permission.REPORT_DOWNLOAD),
    db: Session = Depends(get_db),
):
    """Download a report version file.

    Args:
        deal_id: Deal UUID.
        version: Version number to download.

    Returns:
        File download as StreamingResponse.
    """
    stmt = select(ReportVersion).where(
        ReportVersion.deal_id == deal_id,
        ReportVersion.version == version,
    )
    report_version = db.scalar(stmt)
    if report_version is None:
        raise HTTPException(status_code=404, detail="Report version not found")

    if not report_version.file_path or not Path(report_version.file_path).exists():
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    file_path = Path(report_version.file_path)
    file_format = report_version.file_format

    if file_format == "docx":
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    elif file_format == "xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

    filename = f"FDD_Report_v{version}.{file_format}"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
