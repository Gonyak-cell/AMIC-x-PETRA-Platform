"""클라이언트 포털 — CLIENT 역할 전용 대시보드 스키마."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class TeamContactForClient(BaseModel):
    """담당자 정보 (CLIENT에게 표시)."""

    name: str
    email: str
    role: str


class MaterialDistributionForClient(BaseModel):
    """문서 배포 현황 (CLIENT에게 표시)."""

    id: uuid.UUID
    doc_type: str  # TM / DM / IM
    title: str
    status: str
    distributed_to: list[str] | None = None
    distributed_at: str | None = None


class BuyerSummaryForClient(BaseModel):
    """매수자별 현황 요약 (IOI/LOI 금액 제외)."""

    buyer_id: uuid.UUID
    company_name: str
    status: str
    status_label: str
    latest_reaction: str | None = None
    latest_reaction_comments: str | None = None
    condition_match: str | None = None
    condition_notes: str | None = None
    next_meeting_date: str | None = None
    next_meeting_title: str | None = None
    meeting_count: int = 0


class UpcomingMeetingForClient(BaseModel):
    """예정된 미팅 (CLIENT에게 표시)."""

    id: uuid.UUID
    title: str
    meeting_date: str
    meeting_time: str | None = None
    location: str | None = None
    channel: str
    attendee_count: int = 0


class RecentActivityForClient(BaseModel):
    """최근 활동 항목."""

    event_type: str  # MEETING_COMPLETED / DOCUMENT_DISTRIBUTED / STATUS_CHANGED
    description: str
    timestamp: str


class ClientPortalDashboard(BaseModel):
    """CLIENT 전용 대시보드 집계 데이터."""

    transaction_name: str
    codename: str
    current_phase: str
    phase_label: str
    team_contacts: list[TeamContactForClient]
    materials: list[MaterialDistributionForClient]
    buyer_summaries: list[BuyerSummaryForClient]
    upcoming_meetings: list[UpcomingMeetingForClient]
    recent_activity: list[RecentActivityForClient]
