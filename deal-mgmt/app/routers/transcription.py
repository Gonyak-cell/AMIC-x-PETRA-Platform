"""녹음 변환 — 오디오 업로드 + Clova STT + LLM 회의록 자동 생성."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import (
    ActionItemStatus,
    AuditAction,
    MeetingChannel,
    MeetingPhase,
    MeetingStatus,
    TranscriptionJobStatus,
)
from app.models.meeting_action_item import MeetingActionItem
from app.models.meeting_attendee import MeetingAttendee
from app.models.meeting_log import MeetingLog
from app.models.transcription_job import TranscriptionJob
from app.schemas.transcription import TranscriptionApproval, TranscriptionJobOut
from app.services import audit_service, transaction_service
from app.services.transcription_service import ALLOWED_AUDIO_TYPES, MAX_AUDIO_SIZE_BYTES

router = APIRouter(
    prefix="/transactions/{txn_id}/transcription",
    tags=["Transcription"],
)

UPLOAD_DIR = Path("uploads/transcription")

_WRITE = require_write_access()


@router.post("", response_model=TranscriptionJobOut, status_code=202)
async def start_transcription(
    txn_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    audio: UploadFile,
    title: str = Form(...),
    meeting_date: str = Form(...),
    meeting_phase: MeetingPhase = Form(MeetingPhase.MARKETING),
    buyer_id: str | None = Form(None),
    attendees_json: str = Form("[]"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_WRITE),
):
    """녹음 파일을 업로드하고 비동기 변환을 시작한다.

    202 Accepted를 반환하고, 백그라운드에서 STT + LLM 처리를 진행한다.
    """
    await check_client_deal_access(db, txn_id, claims)
    await transaction_service.get_transaction(db, txn_id)

    # 파일 검증 — content_type이 None이면 octet-stream으로 폴백 (우회 방지)
    content_type = audio.content_type or "application/octet-stream"
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 오디오 형식입니다: {content_type}",
        )

    # 파일 저장
    save_dir = UPLOAD_DIR / str(txn_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    ext = Path(audio.filename or "audio.mp3").suffix
    safe_filename = re.sub(r"[^\w\-. ]", "_", audio.filename or "audio")[:255]
    file_path = save_dir / f"{file_id}{ext}"

    content = await audio.read()
    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 크기가 {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB를 초과합니다",
        )
    file_path.write_bytes(content)

    # attendees JSON 파싱 — 유효하지 않은 형식은 400 에러 반환
    try:
        attendees = json.loads(attendees_json)
        if not isinstance(attendees, list):
            raise ValueError("attendees must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"참석자 JSON 형식 오류: {e}",
        )

    # 작업 생성
    job = TranscriptionJob(
        transaction_id=txn_id,
        title=title,
        meeting_date=meeting_date,
        meeting_phase=meeting_phase,
        buyer_id=uuid.UUID(buyer_id) if buyer_id else None,
        attendees_json=attendees,
        audio_file_path=str(file_path),
        audio_file_name=safe_filename,
        status=TranscriptionJobStatus.PENDING,
        created_by_email=claims.email,
    )
    db.add(job)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="TranscriptionJob",
        entity_id=job.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"title": title, "meeting_date": meeting_date},
    )
    await db.commit()
    await db.refresh(job)

    # 백그라운드 처리 시작
    background_tasks.add_task(_run_transcription, job.id)

    return TranscriptionJobOut.model_validate(job)


async def _run_transcription(job_id: uuid.UUID) -> None:
    """백그라운드에서 새 DB 세션으로 변환 작업을 실행한다."""
    from app.core.database import async_session_factory
    from app.services.transcription_service import process_transcription_job

    async with async_session_factory() as db:
        await process_transcription_job(db, job_id)


@router.get("/{job_id}", response_model=TranscriptionJobOut)
async def get_transcription_status(
    txn_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """변환 작업 상태를 조회한다 (폴링용)."""
    await check_client_deal_access(db, txn_id, claims)

    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.transaction_id == txn_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="변환 작업을 찾을 수 없습니다")

    return TranscriptionJobOut.model_validate(job)


@router.get("", response_model=list[TranscriptionJobOut])
async def list_transcription_jobs(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """거래의 변환 작업 목록을 반환한다."""
    await check_client_deal_access(db, txn_id, claims)

    result = await db.execute(
        select(TranscriptionJob)
        .where(TranscriptionJob.transaction_id == txn_id)
        .order_by(TranscriptionJob.created_at.desc())
    )
    return [TranscriptionJobOut.model_validate(j) for j in result.scalars().all()]


@router.post("/{job_id}/approve", response_model=TranscriptionJobOut)
async def approve_transcription(
    txn_id: uuid.UUID,
    job_id: uuid.UUID,
    body: TranscriptionApproval,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_WRITE),
):
    """사용자가 검토/편집한 결과를 확정하고 meeting_log를 생성한다."""
    await check_client_deal_access(db, txn_id, claims)

    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.transaction_id == txn_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="변환 작업을 찾을 수 없습니다")

    if job.status not in (TranscriptionJobStatus.COMPLETED,):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"현재 상태({job.status.value})에서는 확정할 수 없습니다",
        )

    # MeetingLog 생성
    meeting_log = MeetingLog(
        transaction_id=txn_id,
        meeting_phase=job.meeting_phase,
        title=job.title,
        meeting_date=job.meeting_date,
        channel=MeetingChannel.IN_PERSON,
        status=MeetingStatus.COMPLETED,
        minutes=body.minutes,
        summary=body.summary,
        buyer_id=job.buyer_id,
        condition_match=body.condition_match,
        condition_notes=body.condition_notes,
        created_by_email=claims.email,
    )
    db.add(meeting_log)
    await db.flush()

    # 참석자 생성
    attendee_count = 0
    if job.attendees_json:
        from app.models.enums import AttendeeRole

        for att in job.attendees_json:
            attendee = MeetingAttendee(
                meeting_id=meeting_log.id,
                name=att.get("name", "Unknown"),
                email=att.get("email"),
                organization=att.get("organization"),
                role=AttendeeRole(att.get("role", "OTHER")),
                reaction=body.buyer_reaction if att.get("role") in ("BUYER_ADVISOR", "COUNTERPARTY") else None,
                comments=att.get("comments"),
            )
            db.add(attendee)
            attendee_count += 1

    meeting_log.attendee_count = attendee_count

    # 액션아이템 생성
    if body.action_items:
        from app.models.enums import NegotiationIssuePriority

        for item in body.action_items:
            action = MeetingActionItem(
                meeting_id=meeting_log.id,
                title=item.title,
                description=item.description,
                assignee_name=item.assignee_name,
                assignee_email=item.assignee_email,
                due_date=item.due_date,
                status=ActionItemStatus.PENDING,
                priority=NegotiationIssuePriority(item.priority) if item.priority else NegotiationIssuePriority.MEDIUM,
            )
            db.add(action)

    # 감사 기록 — MeetingLog CREATE (참석자/액션아이템 포함)
    await audit_service.record(
        db,
        entity_type="MeetingLog",
        entity_id=meeting_log.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={
            "title": job.title,
            "source": "transcription",
            "transcription_job_id": job.id,
            "attendee_count": attendee_count,
        },
    )

    # 작업 상태 업데이트
    job.status = TranscriptionJobStatus.APPROVED
    job.meeting_log_id = meeting_log.id

    await audit_service.record(
        db,
        entity_type="TranscriptionJob",
        entity_id=job.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value={"status": TranscriptionJobStatus.COMPLETED},
        new_value={"status": TranscriptionJobStatus.APPROVED, "meeting_log_id": meeting_log.id},
    )

    await db.commit()
    await db.refresh(job)

    return TranscriptionJobOut.model_validate(job)
