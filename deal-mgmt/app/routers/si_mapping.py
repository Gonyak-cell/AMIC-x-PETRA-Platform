"""SI(전략적 투자자) 자동 매핑 + ValueChain 매핑 라우터."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limiter import si_rate_limiter
from app.core.security import JWTClaims, check_client_deal_access, require_role
from app.models.enums import AuditAction
from app.schemas.si_mapping import (
    BulkAddBuyersRequest,
    BulkAddBuyersResponse,
    DeepDiveResponse,
    KsicSuggestion,
    SICompanyOut,
    SIDataStats,
    SIMappingRequest,
    SIMappingResponse,
    VcDataStats,
    VcIndustrySuggestion,
    VcMappingResponse,
)
from app.services import audit_service, si_mapping_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["SI Mapping"])

# RBAC — 읽기: 전체 인증 사용자, 쓰기: ADMIN/MANAGER
_READ_ACCESS = require_role("ADMIN", "MANAGER", "ANALYST")
_WRITE_ACCESS = require_role("ADMIN", "MANAGER")


# ── 참조 데이터 통계 ──────────────────────────────────────
@router.get(
    "/si-mapping/stats",
    response_model=SIDataStats,
    responses={403: {"description": "접근 권한 없음"}},
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> SIDataStats:
    """SI 매핑 참조 데이터 시딩 상태."""
    try:
        return await si_mapping_service.get_data_stats(db)
    except SQLAlchemyError:
        logger.exception("SI 통계 조회 DB 오류")
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")


# ── KSIC 자동완성 검색 ────────────────────────────────────
@router.get(
    "/si-mapping/ksic/search",
    response_model=list[KsicSuggestion],
    responses={403: {"description": "접근 권한 없음"}},
)
async def search_ksic(
    q: str = Query("", min_length=0, max_length=50),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> list[KsicSuggestion]:
    """KSIC 코드/이름 자동완성 검색."""
    try:
        return await si_mapping_service.search_ksic(db, q, limit)
    except SQLAlchemyError:
        logger.exception("KSIC 검색 DB 오류: q=%s", q)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")


# ── SI 매핑 실행 ──────────────────────────────────────────
@router.post(
    "/si-mapping/map",
    response_model=SIMappingResponse,
    responses={
        403: {"description": "접근 권한 없음"},
        429: {"description": "요청 횟수 초과"},
    },
)
async def map_si(
    body: SIMappingRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> SIMappingResponse:
    """KSIC 코드 기반 SI 후보 매핑 실행."""
    si_rate_limiter.check(claims.email or claims.user_id or "unknown")
    try:
        result = await si_mapping_service.map_si_candidates(
            db,
            ksic_codes=body.ksic_codes,
            top_n=body.top_n,
            max_companies_per_panel=body.max_companies_per_panel,
            min_revenue=body.min_revenue,
            require_investment_history=body.require_investment_history,
        )
    except SQLAlchemyError:
        logger.exception("SI 매핑 DB 오류: ksic_codes=%s", body.ksic_codes)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")
    try:
        await audit_service.record(
            db,
            entity_type="SIMapping",
            entity_id="SIMapping",
            action=AuditAction.READ,
            actor_email=claims.email or claims.user_id or "unknown",
            new_value={"action": "map_si", "ksic_codes": body.ksic_codes, "candidates": len(result.all_candidates)},
        )
    except Exception:
        logger.exception("SI 매핑 감사 로그 기록 실패 (결과 반환은 정상 진행)")
    return result


# ── 기업명 검색 ──────────────────────────────────────────
@router.get(
    "/si-mapping/companies/search-by-name",
    response_model=SICompanyOut,
    responses={
        403: {"description": "접근 권한 없음"},
        404: {"description": "기업을 찾을 수 없음"},
    },
)
async def search_si_company_by_name(
    name: str = Query(..., min_length=1, max_length=300),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> SICompanyOut:
    """기업명으로 SI 기업 검색 (정확 매칭)."""
    try:
        si = await si_mapping_service.find_si_company_by_name(db, name)
    except SQLAlchemyError:
        logger.exception("기업명 검색 DB 오류: name=%s", name)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")
    if si is None:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {name}")
    return SICompanyOut.model_validate(si)


# ── 기업 딥다이브 ──────────────────────────────────────────
@router.get(
    "/si-mapping/companies/{company_id}/deep-dive",
    response_model=DeepDiveResponse,
    responses={
        403: {"description": "접근 권한 없음"},
        404: {"description": "기업을 찾을 수 없음"},
    },
)
async def get_deep_dive(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> DeepDiveResponse:
    """SI 기업 딥다이브 — DART 기업개황, 재무제표, 공시 조회."""
    try:
        return await si_mapping_service.get_deep_dive(db, company_id)
    except SQLAlchemyError:
        logger.exception("딥다이브 DB 오류: company_id=%s", company_id)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")


# ── 일괄 BuyerCandidate 등록 ─────────────────────────────
@router.post(
    "/transactions/{txn_id}/si-mapping/add-buyers",
    response_model=BulkAddBuyersResponse,
    status_code=201,
    responses={
        403: {"description": "접근 권한 없음"},
        404: {"description": "거래를 찾을 수 없음"},
    },
)
async def bulk_add_buyers(
    txn_id: uuid.UUID,
    body: BulkAddBuyersRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_WRITE_ACCESS),
) -> BulkAddBuyersResponse:
    """SI 매핑 결과를 BuyerCandidate로 일괄 등록."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    try:
        result = await si_mapping_service.bulk_add_to_buyers(
            db,
            txn_id=txn_id,
            si_company_ids=body.si_company_ids,
            actor_email=claims.email or claims.user_id or "unknown",
        )
    except SQLAlchemyError:
        logger.exception("BuyerCandidate 일괄 등록 실패: txn_id=%s", txn_id)
        raise HTTPException(status_code=503, detail="매수후보 등록에 실패했습니다")
    return result


# ══════════════════════════════════════════════════════════
# ValueChain (VC) 매핑 — 1,574 세부 업종 계수표 기반
# ══════════════════════════════════════════════════════════


# ── VC 데이터 통계 ────────────────────────────────────────
@router.get(
    "/si-mapping/vc-stats",
    response_model=VcDataStats,
    responses={403: {"description": "접근 권한 없음"}},
)
async def get_vc_stats(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> VcDataStats:
    """ValueChain 데이터 시딩 상태 (기업 수, 계수 수, 매출 보유 기업 수)."""
    try:
        return await si_mapping_service.get_vc_data_stats(db)
    except SQLAlchemyError:
        logger.exception("VC 통계 조회 DB 오류")
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")


# ── 업종명 자동완성 ──────────────────────────────────────
@router.get(
    "/si-mapping/industries/search",
    response_model=list[VcIndustrySuggestion],
    responses={403: {"description": "접근 권한 없음"}},
)
async def search_industries(
    q: str = Query(..., min_length=1, max_length=200, description="업종명 검색어"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> list[VcIndustrySuggestion]:
    """업종명(1,574) 자동완성 — VcCompany.industry_name DISTINCT LIKE 검색."""
    try:
        return await si_mapping_service.search_vc_industries(db, q, limit)
    except SQLAlchemyError:
        logger.exception("업종명 검색 DB 오류: q=%s", q)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")


# ── ValueChain 매핑 실행 ─────────────────────────────────
@router.get(
    "/si-mapping/vc-map",
    response_model=VcMappingResponse,
    responses={
        403: {"description": "접근 권한 없음"},
        429: {"description": "요청 횟수 초과"},
    },
)
async def map_vc(
    industry: str = Query(..., min_length=1, max_length=300, description="타겟 업종명 (1,574 중 하나)"),
    min_revenue: Decimal = Query(Decimal("100"), ge=Decimal("0"), description="최소 매출액 (억원)"),
    top_n: int = Query(20, ge=1, le=50, description="전방/후방/경쟁 각각의 최대 건수"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> VcMappingResponse:
    """업종명 기반 Value Chain 매핑 — 전방(고객)/후방(공급)/경쟁(동종) 추출."""
    si_rate_limiter.check(claims.email or claims.user_id or "unknown")
    try:
        result = await si_mapping_service.map_vc_candidates(
            db,
            target_industry_name=industry,
            min_revenue=min_revenue,
            top_n=top_n,
        )
    except SQLAlchemyError:
        logger.exception("VC 매핑 DB 오류: industry=%s", industry)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다")
    try:
        await audit_service.record(
            db,
            entity_type="VcMapping",
            entity_id="VcMapping",
            action=AuditAction.READ,
            actor_email=claims.email or claims.user_id or "unknown",
            new_value={"action": "map_vc", "industry": industry},
        )
    except Exception:
        logger.exception("VC 매핑 감사 로그 기록 실패 (결과 반환은 정상 진행)")
    return result
