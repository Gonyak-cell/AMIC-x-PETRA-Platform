"""연결 분석 서비스 — Sprint 16.

딜의 전체 엔티티를 로드하고, 엔티티별 데이터를 구성(FX 변환 포함)한 뒤
연결 엔진을 호출한다.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.engines.consolidation_engine import (
    ConsolidationResult,
    EntityAccountData,
    EvidenceLinkData,
    consolidate_entities,
)
from app.models.account_mapping import AccountMapping, MappingStatus
from app.models.deal import Deal
from app.models.entity import Entity, EntityType
from app.models.standard_line_item import FinancialStatement, StandardLineItem
from app.services.fx.fx_service import build_fx_converted_tb_map

logger = get_logger(__name__)


def _get_line_items_map(db: Session) -> dict[str, StandardLineItem]:
    items = list(db.scalars(select(StandardLineItem)))
    return {item.code: item for item in items}


def run_consolidation(
    db: Session,
    deal_id: uuid.UUID,
    ic_pairs: list[tuple[str, str, str, Decimal]] | None = None,
) -> tuple[ConsolidationResult, list[EvidenceLinkData]]:
    """딜의 멀티 엔티티 데이터를 연결 분석한다.

    Args:
        deal_id: 딜 ID
        ic_pairs: 수동 IC 제거 항목 [(debit_entity, credit_entity, category, amount)]

    Returns:
        (ConsolidationResult, evidence_links)
    """
    deal = db.get(Deal, deal_id)
    if deal is None:
        msg = f"Deal not found: {deal_id}"
        raise ValueError(msg)

    # 1. 엔티티 목록 로드
    entities = list(
        db.scalars(
            select(Entity).where(
                Entity.deal_id == deal_id,
                Entity.is_active.is_(True),
                Entity.entity_type != EntityType.CONSOLIDATED,
            )
        )
    )

    if not entities:
        msg = f"No active entities found for deal {deal_id}"
        raise ValueError(msg)

    target_currency = deal.base_currency
    li_map = _get_line_items_map(db)

    # 2. 엔티티별 account data 구성
    entity_accounts: dict[str, list[EntityAccountData]] = {}
    ownership_pcts: dict[str, Decimal] = {}

    for entity in entities:
        ownership_pcts[str(entity.id)] = entity.ownership_pct or Decimal("100.0000")

        # FX 변환된 TB 맵
        if entity.functional_currency != target_currency:
            tb_map = build_fx_converted_tb_map(
                db,
                deal_id,
                target_currency=target_currency,
                reference_date=deal.reference_date,
                entity_id=entity.id,
            )
        else:
            # 동일 통화: 직접 집계
            from app.services.nwc.nwc_service import _get_tb_accounts

            tb_map = _get_tb_accounts(db, deal_id, entity_id=entity.id)

        # APPROVED 매핑 기준 계정 구성
        mappings = list(
            db.scalars(
                select(AccountMapping).where(
                    AccountMapping.deal_id == deal_id,
                    AccountMapping.status == MappingStatus.APPROVED,
                )
            )
        )

        accounts: list[EntityAccountData] = []
        for mapping in mappings:
            li = li_map.get(mapping.target_line_item_code)
            if not li or li.is_subtotal:
                continue
            # BS + IS 모두 포함 (연결 분석용)
            if li.statement_type not in (FinancialStatement.BS, FinancialStatement.IS):
                continue

            balance = tb_map.get(mapping.source_account_code, Decimal("0"))
            accounts.append(
                EntityAccountData(
                    entity_id=str(entity.id),
                    entity_code=entity.code,
                    account_code=mapping.source_account_code,
                    account_name=mapping.source_account_name,
                    category=li.category.value,
                    amount=balance,
                )
            )

        entity_accounts[str(entity.id)] = accounts

    logger.info(
        "Consolidation data prepared",
        extra={
            "ctx": {
                "deal_id": str(deal_id),
                "entity_count": len(entities),
                "target_currency": target_currency,
            }
        },
    )

    # 3. 연결 엔진 호출
    return consolidate_entities(
        entity_accounts=entity_accounts,
        ownership_pcts=ownership_pcts,
        ic_pairs=ic_pairs,
    )
