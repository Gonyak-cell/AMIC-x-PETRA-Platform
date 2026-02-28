"""DART 대량보유 수집 + 딜 신호 생성 배치 태스크."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.deal import Deal
from app.models.holding import DartMajorHolding
from app.services.dart_service import DARTService
from app.services.holding_signal_service import HoldingSignalService
from app.services.source_document_service import SourceDocumentService
from app.tasks.dart_pipeline import run_dart_pipeline
from app.utils.dart_helpers import DartSyncResult


async def run_holding_sync(*, triggered_by: str = "scheduler") -> dict[str, int | list[str]]:
    """대량보유 수집 + 딜 신호 생성을 실행한다."""
    dart = DARTService()
    service = HoldingSignalService(dart)

    lookback_days = settings.HOLDING_SYNC_LOOKBACK_DAYS
    bgn_de = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d")

    async def sync_one(db: object, corp_code: str) -> DartSyncResult:
        return await service.sync_holdings(db, corp_code, bgn_de=bgn_de)

    return await run_dart_pipeline(
        session_factory=async_session_factory,
        dart_close=dart.close,
        sync_one=sync_one,
        generate_signals=service.generate_deal_signals,
        source_doc_service=SourceDocumentService(),
        link_models=[Deal, DartMajorHolding],
        log_prefix="대량보유",
        triggered_by=triggered_by,
    )
