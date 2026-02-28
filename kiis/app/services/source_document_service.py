"""원문 공시 연결 서비스.

Deal, DartMajorHolding, DartExecutiveHolding의 rcept_no를
Disclosure 테이블과 매칭하여 disclosure_id FK를 설정한다.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal
from app.models.disclosure import Disclosure
from app.models.elestock import DartExecutiveHolding
from app.models.holding import DartMajorHolding

logger = logging.getLogger(__name__)


@dataclass
class LinkResult:
    """원문 공시 연결 결과."""

    deals_linked: int = 0
    major_holdings_linked: int = 0
    executive_holdings_linked: int = 0


class SourceDocumentService:
    """rcept_no 기반 원문 공시(Disclosure) 자동 연결 서비스."""

    async def link_all(self, db: AsyncSession) -> LinkResult:
        """Deal + DartMajorHolding + DartExecutiveHolding에서
        rcept_no IS NOT NULL AND disclosure_id IS NULL인 레코드를 찾아
        Disclosure.rcept_no와 매칭하여 disclosure_id를 설정한다.
        """
        result = LinkResult()

        result.deals_linked = await self.link_table(db, Deal)
        result.major_holdings_linked = await self.link_table(db, DartMajorHolding)
        result.executive_holdings_linked = await self.link_table(db, DartExecutiveHolding)

        logger.info(
            "원문 공시 연결 완료: deals=%d, major_holdings=%d, executive_holdings=%d",
            result.deals_linked,
            result.major_holdings_linked,
            result.executive_holdings_linked,
        )

        return result

    async def link_table(
        self,
        db: AsyncSession,
        model: type,
    ) -> int:
        """특정 모델의 미연결 레코드에 disclosure_id를 설정한다."""
        # 1. 미연결 레코드의 rcept_no 수집
        stmt = select(model.id, model.rcept_no).where(
            model.rcept_no.isnot(None),
            model.disclosure_id.is_(None),
        )
        db_result = await db.execute(stmt)
        rows = db_result.all()
        if not rows:
            return 0

        # 2. 필요한 rcept_no만 Disclosure에서 조회 (전체 테이블 로드 방지)
        rcept_nos = {r[1] for r in rows}
        disc_stmt = select(Disclosure.rcept_no, Disclosure.id).where(
            Disclosure.rcept_no.in_(rcept_nos),
        )
        disc_result = await db.execute(disc_stmt)
        disclosure_map = {r[0]: r[1] for r in disc_result.all()}
        if not disclosure_map:
            return 0

        # 3. disclosure_id별 레코드 ID를 그룹핑하여 배치 UPDATE
        groups: dict[int, list[int]] = defaultdict(list)
        for row_id, rcept_no in rows:
            disclosure_id = disclosure_map.get(rcept_no)
            if disclosure_id:
                groups[disclosure_id].append(row_id)

        linked = 0
        for disclosure_id, row_ids in groups.items():
            await db.execute(update(model).where(model.id.in_(row_ids)).values(disclosure_id=disclosure_id))
            linked += len(row_ids)

        return linked
