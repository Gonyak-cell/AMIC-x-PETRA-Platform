"""S1-B-04: 캐싱 단위 테스트"""

import json
from unittest.mock import patch

import fakeredis.aioredis
import pytest

from app.utils.cache import _make_cache_key, _serialize, cache

# --- 키 생성 테스트 ---


def test_make_cache_key_basic():
    """기본 캐시 키 생성"""
    key = _make_cache_key("dart", "get_company_info", ("00126380",), {})
    assert key.startswith("dart:get_company_info:")
    assert len(key.split(":")) == 3


def test_make_cache_key_with_kwargs():
    """kwargs 포함 캐시 키"""
    key1 = _make_cache_key("dart", "search", (), {"corp_code": "001"})
    key2 = _make_cache_key("dart", "search", (), {"corp_code": "002"})
    assert key1 != key2


def test_make_cache_key_deterministic():
    """동일 인자 시 동일 키"""
    key1 = _make_cache_key("dart", "func", ("a", "b"), {"x": "1"})
    key2 = _make_cache_key("dart", "func", ("a", "b"), {"x": "1"})
    assert key1 == key2


def test_make_cache_key_no_prefix():
    """prefix 없는 키"""
    key = _make_cache_key("", "func", ("a",), {})
    assert key.startswith("func:")


# --- 직렬화 테스트 ---


def test_serialize_dict():
    """dict 직렬화"""
    result = _serialize({"name": "test", "value": 123})
    parsed = json.loads(result)
    assert parsed["name"] == "test"
    assert parsed["value"] == 123


def test_serialize_list():
    """list 직렬화"""
    result = _serialize([{"a": 1}, {"b": 2}])
    parsed = json.loads(result)
    assert len(parsed) == 2


# --- 캐시 데코레이터 테스트 (fakeredis) ---


@pytest.fixture
async def fake_redis():
    """fakeredis 인스턴스"""
    server = fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()


async def test_cache_hit(fake_redis):
    """캐시 hit 테스트"""
    call_count = 0

    @cache(ttl=60, prefix="test")
    async def expensive_func(x: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {"result": x * 2}

    with patch("app.utils.cache.get_redis", return_value=fake_redis):
        # 첫 번째 호출: cache miss
        result1 = await expensive_func(5)
        assert result1 == {"result": 10}
        assert call_count == 1

        # 두 번째 호출: cache hit
        result2 = await expensive_func(5)
        assert result2 == {"result": 10}
        assert call_count == 1  # 실제 함수는 호출되지 않음


async def test_cache_miss_different_args(fake_redis):
    """다른 인자 시 cache miss"""
    call_count = 0

    @cache(ttl=60, prefix="test")
    async def func(x: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {"result": x}

    with patch("app.utils.cache.get_redis", return_value=fake_redis):
        await func(1)
        await func(2)
        assert call_count == 2  # 다른 인자이므로 각각 호출


async def test_cache_no_redis():
    """Redis 미연결 시 원본 함수 직접 호출"""
    call_count = 0

    @cache(ttl=60, prefix="test")
    async def func() -> dict:
        nonlocal call_count
        call_count += 1
        return {"ok": True}

    with patch("app.utils.cache.get_redis", return_value=None):
        result = await func()
        assert result == {"ok": True}
        assert call_count == 1

        # Redis 없으면 매번 원본 함수 호출
        await func()
        assert call_count == 2


async def test_cache_ttl_expiry(fake_redis):
    """TTL 설정 테스트"""
    call_count = 0

    @cache(ttl=300, prefix="test")
    async def func() -> dict:
        nonlocal call_count
        call_count += 1
        return {"data": "value"}

    with patch("app.utils.cache.get_redis", return_value=fake_redis):
        await func()
        assert call_count == 1

        # TTL 설정 확인 (fakeredis에서 키 존재 확인)
        keys = await fake_redis.keys("test:*")
        assert len(keys) == 1

        # TTL이 설정되어 있는지 확인
        ttl = await fake_redis.ttl(keys[0])
        assert ttl > 0
        assert ttl <= 300
