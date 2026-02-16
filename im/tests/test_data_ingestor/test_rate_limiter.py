"""Rate Limiter 테스트.

T-D02 검증: Token Bucket 동작 및 동시 요청 시 rate limit 확인
"""

import asyncio
from time import monotonic
from unittest.mock import patch

import pytest

from src.data_ingestor.dart.rate_limiter import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    RateLimiter,
    RetryConfig,
    DART_CIRCUIT_BREAKER,
    DART_RATE_LIMITER,
    DART_RETRY_CONFIG,
)


class TestRateLimiter:
    """RateLimiter 테스트."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """테스트 전 싱글톤 인스턴스 클리어."""
        RateLimiter.clear_instances()

    @pytest.mark.asyncio
    async def test_basic_acquire(self) -> None:
        """기본 acquire 동작 테스트."""
        limiter = RateLimiter(max_calls=10, period=1.0)

        # 10회 호출 가능
        for _ in range(10):
            await limiter.acquire()

        assert limiter._total_calls == 10

    @pytest.mark.asyncio
    async def test_rate_limit_waits(self) -> None:
        """Rate limit 도달 시 대기 테스트."""
        limiter = RateLimiter(max_calls=2, period=0.1)

        start = monotonic()

        # 2회 즉시 호출
        await limiter.acquire()
        await limiter.acquire()

        # 3번째 호출은 대기해야 함
        await limiter.acquire()

        elapsed = monotonic() - start
        assert elapsed >= 0.08  # 최소 ~0.1초 대기 (타이밍 허용 오차 고려)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self) -> None:
        """동시 요청 시 rate limit 동작 확인."""
        limiter = RateLimiter(max_calls=3, period=0.2)

        async def make_request() -> float:
            await limiter.acquire()
            return monotonic()

        # 5개 동시 요청
        tasks = [make_request() for _ in range(5)]
        timestamps = await asyncio.gather(*tasks)

        # 처음 3개는 즉시, 나머지는 대기 후 실행
        sorted_times = sorted(timestamps)
        first_batch = sorted_times[:3]
        second_batch = sorted_times[3:]

        # 두 번째 배치는 첫 번째보다 늦게 실행
        assert min(second_batch) >= max(first_batch)

    def test_available_calls(self) -> None:
        """사용 가능한 호출 횟수 확인."""
        limiter = RateLimiter(max_calls=100, period=60.0)
        assert limiter.available_calls == 100

    def test_stats(self) -> None:
        """통계 정보 확인."""
        limiter = RateLimiter(max_calls=100, period=60.0)
        stats = limiter.stats

        assert stats["max_calls"] == 100
        assert stats["period"] == 60.0
        assert stats["total_calls"] == 0
        assert stats["total_waits"] == 0

    def test_singleton_pattern(self) -> None:
        """싱글톤 패턴 동작 확인."""
        limiter1 = RateLimiter.get_instance("test", max_calls=100, period=60.0)
        limiter2 = RateLimiter.get_instance("test", max_calls=50, period=30.0)  # 설정 무시됨

        assert limiter1 is limiter2
        assert limiter1.max_calls == 100  # 첫 번째 설정 유지

    def test_reset(self) -> None:
        """리셋 동작 확인."""
        limiter = RateLimiter(max_calls=100, period=60.0)
        limiter._calls.append(monotonic())
        limiter._total_calls = 10
        limiter._total_waits = 2

        limiter.reset()

        assert len(limiter._calls) == 0
        assert limiter._total_calls == 0
        assert limiter._total_waits == 0


class TestCircuitBreaker:
    """CircuitBreaker 테스트."""

    def test_initial_state(self) -> None:
        """초기 상태 확인."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self) -> None:
        """성공 시 CLOSED 상태 유지."""
        cb = CircuitBreaker(failure_threshold=3)

        async def success() -> str:
            return "ok"

        result = await cb.call(success)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self) -> None:
        """임계값 초과 시 OPEN 상태 전환."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)

        async def fail() -> None:
            raise ValueError("error")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_state_raises_error(self) -> None:
        """OPEN 상태에서 호출 시 즉시 실패."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)

        async def fail() -> None:
            raise ValueError("error")

        with pytest.raises(ValueError):
            await cb.call(fail)

        # 이제 회로가 열림
        with pytest.raises(CircuitBreakerError) as exc_info:
            await cb.call(fail)

        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self) -> None:
        """recovery_timeout 후 HALF_OPEN 상태."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        async def fail() -> None:
            raise ValueError("error")

        with pytest.raises(ValueError):
            await cb.call(fail)

        assert cb._state == CircuitState.OPEN

        # 대기 후 상태 확인
        await asyncio.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes(self) -> None:
        """HALF_OPEN에서 성공 시 CLOSED."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        async def fail() -> None:
            raise ValueError("error")

        async def success() -> str:
            return "ok"

        with pytest.raises(ValueError):
            await cb.call(fail)

        await asyncio.sleep(0.15)
        result = await cb.call(success)

        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    def test_reset(self) -> None:
        """수동 리셋 동작."""
        cb = CircuitBreaker()
        cb._state = CircuitState.OPEN
        cb._failure_count = 5

        cb.reset()

        assert cb._state == CircuitState.CLOSED
        assert cb._failure_count == 0


class TestRetryConfig:
    """RetryConfig 테스트."""

    def test_default_config(self) -> None:
        """기본 설정 확인."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.factor == 2.0
        assert 429 in config.retryable_status_codes

    def test_exponential_delay(self) -> None:
        """지수 백오프 지연 계산."""
        config = RetryConfig(base_delay=1.0, factor=2.0, max_delay=10.0)

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0
        assert config.get_delay(4) == 10.0  # max_delay 적용


class TestDartDefaults:
    """DART 기본 인스턴스 테스트."""

    def test_dart_rate_limiter_exists(self) -> None:
        """DART_RATE_LIMITER 존재 확인."""
        assert DART_RATE_LIMITER is not None
        assert DART_RATE_LIMITER.max_calls == 100
        assert DART_RATE_LIMITER.period == 60.0

    def test_dart_circuit_breaker_exists(self) -> None:
        """DART_CIRCUIT_BREAKER 존재 확인."""
        assert DART_CIRCUIT_BREAKER is not None
        assert DART_CIRCUIT_BREAKER.failure_threshold == 5
        assert DART_CIRCUIT_BREAKER.recovery_timeout == 30.0

    def test_dart_retry_config_exists(self) -> None:
        """DART_RETRY_CONFIG 존재 확인."""
        assert DART_RETRY_CONFIG is not None
        assert DART_RETRY_CONFIG.max_retries == 3
        assert 429 in DART_RETRY_CONFIG.retryable_status_codes
