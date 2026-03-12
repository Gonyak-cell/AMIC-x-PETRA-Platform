"""워크스페이스 요약 서비스 — 배지 카운트 집계."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.closing_checklist import ClosingChecklist
from app.models.contract import Contract
from app.models.dd_checklist import DDChecklist
from app.models.earnout import EarnoutMilestone
from app.models.engagement import Engagement
from app.models.financial_model import FinancialModel
from app.models.legal_document import LegalDocument
from app.models.marketing_material import MarketingMaterial
from app.models.nda import NDA
from app.models.pmi_task import PMITask
from app.models.timeline import DealTimeline
from app.schemas.workspace_summary import WorkspaceSummary

# (field_name, Model) — 모든 모델은 transaction_id FK를 가짐
_COUNT_TARGETS: list[tuple[str, type]] = [
    ("buyer_count", BuyerCandidate),
    ("engagement_count", Engagement),
    ("timeline_count", DealTimeline),
    ("nda_count", NDA),
    ("bid_count", Bid),
    ("dd_item_count", DDChecklist),
    ("contract_count", Contract),
    ("closing_item_count", ClosingChecklist),
    ("pmi_count", PMITask),
    ("earnout_count", EarnoutMilestone),
    ("marketing_material_count", MarketingMaterial),
    ("financial_model_count", FinancialModel),
    ("legal_document_count", LegalDocument),
]


async def get_workspace_summary(
    db: AsyncSession,
    txn_id: uuid.UUID,
) -> WorkspaceSummary:
    """거래 워크스페이스의 모든 배지 카운트를 단일 쿼리로 집계.

    13개 엔티티의 COUNT(*)를 scalar subquery로 묶어
    한 번의 DB 라운드트립으로 처리한다.
    """
    subqueries = [
        select(func.count())
        .where(model.transaction_id == txn_id)  # type: ignore[attr-defined]
        .correlate()
        .scalar_subquery()
        .label(field)
        for field, model in _COUNT_TARGETS
    ]
    row = (await db.execute(select(*subqueries))).one()
    return WorkspaceSummary(**row._asdict())
