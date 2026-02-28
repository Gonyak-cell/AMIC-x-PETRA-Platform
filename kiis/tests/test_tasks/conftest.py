"""test_tasks 공용 페이크 세션/세이브포인트."""

from unittest.mock import AsyncMock


class FakeSavepoint:
    """SAVEPOINT async context manager."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """async context manager를 흉내내는 페이크 DB 세션.

    holding_sync / elestock_sync 태스크 테스트에서 공통 사용.
    """

    def __init__(self, execute_return=None):
        self._execute_return = execute_return
        self.commit = AsyncMock()

    async def execute(self, stmt):
        return self._execute_return

    def begin_nested(self):
        return FakeSavepoint()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False
