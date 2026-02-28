"""DART 대량보유 딜 신호 서비스.

대량보유상황보고서 데이터를 수집·저장하고,
GP의 지분 취득을 자동으로 Deal로 변환한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DARTAPIError
from app.models.company import Company
from app.models.deal import Deal
from app.models.holding import DartMajorHolding
from app.schemas.dart import MajorHoldingItem
from app.services.dart_service import DARTService
from app.utils.dart_helpers import (
    is_acquisition,
    parse_date,
    parse_float,
    parse_year,
    resolve_company_by_corp_code,
)
from app.utils.entity_resolver import EntityResolver

logger = logging.getLogger(__name__)

# 딜 신호 생성 대상 보고사유 키워드
_ACQUISITION_KEYWORDS = ("주식취득", "취득", "매수", "인수")


@dataclass
class HoldingSyncResult:
    """대량보유 동기화 + 딜 신호 생성 결과."""

    total_fetched: int = 0
    new_records: int = 0
    updated_records: int = 0
    deals_created: int = 0
    errors: list[str] = field(default_factory=list)


class HoldingSignalService:
    """DART 대량보유 수집 및 딜 신호 생성 서비스."""

    def __init__(self, dart_service: DARTService) -> None:
        self.dart = dart_service
        self.resolver = EntityResolver()

    async def sync_holdings(
        self,
        db: AsyncSession,
        corp_code: str,
        *,
        bgn_de: str | None = None,
        end_de: str | None = None,
    ) -> HoldingSyncResult:
        """특정 기업의 대량보유 데이터를 수집하여 DB에 저장한다.

        1. DART API 호출 (majorstock.json)
        2. dart_major_holdings upsert (rcept_no 기준)
        3. EntityResolver로 reporter_company_id 매칭
        """
        result = HoldingSyncResult()

        try:
            items, _, total_page = await self.dart.get_major_holdings(
                corp_code,
                bgn_de=bgn_de,
                end_de=end_de,
                page_count=100,
            )
            if total_page > 1:
                logger.warning(
                    "대량보유 %d 페이지 중 1페이지만 수집 (corp_code=%s)",
                    total_page,
                    corp_code,
                )
        except DARTAPIError as exc:
            if exc.status_code == "013":
                logger.debug("대량보유 데이터 없음 (corp_code=%s)", corp_code)
                return result
            logger.warning(
                "대량보유 DART API 오류 (corp_code=%s, status=%s): %s", corp_code, exc.status_code, exc.message
            )
            result.errors.append(f"{corp_code}: [{exc.status_code}] {exc.message}")
            return result
        except Exception as exc:
            logger.warning("대량보유 조회 실패 (corp_code=%s): %s", corp_code, exc)
            result.errors.append(f"{corp_code}: 조회 실패")
            return result

        result.total_fetched = len(items)

        # company_id 매칭 (corp_code → Company)
        company_id = await resolve_company_by_corp_code(db, corp_code)

        # 배치 조회: 기존 레코드를 rcept_no 기준으로 한 번에 가져온다 (N+1 방지)
        rcept_nos = [item.rcept_no for item in items]
        existing_stmt = select(DartMajorHolding).where(DartMajorHolding.rcept_no.in_(rcept_nos))
        existing_result = await db.execute(existing_stmt)
        existing_map: dict[str, DartMajorHolding] = {h.rcept_no: h for h in existing_result.scalars().all()}

        for item in items:
            try:
                await self._upsert_holding(db, item, company_id, result, existing=existing_map.get(item.rcept_no))
            except Exception:
                logger.exception(
                    "대량보유 upsert 실패: rcept_no=%s, corp=%s, repror=%s",
                    item.rcept_no,
                    item.corp_name,
                    item.repror,
                )
                result.errors.append(f"{item.rcept_no} ({item.corp_name}/{item.repror})")

        return result

    async def generate_deal_signals(self, db: AsyncSession) -> int:
        """미처리 대량보유 레코드에서 딜 신호를 생성한다.

        조건:
        - deal_id IS NULL (아직 딜 미생성)
        - reporter_company_id의 is_gp=True
        - report_resn에 취득 관련 키워드 포함
        - stkrt >= HOLDING_SIGNAL_MIN_STKRT

        Returns:
            생성된 딜 수
        """
        # 미처리 + GP 보고자 대량보유 조회
        stmt = (
            select(DartMajorHolding)
            .join(
                Company,
                DartMajorHolding.reporter_company_id == Company.id,
            )
            .where(
                DartMajorHolding.deal_id.is_(None),
                Company.is_gp.is_(True),
            )
        )
        db_result = await db.execute(stmt)
        holdings = list(db_result.scalars().all())

        deals_created = 0
        min_stkrt = settings.HOLDING_SIGNAL_MIN_STKRT

        # 배치 조회: 기존 Deal을 rcept_no 기준으로 한 번에 조회 (N+1 방지)
        holding_rcept_nos = [h.rcept_no for h in holdings if h.rcept_no]
        if holding_rcept_nos:
            deal_stmt = select(Deal.rcept_no, Deal.id).where(Deal.rcept_no.in_(holding_rcept_nos))
            deal_result = await db.execute(deal_stmt)
            existing_deals: dict[str, int] = {r[0]: r[1] for r in deal_result.all()}
        else:
            existing_deals = {}

        for holding in holdings:
            # 보고사유 키워드 필터
            if not is_acquisition(holding.report_resn, _ACQUISITION_KEYWORDS):
                continue

            # 최소 지분율 필터
            stkrt = parse_float(holding.stkrt)
            if stkrt is not None and stkrt < min_stkrt:
                continue

            # 동시 실행 중복 방지: 동일 rcept_no의 Deal이 이미 존재하면 연결만
            existing_deal_id = existing_deals.get(holding.rcept_no)
            if existing_deal_id:
                holding.deal_id = existing_deal_id
                continue

            # Deal 생성
            deal = Deal(
                company_id=holding.reporter_company_id,
                target_company=holding.corp_name,
                target_company_id=holding.company_id,
                deal_type="holding_change",
                source_type="disclosure",
                source_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={holding.rcept_no}",
                rcept_no=holding.rcept_no,
                deal_date=parse_date(holding.rcept_dt),
                deal_year=parse_year(holding.rcept_dt),
                description=f"대량보유 변동: {holding.repror} → {holding.corp_name} ({holding.stkrt}%)",
            )
            db.add(deal)
            await db.flush()

            holding.deal_id = deal.id
            deals_created += 1
            logger.info(
                "딜 신호 생성: %s → %s (%.1f%%, rcept_no=%s)",
                holding.repror,
                holding.corp_name,
                stkrt or 0,
                holding.rcept_no,
            )

        return deals_created

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    async def _upsert_holding(
        self,
        db: AsyncSession,
        item: MajorHoldingItem,
        company_id: int | None,
        result: HoldingSyncResult,
        *,
        existing: DartMajorHolding | None = None,
    ) -> None:
        """대량보유 레코드를 upsert한다."""
        # reporter → Company 매칭
        reporter_company_id = await self._resolve_reporter(db, item.repror)

        if existing:
            # 업데이트
            existing.stkqy = item.stkqy
            existing.stkrt = item.stkrt
            existing.stkqy_irds = item.stkqy_irds
            existing.stkrt_irds = item.stkrt_irds
            existing.report_resn = item.report_resn
            if reporter_company_id:
                existing.reporter_company_id = reporter_company_id
            result.updated_records += 1
        else:
            # 신규 생성
            holding = DartMajorHolding(
                rcept_no=item.rcept_no,
                rcept_dt=item.rcept_dt,
                corp_code=item.corp_code,
                corp_name=item.corp_name,
                report_tp=item.report_tp,
                repror=item.repror,
                stkqy=item.stkqy,
                stkrt=item.stkrt,
                stkqy_irds=item.stkqy_irds,
                stkrt_irds=item.stkrt_irds,
                ctr_stkqy=item.ctr_stkqy,
                ctr_stkrt=item.ctr_stkrt,
                report_resn=item.report_resn,
                company_id=company_id,
                reporter_company_id=reporter_company_id,
            )
            db.add(holding)
            result.new_records += 1

    async def _resolve_reporter(
        self,
        db: AsyncSession,
        repror: str,
    ) -> int | None:
        """보고자명으로 Company를 매칭한다 (EntityResolver 활용)."""
        try:
            match_result = await self.resolver.resolve(db, repror)
            matched = match_result.get("match")
            if matched:
                # corp_code 또는 corp_name으로 ID 조회
                if matched.get("corp_code"):
                    stmt = select(Company.id).where(Company.corp_code == matched["corp_code"])
                else:
                    stmt = select(Company.id).where(func.lower(Company.corp_name) == func.lower(matched["corp_name"]))
                db_result = await db.execute(stmt)
                return db_result.scalar_one_or_none()
        except Exception:
            logger.debug("보고자 매칭 실패: %s", repror)
        return None
