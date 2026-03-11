"""미팅 로그 스키마 — 참석자 포함."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    AttendeeRole,
    BuyerReaction,
    ConditionMatchLevel,
    MarketingStage,
    MeetingChannel,
    MeetingPhase,
    MeetingStatus,
)


# ── 제공자료 스키마 ──────────────────────────────────
class ProvidedMaterial(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = None


# ── 참석자 ────────────────────────────────────────────
class MeetingAttendeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    name: str
    email: str | None = None
    organization: str | None = None
    role: AttendeeRole
    reaction: BuyerReaction | None = None
    comments: str | None = None
    created_at: datetime
    updated_at: datetime


class MeetingAttendeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str | None = None
    organization: str | None = None
    role: AttendeeRole = AttendeeRole.OTHER
    reaction: BuyerReaction | None = None
    comments: str | None = None


class MeetingAttendeeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    email: str | None = None
    organization: str | None = None
    role: AttendeeRole | None = None
    reaction: BuyerReaction | None = None
    comments: str | None = None


# ── 미팅 로그 ─────────────────────────────────────────
class MeetingLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    meeting_phase: MeetingPhase
    title: str
    meeting_date: str
    meeting_time: str | None = None
    location: str | None = None
    channel: MeetingChannel
    status: MeetingStatus
    minutes: str | None = None
    summary: str | None = None
    provided_materials: list[ProvidedMaterial] | None = None
    attachments: list[dict] | None = None
    buyer_id: uuid.UUID | None = None
    marketing_stage: MarketingStage | None = None
    condition_match: ConditionMatchLevel | None = None
    condition_notes: str | None = None
    contract_id: uuid.UUID | None = None
    attendee_count: int = 0
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class MeetingLogDetail(MeetingLogOut):
    """상세 조회 — 참석자 + 액션아이템 포함."""

    attendees: list[MeetingAttendeeOut] = []
    action_items: list = []  # MeetingActionItemOut 사용 (순환 import 방지)


class MeetingLogCreate(BaseModel):
    meeting_phase: MeetingPhase = Field(description="미팅 유형 (MARKETING / NEGOTIATION 등)")
    title: str = Field(..., min_length=1, max_length=300, description="미팅 제목")
    meeting_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="미팅 일자 (YYYY-MM-DD)")
    meeting_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$", description="미팅 시간 (HH:MM)")
    location: str | None = Field(None, description="미팅 장소")
    channel: MeetingChannel = MeetingChannel.IN_PERSON
    status: MeetingStatus = MeetingStatus.COMPLETED
    minutes: str | None = Field(None, description="회의록")
    summary: str | None = Field(None, description="요약")
    provided_materials: list[ProvidedMaterial] | None = None
    attachments: list[dict] | None = None
    buyer_id: uuid.UUID | None = Field(None, description="매수자 ID (마케팅 미팅 시 필수)")
    marketing_stage: MarketingStage | None = Field(
        None, description="마케팅 단계 — meeting_phase=MARKETING일 때만 유효"
    )
    condition_match: ConditionMatchLevel | None = None
    condition_notes: str | None = None
    contract_id: uuid.UUID | None = None
    # 참석자 인라인 생성
    attendees: list[MeetingAttendeeCreate] | None = None

    @model_validator(mode="after")
    def validate_marketing_stage_phase(self) -> Self:
        """marketing_stage는 meeting_phase=MARKETING일 때만 허용."""
        if self.marketing_stage is not None and self.meeting_phase != MeetingPhase.MARKETING:
            msg = "marketing_stage는 meeting_phase가 MARKETING일 때만 지정할 수 있습니다"
            raise ValueError(msg)
        return self


class MeetingLogUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300, description="미팅 제목")
    meeting_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="미팅 일자")
    meeting_time: str | None = None
    location: str | None = None
    channel: MeetingChannel | None = None
    status: MeetingStatus | None = None
    minutes: str | None = None
    summary: str | None = None
    provided_materials: list[ProvidedMaterial] | None = None
    attachments: list[dict] | None = None
    buyer_id: uuid.UUID | None = None
    marketing_stage: MarketingStage | None = Field(
        None, description="마케팅 단계 — meeting_phase=MARKETING일 때만 유효"
    )
    condition_match: ConditionMatchLevel | None = None
    condition_notes: str | None = None
    contract_id: uuid.UUID | None = None


class MeetingLogListResponse(BaseModel):
    items: list[MeetingLogOut]
    total: int


class MeetingLogSummary(BaseModel):
    total: int = 0
    by_status: dict[str, int] = {}
    by_channel: dict[str, int] = {}
