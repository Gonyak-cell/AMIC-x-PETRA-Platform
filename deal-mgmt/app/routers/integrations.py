"""Integration routes for FDD, IM, and KIIS services."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_fdd_client, get_im_client, get_kiis_client
from app.core.security import JWTClaims, get_jwt_claims, require_write_access
from app.models.enums import AuditAction
from app.services import audit_service, transaction_service
from app.services.evidence_import_service import import_artifact_evidence_records, resolve_external_artifact_id
from app.services.protocols import FDDClientProtocol, IMClientProtocol, KIISClientProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}/integrations", tags=["Integrations"])


class FDDLinkRequest(BaseModel):
    target_name: str
    industry: str | None = None


class IMLinkRequest(BaseModel):
    company_name: str
    project_name: str
    corp_code: str | None = None


class IntegrationResult(BaseModel):
    service: str
    status: str
    data: dict | None = None
    error: str | None = None


def _forbid_client_role(claims: JWTClaims) -> None:
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="Clients cannot use this integration endpoint.")


def _linked_fdd_deal_id(txn) -> uuid.UUID:
    raw_deal_id = (txn.fdd_deal_id or "").strip()
    if not raw_deal_id:
        raise HTTPException(status_code=409, detail="FDD deal is not linked for this transaction.")
    try:
        return uuid.UUID(raw_deal_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Stored FDD deal id is invalid.") from exc


@router.post("/fdd/link", response_model=IntegrationResult)
async def link_fdd(
    txn_id: uuid.UUID,
    body: FDDLinkRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    _forbid_client_role(claims)
    txn = await transaction_service.get_transaction(db, txn_id)
    try:
        result = await fdd.create_deal(body.target_name, body.industry)
        linked_deal_id = str(result.get("id") or "").strip()
        if linked_deal_id:
            txn.fdd_deal_id = linked_deal_id
        await audit_service.record(
            db,
            entity_type="Transaction",
            entity_id=txn.id,
            action=AuditAction.SERVICE_LINKED,
            actor_email=claims.email,
            new_value={"service": "FDD", "result": result},
        )
        await db.commit()
        return IntegrationResult(service="FDD", status="linked", data=result)
    except Exception as exc:
        logger.warning("FDD link failed for txn %s: %s", txn_id, exc)
        raise HTTPException(status_code=502, detail="FDD service link failed.") from exc


@router.post("/fdd/uploads", response_model=IntegrationResult)
async def upload_fdd_file(
    txn_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    _forbid_client_role(claims)
    txn = await transaction_service.get_transaction(db, txn_id)
    deal_id = _linked_fdd_deal_id(txn)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty files cannot be uploaded to FDD.")
    try:
        result = await fdd.upload_file(
            deal_id,
            file.filename or "upload.xlsx",
            content,
            file.content_type or "application/octet-stream",
        )
        return IntegrationResult(service="FDD", status="uploaded", data=result)
    except Exception as exc:
        logger.warning("FDD upload failed for txn %s: %s", txn_id, exc)
        raise HTTPException(status_code=502, detail="FDD upload failed.") from exc


@router.post("/fdd/uploads/{upload_id}/ingest", response_model=IntegrationResult)
async def ingest_fdd_upload(
    txn_id: uuid.UUID,
    upload_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    _forbid_client_role(claims)
    txn = await transaction_service.get_transaction(db, txn_id)
    deal_id = _linked_fdd_deal_id(txn)
    try:
        result = await fdd.ingest_upload(deal_id, upload_id)
        return IntegrationResult(service="FDD", status="ingested", data=result)
    except Exception as exc:
        logger.warning("FDD upload ingest failed for txn %s upload %s: %s", txn_id, upload_id, exc)
        raise HTTPException(status_code=502, detail="FDD upload ingest failed.") from exc


@router.post("/fdd/evidence-sync", response_model=IntegrationResult)
async def sync_fdd_evidence(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    _forbid_client_role(claims)
    txn = await transaction_service.get_transaction(db, txn_id)
    raw_deal_id = (txn.fdd_deal_id or "").strip()
    if not raw_deal_id:
        raise HTTPException(status_code=409, detail="FDD deal is not linked for this transaction.")

    try:
        deal_id = uuid.UUID(raw_deal_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Stored FDD deal id is invalid.") from exc

    try:
        payload = await fdd.get_evidence_export(deal_id)
        artifact_type = str(payload.get("artifact_type") or "FDD_REPORT").strip().upper()
        default_workstream = str(payload.get("default_workstream") or "FDD").strip().upper()
        artifact_id = resolve_external_artifact_id(
            transaction_id=txn_id,
            artifact_type=artifact_type,
            external_artifact_ref=str(payload.get("external_artifact_ref") or deal_id),
        )
        imported_count = await import_artifact_evidence_records(
            db,
            transaction_id=txn_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            default_workstream=default_workstream,
            records=list(payload.get("records") or []),
        )
        await audit_service.record(
            db,
            entity_type="Transaction",
            entity_id=txn.id,
            action=AuditAction.SERVICE_LINKED,
            actor_email=claims.email,
            new_value={
                "service": "FDD",
                "evidence_sync": {
                    "artifact_type": artifact_type,
                    "artifact_id": str(artifact_id),
                    "imported_count": imported_count,
                },
            },
        )
        await db.commit()
        return IntegrationResult(
            service="FDD",
            status="synced",
            data={
                "artifact_type": artifact_type,
                "artifact_id": str(artifact_id),
                "imported_count": imported_count,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("FDD evidence sync failed for txn %s: %s", txn_id, exc)
        raise HTTPException(status_code=502, detail="FDD evidence sync failed.") from exc


@router.get("/fdd/status", response_model=IntegrationResult)
async def fdd_status(
    txn_id: uuid.UUID,
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    _forbid_client_role(claims)
    await transaction_service.get_transaction(db, txn_id)
    try:
        result = await fdd.get_deal_status(deal_id)
        return IntegrationResult(service="FDD", status="ok", data=result)
    except Exception as exc:
        logger.warning("FDD status query failed for txn %s, deal %s: %s", txn_id, deal_id, exc)
        raise HTTPException(status_code=502, detail="FDD status query failed.") from exc


@router.post("/im/link", response_model=IntegrationResult)
async def link_im(
    txn_id: uuid.UUID,
    body: IMLinkRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    im: IMClientProtocol = Depends(get_im_client),
):
    _forbid_client_role(claims)
    txn = await transaction_service.get_transaction(db, txn_id)
    try:
        result = await im.create_document(body.company_name, body.project_name, body.corp_code)
        linked_document_id = str(result.get("id") or "").strip()
        if linked_document_id:
            txn.im_document_id = linked_document_id
        await audit_service.record(
            db,
            entity_type="Transaction",
            entity_id=txn.id,
            action=AuditAction.SERVICE_LINKED,
            actor_email=claims.email,
            new_value={"service": "IM", "result": result},
        )
        await db.commit()
        return IntegrationResult(service="IM", status="linked", data=result)
    except Exception as exc:
        logger.warning("IM link failed for txn %s: %s", txn_id, exc)
        raise HTTPException(status_code=502, detail="IM service link failed.") from exc


@router.get("/im/status", response_model=IntegrationResult)
async def im_status(
    txn_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    im: IMClientProtocol = Depends(get_im_client),
):
    _forbid_client_role(claims)
    await transaction_service.get_transaction(db, txn_id)
    try:
        result = await im.get_document_status(document_id)
        return IntegrationResult(service="IM", status="ok", data=result)
    except Exception as exc:
        logger.warning("IM status query failed for txn %s, doc %s: %s", txn_id, document_id, exc)
        raise HTTPException(status_code=502, detail="IM status query failed.") from exc


@router.get("/kiis/company", response_model=IntegrationResult)
async def kiis_company_search(
    txn_id: uuid.UUID,
    q: str,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    kiis: KIISClientProtocol = Depends(get_kiis_client),
):
    _forbid_client_role(claims)
    await transaction_service.get_transaction(db, txn_id)
    try:
        results = await kiis.search_company(q)
        return IntegrationResult(service="KIIS", status="ok", data={"items": results})
    except Exception as exc:
        logger.warning("KIIS company search failed for txn %s, q=%s: %s", txn_id, q, exc)
        raise HTTPException(status_code=502, detail="KIIS company search failed.") from exc
