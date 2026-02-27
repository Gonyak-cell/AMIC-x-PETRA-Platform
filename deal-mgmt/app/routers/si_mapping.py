"""SI(전략적 투자자) 자동 매핑 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.schemas.si_mapping import (
    BulkAddBuyersRequest,
    BulkAddBuyersResponse,
    DeepDiveResponse,
    KsicSuggestion,
    SIDataStats,
    SIMappingRequest,
    SIMappingResponse,
)
from app.services import si_mapping_service, transaction_service

router = APIRouter(tags=["SI Mapping"])


# ── 참조 데이터 통계 ──────────────────────────────────────
@router.get("/si-mapping/stats", response_model=SIDataStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """SI 매핑 참조 데이터 시딩 상태."""
    return await si_mapping_service.get_data_stats(db)


# ── KSIC 자동완성 검색 ────────────────────────────────────
@router.get("/si-mapping/ksic/search", response_model=list[KsicSuggestion])
async def search_ksic(
    q: str = Query("", min_length=0, max_length=50),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """KSIC 코드/이름 자동완성 검색."""
    return await si_mapping_service.search_ksic(db, q, limit)


# ── SI 매핑 실행 ──────────────────────────────────────────
@router.post("/si-mapping/map", response_model=SIMappingResponse)
async def map_si(
    body: SIMappingRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """KSIC 코드 기반 SI 후보 매핑 실행."""
    return await si_mapping_service.map_si_candidates(
        db,
        ksic_codes=body.ksic_codes,
        top_n=body.top_n,
        max_companies_per_panel=body.max_companies_per_panel,
        min_revenue=body.min_revenue,
        require_investment_history=body.require_investment_history,
    )


# ── 기업 딥다이브 ──────────────────────────────────────────
@router.get("/si-mapping/companies/{company_id}/deep-dive", response_model=DeepDiveResponse)
async def get_deep_dive(
    company_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """SI 기업 딥다이브 — DART 기업개황, 재무제표, 공시 조회."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip() if auth_header else None
    return await si_mapping_service.get_deep_dive(db, company_id, auth_token=token)


# ── 일괄 BuyerCandidate 등록 ─────────────────────────────
@router.post(
    "/transactions/{txn_id}/si-mapping/add-buyers",
    response_model=BulkAddBuyersResponse,
    status_code=201,
)
async def bulk_add_buyers(
    txn_id: uuid.UUID,
    body: BulkAddBuyersRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """SI 매핑 결과를 BuyerCandidate로 일괄 등록."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return await si_mapping_service.bulk_add_to_buyers(
        db,
        txn_id=txn_id,
        si_company_ids=body.si_company_ids,
        actor_email=claims.email,
    )
