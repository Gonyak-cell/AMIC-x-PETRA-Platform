"""SPA 계약서 LLM 역분석 라우터 — 3단계 Human-in-the-Loop API."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, require_write_access
from app.models.transaction import Transaction
from app.schemas.spa_analysis import (
    SpaStep1Request,
    SpaStep1Response,
    SpaStep2Request,
    SpaStep2Response,
    SpaStep3Request,
    SpaStep3Response,
)
from app.services import spa_analysis_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions/{txn_id}/spa-analysis",
    tags=["Contract Generation"],
)

# ── Rate Limiting (인메모리, 분당 3회) ────────────────────────────────────────

_analysis_rate: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW = 60.0
_RATE_LIMIT_MAX = 3


def _check_analysis_rate(email: str) -> None:
    """LLM 분석 엔드포인트 분당 요청 수를 제한한다."""
    now = time.monotonic()
    active = [t for t in _analysis_rate.get(email, []) if now - t < _RATE_LIMIT_WINDOW]
    if len(active) >= _RATE_LIMIT_MAX:
        _analysis_rate[email] = active
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="SPA 분석 요청이 너무 많습니다. 1분 후 다시 시도하세요.",
        )
    active.append(now)
    _analysis_rate[email] = active

    # 만료 키 정리
    stale_keys = [k for k, v in _analysis_rate.items() if k != email and all(now - t >= _RATE_LIMIT_WINDOW for t in v)]
    for k in stale_keys:
        del _analysis_rate[k]


# ── 공통 유틸 ─────────────────────────────────────────────────────────────────


async def _get_and_authorize_txn(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
) -> Transaction:
    """거래를 조회하고 접근 권한을 확인한다."""
    txn = await transaction_service.get_transaction(db, txn_id)
    if claims.role == "CLIENT":
        await check_client_deal_access(db, txn_id, claims)
        return txn
    if claims.role != "ADMIN":
        if not claims.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="인증 정보에 이메일이 없습니다",
            )
        if txn.lead_advisor_email != claims.email and txn.deal_captain_email != claims.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 거래에 접근할 권한이 없습니다",
            )
    return txn


# ── Step 1: 변수 추출 ─────────────────────────────────────────────────────────


@router.post("/step1-variables", response_model=SpaStep1Response, status_code=201)
async def step1_extract_variables(
    txn_id: uuid.UUID,
    body: SpaStep1Request,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> SpaStep1Response:
    """Step 1: SPA 원문에서 변수를 추출한다. LLM 호출 포함 (10~30초 소요)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    _check_analysis_rate(claims.email or "anonymous")

    try:
        (
            session_id,
            variables,
            deal_structure,
            industry_type,
            detected_doc_type,
            discovered,
            cost,
            model,
        ) = await spa_analysis_service.analyze_step1_variables(
            body.spa_text,
            body.language_hint,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return SpaStep1Response(
        session_id=session_id,
        variables=variables,
        deal_structure=deal_structure,
        industry_type=industry_type,
        detected_doc_type=detected_doc_type,
        discovered_booleans=discovered,
        llm_cost_usd=cost if claims.role == "ADMIN" else None,
        model_used=model if claims.role == "ADMIN" else None,
    )


# ── Step 2: 조항 분해 ─────────────────────────────────────────────────────────


@router.post("/step2-clauses", response_model=SpaStep2Response, status_code=201)
async def step2_decompose_clauses(
    txn_id: uuid.UUID,
    body: SpaStep2Request,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> SpaStep2Response:
    """Step 2: 확정된 변수를 기반으로 조항을 분해한다. LLM 호출 포함 (10~30초 소요)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    _check_analysis_rate(claims.email or "anonymous")

    try:
        clauses, cost, model = await spa_analysis_service.analyze_step2_clauses(
            body.session_id,
            body.variables,
            body.deal_structure,
            body.industry_type,
            spa_text=body.spa_text,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return SpaStep2Response(
        session_id=body.session_id,
        clauses=clauses,
        llm_cost_usd=cost if claims.role == "ADMIN" else None,
        model_used=model if claims.role == "ADMIN" else None,
    )


# ── Step 3: 템플릿 생성 ────────────────────────────────────────────────────────


@router.post("/step3-seed", response_model=SpaStep3Response, status_code=201)
async def step3_create_template(
    txn_id: uuid.UUID,
    body: SpaStep3Request,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> SpaStep3Response:
    """Step 3: 최종 확정된 변수/조항을 DB에 ContractTemplate으로 저장한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    # Step 3은 LLM 미호출 (DB 저장만) → rate limiting 불필요

    try:
        template = await spa_analysis_service.create_template_from_analysis(
            db,
            template_name=body.template_name,
            template_description=body.template_description,
            variables=body.variables,
            clauses=body.clauses,
            created_by_email=claims.email,
            doc_type=body.doc_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await db.commit()

    return SpaStep3Response(
        template_id=template.id,
        template_name=template.name,
        variables_count=len(body.variables),
        clauses_count=len(body.clauses),
        message=f"SPA 분석 템플릿 '{template.name}'이(가) 생성되었습니다.",
    )
