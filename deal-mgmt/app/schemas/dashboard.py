from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class PhaseSummary(BaseModel):
    phase: str
    count: int
    total_value: Decimal | None = None


class DashboardStats(BaseModel):
    total_transactions: int
    active_transactions: int
    total_deal_value: Decimal | None = None
    by_phase: list[PhaseSummary]
    by_status: dict[str, int]
    by_side: dict[str, int]
    recent_activity_count: int
