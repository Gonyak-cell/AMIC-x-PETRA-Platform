from __future__ import annotations

from pydantic import BaseModel


class PhaseSummary(BaseModel):
    phase: str
    count: int
    total_value: float | None = None


class DashboardStats(BaseModel):
    total_transactions: int
    active_transactions: int
    total_deal_value: float | None = None
    by_phase: list[PhaseSummary]
    by_status: dict[str, int]
    by_side: dict[str, int]
    recent_activity_count: int
