"""DART 수집 → 딜 신호 → 원문 공시 연결 공통 파이프라인.

holding_sync / elestock_sync 태스크의 구조적 중복을 제거한다.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from sqlalchemy import select

from app.models.company import Company
from app.utils.dart_helpers import DartSyncResult

logger = logging.getLogger(__name__)


async def run_dart_pipeline(
    *,
    session_factory: Any,
    dart_close: Callable[[], Awaitable[None]],
    sync_one: Callable[..., Awaitable[DartSyncResult]],
    generate_signals: Callable[..., Awaitable[int]],
    source_doc_service: Any,
    link_models: Sequence[type],
    log_prefix: str,
    triggered_by: str = "scheduler",
) -> dict[str, int | list[str]]:
    """DART 데이터 수집 → 딜 신호 → 원문 공시 연결 공통 파이프라인.

    5단계 파이프라인:
    1. GP 중 corp_code가 있는 기업 조회
    2. corp_code 순회: sync_one 호출 (SAVEPOINT)
    3. 딜 신호 생성 (SAVEPOINT)
    4. 원문 공시 연결 (SAVEPOINT)
    5. commit + 로그

    Args:
        session_factory: async_session_factory (async context manager)
        dart_close: DARTService.close 호출
        sync_one: (db, corp_code) → DartSyncResult
        generate_signals: (db) → 생성된 딜 수
        source_doc_service: SourceDocumentService 인스턴스
        link_models: link_table에 전달할 모델 목록
        log_prefix: 로그 접두사 (예: "대량보유", "임원소유보고")
        triggered_by: 실행 주체
    """
    total_result = DartSyncResult()
    linked_disclosures = 0

    try:
        async with session_factory() as db:
            # GP 중 corp_code가 있는 기업 (DART 등록 기업만 API 조회 가능)
            stmt = select(Company.corp_code).where(
                Company.is_gp.is_(True),
                Company.corp_code.isnot(None),
            )
            db_result = await db.execute(stmt)
            corp_codes = [row[0] for row in db_result.all()]

            logger.info(
                "%s 동기화 시작: %d개 GP 대상, triggered_by=%s",
                log_prefix,
                len(corp_codes),
                triggered_by,
            )

            for corp_code in corp_codes:
                try:
                    async with db.begin_nested():
                        result = await sync_one(db, corp_code)
                        total_result.total_fetched += result.total_fetched
                        total_result.new_records += result.new_records
                        total_result.updated_records += result.updated_records
                        total_result.errors.extend(result.errors)
                except Exception:
                    logger.exception("%s 동기화 실패 (corp_code=%s)", log_prefix, corp_code)
                    total_result.errors.append(f"{corp_code}: 동기화 실패")

            # 딜 신호 생성
            try:
                async with db.begin_nested():
                    deals_created = await generate_signals(db)
                    total_result.deals_created = deals_created
            except Exception:
                logger.exception("%s 딜 신호 생성 실패", log_prefix)
                total_result.errors.append("deal_signals: 처리 실패")

            # 원문 공시 연결
            try:
                async with db.begin_nested():
                    for model in link_models:
                        linked_disclosures += await source_doc_service.link_table(db, model)
            except Exception:
                logger.exception("원문 공시 연결 실패")
                total_result.errors.append("source_docs: 처리 실패")

            await db.commit()

        logger.info(
            "%s 동기화 완료: 수집 %d, 신규 %d, 업데이트 %d, 딜 %d, 공시연결 %d, 에러 %d",
            log_prefix,
            total_result.total_fetched,
            total_result.new_records,
            total_result.updated_records,
            total_result.deals_created,
            linked_disclosures,
            len(total_result.errors),
        )
    finally:
        await dart_close()

    return {
        "total_fetched": total_result.total_fetched,
        "new_records": total_result.new_records,
        "updated_records": total_result.updated_records,
        "deals_created": total_result.deals_created,
        "linked_disclosures": linked_disclosures,
        "errors": total_result.errors,
    }
