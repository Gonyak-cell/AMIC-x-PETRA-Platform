"""승인 워크플로우 라우터 — 결재선 관리."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalStatus, ApprovalType, AuditAction
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalListResponse,
    ApprovalOut,
    ApprovalSummary,
)
from app.services import audit_service, transaction_service

router = APIRouter(tags=["Approvals"])

# ── Transaction-scoped 라우터 ────────────────────────────────


@router.get("/transactions/{txn_id}/approvals", response_model=ApprovalListResponse)
async def list_approvals(
    txn_id: uuid.UUID,
    approval_type: ApprovalType | None = None,
    approval_status: ApprovalStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(ApprovalRequest).where(ApprovalRequest.transaction_id == txn_id)
    count_q = select(func.count(ApprovalRequest.id)).where(ApprovalRequest.transaction_id == txn_id)

    if approval_type:
        q = q.where(ApprovalRequest.approval_type == approval_type)
        count_q = count_q.where(ApprovalRequest.approval_type == approval_type)
    if approval_status:
        q = q.where(ApprovalRequest.status == approval_status)
        count_q = count_q.where(ApprovalRequest.status == approval_status)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    items = [ApprovalOut.model_validate(a) for a in result.scalars().all()]
    return ApprovalListResponse(items=items, total=total)


@router.get("/transactions/{txn_id}/approvals/summary", response_model=ApprovalSummary)
async def approval_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(ApprovalRequest).where(ApprovalRequest.transaction_id == txn_id)
    result = await db.execute(q)
    approvals = list(result.scalars().all())

    pending = sum(1 for a in approvals if a.status == ApprovalStatus.PENDING)
    approved = sum(1 for a in approvals if a.status == ApprovalStatus.APPROVED)
    rejected = sum(1 for a in approvals if a.status == ApprovalStatus.REJECTED)

    return ApprovalSummary(total=len(approvals), pending=pending, approved=approved, rejected=rejected)


@router.post("/transactions/{txn_id}/approvals", response_model=ApprovalOut, status_code=201)
async def create_approval(
    txn_id: uuid.UUID,
    body: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    approval = ApprovalRequest(
        transaction_id=txn_id,
        requester_email=claims.email,
        approval_type=body.approval_type,
        title=body.title,
        description=body.description,
        approvers=[a.model_dump() for a in body.approvers],
        deadline=body.deadline,
        related_entity_type=body.related_entity_type,
        related_entity_id=body.related_entity_id,
    )
    db.add(approval)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="ApprovalRequest",
        entity_id=approval.id,
        action=AuditAction.APPROVAL_REQUESTED,
        actor_email=claims.email,
        new_value={
            "approval_type": body.approval_type,
            "title": body.title,
            "approver_count": len(body.approvers),
        },
    )
    await db.commit()
    await db.refresh(approval)
    return ApprovalOut.model_validate(approval)


# ── Approval-level 라우터 ─────────────────────────────────────


@router.get("/approvals/{approval_id}", response_model=ApprovalOut)
async def get_approval(
    approval_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    approval = await _get_approval_or_404(db, approval_id)
    return ApprovalOut.model_validate(approval)


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalOut)
async def decide_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """승인자가 승인/거부 결정을 내린다."""
    approval = await _get_approval_or_404(db, approval_id)
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리된 승인 요청입니다",
        )

    # approvers 목록에서 해당 이메일 찾기
    approvers = list(approval.approvers)
    found = False
    for approver in approvers:
        if approver["email"] == body.email:
            approver["status"] = body.decision
            approver["comment"] = body.comment
            approver["decided_at"] = datetime.now(UTC).isoformat()
            found = True
            break

    if not found:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 승인 요청의 승인자가 아닙니다",
        )

    # 전체 상태 업데이트: 전원 승인 → APPROVED, 한 명이라도 거부 → REJECTED
    any_rejected = any(a.get("status") == "REJECTED" for a in approvers)
    all_approved = all(a.get("status") == "APPROVED" for a in approvers)

    if any_rejected:
        approval.status = ApprovalStatus.REJECTED
    elif all_approved:
        approval.status = ApprovalStatus.APPROVED
    # else: 일부만 결정 → PENDING 유지

    approval.approvers = approvers
    flag_modified(approval, "approvers")

    await audit_service.record(
        db,
        entity_type="ApprovalRequest",
        entity_id=approval.id,
        action=AuditAction.APPROVAL_DECIDED,
        actor_email=claims.email,
        new_value={
            "decision": body.decision,
            "decider": body.email,
            "overall_status": approval.status,
        },
    )
    await db.commit()
    await db.refresh(approval)
    return ApprovalOut.model_validate(approval)


@router.post("/approvals/{approval_id}/cancel", response_model=ApprovalOut)
async def cancel_approval(
    approval_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """요청자가 승인 요청을 취소한다."""
    approval = await _get_approval_or_404(db, approval_id)
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="대기 중인 승인 요청만 취소할 수 있습니다",
        )
    approval.status = ApprovalStatus.CANCELLED
    await audit_service.record(
        db,
        entity_type="ApprovalRequest",
        entity_id=approval.id,
        action=AuditAction.APPROVAL_DECIDED,
        actor_email=claims.email,
        new_value={"decision": "CANCELLED"},
    )
    await db.commit()
    await db.refresh(approval)
    return ApprovalOut.model_validate(approval)


@router.get("/approvals/pending/me", response_model=ApprovalListResponse)
async def my_pending_approvals(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """내가 승인해야 할 대기 중인 요청 목록."""
    q = select(ApprovalRequest).where(ApprovalRequest.status == ApprovalStatus.PENDING)
    result = await db.execute(q)
    all_pending = list(result.scalars().all())

    # approvers JSONB에서 내 이메일이 PENDING인 것만 필터링
    my_items = []
    for approval in all_pending:
        for approver in approval.approvers:
            if approver.get("email") == claims.email and approver.get("status") == "PENDING":
                my_items.append(ApprovalOut.model_validate(approval))
                break

    return ApprovalListResponse(items=my_items, total=len(my_items))


async def _get_approval_or_404(db: AsyncSession, approval_id: uuid.UUID) -> ApprovalRequest:
    q = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    approval = (await db.execute(q)).scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="승인 요청을 찾을 수 없습니다")
    return approval
