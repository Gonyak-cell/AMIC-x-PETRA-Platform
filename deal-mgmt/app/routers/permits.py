"""인허가 분석 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import AuditAction
from app.schemas.permit import (
    IndustryOption,
    PermitAnalysisOut,
    PermitAnalyzeRequest,
    PermitRequirementCreate,
    PermitRequirementOut,
    PermitRequirementUpdate,
)
from app.services import audit_service, permit_analysis_service, transaction_service
from app.services.permit_knowledge_base import get_all_industry_options

router = APIRouter(prefix="/transactions/{txn_id}/permits", tags=["Permits"])

# ── KB 참조 (인증 불필요) ────────────────────────────────────

kb_router = APIRouter(prefix="/permits/kb", tags=["Permits"])


@kb_router.get("/industries", response_model=list[IndustryOption])
async def list_industries():
    """지원 업종 목록을 반환한다."""
    return [IndustryOption(**opt) for opt in get_all_industry_options()]


# ── 분석 ─────────────────────────────────────────────────────


@router.post("/analyze", response_model=PermitAnalysisOut, status_code=201)
async def analyze_permits(
    txn_id: uuid.UUID,
    body: PermitAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """인허가 분석을 실행한다."""
    txn = await transaction_service.get_transaction(db, txn_id)
    analysis = await permit_analysis_service.analyze_permits(
        db,
        txn,
        body.business_types,
        [p.model_dump() for p in body.existing_permits],
        actor_email=claims.email,
    )
    await audit_service.record(
        db,
        entity_type="PermitAnalysis",
        entity_id=analysis.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"business_types": body.business_types},
    )
    await db.commit()
    await db.refresh(analysis)
    return PermitAnalysisOut.model_validate(analysis)


@router.get("/analysis", response_model=PermitAnalysisOut | None)
async def get_analysis(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """현재 분석 결과를 조회한다."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    analysis = await permit_analysis_service.get_analysis(db, txn_id)
    if analysis is None:
        return None
    return PermitAnalysisOut.model_validate(analysis)


@router.post("/analysis/reanalyze", response_model=PermitAnalysisOut, status_code=201)
async def reanalyze_permits(
    txn_id: uuid.UUID,
    body: PermitAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """인허가를 재분석한다 (기존 분석 결과 교체)."""
    txn = await transaction_service.get_transaction(db, txn_id)
    analysis = await permit_analysis_service.analyze_permits(
        db,
        txn,
        body.business_types,
        [p.model_dump() for p in body.existing_permits],
        actor_email=claims.email,
    )
    await db.commit()
    await db.refresh(analysis)
    return PermitAnalysisOut.model_validate(analysis)


# ── 요건 CRUD ────────────────────────────────────────────────


@router.get("/requirements", response_model=list[PermitRequirementOut])
async def list_requirements(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """인허가 요건 목록을 조회한다."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    reqs = await permit_analysis_service.get_requirements(db, txn_id)
    return [PermitRequirementOut.model_validate(r) for r in reqs]


@router.get("/requirements/{req_id}", response_model=PermitRequirementOut)
async def get_requirement(
    txn_id: uuid.UUID,
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """단일 인허가 요건을 조회한다."""
    await check_client_deal_access(db, txn_id, claims)
    req = await permit_analysis_service.get_requirement(db, txn_id, req_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인허가 요건을 찾을 수 없습니다")
    return PermitRequirementOut.model_validate(req)


@router.post("/requirements", response_model=PermitRequirementOut, status_code=201)
async def create_requirement(
    txn_id: uuid.UUID,
    body: PermitRequirementCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """인허가 요건을 수동 추가한다."""
    txn = await transaction_service.get_transaction(db, txn_id)
    analysis = await permit_analysis_service.get_analysis(db, txn_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="먼저 인허가 분석을 실행해야 합니다",
        )
    target_close_date = getattr(txn, "target_close_date", None)
    req = await permit_analysis_service.add_manual_requirement(
        db,
        txn_id,
        analysis.id,
        body.model_dump(),
        target_close_date,
    )
    await audit_service.record(
        db,
        entity_type="PermitRequirement",
        entity_id=req.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(req)
    return PermitRequirementOut.model_validate(req)


@router.patch("/requirements/{req_id}", response_model=PermitRequirementOut)
async def update_requirement(
    txn_id: uuid.UUID,
    req_id: uuid.UUID,
    body: PermitRequirementUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """인허가 요건을 수정한다."""
    req = await permit_analysis_service.get_requirement(db, txn_id, req_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인허가 요건을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(req, k, v)
    await audit_service.record(
        db,
        entity_type="PermitRequirement",
        entity_id=req.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(req)
    return PermitRequirementOut.model_validate(req)


@router.delete("/requirements/{req_id}", status_code=204)
async def delete_requirement(
    txn_id: uuid.UUID,
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """인허가 요건을 삭제한다 (수동 추가된 항목만)."""
    req = await permit_analysis_service.get_requirement(db, txn_id, req_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인허가 요건을 찾을 수 없습니다")
    if req.source != "MANUAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KB 기반 항목은 삭제할 수 없습니다. 상태를 '해당 없음'으로 변경하세요.",
        )
    await audit_service.record(
        db,
        entity_type="PermitRequirement",
        entity_id=req.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(req)
    await db.commit()
