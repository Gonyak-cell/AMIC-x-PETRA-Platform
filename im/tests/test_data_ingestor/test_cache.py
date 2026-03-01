"""캐시 레이어 테스트."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.data_ingestor.cache import (
    CacheConfig,
    CachedDartClient,
    CacheManager,
    CacheTTL,
)


# ============================================================================
# CacheTTL 테스트
# ============================================================================


class TestCacheTTL:
    """CacheTTL enum 테스트."""

    def test_company_info_ttl(self) -> None:
        """기업정보 TTL은 24시간."""
        assert CacheTTL.COMPANY_INFO == 86400

    def test_financial_statements_ttl(self) -> None:
        """재무제표 TTL은 24시간."""
        assert CacheTTL.FINANCIAL_STATEMENTS == 86400

    def test_news_ttl(self) -> None:
        """뉴스 TTL은 6시간."""
        assert CacheTTL.NEWS == 21600

    def test_web_info_ttl(self) -> None:
        """웹사이트 TTL은 7일."""
        assert CacheTTL.WEB_INFO == 604800

    def test_is_int(self) -> None:
        """CacheTTL은 int로 사용 가능."""
        assert isinstance(CacheTTL.NEWS, int)
        assert CacheTTL.NEWS + 100 == 21700


# ============================================================================
# CacheConfig 테스트
# ============================================================================


class TestCacheConfig:
    """CacheConfig 테스트."""

    def test_default_config(self) -> None:
        """기본 설정 테스트."""
        config = CacheConfig()
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.prefix == "imgen:"
        assert config.default_ttl == CacheTTL.COMPANY_INFO
        assert config.memory_max_size == 1000
        assert config.enable_redis is True

    def test_custom_config(self) -> None:
        """커스텀 설정 테스트."""
        config = CacheConfig(
            redis_url="redis://custom:6380/1",
            prefix="test:",
            default_ttl=3600,
            memory_max_size=500,
            enable_redis=False,
        )
        assert config.redis_url == "redis://custom:6380/1"
        assert config.prefix == "test:"
        assert config.default_ttl == 3600
        assert config.memory_max_size == 500
        assert config.enable_redis is False


# ============================================================================
# CacheManager 테스트 (메모리 전용)
# ============================================================================


class TestCacheManagerMemory:
    """CacheManager 메모리 캐시 테스트."""

    @pytest.fixture
    def config(self) -> CacheConfig:
        """메모리 전용 캐시 설정."""
        return CacheConfig(enable_redis=False, prefix="test:")

    @pytest.mark.asyncio
    async def test_context_manager(self, config: CacheConfig) -> None:
        """컨텍스트 매니저 진입/종료 테스트."""
        async with CacheManager(config) as cache:
            assert cache is not None
            assert not cache.redis_available

    @pytest.mark.asyncio
    async def test_set_and_get(self, config: CacheConfig) -> None:
        """캐시 저장 및 조회 테스트."""
        async with CacheManager(config) as cache:
            await cache.set("key1", {"data": "value1"}, ttl=60)
            result = await cache.get("key1")
            assert result == {"data": "value1"}

    @pytest.mark.asyncio
    async def test_get_miss(self, config: CacheConfig) -> None:
        """캐시 미스 테스트."""
        async with CacheManager(config) as cache:
            result = await cache.get("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_set_overwrite(self, config: CacheConfig) -> None:
        """같은 키 덮어쓰기 테스트."""
        async with CacheManager(config) as cache:
            await cache.set("key1", "first", ttl=60)
            await cache.set("key1", "second", ttl=60)
            result = await cache.get("key1")
            assert result == "second"

    @pytest.mark.asyncio
    async def test_delete(self, config: CacheConfig) -> None:
        """캐시 삭제 테스트."""
        async with CacheManager(config) as cache:
            await cache.set("key1", "value1", ttl=60)
            await cache.delete("key1")
            result = await cache.get("key1")
            assert result is None

    @pytest.mark.asyncio
    async def test_clear_all(self, config: CacheConfig) -> None:
        """전체 캐시 삭제 테스트."""
        async with CacheManager(config) as cache:
            await cache.set("key1", "value1", ttl=60)
            await cache.set("key2", "value2", ttl=60)
            await cache.clear()
            assert await cache.get("key1") is None
            assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_expired_entry(self, config: CacheConfig) -> None:
        """만료된 항목 테스트."""
        async with CacheManager(config) as cache:
            await cache.set("key1", "value1", ttl=1)
            # 만료 시뮬레이션
            full_key = cache._prefixed_key("key1")
            value, _ = cache._memory[full_key]
            cache._memory[full_key] = (value, time.time() - 1)

            result = await cache.get("key1")
            assert result is None

    @pytest.mark.asyncio
    async def test_memory_size_tracking(self, config: CacheConfig) -> None:
        """메모리 캐시 크기 추적 테스트."""
        async with CacheManager(config) as cache:
            assert cache.memory_size == 0
            await cache.set("key1", "value1", ttl=60)
            assert cache.memory_size == 1
            await cache.set("key2", "value2", ttl=60)
            assert cache.memory_size == 2

    @pytest.mark.asyncio
    async def test_default_ttl(self, config: CacheConfig) -> None:
        """기본 TTL 적용 테스트."""
        async with CacheManager(config) as cache:
            await cache.set("key1", "value1")
            full_key = cache._prefixed_key("key1")
            _, expiry = cache._memory[full_key]
            # default_ttl (86400초) 내에 만료
            expected_expiry = time.time() + config.default_ttl
            assert abs(expiry - expected_expiry) < 2  # 2초 오차 허용

    @pytest.mark.asyncio
    async def test_prefixed_key(self, config: CacheConfig) -> None:
        """키 프리픽스 테스트."""
        cache = CacheManager(config)
        assert cache._prefixed_key("mykey") == "test:mykey"

    @pytest.mark.asyncio
    async def test_evict_expired(self, config: CacheConfig) -> None:
        """만료된 항목 제거 테스트."""
        async with CacheManager(config) as cache:
            # 만료된 항목 추가
            full_key = cache._prefixed_key("expired")
            cache._memory[full_key] = ("old", time.time() - 1)

            # 유효한 항목 추가
            await cache.set("valid", "data", ttl=60)

            cache._evict_expired()

            assert full_key not in cache._memory
            assert cache.memory_size == 1

    @pytest.mark.asyncio
    async def test_memory_max_size_eviction(self) -> None:
        """메모리 최대 크기 초과 시 만료 항목 제거 테스트."""
        config = CacheConfig(enable_redis=False, memory_max_size=2, prefix="test:")
        async with CacheManager(config) as cache:
            await cache.set("key1", "value1", ttl=60)
            await cache.set("key2", "value2", ttl=60)

            # key1을 만료시킴
            full_key1 = cache._prefixed_key("key1")
            value, _ = cache._memory[full_key1]
            cache._memory[full_key1] = (value, time.time() - 1)

            # 새 항목 추가 → 만료 항목 제거됨
            await cache.set("key3", "value3", ttl=60)
            assert cache.memory_size == 2  # key2 + key3

    @pytest.mark.asyncio
    async def test_json_serializable_values(self, config: CacheConfig) -> None:
        """다양한 JSON 직렬화 가능 값 테스트."""
        async with CacheManager(config) as cache:
            # dict
            await cache.set("dict", {"a": 1, "b": [1, 2]}, ttl=60)
            assert await cache.get("dict") == {"a": 1, "b": [1, 2]}

            # list
            await cache.set("list", [1, 2, 3], ttl=60)
            assert await cache.get("list") == [1, 2, 3]

            # string
            await cache.set("str", "hello", ttl=60)
            assert await cache.get("str") == "hello"

            # number
            await cache.set("int", 42, ttl=60)
            assert await cache.get("int") == 42

    @pytest.mark.asyncio
    async def test_close_clears_memory(self, config: CacheConfig) -> None:
        """close() 호출 시 메모리 캐시 초기화 테스트."""
        cache = CacheManager(config)
        await cache.__aenter__()
        await cache.set("key1", "value1", ttl=60)
        assert cache.memory_size == 1

        await cache.close()
        assert cache.memory_size == 0


# ============================================================================
# CacheManager Redis 폴백 테스트
# ============================================================================


class TestCacheManagerRedisFallback:
    """Redis 연결 실패 시 메모리 폴백 테스트."""

    @pytest.mark.asyncio
    async def test_redis_connection_failure_fallback(self) -> None:
        """Redis 연결 실패 시 메모리 캐시로 폴백."""
        config = CacheConfig(
            enable_redis=True,
            redis_url="redis://nonexistent:9999/0",
            prefix="test:",
        )
        async with CacheManager(config) as cache:
            assert not cache.redis_available

            # 메모리 캐시가 정상 작동해야 함
            await cache.set("key1", "value1", ttl=60)
            result = await cache.get("key1")
            assert result == "value1"

    @pytest.mark.asyncio
    async def test_redis_get_failure_fallback(self) -> None:
        """Redis get 실패 시 메모리 폴백."""
        config = CacheConfig(enable_redis=False, prefix="test:")
        cache = CacheManager(config)
        await cache.__aenter__()

        # Redis 사용 가능으로 설정하되, 실패하도록 모킹
        cache._redis_available = True
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        cache._redis = mock_redis

        # 메모리에 직접 저장
        full_key = cache._prefixed_key("key1")
        cache._memory[full_key] = ("value1", time.time() + 60)

        result = await cache.get("key1")
        assert result == "value1"

        await cache.close()

    @pytest.mark.asyncio
    async def test_redis_set_failure_fallback(self) -> None:
        """Redis set 실패 시 메모리 폴백."""
        config = CacheConfig(enable_redis=False, prefix="test:")
        cache = CacheManager(config)
        await cache.__aenter__()

        # Redis 사용 가능으로 설정하되, 실패하도록 모킹
        cache._redis_available = True
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Redis error")
        cache._redis = mock_redis

        await cache.set("key1", "value1", ttl=60)

        # 메모리에 저장되었는지 확인
        assert cache.memory_size == 1

        await cache.close()


# ============================================================================
# CachedDartClient 테스트
# ============================================================================


class TestCachedDartClient:
    """CachedDartClient 테스트."""

    @pytest.fixture
    def mock_dart_client(self) -> AsyncMock:
        """모킹된 DartAPIClient."""
        client = AsyncMock()

        # get_company_info 모킹
        mock_company = MagicMock()
        mock_company.model_dump.return_value = {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "corp_cls": "Y",
        }
        client.get_company_info.return_value = mock_company

        # get_financial_statements 모킹
        mock_fs = MagicMock()
        mock_fs.model_dump.return_value = {
            "corp_code": "00126380",
            "items": [],
        }
        client.get_financial_statements.return_value = mock_fs

        # get_major_shareholders 모킹
        mock_sh = MagicMock()
        mock_sh.model_dump.return_value = {
            "rcept_no": "20240101",
            "rcept_dt": "20240101",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "report_tp": "대량보유",
            "repror": "이재용",
        }
        client.get_major_shareholders.return_value = [mock_sh]

        # get_dividend 모킹
        mock_div = MagicMock()
        mock_div.model_dump.return_value = {
            "rcept_no": "20240101",
            "corp_cls": "Y",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "se": "주당배당금",
            "stock_knd": "보통주",
        }
        client.get_dividend.return_value = [mock_div]

        return client

    @pytest.fixture
    def cache_config(self) -> CacheConfig:
        """메모리 전용 캐시 설정."""
        return CacheConfig(enable_redis=False, prefix="test:")

    @pytest.mark.asyncio
    async def test_get_company_info_cache_miss(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """캐시 미스 시 API 호출 테스트."""
        async with CacheManager(cache_config) as cache:
            client = CachedDartClient(client=mock_dart_client, cache=cache)
            result = await client.get_company_info("00126380")

            mock_dart_client.get_company_info.assert_called_once_with("00126380")
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_company_info_cache_hit(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """캐시 히트 시 API 미호출 테스트."""
        async with CacheManager(cache_config) as cache:
            client = CachedDartClient(client=mock_dart_client, cache=cache)

            # 첫 번째 호출 (캐시 미스 → API 호출)
            await client.get_company_info("00126380")

            # 두 번째 호출 (캐시 히트 → API 미호출)
            await client.get_company_info("00126380")

            assert mock_dart_client.get_company_info.call_count == 1

    @pytest.mark.asyncio
    async def test_get_financial_statements_cache_miss(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """재무제표 캐시 미스 테스트."""
        async with CacheManager(cache_config) as cache:
            client = CachedDartClient(client=mock_dart_client, cache=cache)
            result = await client.get_financial_statements(
                "00126380", "2024"
            )

            mock_dart_client.get_financial_statements.assert_called_once()
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_financial_statements_cache_hit(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """재무제표 캐시 히트 테스트."""
        async with CacheManager(cache_config) as cache:
            client = CachedDartClient(client=mock_dart_client, cache=cache)

            await client.get_financial_statements("00126380", "2024")
            await client.get_financial_statements("00126380", "2024")

            assert mock_dart_client.get_financial_statements.call_count == 1

    @pytest.mark.asyncio
    async def test_different_keys_separate_cache(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """다른 키는 별도 캐시 테스트."""
        async with CacheManager(cache_config) as cache:
            client = CachedDartClient(client=mock_dart_client, cache=cache)

            await client.get_financial_statements("00126380", "2024")
            await client.get_financial_statements("00126380", "2023")

            assert mock_dart_client.get_financial_statements.call_count == 2

    @pytest.mark.asyncio
    async def test_get_major_shareholders_cache(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """주주정보 캐시 테스트."""
        async with CacheManager(cache_config) as cache:
            client = CachedDartClient(client=mock_dart_client, cache=cache)

            result1 = await client.get_major_shareholders("00126380")
            await client.get_major_shareholders("00126380")

            assert mock_dart_client.get_major_shareholders.call_count == 1
            assert len(result1) > 0

    @pytest.mark.asyncio
    async def test_get_dividend_cache(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """배당정보 캐시 테스트."""
        async with CacheManager(cache_config) as cache:
            client = CachedDartClient(client=mock_dart_client, cache=cache)

            result1 = await client.get_dividend("00126380", "2024")
            await client.get_dividend("00126380", "2024")

            assert mock_dart_client.get_dividend.call_count == 1
            assert len(result1) > 0

    @pytest.mark.asyncio
    async def test_context_manager(
        self, mock_dart_client: AsyncMock, cache_config: CacheConfig
    ) -> None:
        """컨텍스트 매니저 테스트."""
        async with CacheManager(cache_config) as cache:
            async with CachedDartClient(
                client=mock_dart_client, cache=cache
            ) as client:
                result = await client.get_company_info("00126380")
                assert result is not None
