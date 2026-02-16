"""Reports API endpoints."""

import io
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.audit import AuditAction, AuditLog
from app.models.report_version import ReportStatus, ReportVersion
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
    # Report IR 생성
    report_ir = build_report_ir(
        db=db,
        deal_id=deal_id,
        include_qoe=request.include_qoe,
        include_nwc=request.include_nwc,
        include_debt=request.include_debt,
        include_issues=request.include_issues,
    )

    if request.format == "json":
        # JSON IR 반환
        return report_ir_to_dict(report_ir)

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

    # PPTX 생성 (기본값)
    pptx_bytes = await generate_pptx(report_ir)
    filename = f"FDD_Report_{report_ir.metadata.deal_name}.pptx"

    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/generate-word")
def generate_word_report(
    deal_id: UUID,
    include_qoe: bool = True,
    include_nwc: bool = True,
    include_debt: bool = True,
    include_issues: bool = True,
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
    )

    return report_ir_to_dict(report_ir)


# ── Report Versions ──────────────────────────────────────


@router.get("/versions", response_model=list[ReportVersionRead])
def list_report_versions(
    deal_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
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
    current_user: CurrentUser = Depends(get_current_user),
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

    # Build report IR
    report_ir = build_report_ir(
        db=db,
        deal_id=deal_id,
        include_qoe=body.include_qoe,
        include_nwc=body.include_nwc,
        include_debt=body.include_debt,
        include_issues=body.include_issues,
    )

    # Generate file
    file_dir = f"uploads/{deal_id}/reports"
    os.makedirs(file_dir, exist_ok=True)
    file_name = f"v{next_version}.{body.file_format}"
    file_path = f"{file_dir}/{file_name}"

    if body.file_format == "docx":
        docx_buffer = render_word_report(report_ir)
        Path(file_path).write_bytes(docx_buffer.getvalue())
    else:
        pptx_bytes = await generate_pptx(report_ir)
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
    current_user: CurrentUser = Depends(get_current_user),
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
    current_user: CurrentUser = Depends(get_current_user),
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
    else:
        media_type = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

    filename = f"FDD_Report_v{version}.{file_format}"

    return StreamingResponse(
        open(file_path, "rb"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
