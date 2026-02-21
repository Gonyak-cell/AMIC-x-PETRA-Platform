"""딜 내부 노트/코멘트 라우터 — 스레드 기반 협업."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.enums import AuditAction, NoteType
from app.models.note import DealNote
from app.schemas.note import NoteCreate, NoteListResponse, NoteOut, NoteUpdate
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/notes", tags=["Notes"])


@router.get("", response_model=NoteListResponse)
async def list_notes(
    txn_id: uuid.UUID,
    note_type: NoteType | None = None,
    pinned_only: bool = False,
    parent_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(DealNote).where(DealNote.transaction_id == txn_id)
    count_q = select(func.count(DealNote.id)).where(DealNote.transaction_id == txn_id)

    if note_type:
        q = q.where(DealNote.note_type == note_type)
        count_q = count_q.where(DealNote.note_type == note_type)
    if pinned_only:
        q = q.where(DealNote.is_pinned.is_(True))
        count_q = count_q.where(DealNote.is_pinned.is_(True))
    if parent_id is not None:
        q = q.where(DealNote.parent_id == parent_id)
        count_q = count_q.where(DealNote.parent_id == parent_id)
    else:
        # 루트 노트만 (스레드 최상위)
        q = q.where(DealNote.parent_id.is_(None))
        count_q = count_q.where(DealNote.parent_id.is_(None))

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(DealNote.is_pinned.desc(), DealNote.created_at.desc())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    items = [NoteOut.model_validate(n) for n in result.scalars().all()]
    return NoteListResponse(items=items, total=total)


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    txn_id: uuid.UUID,
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    note = await _get_note_or_404(db, txn_id, note_id)
    return NoteOut.model_validate(note)


@router.get("/{note_id}/replies", response_model=NoteListResponse)
async def list_replies(
    txn_id: uuid.UUID,
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    """특정 노트의 답글 목록."""
    await _get_note_or_404(db, txn_id, note_id)
    q = select(DealNote).where(
        DealNote.transaction_id == txn_id,
        DealNote.parent_id == note_id,
    ).order_by(DealNote.created_at.asc())
    result = await db.execute(q)
    items = [NoteOut.model_validate(n) for n in result.scalars().all()]
    return NoteListResponse(items=items, total=len(items))


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(
    txn_id: uuid.UUID,
    body: NoteCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    # parent_id가 지정되면 부모 노트 존재 확인
    if body.parent_id:
        await _get_note_or_404(db, txn_id, body.parent_id)

    note = DealNote(
        transaction_id=txn_id,
        author_email=claims.email,
        **body.model_dump(),
    )
    db.add(note)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="DealNote",
        entity_id=note.id,
        action=AuditAction.NOTE_CREATED,
        actor_email=claims.email,
        new_value={"note_type": body.note_type.value, "content_preview": body.content[:100]},
    )
    await db.commit()
    await db.refresh(note)
    return NoteOut.model_validate(note)


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    txn_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    note = await _get_note_or_404(db, txn_id, note_id)
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(note, k, v)
    await audit_service.record(
        db,
        entity_type="DealNote",
        entity_id=note.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(note)
    return NoteOut.model_validate(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    txn_id: uuid.UUID,
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    note = await _get_note_or_404(db, txn_id, note_id)
    await audit_service.record(
        db,
        entity_type="DealNote",
        entity_id=note.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(note)
    await db.commit()


async def _get_note_or_404(db: AsyncSession, txn_id: uuid.UUID, note_id: uuid.UUID) -> DealNote:
    q = select(DealNote).where(DealNote.id == note_id, DealNote.transaction_id == txn_id)
    note = (await db.execute(q)).scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="노트를 찾을 수 없습니다")
    return note
