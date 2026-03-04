"""SI(전략적 투자자) 자동 매핑 + ValueChain 매핑 라우터."""

from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import CompanyNotFoundError
from app.core.rate_limiter import si_rate_limiter
from app.core.security import JWTClaims, check_client_deal_access, require_role
from app.models.enums import AuditAction
from app.schemas.si_mapping import (
    BulkAddBuyersRequest,
    BulkAddBuyersResponse,
    BulkAddVcBuyersRequest,
    DeepDiveResponse,
    KsicSuggestion,
    SICompanyOut,
    SIDataStats,
    SIMappingRequest,
    SIMappingResponse,
    VcDataStats,
    VcIndustrySuggestion,
    VcMappingByRegResponse,
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
    except SQLAlchemyError as exc:
        logger.exception("SI 매핑 DB 오류: ksic_codes=%s", body.ksic_codes)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다") from exc
    try:
        await audit_service.record(
            db,
            entity_type="SIMapping",
            entity_id="SIMapping",
            action=AuditAction.READ,
            actor_email=claims.email or claims.user_id or "unknown",
            new_value={"action": "map_si", "ksic_codes": body.ksic_codes, "candidates": len(result.all_candidates)},
        )
        await db.commit()
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
    except SQLAlchemyError as exc:
        logger.exception("기업명 검색 DB 오류: name=%s", name)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다") from exc
    if si is None:
        raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다")
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
    si_rate_limiter.check(claims.email or claims.user_id or "unknown")
    try:
        return await si_mapping_service.get_deep_dive(db, company_id)
    except CompanyNotFoundError:
        raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다")
    except SQLAlchemyError as exc:
        logger.exception("딥다이브 DB 오류: company_id=%s", company_id)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다") from exc


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
    except ValueError as exc:
        logger.warning("SI BuyerCandidate 유효성 오류: %s", exc)
        raise HTTPException(status_code=422, detail="요청 데이터가 유효하지 않습니다") from exc
    except SQLAlchemyError as exc:
        logger.exception("BuyerCandidate 일괄 등록 실패: txn_id=%s", txn_id)
        raise HTTPException(status_code=503, detail="매수후보 등록에 실패했습니다") from exc
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
    except SQLAlchemyError as exc:
        logger.exception("VC 통계 조회 DB 오류")
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다") from exc


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
    si_rate_limiter.check(claims.email or claims.user_id or "unknown")
    try:
        return await si_mapping_service.search_vc_industries(db, q, limit)
    except SQLAlchemyError as exc:
        logger.exception("업종명 검색 DB 오류: q=%s", q)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다") from exc


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
    except SQLAlchemyError as exc:
        logger.exception("VC 매핑 DB 오류: industry=%s", industry)
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다") from exc
    try:
        await audit_service.record(
            db,
            entity_type="VcMapping",
            entity_id="VcMapping",
            action=AuditAction.READ,
            actor_email=claims.email or claims.user_id or "unknown",
            new_value={"action": "map_vc", "industry": industry},
        )
        await db.commit()
    except Exception:
        logger.exception("VC 매핑 감사 로그 기록 실패 (결과 반환은 정상 진행)")
    return result


# ── 등록번호 기반 VC 매핑 ─────────────────────────────────

_REG_NO_MASK_RE = re.compile(r"[\s\-]")


def _mask_reg_no(value: str | None) -> str | None:
    """감사 로그용 등록번호 마스킹 (앞 6자리만 표시).

    cf. schemas/si_mapping.py:_mask_registration — API 응답용 마스킹
    """
    if not value:
        return None
    clean = _REG_NO_MASK_RE.sub("", value)
    if len(clean) <= 6:
        return clean[:3] + "***"
    return clean[:6] + "*" * (len(clean) - 6)


@router.get(
    "/si-mapping/vc-map-by-registration",
    response_model=VcMappingByRegResponse,
    responses={
        403: {"description": "접근 권한 없음"},
        404: {"description": "기업을 찾을 수 없음"},
        429: {"description": "요청 횟수 초과"},
    },
)
async def map_vc_by_registration(
    corp_reg_no: str | None = Query(None, max_length=20, pattern=r"^[\d\-\s]+$", description="법인등록번호"),
    biz_reg_no: str | None = Query(None, max_length=20, pattern=r"^[\d\-\s]+$", description="사업자등록번호"),
    min_revenue: Decimal = Query(Decimal("100"), ge=Decimal("0"), description="최소 매출액 (억원)"),
    top_n: int = Query(20, ge=1, le=50, description="전방/후방/경쟁 각각의 최대 건수"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> VcMappingByRegResponse:
    """법인등록번호 또는 사업자등록번호 → VC 기업 조회 → Value Chain 매핑."""
    if not corp_reg_no and not biz_reg_no:
        raise HTTPException(
            status_code=422,
            detail="corp_reg_no 또는 biz_reg_no 중 하나를 제공해야 합니다",
        )
    si_rate_limiter.check(claims.email or claims.user_id or "unknown")
    try:
        result = await si_mapping_service.map_vc_by_registration(
            db,
            corp_reg_no=corp_reg_no,
            biz_reg_no=biz_reg_no,
            min_revenue=min_revenue,
            top_n=top_n,
        )
    except CompanyNotFoundError:
        # R2-S05: 404 분기에서도 감사 로그 기록
        try:
            await audit_service.record(
                db,
                entity_type="VcMapping",
                entity_id="VcMapping",
                action=AuditAction.READ,
                actor_email=claims.email or claims.user_id or "unknown",
                new_value={
                    "action": "map_vc_by_registration_not_found",
                    "corp_reg_no": _mask_reg_no(corp_reg_no),
                    "biz_reg_no": _mask_reg_no(biz_reg_no),
                },
            )
            await db.commit()
        except Exception:
            logger.exception("VC 등록번호 매핑 404 감사 로그 실패")
        raise HTTPException(
            status_code=404,
            detail="등록번호에 해당하는 기업을 찾을 수 없습니다",
        )
    except SQLAlchemyError as exc:
        logger.exception("VC 등록번호 매핑 DB 오류")
        raise HTTPException(status_code=503, detail="데이터베이스 오류가 발생했습니다") from exc
    try:
        await audit_service.record(
            db,
            entity_type="VcMapping",
            entity_id="VcMapping",
            action=AuditAction.READ,
            actor_email=claims.email or claims.user_id or "unknown",
            new_value={
                "action": "map_vc_by_registration",
                "corp_reg_no": _mask_reg_no(corp_reg_no),
                "biz_reg_no": _mask_reg_no(biz_reg_no),
            },
        )
        await db.commit()
    except Exception:
        logger.exception("VC 등록번호 매핑 감사 로그 기록 실패")
    return result


# ── VC 매핑 결과 → BuyerCandidate 일괄 등록 ──────────────
@router.post(
    "/transactions/{txn_id}/vc-mapping/add-buyers",
    response_model=BulkAddBuyersResponse,
    status_code=201,
    responses={
        403: {"description": "접근 권한 없음"},
        404: {"description": "거래를 찾을 수 없음"},
    },
)
async def bulk_add_vc_buyers(
    txn_id: uuid.UUID,
    body: BulkAddVcBuyersRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_WRITE_ACCESS),
) -> BulkAddBuyersResponse:
    """VC 매핑 결과를 BuyerCandidate로 일괄 등록."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    try:
        result = await si_mapping_service.bulk_add_vc_to_buyers(
            db,
            txn_id=txn_id,
            vc_company_ids=body.vc_company_ids,
            actor_email=claims.email or claims.user_id or "unknown",
        )
    except ValueError as exc:
        logger.warning("VC BuyerCandidate 유효성 오류: %s", exc)
        raise HTTPException(status_code=422, detail="요청 데이터가 유효하지 않습니다") from exc
    except SQLAlchemyError as exc:
        logger.exception("VC BuyerCandidate 일괄 등록 실패: txn_id=%s", txn_id)
        raise HTTPException(status_code=503, detail="매수후보 등록에 실패했습니다") from exc
    return result
