"""M&A 대시보드 KPI 라우터."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

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
) -> DashboardStats:
    """M&A 대시보드 통계."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")

    _not_deleted = Transaction.is_deleted.is_(False)

    # 1) phase별 count + sum (→ total, total_value도 합산으로 도출)
    phase_q = (
        select(
            Transaction.phase,
            func.count().label("cnt"),
            func.sum(Transaction.estimated_deal_value).label("phase_value"),
        )
        .where(_not_deleted)
        .group_by(Transaction.phase)
    )
    phase_rows = (await db.execute(phase_q)).all()

    by_phase = [
        PhaseSummary(phase=row.phase.value, count=row.cnt, total_value=row.phase_value or None) for row in phase_rows
    ]
    total = sum(row.cnt for row in phase_rows)
    total_value = sum(row.phase_value or Decimal(0) for row in phase_rows) or None

    # 2) status별 count (→ active 건수도 여기서 추출)
    status_q = select(Transaction.status, func.count().label("cnt")).where(_not_deleted).group_by(Transaction.status)
    by_status = {row.status.value: row.cnt for row in (await db.execute(status_q)).all()}
    active = by_status.get("ACTIVE", 0)

    # 3) side별 count
    side_q = select(Transaction.side, func.count().label("cnt")).where(_not_deleted).group_by(Transaction.side)
    by_side = {row.side.value: row.cnt for row in (await db.execute(side_q)).all()}

    # 4) recent activity (last 7 days)
    week_ago = datetime.now(UTC) - timedelta(days=7)
    activity_q = select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= week_ago)
    recent_count = (await db.execute(activity_q)).scalar_one()

    return DashboardStats(
        total_transactions=total,
        active_transactions=active,
        total_deal_value=total_value,
        by_phase=by_phase,
        by_status=by_status,
        by_side=by_side,
        recent_activity_count=recent_count,
    )


@router.get("/docs-stats")
async def get_docs_stats(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> dict[str, int]:
    """Deal Document Studio 전체 문서 통계."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    legal_sq = select(func.count()).select_from(LegalDocument).scalar_subquery()
    marketing_sq = select(func.count()).select_from(MarketingMaterial).scalar_subquery()
    ldd_sq = select(func.count()).select_from(LDDReport).scalar_subquery()
    row = (
        await db.execute(select(legal_sq.label("legal"), marketing_sq.label("marketing"), ldd_sq.label("ldd")))
    ).one()
    return {
        "total_legal": row.legal or 0,
        "total_marketing": row.marketing or 0,
        "total_ldd": row.ldd or 0,
    }
