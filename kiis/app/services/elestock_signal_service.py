"""DART 임원·주요주주 소유보고 딜 신호 서비스.

임원·주요주주 소유보고 데이터를 수집·저장하고,
지분 취득을 자동으로 Deal로 변환한다.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DARTAPIError
from app.models.deal import Deal
from app.models.disclosure import Disclosure
from app.models.elestock import DartExecutiveHolding
from app.schemas.dart import ElestockItem
from app.services.dart_service import DARTService
from app.utils.dart_helpers import (
    DartSyncResult,
    is_acquisition,
    parse_date,
    parse_float,
    parse_year,
    resolve_company_by_corp_code,
)

logger = logging.getLogger(__name__)

# 딜 신호 생성 대상 보고사유 키워드
_ACQUISITION_KEYWORDS = ("취득", "매수", "증여받음", "상속")


class ElestockSignalService:
    """DART 임원·주요주주 소유보고 수집 및 딜 신호 생성 서비스."""

    def __init__(self, dart_service: DARTService) -> None:
        self.dart = dart_service

    async def sync_executive_holdings(
        self,
        db: AsyncSession,
        corp_code: str,
    ) -> DartSyncResult:
        """특정 기업의 임원소유보고 데이터를 수집하여 DB에 저장한다.

        1. DART API /elestock.json 호출
        2. dart_executive_holdings upsert (rcept_no 기준)
        3. rcept_no → Disclosure 자동 연결 (disclosure_id)
        """
        result = DartSyncResult()

        try:
            items = await self.dart.get_executive_holdings(corp_code)
        except DARTAPIError as exc:
            if exc.status_code == "013":
                logger.debug("임원소유보고 데이터 없음 (corp_code=%s)", corp_code)
                return result
            logger.warning(
                "임원소유보고 DART API 오류 (corp_code=%s, status=%s): %s", corp_code, exc.status_code, exc.message
            )
            result.errors.append(f"{corp_code}: [{exc.status_code}] {exc.message}")
            return result
        except Exception as exc:
            logger.warning("임원소유보고 조회 실패 (corp_code=%s): %s", corp_code, exc)
            result.errors.append(f"{corp_code}: 조회 실패")
            return result

        result.total_fetched = len(items)

        # company_id 매칭 (corp_code → Company)
        company_id = await resolve_company_by_corp_code(db, corp_code)

        # 배치 조회: 기존 레코드 + Disclosure를 한 번에 가져온다 (N+1 방지)
        rcept_nos = [item.rcept_no for item in items]
        existing_stmt = select(DartExecutiveHolding).where(DartExecutiveHolding.rcept_no.in_(rcept_nos))
        existing_result = await db.execute(existing_stmt)
        existing_map: dict[str, DartExecutiveHolding] = {h.rcept_no: h for h in existing_result.scalars().all()}

        disc_stmt = select(Disclosure.rcept_no, Disclosure.id).where(Disclosure.rcept_no.in_(rcept_nos))
        disc_result = await db.execute(disc_stmt)
        disclosure_map: dict[str, int] = {r[0]: r[1] for r in disc_result.all()}

        for item in items:
            try:
                await self._upsert_holding(
                    db,
                    item,
                    company_id,
                    result,
                    existing=existing_map.get(item.rcept_no),
                    disclosure_id=disclosure_map.get(item.rcept_no),
                )
            except Exception:
                logger.exception(
                    "임원소유보고 upsert 실패: rcept_no=%s, corp=%s, repror=%s",
                    item.rcept_no,
                    item.corp_name,
                    item.repror,
                )
                result.errors.append(f"{item.rcept_no} ({item.corp_name}/{item.repror})")

        return result

    async def generate_deal_signals(self, db: AsyncSession) -> int:
        """미처리 임원소유보고 레코드에서 딜 신호를 생성한다.

        조건:
        - deal_id IS NULL (아직 딜 미생성)
        - 임원(isu_exctv_rgist_at=Y) 또는 주요주주(isu_main_shrholdr=Y)
        - report_resn에 취득 관련 키워드 포함
        - sp_stock_lmp_rate >= ELESTOCK_SIGNAL_MIN_RATE

        Returns:
            생성된 딜 수
        """
        stmt = select(DartExecutiveHolding).where(
            DartExecutiveHolding.deal_id.is_(None),
        )
        db_result = await db.execute(stmt)
        holdings = list(db_result.scalars().all())

        deals_created = 0
        min_rate = settings.ELESTOCK_SIGNAL_MIN_RATE

        # 배치 조회: 기존 Deal을 rcept_no 기준으로 한 번에 조회 (N+1 방지)
        holding_rcept_nos = [h.rcept_no for h in holdings if h.rcept_no]
        if holding_rcept_nos:
            deal_stmt = select(Deal.rcept_no, Deal.id).where(Deal.rcept_no.in_(holding_rcept_nos))
            deal_result = await db.execute(deal_stmt)
            existing_deals: dict[str, int] = {r[0]: r[1] for r in deal_result.all()}
        else:
            existing_deals = {}

        for holding in holdings:
            # 임원 또는 주요주주 필터
            if not self._is_significant_person(holding):
                continue

            # 보고사유 키워드 필터
            if not is_acquisition(holding.report_resn, _ACQUISITION_KEYWORDS):
                continue

            # 최소 비율 필터
            rate = parse_float(holding.sp_stock_lmp_rate)
            if rate is not None and rate < min_rate:
                continue

            # 동시 실행 중복 방지: 동일 rcept_no의 Deal이 이미 존재하면 연결만
            existing_deal_id = existing_deals.get(holding.rcept_no)
            if existing_deal_id:
                holding.deal_id = existing_deal_id
                continue

            # Deal 생성
            # NOTE: 임원소유보고는 보고자가 개인(임원)이므로 "취득 주체 기업"이 없다.
            # company_id = target_company_id = 대상 기업으로 설정한다.
            # (대량보유는 company_id=GP, target_company_id=대상 기업으로 구분됨)
            deal = Deal(
                company_id=holding.company_id,
                target_company=holding.corp_name,
                target_company_id=holding.company_id,
                deal_type="executive_change",
                source_type="disclosure",
                source_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={holding.rcept_no}",
                rcept_no=holding.rcept_no,
                deal_date=parse_date(holding.rcept_dt),
                deal_year=parse_year(holding.rcept_dt),
                disclosure_id=holding.disclosure_id,
                description=(f"임원소유보고: {holding.repror} → {holding.corp_name} ({holding.sp_stock_lmp_rate}%)"),
            )
            db.add(deal)
            await db.flush()

            holding.deal_id = deal.id
            deals_created += 1
            logger.info(
                "임원소유보고 딜 신호 생성: %s → %s (%.1f%%, rcept_no=%s)",
                holding.repror,
                holding.corp_name,
                rate or 0,
                holding.rcept_no,
            )

        return deals_created

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    async def _upsert_holding(
        self,
        db: AsyncSession,
        item: ElestockItem,
        company_id: int | None,
        result: DartSyncResult,
        *,
        existing: DartExecutiveHolding | None = None,
        disclosure_id: int | None = None,
    ) -> None:
        """임원소유보고 레코드를 upsert한다."""
        if existing:
            # 업데이트
            existing.sp_stock_lmp_cnt = item.sp_stock_lmp_cnt
            existing.sp_stock_lmp_rate = item.sp_stock_lmp_rate
            existing.sp_stock_lmp_irds_cnt = item.sp_stock_lmp_irds_cnt
            existing.sp_stock_lmp_irds_rate = item.sp_stock_lmp_irds_rate
            existing.report_resn = item.report_resn
            if disclosure_id:
                existing.disclosure_id = disclosure_id
            result.updated_records += 1
        else:
            # 신규 생성
            holding = DartExecutiveHolding(
                rcept_no=item.rcept_no,
                rcept_dt=item.rcept_dt,
                corp_code=item.corp_code,
                corp_name=item.corp_name,
                repror=item.repror,
                isu_exctv_rgist_at=item.isu_exctv_rgist_at,
                isu_exctv_ofcps=item.isu_exctv_ofcps,
                isu_main_shrholdr=item.isu_main_shrholdr,
                sp_stock_lmp_cnt=item.sp_stock_lmp_cnt,
                sp_stock_lmp_irds_cnt=item.sp_stock_lmp_irds_cnt,
                sp_stock_lmp_rate=item.sp_stock_lmp_rate,
                sp_stock_lmp_irds_rate=item.sp_stock_lmp_irds_rate,
                ctr_stkqy=item.ctr_stkqy,
                ctr_stkrt=item.ctr_stkrt,
                report_resn=item.report_resn,
                company_id=company_id,
                reporter_company_id=company_id,
                disclosure_id=disclosure_id,
            )
            db.add(holding)
            result.new_records += 1

    @staticmethod
    def _is_significant_person(holding: DartExecutiveHolding) -> bool:
        """임원 또는 주요주주인지 확인한다."""
        is_exec = holding.isu_exctv_rgist_at and holding.isu_exctv_rgist_at.upper() == "Y"
        is_major = holding.isu_main_shrholdr and holding.isu_main_shrholdr.upper() == "Y"
        return bool(is_exec or is_major)
