"""DART 임원소유보고 수집 + 딜 신호 생성 + 원문 공시 연결 배치 태스크."""

from __future__ import annotations

from app.core.database import async_session_factory
from app.models.deal import Deal
from app.models.elestock import DartExecutiveHolding
from app.services.dart_service import DARTService
from app.services.elestock_signal_service import ElestockSignalService
from app.services.source_document_service import SourceDocumentService
from app.tasks.dart_pipeline import run_dart_pipeline


async def run_elestock_sync(*, triggered_by: str = "scheduler") -> dict[str, int | list[str]]:
    """임원소유보고 수집 + 딜 신호 생성 + 원문 공시 연결을 실행한다."""
    dart = DARTService()
    service = ElestockSignalService(dart)

    return await run_dart_pipeline(
        session_factory=async_session_factory,
        dart_close=dart.close,
        sync_one=service.sync_executive_holdings,
        generate_signals=service.generate_deal_signals,
        source_doc_service=SourceDocumentService(),
        link_models=[Deal, DartExecutiveHolding],
        log_prefix="임원소유보고",
        triggered_by=triggered_by,
    )
