"""VDR 접근 추적 서비스 — 매수자별 실사 활동 기록·조회."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import case

from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import VdrAccessAction
from app.models.vdr_access_log import VdrAccessLog

logger = logging.getLogger(__name__)


async def record_access(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    document_id: uuid.UUID | None,
    folder_id: uuid.UUID | None,
    user_email: str,
    user_id: str,
    action: VdrAccessAction,
    ip_address: str | None = None,
    user_agent: str | None = None,
    buyer_id: uuid.UUID | None = None,
) -> None:
    """VDR 접근 기록을 저장한다 (BackgroundTasks에서 호출)."""
    log = VdrAccessLog(
        transaction_id=transaction_id,
        document_id=document_id,
        folder_id=folder_id,
        user_email=user_email,
        user_id=user_id,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        buyer_id=buyer_id,
    )
    db.add(log)
    await db.commit()
    logger.debug(
        "VDR 접근 기록 저장: txn=%s, user=%s, action=%s",
        transaction_id,
        user_email,
        action,
    )


async def record_access_background(
    *,
    transaction_id: uuid.UUID,
    document_id: uuid.UUID | None,
    folder_id: uuid.UUID | None,
    user_email: str,
    user_id: str,
    action: VdrAccessAction,
    ip_address: str | None = None,
    user_agent: str | None = None,
    buyer_id: uuid.UUID | None = None,
) -> None:
    """BackgroundTasks용 래퍼 — 새 DB 세션 생성."""
    from app.core.database import async_session_factory

    async with async_session_factory() as db:
        await record_access(
            db,
            transaction_id=transaction_id,
            document_id=document_id,
            folder_id=folder_id,
            user_email=user_email,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            buyer_id=buyer_id,
        )


async def get_access_logs(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    *,
    buyer_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    action: VdrAccessAction | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[VdrAccessLog], int]:
    """접근 로그를 필터링하여 조회한다."""
    stmt = select(VdrAccessLog).where(VdrAccessLog.transaction_id == transaction_id)
    count_stmt = select(func.count()).select_from(VdrAccessLog).where(VdrAccessLog.transaction_id == transaction_id)

    if buyer_id is not None:
        stmt = stmt.where(VdrAccessLog.buyer_id == buyer_id)
        count_stmt = count_stmt.where(VdrAccessLog.buyer_id == buyer_id)
    if document_id is not None:
        stmt = stmt.where(VdrAccessLog.document_id == document_id)
        count_stmt = count_stmt.where(VdrAccessLog.document_id == document_id)
    if action is not None:
        stmt = stmt.where(VdrAccessLog.action == action)
        count_stmt = count_stmt.where(VdrAccessLog.action == action)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(VdrAccessLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_buyer_activity_summary(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[dict]:
    """매수자별 VDR 활동 요약을 반환한다."""
    # SQLite + PostgreSQL 호환: CASE WHEN 사용
    stmt = (
        select(
            VdrAccessLog.buyer_id,
            func.count(func.distinct(VdrAccessLog.document_id)).label("unique_docs"),
            func.sum(
                case(
                    (VdrAccessLog.action == VdrAccessAction.VIEW, 1),
                    else_=0,
                ).cast(Integer)
            ).label("views"),
            func.sum(
                case(
                    (VdrAccessLog.action == VdrAccessAction.DOWNLOAD, 1),
                    else_=0,
                ).cast(Integer)
            ).label("downloads"),
            func.max(VdrAccessLog.created_at).label("last_access"),
        )
        .where(
            VdrAccessLog.transaction_id == transaction_id,
            VdrAccessLog.buyer_id.is_not(None),
        )
        .group_by(VdrAccessLog.buyer_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    # 매수자 이름 조회 (N+1 방지: 한 번에 조회)
    buyer_ids = [r.buyer_id for r in rows]
    buyer_stmt = select(BuyerCandidate.id, BuyerCandidate.company_name).where(BuyerCandidate.id.in_(buyer_ids))
    buyer_result = await db.execute(buyer_stmt)
    buyer_names: dict[uuid.UUID, str] = {row.id: row.company_name for row in buyer_result.all()}

    return [
        {
            "buyer_id": r.buyer_id,
            "buyer_name": buyer_names.get(r.buyer_id, "Unknown"),
            "unique_documents_accessed": r.unique_docs,
            "total_views": r.views or 0,
            "total_downloads": r.downloads or 0,
            "last_access_at": r.last_access,
        }
        for r in rows
    ]


async def get_document_access_logs(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[VdrAccessLog], int]:
    """특정 문서의 접근 이력을 조회한다."""
    return await get_access_logs(db, transaction_id, document_id=document_id, skip=skip, limit=limit)
