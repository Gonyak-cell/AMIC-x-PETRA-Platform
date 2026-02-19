"""FDD/IM/KIIS 서비스 연동 라우터."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.enums import AuditAction
from app.services import audit_service, transaction_service
from app.services.fdd_client import fdd_client
from app.services.im_client import im_client
from app.services.kiis_client import kiis_client

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
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """FDD Deal 생성/연결."""
    txn = await transaction_service.get_transaction(db, txn_id)
    try:
        result = await fdd_client.create_deal(body.target_name, body.industry)
        await audit_service.record(
            db, entity_type="Transaction", entity_id=txn.id,
            action=AuditAction.SERVICE_LINKED, actor_email=claims.email,
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
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    """FDD 분석 상태 조회."""
    await transaction_service.get_transaction(db, txn_id)
    try:
        result = await fdd_client.get_deal_status(deal_id)
        return IntegrationResult(service="FDD", status="ok", data=result)
    except Exception as e:
        return IntegrationResult(service="FDD", status="error", error=str(e))


# ── IM ───────────────────────────────────────────────────

@router.post("/im/link", response_model=IntegrationResult)
async def link_im(
    txn_id: uuid.UUID,
    body: IMLinkRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """IM Document(CIM) 생성/연결."""
    txn = await transaction_service.get_transaction(db, txn_id)
    try:
        result = await im_client.create_document(
            body.company_name, body.project_name, body.corp_code
        )
        await audit_service.record(
            db, entity_type="Transaction", entity_id=txn.id,
            action=AuditAction.SERVICE_LINKED, actor_email=claims.email,
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
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    """CIM 생성 상태 조회."""
    await transaction_service.get_transaction(db, txn_id)
    try:
        result = await im_client.get_document_status(document_id)
        return IntegrationResult(service="IM", status="ok", data=result)
    except Exception as e:
        return IntegrationResult(service="IM", status="error", error=str(e))


# ── KIIS ─────────────────────────────────────────────────

@router.get("/kiis/company", response_model=IntegrationResult)
async def kiis_company_search(
    txn_id: uuid.UUID,
    q: str,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    """KIIS 기업 검색."""
    await transaction_service.get_transaction(db, txn_id)
    try:
        results = await kiis_client.search_company(q)
        return IntegrationResult(service="KIIS", status="ok", data={"items": results})
    except Exception as e:
        return IntegrationResult(service="KIIS", status="error", error=str(e))
