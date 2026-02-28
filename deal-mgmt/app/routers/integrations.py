"""FDD/IM/KIIS 서비스 연동 라우터."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_fdd_client, get_im_client, get_kiis_client
from app.core.security import JWTClaims, get_jwt_claims, require_write_access
from app.models.enums import AuditAction
from app.services import audit_service, transaction_service
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
        await audit_service.record(
            db,
            entity_type="Transaction",
            entity_id=txn.id,
            action=AuditAction.SERVICE_LINKED,
            actor_email=claims.email,
            new_value={"service": "FDD", "result": str(result)},
        )
        await db.commit()
        return IntegrationResult(service="FDD", status="linked", data=result)
    except Exception as e:
        logger.warning("FDD link failed for txn %s: %s", txn_id, e)
        return IntegrationResult(service="FDD", status="error", error=str(e))


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
        return IntegrationResult(service="FDD", status="error", error=str(e))


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
            new_value={"service": "IM", "result": str(result)},
        )
        await db.commit()
        return IntegrationResult(service="IM", status="linked", data=result)
    except Exception as e:
        logger.warning("IM link failed for txn %s: %s", txn_id, e)
        return IntegrationResult(service="IM", status="error", error=str(e))


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
        return IntegrationResult(service="IM", status="error", error=str(e))


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
        return IntegrationResult(service="KIIS", status="error", error=str(e))
