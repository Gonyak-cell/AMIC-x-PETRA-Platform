"""DART 공시 동기화 태스크 테스트"""

from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.dart_sync import run_dart_sync


class FakeSession:
    """async context manager를 흉내내는 페이크 DB 세션"""

    def __init__(self, execute_return=None):
        self._execute_return = execute_return
        self.commit = AsyncMock()

    async def execute(self, stmt):
        return self._execute_return

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class TestRunDartSync:
    """run_dart_sync 태스크 테스트"""

    async def test_sync_success(self):
        """Company를 순회하며 sync_disclosures가 호출된다."""
        with (
            patch("app.tasks.dart_sync.async_session_factory") as mock_factory,
            patch("app.tasks.dart_sync.DisclosureService") as mock_svc_cls,
        ):
            mock_svc = mock_svc_cls.return_value
            mock_svc.sync_disclosures = AsyncMock()

            query_result = MagicMock()
            query_result.all.return_value = [("00100001",), ("00100002",)]

            sessions = [FakeSession(execute_return=query_result), FakeSession(), FakeSession()]
            idx = [0]

            def make_session():
                s = sessions[idx[0]]
                idx[0] += 1
                return s

            mock_factory.side_effect = make_session

            result = await run_dart_sync()

        assert result["total"] == 2
        assert result["synced"] == 2
        assert result["errors"] == 0
        assert mock_svc.sync_disclosures.call_count == 2

    async def test_sync_with_error_isolation(self):
        """한 기업 실패 시에도 나머지는 계속 처리된다."""
        with (
            patch("app.tasks.dart_sync.async_session_factory") as mock_factory,
            patch("app.tasks.dart_sync.DisclosureService") as mock_svc_cls,
        ):
            mock_svc = mock_svc_cls.return_value

            async def sync_side_effect(db, corp_code):
                if corp_code == "00100001":
                    raise RuntimeError("DART API error")

            mock_svc.sync_disclosures = AsyncMock(side_effect=sync_side_effect)

            query_result = MagicMock()
            query_result.all.return_value = [("00100001",), ("00100002",)]

            sessions = [FakeSession(execute_return=query_result), FakeSession(), FakeSession()]
            idx = [0]
            mock_factory.side_effect = lambda: sessions[idx.__setitem__(0, idx[0] + 1) or idx[0] - 1]

            result = await run_dart_sync()

        assert result["total"] == 2
        assert result["synced"] == 1
        assert result["errors"] == 1

    async def test_sync_no_companies(self):
        """기업이 없으면 동기화하지 않는다."""
        with (
            patch("app.tasks.dart_sync.async_session_factory") as mock_factory,
            patch("app.tasks.dart_sync.DisclosureService") as mock_svc_cls,
        ):
            mock_svc = mock_svc_cls.return_value
            mock_svc.sync_disclosures = AsyncMock()

            query_result = MagicMock()
            query_result.all.return_value = []

            mock_factory.side_effect = lambda: FakeSession(execute_return=query_result)

            result = await run_dart_sync()

        assert result["total"] == 0
        assert result["synced"] == 0
        mock_svc.sync_disclosures.assert_not_called()
