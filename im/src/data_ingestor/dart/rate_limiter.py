"""DART API Rate Limiter.

Token Bucket 알고리즘 기반 100 calls/min 제한기.
Circuit Breaker 패턴으로 연속 실패 시 자동 차단.

Usage::
    limiter = RateLimiter(max_calls=100, period=60.0)
    await limiter.acquire()  # 호출 가능할 때까지 대기
"""

from __future__ import annotations

import asyncio
import enum
import logging
from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """Circuit Breaker 상태."""

    CLOSED = "closed"  # 정상 동작
    OPEN = "open"  # 차단 (호출 즉시 실패)
    HALF_OPEN = "half_open"  # 테스트 중 (1회 성공 시 CLOSED)


class CircuitBreakerError(Exception):
    """Circuit Breaker가 열려있을 때 발생하는 예외."""

    def __init__(self, retry_after: float) -> None:
        super().__init__(
            f"Circuit breaker is open. Retry after {retry_after:.1f} seconds."
        )
        self.retry_after = retry_after


@dataclass
class CircuitBreaker:
    """Circuit Breaker 패턴 구현.

    Attributes:
        failure_threshold: 연속 실패 횟수 임계값 (기본 5)
        recovery_timeout: 회로 개방 후 대기 시간 초 (기본 30)
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float | None = field(default=None, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        """현재 상태 조회 (시간 경과에 따른 상태 전이 포함)."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def call(self, func: Callable[[], Awaitable[_T]]) -> _T:
        """Circuit Breaker로 감싸서 함수 호출.

        Args:
            func: 호출할 비동기 함수

        Returns:
            함수 반환값

        Raises:
            CircuitBreakerError: 회로가 열려있을 때
        """
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                retry_after = self.recovery_timeout - (
                    monotonic() - (self._last_failure_time or 0)
                )
                raise CircuitBreakerError(retry_after=max(0, retry_after))

        try:
            result = await func()
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """호출 성공 시 상태 업데이트."""
        async with self._lock:
            self._failure_count = 0
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                self._state = CircuitState.CLOSED
                logger.info("Circuit breaker closed after successful call")

    async def _on_failure(self) -> None:
        """호출 실패 시 상태 업데이트."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker re-opened after failure in half-open state"
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker opened after %d consecutive failures",
                    self._failure_count,
                )

    def reset(self) -> None:
        """수동으로 Circuit Breaker 리셋."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None


class RateLimiter:
    """Token Bucket 알고리즘 기반 Rate Limiter.

    DART API는 분당 100회 호출 제한이 있습니다.
    이 클래스는 호출 간격을 자동으로 조절합니다.

    Attributes:
        max_calls: 기간 내 최대 호출 횟수
        period: 기간 (초)

    Example::
        limiter = RateLimiter(max_calls=100, period=60.0)

        async def call_dart_api():
            await limiter.acquire()
            # API 호출
    """

    # 싱글톤 인스턴스 저장 (API별)
    _instances: dict[str, "RateLimiter"] = {}

    def __init__(self, max_calls: int = 100, period: float = 60.0) -> None:
        """Rate Limiter 초기화.

        Args:
            max_calls: 기간 내 최대 호출 횟수 (기본 100)
            period: 기간 초 (기본 60초 = 1분)
        """
        self.max_calls = max_calls
        self.period = period
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._total_calls = 0
        self._total_waits = 0

    @classmethod
    def get_instance(
        cls, name: str, max_calls: int = 100, period: float = 60.0
    ) -> "RateLimiter":
        """싱글톤 인스턴스 반환.

        Args:
            name: 인스턴스 식별자 (예: "dart", "brandfetch")
            max_calls: 기간 내 최대 호출 횟수
            period: 기간 초

        Returns:
            RateLimiter 인스턴스
        """
        if name not in cls._instances:
            cls._instances[name] = cls(max_calls=max_calls, period=period)
        return cls._instances[name]

    @classmethod
    def clear_instances(cls) -> None:
        """모든 싱글톤 인스턴스 제거 (테스트용)."""
        cls._instances.clear()

    async def acquire(self) -> None:
        """호출 권한 획득 (필요시 대기).

        Token Bucket에서 토큰을 소비합니다.
        버킷이 비었으면 토큰이 리필될 때까지 대기합니다.
        """
        async with self._lock:
            now = monotonic()

            # 기간이 지난 호출 기록 제거
            while self._calls and self._calls[0] <= now - self.period:
                self._calls.popleft()

            # 버킷이 가득 찼으면 대기
            if len(self._calls) >= self.max_calls:
                sleep_time = self._calls[0] + self.period - now
                if sleep_time > 0:
                    self._total_waits += 1
                    logger.warning(
                        "Rate limit reached (%d/%d). Waiting %.2f seconds...",
                        len(self._calls),
                        self.max_calls,
                        sleep_time,
                    )
                    await asyncio.sleep(sleep_time)

                    # 대기 후 다시 정리
                    now = monotonic()
                    while self._calls and self._calls[0] <= now - self.period:
                        self._calls.popleft()

            # 현재 호출 기록
            self._calls.append(monotonic())
            self._total_calls += 1

    @property
    def available_calls(self) -> int:
        """현재 사용 가능한 호출 횟수."""
        now = monotonic()
        # 기간 내 호출 수 계산
        active_calls = sum(1 for t in self._calls if t > now - self.period)
        return max(0, self.max_calls - active_calls)

    @property
    def stats(self) -> dict[str, int | float]:
        """Rate limiter 통계."""
        return {
            "max_calls": self.max_calls,
            "period": self.period,
            "available_calls": self.available_calls,
            "total_calls": self._total_calls,
            "total_waits": self._total_waits,
        }

    def reset(self) -> None:
        """Rate limiter 리셋 (테스트용)."""
        self._calls.clear()
        self._total_calls = 0
        self._total_waits = 0


class RetryConfig:
    """재시도 설정.

    Exponential backoff 전략을 사용합니다.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        factor: float = 2.0,
        max_delay: float = 30.0,
        retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504),
    ) -> None:
        """재시도 설정 초기화.

        Args:
            max_retries: 최대 재시도 횟수
            base_delay: 기본 지연 시간 (초)
            factor: 지연 증가 배수
            max_delay: 최대 지연 시간 (초)
            retryable_status_codes: 재시도 대상 HTTP 상태 코드
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.factor = factor
        self.max_delay = max_delay
        self.retryable_status_codes = retryable_status_codes

    def get_delay(self, attempt: int) -> float:
        """재시도 시 대기 시간 계산.

        Args:
            attempt: 현재 시도 횟수 (0부터 시작)

        Returns:
            대기 시간 (초)
        """
        delay = self.base_delay * (self.factor**attempt)
        return min(delay, self.max_delay)


# 기본 DART API용 인스턴스
DART_RATE_LIMITER = RateLimiter.get_instance("dart", max_calls=100, period=60.0)
DART_CIRCUIT_BREAKER = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
DART_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    factor=2.0,
    retryable_status_codes=(429, 500, 502, 503, 504),
)
