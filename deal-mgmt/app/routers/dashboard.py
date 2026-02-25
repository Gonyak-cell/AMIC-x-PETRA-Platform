"""M&A 대시보드 KPI 라우터."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.audit import AuditLog
from app.models.ldd_report import LDDReport
from app.models.legal_document import LegalDocument
from app.models.marketing_material import MarketingMaterial
from app.models.transaction import Transaction
from app.schemas.dashboard import DashboardStats, PhaseSummary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """M&A 대시보드 통계."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    base = select(Transaction).where(Transaction.is_deleted.is_(False))
    result = await db.execute(base)
    transactions = list(result.scalars().all())

    total = len(transactions)
    active = sum(1 for t in transactions if t.status.value == "ACTIVE")
    total_value = sum(float(t.estimated_deal_value) for t in transactions if t.estimated_deal_value)

    # by phase
    phase_counts: dict[str, list] = {}
    for t in transactions:
        p = t.phase.value
        if p not in phase_counts:
            phase_counts[p] = [0, 0.0]
        phase_counts[p][0] += 1
        if t.estimated_deal_value:
            phase_counts[p][1] += float(t.estimated_deal_value)

    by_phase = [
        PhaseSummary(phase=phase, count=vals[0], total_value=vals[1] or None) for phase, vals in phase_counts.items()
    ]

    # by status
    by_status: dict[str, int] = {}
    for t in transactions:
        s = t.status.value
        by_status[s] = by_status.get(s, 0) + 1

    # by side
    by_side: dict[str, int] = {}
    for t in transactions:
        s = t.side.value
        by_side[s] = by_side.get(s, 0) + 1

    # recent activity (last 7 days)
    week_ago = datetime.now(UTC) - timedelta(days=7)
    activity_q = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= week_ago)
    recent_count = (await db.execute(activity_q)).scalar_one()

    return DashboardStats(
        total_transactions=total,
        active_transactions=active,
        total_deal_value=total_value or None,
        by_phase=by_phase,
        by_status=by_status,
        by_side=by_side,
        recent_activity_count=recent_count,
    )


@router.get("/docs-stats")
async def get_docs_stats(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """Deal Document Studio 전체 문서 통계."""
    legal = await db.scalar(select(func.count()).select_from(LegalDocument))
    marketing = await db.scalar(select(func.count()).select_from(MarketingMaterial))
    ldd = await db.scalar(select(func.count()).select_from(LDDReport))
    return {
        "total_legal": legal or 0,
        "total_marketing": marketing or 0,
        "total_ldd": ldd or 0,
    }
