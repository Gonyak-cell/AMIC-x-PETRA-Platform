"""계약서 자동 생성 라우터 — 템플릿 조회, HTML 생성, DOCX 내보내기."""

from __future__ import annotations

import logging
import time
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DocumentNotFoundError
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.transaction import Transaction
from app.schemas.contract_generation import (
    ContractClauseOut,
    ContractExportRequest,
    ContractGenerateRequest,
    ContractGenerationOut,
    ContractSaveHtmlOut,
    ContractSaveHtmlRequest,
    ContractTemplateDetailOut,
    ContractTemplateOut,
    GenerationTimingOut,
    TemplateVariableOut,
)
from app.services import contract_generation_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions/{txn_id}/contract-generation",
    tags=["Contract Generation"],
)

# ── Rate Limiting (인메모리, 분당 5회) ───────────────────────────────────────
# NOTE: 인메모리 딕셔너리 → 멀티 워커(gunicorn) 환경에서 워커별 독립 카운트.
# 프로덕션 스케일 시 Redis 기반 분산 rate limiter로 전환 필요.

_generate_rate: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW = 60.0
_RATE_LIMIT_MAX = 5


def _check_generate_rate(email: str) -> None:
    """LLM 생성 엔드포인트 분당 요청 수를 제한한다."""
    now = time.monotonic()
    active = [t for t in _generate_rate.get(email, []) if now - t < _RATE_LIMIT_WINDOW]
    if len(active) >= _RATE_LIMIT_MAX:
        _generate_rate[email] = active
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="계약서 생성 요청이 너무 많습니다. 1분 후 다시 시도하세요.",
        )
    active.append(now)
    _generate_rate[email] = active

    # 만료된 키 정리 — 메모리 누수 방지
    stale_keys = [k for k, v in _generate_rate.items() if k != email and all(now - t >= _RATE_LIMIT_WINDOW for t in v)]
    for k in stale_keys:
        del _generate_rate[k]


# ── 공통 유틸 ─────────────────────────────────────────────────────────────


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


# ── 템플릿 조회 ─────────────────────────────────────────────────────────────


@router.get("/templates", response_model=list[ContractTemplateOut])
async def list_templates(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[ContractTemplateOut]:
    """활성 계약서 템플릿 목록을 조회한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    templates = await contract_generation_service.list_active_templates(db)
    return [ContractTemplateOut.model_validate(t) for t in templates]


@router.get("/templates/{template_id}", response_model=ContractTemplateDetailOut)
async def get_template_detail(
    txn_id: uuid.UUID,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> ContractTemplateDetailOut:
    """템플릿 상세 (조항 + 변수 포함)를 조회한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    template = await contract_generation_service.get_template_with_details(db, template_id)
    return ContractTemplateDetailOut(
        template=ContractTemplateOut.model_validate(template),
        clauses=[ContractClauseOut.model_validate(c) for c in template.clauses],
        variables=[TemplateVariableOut.model_validate(v) for v in template.variables],
    )


# ── 계약서 HTML 생성 ────────────────────────────────────────────────────────


@router.post("/generate", response_model=ContractGenerationOut, status_code=201)
async def generate_contract(
    txn_id: uuid.UUID,
    body: ContractGenerateRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> ContractGenerationOut:
    """계약서 초안을 생성한다. LLM 스무딩 포함 시 10~30초 소요."""
    await _get_and_authorize_txn(db, txn_id, claims)
    _check_generate_rate(claims.email or "anonymous")

    try:
        result = await contract_generation_service.generate_contract_html(
            db,
            transaction_id=txn_id,
            template_id=body.template_id,
            title=body.title,
            variables=body.variables,
            use_llm=body.use_llm_smoothing,
            created_by_email=claims.email,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    await db.commit()

    return ContractGenerationOut(
        legal_document_id=result.legal_document.id,
        html=result.legal_document.generated_html or "",
        clauses_used=result.clauses_used,
        clauses_skipped=result.clauses_skipped,
        llm_smoothed=result.llm_smoothed,
        llm_cost_usd=result.llm_cost if claims.role == "ADMIN" else None,
        updated_at=result.legal_document.updated_at,
        timing=GenerationTimingOut(**result.timing) if claims.role == "ADMIN" else None,
    )


# ── DOCX 내보내기 ──────────────────────────────────────────────────────────


@router.post("/export-docx")
async def export_docx(
    txn_id: uuid.UUID,
    body: ContractExportRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> Response:
    """HTML 계약서를 DOCX로 변환하여 다운로드한다."""
    await _get_and_authorize_txn(db, txn_id, claims)

    from app.services.contract_export_service import html_to_docx

    # export-docx도 사용자 입력 HTML이므로 서버 측 sanitize 적용
    sanitized_html = contract_generation_service.sanitize_html(body.html)

    try:
        docx_bytes = await html_to_docx(sanitized_html, body.title)
    except TimeoutError:
        logger.error("DOCX 변환 타임아웃: txn=%s, title=%s, html_size=%d", txn_id, body.title, len(sanitized_html))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="DOCX 변환이 시간 제한을 초과했습니다. 문서 크기를 줄여 다시 시도하세요.",
        )
    except (ValueError, TypeError, KeyError, OSError) as exc:
        logger.exception("DOCX 변환 실패: txn=%s, title=%s, error=%s", txn_id, body.title, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DOCX 변환 중 오류가 발생했습니다.",
        ) from exc

    safe_filename = body.title.replace('"', "'").replace("\r", "").replace("\n", "")
    encoded_filename = quote(f"{safe_filename}.docx")
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=\"contract.docx\"; filename*=UTF-8''{encoded_filename}",
        },
    )


# ── HTML 저장 ───────────────────────────────────────────────────────────────


@router.patch("/{doc_id}/save-html", response_model=ContractSaveHtmlOut)
async def save_contract_html(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: ContractSaveHtmlRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> ContractSaveHtmlOut:
    """편집된 HTML을 LegalDocument에 저장한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        doc = await contract_generation_service.save_html(
            db,
            txn_id,
            doc_id,
            body.html,
            last_modified_at=body.last_modified_at,
            last_modified_by_email=claims.email,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()

    # 살균 후 HTML이 원본과 다를 경우 FE 동기화용으로 반환
    sanitized = doc.generated_html
    return_html = sanitized if sanitized != body.html else None

    return ContractSaveHtmlOut(status="saved", updated_at=doc.updated_at, html=return_html)
