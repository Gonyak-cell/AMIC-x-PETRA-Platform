"""공유 InMemoryRateLimiter — 엔드포인트별 분당 요청 수 제한."""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

_CLEANUP_INTERVAL = 60.0  # stale 키 정리 주기 (초)


class InMemoryRateLimiter:
    """인메모리 슬라이딩 윈도우 기반 요청 횟수 제한기.

    Parameters
    ----------
    max_calls : int
        윈도우 내 최대 허용 요청 수.
    window_seconds : float
        슬라이딩 윈도우 크기 (초).

    Warning
    -------
    단일 프로세스 메모리 기반이므로 다중 워커(Gunicorn/Uvicorn --workers > 1) 환경에서는
    워커별로 상태가 분리되어 실질적 제한치가 max_calls × 워커 수가 된다.
    분산 환경 대응이 필요한 경우 Redis 기반 Rate Limiter로 교체해야 한다.
    """

    def __init__(self, max_calls: int = 10, window_seconds: float = 60.0) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._store: dict[str, list[float]] = {}
        self._last_cleanup = 0.0

    def check(self, identifier: str) -> None:
        """요청 횟수를 확인하고 초과 시 429 HTTPException을 발생시킨다."""
        now = time.monotonic()
        active = [t for t in self._store.get(identifier, []) if now - t < self._window]

        if len(active) >= self._max_calls:
            self._store[identifier] = active
            retry_after = int(self._window - (now - active[0])) + 1 if active else int(self._window)
            logger.warning(
                "Rate limit exceeded: identifier=%s, count=%d/%d",
                identifier,
                len(active),
                self._max_calls,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="요청이 너무 많습니다. 잠시 후 다시 시도하세요.",
                headers={"Retry-After": str(retry_after)},
            )

        active.append(now)
        self._store[identifier] = active

        # M-04: 주기적 stale 키 정리 (매 요청이 아닌 _CLEANUP_INTERVAL 마다)
        if now - self._last_cleanup >= _CLEANUP_INTERVAL:
            self._last_cleanup = now
            stale_keys = [
                k for k, v in self._store.items() if k != identifier and all(now - t >= self._window for t in v)
            ]
            for k in stale_keys:
                del self._store[k]

    def clear(self) -> None:
        """테스트용 — 모든 상태를 초기화한다."""
        self._store.clear()


# ── 모듈 레벨 공유 인스턴스 ──────────────────────────────
fi_rate_limiter = InMemoryRateLimiter(max_calls=10, window_seconds=60.0)
si_rate_limiter = InMemoryRateLimiter(max_calls=5, window_seconds=60.0)
qa_rate_limiter = InMemoryRateLimiter(max_calls=10, window_seconds=60.0)
