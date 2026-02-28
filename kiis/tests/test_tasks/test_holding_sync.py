"""DART 대량보유 배치 태스크 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.holding_sync import run_holding_sync
from app.utils.dart_helpers import DartSyncResult

from .conftest import FakeSession


@pytest.mark.asyncio
async def test_holding_sync_success():
    """정상: 2개 GP 순회 → sync + deal signals + source docs."""
    sync_result = DartSyncResult(total_fetched=5, new_records=3, updated_records=2)

    with (
        patch("app.tasks.holding_sync.async_session_factory") as mock_factory,
        patch("app.tasks.holding_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.holding_sync.HoldingSignalService") as mock_svc_cls,
        patch("app.tasks.holding_sync.SourceDocumentService") as mock_src_cls,
        patch("app.tasks.holding_sync.settings") as mock_settings,
    ):
        mock_settings.HOLDING_SYNC_LOOKBACK_DAYS = 90

        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_holdings = AsyncMock(return_value=sync_result)
        mock_svc.generate_deal_signals = AsyncMock(return_value=2)

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(return_value=1)

        query_result = MagicMock()
        query_result.all.return_value = [("00100001",), ("00100002",)]

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_holding_sync()

    assert result["total_fetched"] == 10  # 5 × 2 GP
    assert result["new_records"] == 6  # 3 × 2
    assert result["deals_created"] == 2
    assert result["linked_disclosures"] == 2  # link_table 2회 × 1
    assert result["errors"] == []
    mock_dart.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_holding_sync_error_isolation():
    """1개 GP 실패 시에도 나머지 GP와 후속 단계가 계속 실행된다."""
    ok_result = DartSyncResult(total_fetched=3, new_records=1)

    async def sync_side_effect(db, corp_code, *, bgn_de=None):
        if corp_code == "00100001":
            raise RuntimeError("DART timeout")
        return ok_result

    with (
        patch("app.tasks.holding_sync.async_session_factory") as mock_factory,
        patch("app.tasks.holding_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.holding_sync.HoldingSignalService") as mock_svc_cls,
        patch("app.tasks.holding_sync.SourceDocumentService") as mock_src_cls,
        patch("app.tasks.holding_sync.settings") as mock_settings,
    ):
        mock_settings.HOLDING_SYNC_LOOKBACK_DAYS = 90

        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_holdings = AsyncMock(side_effect=sync_side_effect)
        mock_svc.generate_deal_signals = AsyncMock(return_value=0)

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(return_value=0)

        query_result = MagicMock()
        query_result.all.return_value = [("00100001",), ("00100002",)]

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_holding_sync()

    # 1개 성공 + 1개 실패
    assert result["total_fetched"] == 3
    assert result["new_records"] == 1
    assert len(result["errors"]) == 1
    assert "동기화 실패" in result["errors"][0]
    # dart.close()는 에러 여부와 관계없이 호출
    mock_dart.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_holding_sync_no_companies():
    """GP가 없으면 sync를 실행하지 않고 빈 결과를 반환한다."""
    with (
        patch("app.tasks.holding_sync.async_session_factory") as mock_factory,
        patch("app.tasks.holding_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.holding_sync.HoldingSignalService") as mock_svc_cls,
        patch("app.tasks.holding_sync.SourceDocumentService") as mock_src_cls,
        patch("app.tasks.holding_sync.settings") as mock_settings,
    ):
        mock_settings.HOLDING_SYNC_LOOKBACK_DAYS = 90

        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_holdings = AsyncMock()
        mock_svc.generate_deal_signals = AsyncMock(return_value=0)

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(return_value=0)

        query_result = MagicMock()
        query_result.all.return_value = []

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_holding_sync()

    assert result["total_fetched"] == 0
    assert result["deals_created"] == 0
    assert result["errors"] == []
    mock_svc.sync_holdings.assert_not_called()
    mock_dart.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_holding_sync_deal_signal_failure():
    """딜 신호 생성 실패 시 에러가 기록되고 source_docs 연결은 계속 진행된다."""
    with (
        patch("app.tasks.holding_sync.async_session_factory") as mock_factory,
        patch("app.tasks.holding_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.holding_sync.HoldingSignalService") as mock_svc_cls,
        patch("app.tasks.holding_sync.SourceDocumentService") as mock_src_cls,
        patch("app.tasks.holding_sync.settings") as mock_settings,
    ):
        mock_settings.HOLDING_SYNC_LOOKBACK_DAYS = 90

        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_holdings = AsyncMock(return_value=DartSyncResult(total_fetched=1, new_records=1))
        mock_svc.generate_deal_signals = AsyncMock(side_effect=RuntimeError("DB deadlock"))

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(return_value=1)

        query_result = MagicMock()
        query_result.all.return_value = [("00100001",)]

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_holding_sync()

    assert result["deals_created"] == 0
    assert "deal_signals: 처리 실패" in result["errors"]
    # source_docs는 계속 실행됨
    assert mock_src.link_table.call_count == 2
