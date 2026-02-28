"""DART 임원소유보고 수집 + 딜 신호 생성 + 원문 공시 연결 배치 태스크."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.company import Company
from app.models.deal import Deal
from app.models.elestock import DartExecutiveHolding
from app.services.dart_service import DARTService
from app.services.elestock_signal_service import ElestockSignalService, ElestockSyncResult
from app.services.source_document_service import SourceDocumentService

logger = logging.getLogger(__name__)


async def run_elestock_sync(*, triggered_by: str = "scheduler") -> dict[str, int | list[str]]:
    """임원소유보고 수집 + 딜 신호 생성 + 원문 공시 연결을 실행한다.

    1. is_gp=True이고 corp_code가 있는 Company 대상으로 임원소유보고 수집
    2. 수집 완료 후 딜 신호 생성
    3. 원문 공시 연결 (SourceDocumentService.link_all)

    Args:
        triggered_by: 실행 주체 (scheduler / 사용자 이메일)
    """
    dart = DARTService()
    service = ElestockSignalService(dart)
    source_doc_service = SourceDocumentService()

    total_result = ElestockSyncResult()
    linked_disclosures = 0

    try:
        async with async_session_factory() as db:
            # GP 중 corp_code가 있는 기업
            stmt = select(Company.corp_code).where(
                Company.is_gp.is_(True),
                Company.corp_code.isnot(None),
            )
            db_result = await db.execute(stmt)
            corp_codes = [row[0] for row in db_result.all()]

            logger.info("임원소유보고 동기화 시작: %d개 GP 대상, triggered_by=%s", len(corp_codes), triggered_by)

            for corp_code in corp_codes:
                try:
                    async with db.begin_nested():
                        result = await service.sync_executive_holdings(db, corp_code)
                        total_result.total_fetched += result.total_fetched
                        total_result.new_records += result.new_records
                        total_result.updated_records += result.updated_records
                        total_result.errors.extend(result.errors)
                except Exception:
                    logger.exception("임원소유보고 동기화 실패 (corp_code=%s)", corp_code)
                    total_result.errors.append(f"{corp_code}: 동기화 실패")

            # 딜 신호 생성
            try:
                async with db.begin_nested():
                    deals_created = await service.generate_deal_signals(db)
                    total_result.deals_created = deals_created
            except Exception:
                logger.exception("임원소유보고 딜 신호 생성 실패")
                total_result.errors.append("deal_signals: 처리 실패")

            # 원문 공시 연결 (임원소유보고 관련 테이블만 — holding과 중복 방지)
            try:
                async with db.begin_nested():
                    linked_disclosures = await source_doc_service.link_table(db, Deal)
                    linked_disclosures += await source_doc_service.link_table(db, DartExecutiveHolding)
            except Exception:
                logger.exception("원문 공시 연결 실패")
                total_result.errors.append("source_docs: 처리 실패")

            await db.commit()

        logger.info(
            "임원소유보고 동기화 완료: 수집 %d, 신규 %d, 업데이트 %d, 딜 %d, 공시연결 %d, 에러 %d",
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
