"""
보안 — 사용자 접근 제어 및 속도 제한.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from functools import wraps
from typing import TYPE_CHECKING

from telegram import Update

if TYPE_CHECKING:
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def owner_only(func):
    """허가된 사용자만 봇을 사용할 수 있도록 제한하는 데코레이터."""

    @wraps(func)
    async def wrapper(
        update: Update, context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs
    ):
        config = context.bot_data.get("config")
        if not config:
            return

        user_id = update.effective_user.id
        if user_id not in config.allowed_user_ids:
            logger.warning("[차단] 미허가 사용자 접근: %s", user_id)
            return  # 무응답 — 봇 존재를 노출하지 않음

        return await func(update, context, *args, **kwargs)

    return wrapper


class RateLimiter:
    """분당 최대 요청 수를 제한한다."""

    def __init__(self, max_per_minute: int = 5):
        self.max_per_minute = max_per_minute
        self._timestamps: dict[int, list[float]] = defaultdict(list)

    def check(self, user_id: int) -> bool:
        """True이면 허용, False이면 제한 초과."""
        now = time.monotonic()
        window = now - 60.0

        # 1분 이전 기록 제거
        self._timestamps[user_id] = [
            ts for ts in self._timestamps[user_id] if ts > window
        ]

        if len(self._timestamps[user_id]) >= self.max_per_minute:
            return False

        self._timestamps[user_id].append(now)
        return True

    @property
    def remaining(self) -> dict[int, int]:
        """사용자별 남은 요청 수."""
        now = time.monotonic()
        window = now - 60.0
        result = {}
        for uid, timestamps in self._timestamps.items():
            recent = [ts for ts in timestamps if ts > window]
            result[uid] = max(0, self.max_per_minute - len(recent))
        return result
