"""Evidence API — FDD-401, FDD-402, FDD-1401.

EvidenceLink CRUD + 누락 탐지 + Evidence Index 엔드포인트.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.deal import Deal
from app.models.evidence import SourceType
from app.models.report_version import ReportVersion
from app.models.upload import UploadFile
from app.schemas.evidence import (
    EvidenceExportRecord,
    EvidenceExportResponse,
    EvidenceLinkBulkCreate,
    EvidenceLinkCreate,
    EvidenceLinkRead,
)
from app.services.evidence.detector import DetectionResult, detect_missing_evidence
from app.services.evidence.index_builder import (
    build_evidence_index,
    get_evidence_coverage_stats,
)
from app.services.evidence.ledger_service import (
    bulk_create_evidence_links,
    create_evidence_link,
    delete_evidence_link,
    get_evidence_link,
    list_evidence_links,
)

router = APIRouter()


# ── EvidenceLink CRUD ────────────────────────────────────


@router.post(
    "/deals/{deal_id}/evidence-links",
    response_model=EvidenceLinkRead,
    status_code=201,
)
def create_link(
    deal_id: uuid.UUID,
    body: EvidenceLinkCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """단일 EvidenceLink를 생성한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    link = create_evidence_link(db, deal_id, body)
    return link


@router.post(
    "/deals/{deal_id}/evidence-links/bulk",
    response_model=list[EvidenceLinkRead],
    status_code=201,
)
def create_links_bulk(
    deal_id: uuid.UUID,
    body: EvidenceLinkBulkCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """EvidenceLink를 일괄 생성한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    links = bulk_create_evidence_links(db, deal_id, body.links)
    return links


@router.get(
    "/deals/{deal_id}/evidence-links",
    response_model=list[EvidenceLinkRead],
)
def list_links(
    deal_id: uuid.UUID,
    target_type: str | None = Query(default=None),
    target_id: uuid.UUID | None = Query(default=None),
    source_type: SourceType | None = Query(default=None),
    snapshot_id: uuid.UUID | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """EvidenceLink를 조건별로 조회한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    links = list_evidence_links(
        db,
        deal_id,
        target_type=target_type,
        target_id=target_id,
        source_type=source_type,
        snapshot_id=snapshot_id,
    )
    return links


# ── Evidence Missing Detection (must be before /{link_id}) ──


@router.get(
    "/deals/{deal_id}/evidence-links/missing",
)
def detect_missing(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """매핑에 대한 evidence 누락을 탐지한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    result: DetectionResult = detect_missing_evidence(db, deal_id)
    return {
        "deal_id": str(result.deal_id),
        "total_targets_checked": result.total_targets_checked,
        "missing_count": result.missing_count,
        "coverage_percentage": result.coverage_percentage,
        "missing": [
            {
                "target_type": m.target_type,
                "target_id": str(m.target_id),
                "target_label": m.target_label,
                "reason": m.reason,
            }
            for m in result.missing
        ],
    }


# ── Single item endpoints ────────────────────────────────


@router.get(
    "/deals/{deal_id}/evidence-links/{link_id}",
    response_model=EvidenceLinkRead,
)
def get_link(
    deal_id: uuid.UUID,
    link_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """단일 EvidenceLink를 조회한다."""
    link = get_evidence_link(db, link_id)
    if link is None or link.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Evidence link not found")
    return link


@router.delete(
    "/deals/{deal_id}/evidence-links/{link_id}",
    status_code=204,
)
def delete_link(
    deal_id: uuid.UUID,
    link_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """EvidenceLink를 삭제한다."""
    link = get_evidence_link(db, link_id)
    if link is None or link.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    delete_evidence_link(db, link)


# ── Evidence Index (FDD-1401) ────────────────────────────


@router.get("/deals/{deal_id}/evidence-index")
def get_evidence_index(
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Deal의 Evidence Index를 생성한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    index = build_evidence_index(db, deal_id, snapshot_id=snapshot_id)
    return {
        "deal_id": index.deal_id,
        "total_count": index.total_count,
        "by_source_type": index.by_source_type,
        "by_target_type": index.by_target_type,
        "entries": [
            {
                "evidence_id": e.evidence_id,
                "source_type": e.source_type,
                "source_id": e.source_id,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "referenced_in": [
                    {"section_id": r.section_id, "block_id": r.block_id}
                    for r in e.referenced_in
                ],
            }
            for e in index.entries
        ],
    }


@router.get("/deals/{deal_id}/evidence-coverage")
def get_coverage(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Evidence 커버리지 통계를 반환한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    return get_evidence_coverage_stats(db, deal_id)


def _map_section_type(target_type: str) -> str | None:
    value = target_type.lower()
    if value.startswith("qoe"):
        return "QOE"
    if value.startswith("nwc"):
        return "NWC"
    if "debt" in value:
        return "DEBT"
    if "issue" in value or "anomaly" in value:
        return "ISSUES"
    if "checklist" in value:
        return "CHECKLIST"
    if "revenue" in value:
        return "REVENUE"
    return None


def _map_evidence_kind(source_type: SourceType) -> str:
    return {
        SourceType.FILE: "uploaded_file",
        SourceType.TB: "trial_balance",
        SourceType.GL: "general_ledger",
        SourceType.PDF: "pdf_extract",
    }.get(source_type, source_type.value.lower())


def _map_directness(source_type: SourceType) -> str:
    if source_type in {SourceType.FILE, SourceType.PDF}:
        return "DIRECT"
    return "INDIRECT"


def _derive_source_page(source_detail: dict | None) -> str | None:
    if not source_detail:
        return None
    if source_detail.get("page") is not None:
        return str(source_detail["page"])
    if source_detail.get("sheet"):
        row = source_detail.get("row")
        return f"{source_detail['sheet']}:{row}" if row is not None else str(source_detail["sheet"])
    if source_detail.get("row") is not None:
        return f"row:{source_detail['row']}"
    return None


def _derive_reference_label(link, original_name: str | None) -> str:
    prefix = link.target_type.replace("_", " ").upper()
    if original_name:
        return f"{prefix} - {original_name}"
    return f"{prefix} - {link.source_type.value}:{link.source_id}"


@router.get(
    "/deals/{deal_id}/evidence-export",
    response_model=EvidenceExportResponse,
)
def export_evidence(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export normalized evidence payload for cross-service consumers such as MA."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    links = list_evidence_links(db, deal_id)
    upload_ids: list[uuid.UUID] = []
    for link in links:
        if link.source_type != SourceType.FILE:
            continue
        try:
            upload_ids.append(uuid.UUID(str(link.source_id)))
        except (TypeError, ValueError):
            continue

    upload_name_by_id: dict[str, str] = {}
    if upload_ids:
        uploads = db.scalars(select(UploadFile).where(UploadFile.id.in_(upload_ids))).all()
        upload_name_by_id = {str(upload.id): upload.original_filename for upload in uploads}

    latest_report_id = db.scalar(
        select(ReportVersion.id)
        .where(ReportVersion.deal_id == deal_id)
        .order_by(desc(ReportVersion.created_at))
        .limit(1)
    )

    records: list[EvidenceExportRecord] = []
    for ordinal, link in enumerate(links, start=1):
        source_detail = link.source_detail if isinstance(link.source_detail, dict) else None
        original_name = upload_name_by_id.get(str(link.source_id))
        records.append(
            EvidenceExportRecord(
                workstream="FDD",
                section_type=_map_section_type(link.target_type),
                item_id=str(link.target_id),
                reference_label=_derive_reference_label(link, original_name),
                original_name=original_name,
                primary_workstream="FDD",
                workstream_tags=["FDD"],
                evidence_kind=_map_evidence_kind(link.source_type),
                directness=_map_directness(link.source_type),
                confidence=1.0,
                relevance_score=1.0,
                source_page=_derive_source_page(source_detail),
                source_snippet=(source_detail or {}).get("snippet"),
                evidence_locator=source_detail,
                used_in_draft=True,
                used_in_final=latest_report_id is not None,
                analysis_phase="FINAL" if latest_report_id is not None else "DRAFT",
                ordinal=ordinal,
                chunk_id=(source_detail or {}).get("chunk_id"),
            )
        )

    return EvidenceExportResponse(
        artifact_type="FDD_REPORT",
        artifact_id=latest_report_id,
        external_artifact_ref=f"fdd-deal-{deal_id}",
        default_workstream="FDD",
        records=records,
    )
