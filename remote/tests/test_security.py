"""security.py 유닛 테스트."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.security import RateLimiter, owner_only


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_per_minute=3)
        assert rl.check(1) is True
        assert rl.check(1) is True
        assert rl.check(1) is True

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_per_minute=2)
        assert rl.check(1) is True
        assert rl.check(1) is True
        assert rl.check(1) is False

    def test_separate_users(self):
        rl = RateLimiter(max_per_minute=1)
        assert rl.check(1) is True
        assert rl.check(2) is True
        assert rl.check(1) is False

    def test_window_expiry(self):
        rl = RateLimiter(max_per_minute=1)
        assert rl.check(1) is True
        assert rl.check(1) is False
        # 수동으로 타임스탬프를 과거로 이동
        rl._timestamps[1] = [time.monotonic() - 61]
        assert rl.check(1) is True

    def test_remaining(self):
        rl = RateLimiter(max_per_minute=3)
        rl.check(1)
        rl.check(1)
        assert rl.remaining[1] == 1


class TestOwnerOnly:
    @pytest.mark.asyncio
    async def test_allows_authorized_user(self):
        config = MagicMock()
        config.allowed_user_ids = [123]

        @owner_only
        async def handler(update, context):
            return "ok"

        update = MagicMock()
        update.effective_user.id = 123
        context = MagicMock()
        context.bot_data = {"config": config}

        result = await handler(update, context)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_blocks_unauthorized_user(self):
        config = MagicMock()
        config.allowed_user_ids = [123]

        @owner_only
        async def handler(update, context):
            return "should not reach"

        update = MagicMock()
        update.effective_user.id = 999
        context = MagicMock()
        context.bot_data = {"config": config}

        result = await handler(update, context)
        assert result is None
