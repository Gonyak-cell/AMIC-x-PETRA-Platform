"""Client Portal — CLIENT 역할 전용 대시보드 집계 API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import (
    BuyerCandidateStatus,
    MarketingDocStatus,
    MeetingStatus,
)
from app.models.marketing_material import MarketingMaterial
from app.models.meeting_attendee import MeetingAttendee
from app.models.meeting_log import MeetingLog
from app.models.transaction import Transaction
from app.schemas.client_portal import (
    BuyerSummaryForClient,
    ClientPortalDashboard,
    MaterialDistributionForClient,
    RecentActivityForClient,
    TeamContactForClient,
    UpcomingMeetingForClient,
)
from app.services import transaction_service

router = APIRouter(
    prefix="/transactions/{txn_id}/client-portal",
    tags=["Client Portal"],
)

PHASE_LABELS: dict[str, str] = {
    "ENGAGEMENT": "수임",
    "PREPARATION": "준비",
    "MARKETING": "마케팅",
    "BIDDING_DD": "입찰/실사",
    "NEGOTIATION": "협상",
    "CLOSING": "Closing",
    "POST_CLOSING": "PMI",
}

BUYER_STATUS_LABELS: dict[str, str] = {
    "IDENTIFIED": "발굴",
    "CONTACTED": "컨택",
    "NDA_SENT": "NDA 발송",
    "NDA_SIGNED": "NDA 체결",
    "CIM_SENT": "CIM 발송",
    "INTEREST_CONFIRMED": "관심 확인",
    "IOI_RECEIVED": "IOI 접수",
    "IOI_ACCEPTED": "IOI 수락",
    "DD_GRANTED": "DD 승인",
    "DD_IN_PROGRESS": "DD 진행",
    "LOI_RECEIVED": "LOI 접수",
    "LOI_ACCEPTED": "LOI 수락",
    "SELECTED": "선정",
    "REJECTED": "탈락",
}


@router.get("/dashboard", response_model=ClientPortalDashboard)
async def client_dashboard(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """CLIENT 전용 대시보드 데이터를 집계하여 반환한다.

    내부 사용자도 호출 가능 (check_client_deal_access는 CLIENT만 검증).
    """
    await check_client_deal_access(db, txn_id, claims)

    # 1. 거래 기본 정보
    txn = await transaction_service.get_transaction(db, txn_id)

    # 2. 담당자
    team_contacts = _build_team_contacts(txn)

    # 3. 마케팅 자료 배포 현황
    materials = await _get_materials(db, txn_id)

    # 4. 매수자별 현황
    buyer_summaries = await _get_buyer_summaries(db, txn_id)

    # 5. 다음 미팅 일정
    upcoming = await _get_upcoming_meetings(db, txn_id)

    # 6. 최근 활동
    recent = await _get_recent_activity(db, txn_id)

    return ClientPortalDashboard(
        transaction_name=txn.name,
        codename=txn.code_name,
        current_phase=txn.phase.value,
        phase_label=PHASE_LABELS.get(txn.phase.value, txn.phase.value),
        team_contacts=team_contacts,
        materials=materials,
        buyer_summaries=buyer_summaries,
        upcoming_meetings=upcoming,
        recent_activity=recent,
    )


def _build_team_contacts(txn: Transaction) -> list[TeamContactForClient]:
    """거래의 담당자 정보를 추출한다."""
    contacts: list[TeamContactForClient] = []
    if txn.lead_advisor_email:
        contacts.append(TeamContactForClient(
            name=txn.lead_advisor_email.split("@")[0],
            email=txn.lead_advisor_email,
            role="Lead Advisor",
        ))
    if txn.deal_captain_email:
        contacts.append(TeamContactForClient(
            name=txn.deal_captain_email.split("@")[0],
            email=txn.deal_captain_email,
            role="Deal Captain",
        ))
    return contacts


async def _get_materials(db: AsyncSession, txn_id: uuid.UUID) -> list[MaterialDistributionForClient]:
    """마케팅 자료 배포 현황을 반환한다."""
    result = await db.execute(
        select(MarketingMaterial)
        .where(
            MarketingMaterial.transaction_id == txn_id,
            MarketingMaterial.status == MarketingDocStatus.READY,
        )
        .order_by(MarketingMaterial.created_at.desc())
    )
    return [
        MaterialDistributionForClient(
            id=m.id,
            doc_type=m.doc_type.value,
            title=m.title,
            status=m.status.value,
            distributed_to=m.distributed_to,
            distributed_at=m.distributed_at,
        )
        for m in result.scalars().all()
    ]


async def _get_buyer_summaries(db: AsyncSession, txn_id: uuid.UUID) -> list[BuyerSummaryForClient]:
    """매수자별 현황 요약 (IOI/LOI 금액 제외)."""
    # 매수자 목록
    buyer_result = await db.execute(
        select(BuyerCandidate)
        .where(
            BuyerCandidate.transaction_id == txn_id,
            BuyerCandidate.status != BuyerCandidateStatus.REJECTED,
        )
        .order_by(BuyerCandidate.created_at)
    )
    buyers = buyer_result.scalars().all()
    if not buyers:
        return []

    buyer_ids = [b.id for b in buyers]

    # 매수자별 최근 미팅에서 반응/조건 가져오기
    latest_meetings_sub = (
        select(
            MeetingLog.buyer_id,
            func.max(MeetingLog.meeting_date).label("latest_date"),
        )
        .where(
            MeetingLog.transaction_id == txn_id,
            MeetingLog.buyer_id.in_(buyer_ids),
            MeetingLog.status == MeetingStatus.COMPLETED,
        )
        .group_by(MeetingLog.buyer_id)
        .subquery()
    )

    latest_meetings_result = await db.execute(
        select(MeetingLog)
        .join(
            latest_meetings_sub,
            (MeetingLog.buyer_id == latest_meetings_sub.c.buyer_id)
            & (MeetingLog.meeting_date == latest_meetings_sub.c.latest_date),
        )
        .where(MeetingLog.transaction_id == txn_id)
    )
    latest_meetings = {m.buyer_id: m for m in latest_meetings_result.scalars().all()}

    # 매수자별 최근 미팅 참석자 반응
    latest_meeting_ids = [m.id for m in latest_meetings.values()]
    reaction_map: dict[uuid.UUID, tuple[str | None, str | None]] = {}
    if latest_meeting_ids:
        att_result = await db.execute(
            select(MeetingAttendee)
            .where(
                MeetingAttendee.meeting_id.in_(latest_meeting_ids),
                MeetingAttendee.reaction.isnot(None),
            )
            .order_by(MeetingAttendee.created_at.desc())
        )
        for att in att_result.scalars().all():
            # 미팅 ID → 매수자 ID 역매핑
            for buyer_id, meeting in latest_meetings.items():
                if meeting.id == att.meeting_id and buyer_id not in reaction_map:
                    reaction_map[buyer_id] = (att.reaction.value if att.reaction else None, att.comments)

    # 매수자별 다음 미팅 (SCHEDULED)
    next_meetings_result = await db.execute(
        select(MeetingLog)
        .where(
            MeetingLog.transaction_id == txn_id,
            MeetingLog.buyer_id.in_(buyer_ids),
            MeetingLog.status == MeetingStatus.SCHEDULED,
        )
        .order_by(MeetingLog.meeting_date.asc())
    )
    next_meetings: dict[uuid.UUID, MeetingLog] = {}
    for m in next_meetings_result.scalars().all():
        if m.buyer_id and m.buyer_id not in next_meetings:
            next_meetings[m.buyer_id] = m

    # 매수자별 미팅 수
    count_result = await db.execute(
        select(MeetingLog.buyer_id, func.count(MeetingLog.id))
        .where(
            MeetingLog.transaction_id == txn_id,
            MeetingLog.buyer_id.in_(buyer_ids),
        )
        .group_by(MeetingLog.buyer_id)
    )
    meeting_counts = dict(count_result.all())

    summaries: list[BuyerSummaryForClient] = []
    for b in buyers:
        latest = latest_meetings.get(b.id)
        reaction_info = reaction_map.get(b.id, (None, None))
        next_mtg = next_meetings.get(b.id)

        summaries.append(BuyerSummaryForClient(
            buyer_id=b.id,
            company_name=b.company_name,
            status=b.status.value,
            status_label=BUYER_STATUS_LABELS.get(b.status.value, b.status.value),
            latest_reaction=reaction_info[0],
            latest_reaction_comments=reaction_info[1],
            condition_match=latest.condition_match.value if latest and latest.condition_match else None,
            condition_notes=latest.condition_notes if latest else None,
            next_meeting_date=next_mtg.meeting_date if next_mtg else None,
            next_meeting_title=next_mtg.title if next_mtg else None,
            meeting_count=meeting_counts.get(b.id, 0),
        ))

    return summaries


async def _get_upcoming_meetings(db: AsyncSession, txn_id: uuid.UUID) -> list[UpcomingMeetingForClient]:
    """SCHEDULED 상태 미팅을 반환한다."""
    result = await db.execute(
        select(MeetingLog)
        .where(
            MeetingLog.transaction_id == txn_id,
            MeetingLog.status == MeetingStatus.SCHEDULED,
        )
        .order_by(MeetingLog.meeting_date.asc())
        .limit(10)
    )
    return [
        UpcomingMeetingForClient(
            id=m.id,
            title=m.title,
            meeting_date=m.meeting_date,
            meeting_time=m.meeting_time,
            location=m.location,
            channel=m.channel.value,
            attendee_count=m.attendee_count,
        )
        for m in result.scalars().all()
    ]


async def _get_recent_activity(db: AsyncSession, txn_id: uuid.UUID) -> list[RecentActivityForClient]:
    """최근 활동 목록 (완료 미팅 + 배포된 문서)."""
    activities: list[RecentActivityForClient] = []

    # 최근 완료 미팅
    meeting_result = await db.execute(
        select(MeetingLog)
        .where(
            MeetingLog.transaction_id == txn_id,
            MeetingLog.status == MeetingStatus.COMPLETED,
        )
        .order_by(MeetingLog.meeting_date.desc())
        .limit(5)
    )
    for m in meeting_result.scalars().all():
        activities.append(RecentActivityForClient(
            event_type="MEETING_COMPLETED",
            description=f"미팅 완료: {m.title}",
            timestamp=m.meeting_date,
        ))

    # 배포된 마케팅 자료
    mat_result = await db.execute(
        select(MarketingMaterial)
        .where(
            MarketingMaterial.transaction_id == txn_id,
            MarketingMaterial.distributed_at.isnot(None),
        )
        .order_by(MarketingMaterial.distributed_at.desc())
        .limit(5)
    )
    for m in mat_result.scalars().all():
        count = len(m.distributed_to) if m.distributed_to else 0
        activities.append(RecentActivityForClient(
            event_type="DOCUMENT_DISTRIBUTED",
            description=f"{m.doc_type.value} 배포: {m.title} ({count}곳)",
            timestamp=m.distributed_at or "",
        ))

    # 시간순 정렬 (최신 먼저)
    activities.sort(key=lambda a: a.timestamp, reverse=True)
    return activities[:10]
