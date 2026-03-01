"""협상 이견 추적 라우터 — 다자 입장 + AI 조항 제안."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import AuditAction, NegotiationIssuePriority, NegotiationIssueStatus
from app.models.negotiation_issue import NegotiationIssue
from app.schemas.negotiation_issue import (
    AIClauseSuggestionResponse,
    BatchDecisionUpdate,
    NegotiationIssueCreate,
    NegotiationIssueListResponse,
    NegotiationIssueOut,
    NegotiationIssueUpdate,
)
from app.services import audit_service, transaction_service
from app.services.clause_suggestion_service import suggest_clause_revision

router = APIRouter(prefix="/transactions/{txn_id}/negotiation-issues", tags=["Negotiation Issues"])


@router.get("", response_model=NegotiationIssueListResponse)
async def list_issues(
    txn_id: uuid.UUID,
    status_filter: NegotiationIssueStatus | None = Query(None, alias="status"),
    priority: NegotiationIssuePriority | None = None,
    meeting_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    q = select(NegotiationIssue).where(NegotiationIssue.transaction_id == txn_id)
    count_q = select(func.count(NegotiationIssue.id)).where(NegotiationIssue.transaction_id == txn_id)

    if status_filter:
        q = q.where(NegotiationIssue.status == status_filter)
        count_q = count_q.where(NegotiationIssue.status == status_filter)
    if priority:
        q = q.where(NegotiationIssue.priority == priority)
        count_q = count_q.where(NegotiationIssue.priority == priority)
    if meeting_id:
        q = q.where(NegotiationIssue.meeting_id == meeting_id)
        count_q = count_q.where(NegotiationIssue.meeting_id == meeting_id)
    if contract_id:
        q = q.where(NegotiationIssue.contract_id == contract_id)
        count_q = count_q.where(NegotiationIssue.contract_id == contract_id)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(NegotiationIssue.created_at.desc())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    items = [NegotiationIssueOut.model_validate(i) for i in result.scalars().all()]
    return NegotiationIssueListResponse(items=items, total=total)


# ── Static paths (must precede parametric /{issue_id}) ───


@router.patch("/batch-decision", response_model=list[NegotiationIssueOut])
async def batch_update_decision(
    txn_id: uuid.UUID,
    body: list[BatchDecisionUpdate],
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """일괄 의사결정 상태 업데이트."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    updated: list[NegotiationIssueOut] = []
    for item in body:
        issue = await _get_issue_or_404(db, txn_id, item.issue_id)
        issue.decision_status = item.decision_status
        await audit_service.record(
            db,
            entity_type="NegotiationIssue",
            entity_id=issue.id,
            action=AuditAction.UPDATE,
            actor_email=claims.email,
            new_value={"decision_status": item.decision_status},
        )
        updated.append(NegotiationIssueOut.model_validate(issue))
    await db.commit()
    return updated


# ── Parametric paths /{issue_id} ─────────────────────────


@router.get("/{issue_id}", response_model=NegotiationIssueOut)
async def get_issue(
    txn_id: uuid.UUID,
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await check_client_deal_access(db, txn_id, claims)
    issue = await _get_issue_or_404(db, txn_id, issue_id)
    return NegotiationIssueOut.model_validate(issue)


@router.get("/{issue_id}/linked", response_model=list[NegotiationIssueOut])
async def get_linked_issues(
    txn_id: uuid.UUID,
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """교차 계약 연동 이견 조회."""
    await check_client_deal_access(db, txn_id, claims)
    issue = await _get_issue_or_404(db, txn_id, issue_id)
    if not issue.linked_issue_ids:
        return []

    linked_uuids = [uuid.UUID(lid) for lid in issue.linked_issue_ids]
    q = select(NegotiationIssue).where(
        NegotiationIssue.id.in_(linked_uuids),
        NegotiationIssue.transaction_id == txn_id,
    )
    result = await db.execute(q)
    return [NegotiationIssueOut.model_validate(i) for i in result.scalars().all()]


@router.post("", response_model=NegotiationIssueOut, status_code=201)
async def create_issue(
    txn_id: uuid.UUID,
    body: NegotiationIssueCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    issue = NegotiationIssue(
        transaction_id=txn_id,
        created_by_email=claims.email,
        **body.model_dump(),
    )
    db.add(issue)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="NegotiationIssue",
        entity_id=issue.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"title": body.title},
    )
    await db.commit()
    await db.refresh(issue)
    return NegotiationIssueOut.model_validate(issue)


@router.patch("/{issue_id}", response_model=NegotiationIssueOut)
async def update_issue(
    txn_id: uuid.UUID,
    issue_id: uuid.UUID,
    body: NegotiationIssueUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    issue = await _get_issue_or_404(db, txn_id, issue_id)
    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(issue, k) for k in update_data}
    for k, v in update_data.items():
        setattr(issue, k, v)
    await audit_service.record(
        db,
        entity_type="NegotiationIssue",
        entity_id=issue.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(issue)
    return NegotiationIssueOut.model_validate(issue)


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(
    txn_id: uuid.UUID,
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    issue = await _get_issue_or_404(db, txn_id, issue_id)
    await audit_service.record(
        db,
        entity_type="NegotiationIssue",
        entity_id=issue.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(issue)
    await db.commit()


@router.post("/{issue_id}/ai-suggest", response_model=AIClauseSuggestionResponse)
async def ai_suggest_clause(
    txn_id: uuid.UUID,
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """AI 조항 수정 제안 생성 — 이견의 양측 입장을 기반으로 절충안 제시."""
    issue = await _get_issue_or_404(db, txn_id, issue_id)
    suggestion = await suggest_clause_revision(
        issue_title=issue.title,
        clause_reference=issue.clause_reference,
        our_position=issue.our_position,
        counterpart_position=issue.counterpart_position,
        legal_review=issue.legal_review,
    )
    # AI 제안을 이슈에 저장
    issue.ai_suggestion = suggestion.suggested_text
    issue.ai_suggestion_rationale = suggestion.rationale
    await audit_service.record(
        db,
        entity_type="NegotiationIssue",
        entity_id=issue.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={"action": "ai_suggest", "title": issue.title},
    )
    await db.commit()
    await db.refresh(issue)
    return suggestion


async def _get_issue_or_404(db: AsyncSession, txn_id: uuid.UUID, issue_id: uuid.UUID) -> NegotiationIssue:
    q = select(NegotiationIssue).where(
        NegotiationIssue.id == issue_id,
        NegotiationIssue.transaction_id == txn_id,
    )
    issue = (await db.execute(q)).scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="협상 이견을 찾을 수 없습니다")
    return issue
