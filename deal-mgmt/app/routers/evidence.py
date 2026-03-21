"""Platform-wide evidence traceability endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.schemas.evidence import (
    ArtifactEvidenceImportOut,
    ArtifactEvidenceImportRequest,
    ArtifactEvidenceOut,
    ArtifactEvidenceRecordOut,
    ArtifactEvidenceSummaryOut,
)
from app.services import transaction_service
from app.services.evidence_import_service import import_artifact_evidence_records, resolve_external_artifact_id
from app.services.evidence_query_service import list_artifact_evidence, summarize_artifact_evidence

router = APIRouter(prefix="/transactions/{txn_id}/evidence", tags=["Evidence"])


async def _authorize_transaction(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
) -> None:
    txn = await transaction_service.get_transaction(db, txn_id)
    if claims.role == "CLIENT":
        await check_client_deal_access(db, txn_id, claims)
        return
    if claims.role != "ADMIN" and txn.lead_advisor_email != claims.email and txn.deal_captain_email != claims.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 거래의 evidence traceability를 조회할 권한이 없습니다.",
        )


@router.get("/{artifact_type}/{artifact_id}", response_model=ArtifactEvidenceOut)
async def get_artifact_evidence(
    txn_id: uuid.UUID,
    artifact_type: str,
    artifact_id: uuid.UUID,
    workstream: str | None = Query(default=None),
    section_type: str | None = Query(default=None),
    item_id: str | None = Query(default=None),
    analysis_phase: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await _authorize_transaction(db, txn_id, claims)
    records, used_legacy_fallback = await list_artifact_evidence(
        db,
        transaction_id=txn_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        workstream=workstream,
        section_type=section_type,
        item_id=item_id,
        analysis_phase=analysis_phase,
    )
    return ArtifactEvidenceOut(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        used_legacy_fallback=used_legacy_fallback,
        summary=ArtifactEvidenceSummaryOut(**summarize_artifact_evidence(records)),
        records=[ArtifactEvidenceRecordOut(**record) for record in records],
    )


@router.post("/import", response_model=ArtifactEvidenceImportOut, status_code=status.HTTP_202_ACCEPTED)
async def import_artifact_evidence(
    txn_id: uuid.UUID,
    body: ArtifactEvidenceImportRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _authorize_transaction(db, txn_id, claims)

    artifact_type = body.artifact_type.strip().upper()
    try:
        artifact_id = resolve_external_artifact_id(
            transaction_id=txn_id,
            artifact_type=artifact_type,
            artifact_id=body.artifact_id,
            external_artifact_ref=body.external_artifact_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raw_records = [record.model_dump(mode="python") for record in body.records]
    imported_count = await import_artifact_evidence_records(
        db,
        transaction_id=txn_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        default_workstream=body.default_workstream,
        records=raw_records,
    )
    await db.commit()
    return ArtifactEvidenceImportOut(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        imported_count=imported_count,
    )
