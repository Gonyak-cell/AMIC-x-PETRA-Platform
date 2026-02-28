import asyncio
import time


class TokenBucketRateLimiter:
    """asyncio 기반 토큰 버킷 Rate Limiter

    분당/일별 호출 제한을 동시에 관리한다.
    """

    def __init__(self, per_minute: int = 900, per_day: int = 9000):
        self.per_minute = per_minute
        self.per_day = per_day

        # Minute bucket
        self._minute_tokens = float(per_minute)
        self._minute_last_refill = time.monotonic()
        self._minute_rate = per_minute / 60.0  # tokens per second

        # Day bucket
        self._day_tokens = float(per_day)
        self._day_last_refill = time.monotonic()
        self._day_rate = per_day / 86400.0  # tokens per second

        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()

        # Refill minute bucket
        elapsed = now - self._minute_last_refill
        self._minute_tokens = min(self.per_minute, self._minute_tokens + elapsed * self._minute_rate)
        self._minute_last_refill = now

        # Refill day bucket
        elapsed = now - self._day_last_refill
        self._day_tokens = min(self.per_day, self._day_tokens + elapsed * self._day_rate)
        self._day_last_refill = now

    async def acquire(self, timeout: float = 60.0) -> None:
        """토큰을 획득한다. 토큰이 부족하면 대기한다.

        Args:
            timeout: 최대 대기 시간 (초). 초과 시 TimeoutError 발생.
        """
        deadline = time.monotonic() + timeout

        while True:
            async with self._lock:
                self._refill()
                if self._minute_tokens >= 1.0 and self._day_tokens >= 1.0:
                    self._minute_tokens -= 1.0
                    self._day_tokens -= 1.0
                    return

                # Calculate wait time
                if self._minute_tokens < 1.0:
                    wait = (1.0 - self._minute_tokens) / self._minute_rate
                else:
                    wait = (1.0 - self._day_tokens) / self._day_rate

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Rate limiter 토큰 획득 대기 {timeout}초 초과 "
                    f"(minute={int(self._minute_tokens)}, day={int(self._day_tokens)})"
                )
            await asyncio.sleep(min(wait, remaining))

    @property
    def available_minute_tokens(self) -> int:
        self._refill()
        return int(self._minute_tokens)

    @property
    def available_day_tokens(self) -> int:
        self._refill()
        return int(self._day_tokens)
