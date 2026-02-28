"""DART 임원소유보고 배치 태스크 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.elestock_sync import run_elestock_sync
from app.utils.dart_helpers import DartSyncResult

from .conftest import FakeSession


@pytest.mark.asyncio
async def test_elestock_sync_success():
    """정상: 2개 GP 순회 → sync + deal signals + source docs."""
    sync_result = DartSyncResult(total_fetched=4, new_records=3, updated_records=1)

    with (
        patch("app.tasks.elestock_sync.async_session_factory") as mock_factory,
        patch("app.tasks.elestock_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.elestock_sync.ElestockSignalService") as mock_svc_cls,
        patch("app.tasks.elestock_sync.SourceDocumentService") as mock_src_cls,
    ):
        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_executive_holdings = AsyncMock(return_value=sync_result)
        mock_svc.generate_deal_signals = AsyncMock(return_value=3)

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(return_value=2)

        query_result = MagicMock()
        query_result.all.return_value = [("00100001",), ("00100002",)]

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_elestock_sync()

    assert result["total_fetched"] == 8  # 4 × 2 GP
    assert result["new_records"] == 6  # 3 × 2
    assert result["deals_created"] == 3
    assert result["linked_disclosures"] == 4  # link_table 2회 × 2
    assert result["errors"] == []
    mock_dart.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_elestock_sync_error_isolation():
    """1개 GP 실패 시에도 나머지 GP와 후속 단계가 계속 실행된다."""
    ok_result = DartSyncResult(total_fetched=2, new_records=2)

    async def sync_side_effect(db, corp_code):
        if corp_code == "00100001":
            raise RuntimeError("DART timeout")
        return ok_result

    with (
        patch("app.tasks.elestock_sync.async_session_factory") as mock_factory,
        patch("app.tasks.elestock_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.elestock_sync.ElestockSignalService") as mock_svc_cls,
        patch("app.tasks.elestock_sync.SourceDocumentService") as mock_src_cls,
    ):
        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_executive_holdings = AsyncMock(side_effect=sync_side_effect)
        mock_svc.generate_deal_signals = AsyncMock(return_value=0)

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(return_value=0)

        query_result = MagicMock()
        query_result.all.return_value = [("00100001",), ("00100002",)]

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_elestock_sync()

    assert result["total_fetched"] == 2
    assert result["new_records"] == 2
    assert len(result["errors"]) == 1
    assert "동기화 실패" in result["errors"][0]
    mock_dart.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_elestock_sync_no_companies():
    """GP가 없으면 sync를 실행하지 않고 빈 결과를 반환한다."""
    with (
        patch("app.tasks.elestock_sync.async_session_factory") as mock_factory,
        patch("app.tasks.elestock_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.elestock_sync.ElestockSignalService") as mock_svc_cls,
        patch("app.tasks.elestock_sync.SourceDocumentService") as mock_src_cls,
    ):
        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_executive_holdings = AsyncMock()
        mock_svc.generate_deal_signals = AsyncMock(return_value=0)

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(return_value=0)

        query_result = MagicMock()
        query_result.all.return_value = []

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_elestock_sync()

    assert result["total_fetched"] == 0
    assert result["deals_created"] == 0
    assert result["errors"] == []
    mock_svc.sync_executive_holdings.assert_not_called()
    mock_dart.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_elestock_sync_source_docs_failure():
    """원문 공시 연결 실패 시 에러가 기록되고 commit은 정상 진행된다."""
    with (
        patch("app.tasks.elestock_sync.async_session_factory") as mock_factory,
        patch("app.tasks.elestock_sync.DARTService") as mock_dart_cls,
        patch("app.tasks.elestock_sync.ElestockSignalService") as mock_svc_cls,
        patch("app.tasks.elestock_sync.SourceDocumentService") as mock_src_cls,
    ):
        mock_dart = mock_dart_cls.return_value
        mock_dart.close = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.sync_executive_holdings = AsyncMock(
            return_value=DartSyncResult(total_fetched=1, new_records=1),
        )
        mock_svc.generate_deal_signals = AsyncMock(return_value=1)

        mock_src = mock_src_cls.return_value
        mock_src.link_table = AsyncMock(side_effect=RuntimeError("Disclosure error"))

        query_result = MagicMock()
        query_result.all.return_value = [("00100001",)]

        session = FakeSession(execute_return=query_result)
        mock_factory.return_value = session

        result = await run_elestock_sync()

    assert result["deals_created"] == 1
    assert "source_docs: 처리 실패" in result["errors"]
    # commit은 정상 실행
    session.commit.assert_awaited_once()
