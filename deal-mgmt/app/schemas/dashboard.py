from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, field_serializer


class PhaseSummary(BaseModel):
    phase: str
    count: int
    total_value: Decimal | None = None

    @field_serializer("total_value")
    def _serialize_decimal(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class DashboardStats(BaseModel):
    total_transactions: int
    active_transactions: int
    total_deal_value: Decimal | None = None
    by_phase: list[PhaseSummary]
    by_status: dict[str, int]
    by_side: dict[str, int]
    recent_activity_count: int

    @field_serializer("total_deal_value")
    def _serialize_decimal(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None
