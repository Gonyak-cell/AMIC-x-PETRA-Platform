"""DART 대량보유 수집 + 딜 신호 생성 배치 태스크."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.company import Company
from app.models.deal import Deal
from app.models.holding import DartMajorHolding
from app.services.dart_service import DARTService
from app.services.holding_signal_service import HoldingSignalService, HoldingSyncResult
from app.services.source_document_service import SourceDocumentService

logger = logging.getLogger(__name__)


async def run_holding_sync(*, triggered_by: str = "scheduler") -> dict[str, int | list[str]]:
    """대량보유 수집 + 딜 신호 생성을 실행한다.

    1. is_gp=True이고 corp_code가 있는 Company 대상으로 대량보유 수집
    2. 수집 완료 후 딜 신호 생성

    Args:
        triggered_by: 실행 주체 (scheduler / 사용자 이메일)
    """
    dart = DARTService()
    service = HoldingSignalService(dart)
    source_doc_service = SourceDocumentService()

    lookback_days = settings.HOLDING_SYNC_LOOKBACK_DAYS
    bgn_de = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d")

    total_result = HoldingSyncResult()
    linked_disclosures = 0

    try:
        async with async_session_factory() as db:
            # GP 중 corp_code가 있는 기업 (DART 등록 기업만 API 조회 가능)
            stmt = select(Company.corp_code).where(
                Company.is_gp.is_(True),
                Company.corp_code.isnot(None),
            )
            db_result = await db.execute(stmt)
            corp_codes = [row[0] for row in db_result.all()]

            logger.info("대량보유 동기화 시작: %d개 GP 대상, triggered_by=%s", len(corp_codes), triggered_by)

            for corp_code in corp_codes:
                try:
                    async with db.begin_nested():
                        result = await service.sync_holdings(db, corp_code, bgn_de=bgn_de)
                        total_result.total_fetched += result.total_fetched
                        total_result.new_records += result.new_records
                        total_result.updated_records += result.updated_records
                        total_result.errors.extend(result.errors)
                except Exception:
                    logger.exception("대량보유 동기화 실패 (corp_code=%s)", corp_code)
                    total_result.errors.append(f"{corp_code}: 동기화 실패")

            # 딜 신호 생성
            try:
                async with db.begin_nested():
                    deals_created = await service.generate_deal_signals(db)
                    total_result.deals_created = deals_created
            except Exception:
                logger.exception("대량보유 딜 신호 생성 실패")
                total_result.errors.append("deal_signals: 처리 실패")

            # 원문 공시 연결 (대량보유 관련 테이블만 — elestock과 중복 방지)
            try:
                async with db.begin_nested():
                    linked_disclosures = await source_doc_service.link_table(db, Deal)
                    linked_disclosures += await source_doc_service.link_table(db, DartMajorHolding)
            except Exception:
                logger.exception("원문 공시 연결 실패")
                total_result.errors.append("source_docs: 처리 실패")

            await db.commit()

        logger.info(
            "대량보유 동기화 완료: 수집 %d, 신규 %d, 업데이트 %d, 딜 %d, 공시연결 %d, 에러 %d",
            total_result.total_fetched,
            total_result.new_records,
            total_result.updated_records,
            total_result.deals_created,
            linked_disclosures,
            len(total_result.errors),
        )
    finally:
        await dart.close()

    return {
        "total_fetched": total_result.total_fetched,
        "new_records": total_result.new_records,
        "updated_records": total_result.updated_records,
        "deals_created": total_result.deals_created,
        "linked_disclosures": linked_disclosures,
        "errors": total_result.errors,
    }
