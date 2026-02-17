import functools
import hashlib
import json
import logging
from typing import Any

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


def _make_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """캐시 키를 생성한다. prefix:func_name:sha256(args+kwargs)"""
    key_data = json.dumps({"args": [str(a) for a in args], "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}})
    key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
    parts = [p for p in [prefix, func_name, key_hash] if p]
    return ":".join(parts)


def cache(ttl: int = 3600, prefix: str = "", model=None):
    """Redis 캐싱 데코레이터

    Args:
        ttl: 캐시 유효 시간 (초). 기본 1시간.
        prefix: 캐시 키 접두사.
        model: Pydantic 모델 클래스. 지정 시 캐시 hit에서 해당 모델로 역직렬화한다.

    Redis 미연결 시 캐시를 건너뛰고 원본 함수를 직접 호출한다.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            redis_client = get_redis()
            if redis_client is None:
                return await func(*args, **kwargs)

            # 메서드인 경우 self를 캐시 키에서 제외 (qualname에 클래스명이 포함됨)
            cache_args = args
            if args and "." in func.__qualname__:
                class_name = func.__qualname__.rsplit(".", 1)[0]
                if type(args[0]).__name__ == class_name:
                    cache_args = args[1:]
            cache_key = _make_cache_key(prefix, func.__qualname__, cache_args, kwargs)

            # 캐시 조회
            try:
                cached = await redis_client.get(cache_key)
                if cached is not None:
                    logger.debug("Cache hit: %s", cache_key)
                    return _deserialize(json.loads(cached), model)
            except Exception as e:
                logger.warning("Cache read error: %s", e)

            # 원본 함수 실행
            result = await func(*args, **kwargs)

            # 결과 캐싱
            try:
                serialized = _serialize(result)
                await redis_client.setex(cache_key, ttl, serialized)
                logger.debug("Cache set: %s (ttl=%ds)", cache_key, ttl)
            except Exception as e:
                logger.warning("Cache write error: %s", e)

            return result

        return wrapper

    return decorator


def _to_serializable(obj: Any) -> Any:
    """객체를 JSON 직렬화 가능한 형태로 재귀 변환한다."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    return obj


def _serialize(obj: Any) -> str:
    """객체를 JSON 문자열로 직렬화한다."""
    return json.dumps(_to_serializable(obj), default=str, ensure_ascii=False)


def _deserialize(data: Any, model=None) -> Any:
    """캐시된 데이터를 원래 타입으로 역직렬화한다."""
    if model is None:
        return data
    if isinstance(data, list) and hasattr(model, "model_validate"):
        return [model.model_validate(item) for item in data]
    if isinstance(data, dict) and hasattr(model, "model_validate"):
        return model.model_validate(data)
    return data
