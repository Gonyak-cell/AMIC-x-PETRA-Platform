"""FDD/IM/KIIS 서비스 연동 라우터."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_fdd_client, get_im_client, get_kiis_client
from app.core.security import JWTClaims, get_jwt_claims, require_write_access
from app.models.enums import AuditAction
from app.schemas.evidence import ArtifactEvidenceImportRequest
from app.services import audit_service, transaction_service
from app.services.evidence_import_service import import_artifact_evidence_records, resolve_external_artifact_id
from app.services.protocols import FDDClientProtocol, IMClientProtocol, KIISClientProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}/integrations", tags=["Integrations"])


# ── Request / Response schemas ───────────────────────────


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


class FDDEvidenceSyncRequest(BaseModel):
    deal_id: uuid.UUID | None = None
    artifact_id: uuid.UUID | None = None
    external_artifact_ref: str | None = None
    artifact_type: str = "FDD_REPORT"
    default_workstream: str = "FDD"


# ── FDD ──────────────────────────────────────────────────


@router.post("/fdd/link", response_model=IntegrationResult)
async def link_fdd(
    txn_id: uuid.UUID,
    body: FDDLinkRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    """FDD Deal 생성/연결."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    txn = await transaction_service.get_transaction(db, txn_id)
    try:
        result = await fdd.create_deal(body.target_name, body.industry)
        if result.get("id"):
            txn.fdd_deal_id = str(result["id"])
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
    except Exception as e:
        logger.warning("FDD link failed for txn %s: %s", txn_id, e)
        raise HTTPException(status_code=502, detail="FDD 서비스 연결에 실패했습니다") from e


@router.get("/fdd/status", response_model=IntegrationResult)
async def fdd_status(
    txn_id: uuid.UUID,
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    """FDD 분석 상태 조회."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    await transaction_service.get_transaction(db, txn_id)
    try:
        result = await fdd.get_deal_status(deal_id)
        return IntegrationResult(service="FDD", status="ok", data=result)
    except Exception as e:
        logger.warning("FDD status query failed for txn %s, deal %s: %s", txn_id, deal_id, e)
        raise HTTPException(status_code=502, detail="FDD 상태 조회에 실패했습니다") from e


@router.post("/fdd/evidence-sync", response_model=IntegrationResult)
async def sync_fdd_evidence(
    txn_id: uuid.UUID,
    body: FDDEvidenceSyncRequest | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    fdd: FDDClientProtocol = Depends(get_fdd_client),
):
    """Pull FDD evidence export and import it into common evidence_records."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")

    txn = await transaction_service.get_transaction(db, txn_id)
    raw_deal_id = body.deal_id if body and body.deal_id else txn.fdd_deal_id
    if not raw_deal_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No linked FDD deal id found for this transaction.",
        )

    try:
        deal_id = raw_deal_id if isinstance(raw_deal_id, uuid.UUID) else uuid.UUID(str(raw_deal_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid FDD deal id.") from exc

    try:
        export_payload = await fdd.get_evidence_export(deal_id)
    except Exception as e:
        logger.warning("FDD evidence export failed for txn %s, deal %s: %s", txn_id, deal_id, e)
        raise HTTPException(status_code=502, detail="FDD evidence export fetch failed.") from e

    try:
        import_body = ArtifactEvidenceImportRequest.model_validate(export_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid FDD evidence export payload: {exc}",
        ) from exc

    artifact_type = (body.artifact_type if body else import_body.artifact_type).strip().upper()
    default_workstream = body.default_workstream if body else import_body.default_workstream
    try:
        artifact_id = resolve_external_artifact_id(
            transaction_id=txn.id,
            artifact_type=artifact_type,
            artifact_id=body.artifact_id if body else import_body.artifact_id,
            external_artifact_ref=(
                body.external_artifact_ref if body and body.external_artifact_ref else import_body.external_artifact_ref
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    records = [record.model_dump(mode="python") for record in import_body.records]
    imported_count = await import_artifact_evidence_records(
        db,
        transaction_id=txn.id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        default_workstream=default_workstream,
        records=records,
    )
    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={
            "service": "FDD",
            "action": "evidence_sync",
            "deal_id": str(deal_id),
            "artifact_type": artifact_type,
            "artifact_id": str(artifact_id),
            "imported_count": imported_count,
        },
    )
    await db.commit()
    return IntegrationResult(
        service="FDD",
        status="synced",
        data={
            "deal_id": str(deal_id),
            "artifact_type": artifact_type,
            "artifact_id": str(artifact_id),
            "imported_count": imported_count,
        },
    )


# ── IM ───────────────────────────────────────────────────


@router.post("/im/link", response_model=IntegrationResult)
async def link_im(
    txn_id: uuid.UUID,
    body: IMLinkRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
    im: IMClientProtocol = Depends(get_im_client),
):
    """IM Document(CIM) 생성/연결."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    txn = await transaction_service.get_transaction(db, txn_id)
    try:
        result = await im.create_document(body.company_name, body.project_name, body.corp_code)
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
    except Exception as e:
        logger.warning("IM link failed for txn %s: %s", txn_id, e)
        raise HTTPException(status_code=502, detail="IM 서비스 연결에 실패했습니다") from e


@router.get("/im/status", response_model=IntegrationResult)
async def im_status(
    txn_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    im: IMClientProtocol = Depends(get_im_client),
):
    """CIM 생성 상태 조회."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    await transaction_service.get_transaction(db, txn_id)
    try:
        result = await im.get_document_status(document_id)
        return IntegrationResult(service="IM", status="ok", data=result)
    except Exception as e:
        logger.warning("IM status query failed for txn %s, doc %s: %s", txn_id, document_id, e)
        raise HTTPException(status_code=502, detail="IM 상태 조회에 실패했습니다") from e


# ── KIIS ─────────────────────────────────────────────────


@router.get("/kiis/company", response_model=IntegrationResult)
async def kiis_company_search(
    txn_id: uuid.UUID,
    q: str,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    kiis: KIISClientProtocol = Depends(get_kiis_client),
):
    """KIIS 기업 검색."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    await transaction_service.get_transaction(db, txn_id)
    try:
        results = await kiis.search_company(q)
        return IntegrationResult(service="KIIS", status="ok", data={"items": results})
    except Exception as e:
        logger.warning("KIIS company search failed for txn %s, q=%s: %s", txn_id, q, e)
        raise HTTPException(status_code=502, detail="KIIS 기업 검색에 실패했습니다") from e
