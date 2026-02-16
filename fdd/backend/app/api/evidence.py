"""Evidence API — FDD-401, FDD-402, FDD-1401.

EvidenceLink CRUD + 누락 탐지 + Evidence Index 엔드포인트.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.deal import Deal
from app.models.evidence import SourceType
from app.schemas.evidence import (
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
