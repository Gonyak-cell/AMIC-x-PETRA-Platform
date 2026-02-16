"""캐싱 레이어.

Redis 우선, 메모리 폴백 캐시 매니저와 DartAPIClient 캐시 래퍼를 제공합니다.

사용 예시:
    async with CacheManager(CacheConfig()) as cache:
        await cache.set("key", {"data": 1}, ttl=3600)
        value = await cache.get("key")

    # DartAPIClient에 캐싱 적용
    async with CachedDartClient(api_key="KEY", cache=cache) as client:
        info = await client.get_company_info("00126380")  # 캐시 미스 → API 호출
        info = await client.get_company_info("00126380")  # 캐시 히트
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from src.data_ingestor.dart.endpoints import FinancialStatementDivision, ReportCode
from src.data_ingestor.dart.models import (
    DartCompanyInfo,
    DartDividend,
    DartMajorShareholder,
    FinancialStatementsCollection,
)
from src.data_ingestor.exceptions import CacheError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# TTL 및 설정
# ============================================================================


class CacheTTL(IntEnum):
    """캐시 TTL 상수 (초)."""

    COMPANY_INFO = 86400  # 24시간
    FINANCIAL_STATEMENTS = 86400  # 24시간
    NEWS = 21600  # 6시간
    WEB_INFO = 604800  # 7일


@dataclass
class CacheConfig:
    """캐시 설정."""

    redis_url: str = "redis://localhost:6379/0"
    """Redis 연결 URL."""

    prefix: str = "imgen:"
    """캐시 키 프리픽스."""

    default_ttl: int = CacheTTL.COMPANY_INFO
    """기본 TTL (초)."""

    memory_max_size: int = 1000
    """메모리 캐시 최대 항목 수."""

    enable_redis: bool = True
    """Redis 사용 여부. False이면 메모리 전용."""


# ============================================================================
# CacheManager
# ============================================================================


class CacheManager:
    """캐시 매니저.

    Redis를 우선 사용하고, 연결 실패 시 메모리 dict로 폴백합니다.
    async context manager로 사용합니다.

    Example:
        >>> config = CacheConfig(enable_redis=False)
        >>> async with CacheManager(config) as cache:
        ...     await cache.set("key", "value", ttl=60)
        ...     result = await cache.get("key")
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        self._config = config or CacheConfig()
        self._redis: Any | None = None
        self._redis_available = False
        # 메모리 캐시: key -> (value, expiry_timestamp)
        self._memory: dict[str, tuple[Any, float]] = {}

    async def __aenter__(self) -> CacheManager:
        """비동기 컨텍스트 매니저 진입."""
        if self._config.enable_redis:
            await self._connect_redis()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """비동기 컨텍스트 매니저 종료."""
        await self.close()

    async def _connect_redis(self) -> None:
        """Redis 연결을 시도합니다."""
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self._config.redis_url,
                decode_responses=True,
            )
            await self._redis.ping()
            self._redis_available = True
            logger.info("Redis 연결 성공: %s", self._config.redis_url)
        except Exception as e:
            logger.warning("Redis 연결 실패, 메모리 캐시로 폴백: %s", e)
            self._redis = None
            self._redis_available = False

    async def close(self) -> None:
        """리소스 정리."""
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
            self._redis_available = False
        self._memory.clear()

    def _prefixed_key(self, key: str) -> str:
        """프리픽스가 붙은 캐시 키를 반환합니다."""
        return f"{self._config.prefix}{key}"

    async def get(self, key: str) -> Any | None:
        """캐시에서 값을 조회합니다.

        Args:
            key: 캐시 키.

        Returns:
            캐시된 값 또는 None (미스).
        """
        full_key = self._prefixed_key(key)

        # Redis 시도
        if self._redis_available:
            try:
                value = await self._redis.get(full_key)
                if value is not None:
                    logger.debug("Redis 캐시 히트: %s", key)
                    return json.loads(value)
                logger.debug("Redis 캐시 미스: %s", key)
                return None
            except Exception as e:
                logger.warning("Redis get 실패, 메모리 폴백: %s", e)

        # 메모리 캐시
        entry = self._memory.get(full_key)
        if entry is not None:
            value, expiry = entry
            if time.time() < expiry:
                logger.debug("메모리 캐시 히트: %s", key)
                return value
            # 만료됨
            del self._memory[full_key]

        logger.debug("캐시 미스: %s", key)
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """캐시에 값을 저장합니다.

        Args:
            key: 캐시 키.
            value: 저장할 값 (JSON 직렬화 가능).
            ttl: TTL (초). None이면 기본 TTL 사용.
        """
        full_key = self._prefixed_key(key)
        actual_ttl = ttl if ttl is not None else self._config.default_ttl

        # Redis 시도
        if self._redis_available:
            try:
                await self._redis.set(
                    full_key,
                    json.dumps(value, ensure_ascii=False, default=str),
                    ex=actual_ttl,
                )
                logger.debug("Redis 캐시 저장: %s (TTL=%ds)", key, actual_ttl)
                return
            except Exception as e:
                logger.warning("Redis set 실패, 메모리 폴백: %s", e)

        # 메모리 캐시
        if len(self._memory) >= self._config.memory_max_size:
            self._evict_expired()

        expiry = time.time() + actual_ttl
        self._memory[full_key] = (value, expiry)
        logger.debug("메모리 캐시 저장: %s (TTL=%ds)", key, actual_ttl)

    async def delete(self, key: str) -> None:
        """캐시에서 키를 삭제합니다.

        Args:
            key: 삭제할 캐시 키.
        """
        full_key = self._prefixed_key(key)

        if self._redis_available:
            try:
                await self._redis.delete(full_key)
            except Exception as e:
                logger.warning("Redis delete 실패: %s", e)

        self._memory.pop(full_key, None)

    async def clear(self, pattern: str = "*") -> None:
        """패턴에 맞는 캐시를 삭제합니다.

        Args:
            pattern: 삭제할 키 패턴 (glob). 기본값 "*"은 모든 키.
        """
        full_pattern = self._prefixed_key(pattern)

        if self._redis_available:
            try:
                cursor = "0"
                while cursor != 0:
                    cursor, keys = await self._redis.scan(
                        cursor=cursor, match=full_pattern, count=100
                    )
                    if keys:
                        await self._redis.delete(*keys)
            except Exception as e:
                logger.warning("Redis clear 실패: %s", e)

        # 메모리 캐시에서도 패턴 매칭으로 삭제
        if pattern == "*":
            prefix = self._config.prefix
            keys_to_delete = [k for k in self._memory if k.startswith(prefix)]
        else:
            # 간단한 prefix 매칭 (glob은 Redis에서 처리)
            keys_to_delete = [k for k in self._memory if k.startswith(full_pattern.rstrip("*"))]

        for k in keys_to_delete:
            del self._memory[k]

    def _evict_expired(self) -> None:
        """만료된 메모리 캐시 항목을 제거합니다."""
        now = time.time()
        expired_keys = [k for k, (_, expiry) in self._memory.items() if now >= expiry]
        for k in expired_keys:
            del self._memory[k]

    @property
    def redis_available(self) -> bool:
        """Redis 연결 가능 여부."""
        return self._redis_available

    @property
    def memory_size(self) -> int:
        """메모리 캐시 항목 수."""
        return len(self._memory)


# ============================================================================
# CachedDartClient
# ============================================================================


class CachedDartClient:
    """캐시가 적용된 DartAPIClient 래퍼.

    DartAPIClient와 동일한 인터페이스를 제공하되,
    API 호출 결과를 캐싱하여 반복 호출 시 캐시에서 반환합니다.

    Example:
        >>> cache = CacheManager(CacheConfig(enable_redis=False))
        >>> async with CachedDartClient(api_key="KEY", cache=cache) as client:
        ...     info = await client.get_company_info("00126380")
    """

    def __init__(
        self,
        *,
        client: Any,
        cache: CacheManager,
    ) -> None:
        """CachedDartClient 초기화.

        Args:
            client: DartAPIClient 인스턴스.
            cache: CacheManager 인스턴스.
        """
        self._client = client
        self._cache = cache

    async def __aenter__(self) -> CachedDartClient:
        """비동기 컨텍스트 매니저 진입."""
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """비동기 컨텍스트 매니저 종료."""
        pass

    def _make_key(self, *parts: str) -> str:
        """캐시 키를 생성합니다."""
        return ":".join(parts)

    async def get_company_info(self, corp_code: str) -> DartCompanyInfo:
        """기업 개황 정보를 조회합니다 (캐시 적용).

        Args:
            corp_code: 고유번호 (8자리).

        Returns:
            DartCompanyInfo 객체.
        """
        cache_key = self._make_key("company_info", corp_code)

        # 캐시 조회
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug("캐시 히트 - company_info: %s", corp_code)
            return DartCompanyInfo.model_validate(cached)

        # API 호출
        result = await self._client.get_company_info(corp_code)

        # 캐시 저장
        await self._cache.set(
            cache_key,
            result.model_dump(),
            ttl=CacheTTL.COMPANY_INFO,
        )

        return result

    async def get_financial_statements(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: ReportCode | str = ReportCode.ANNUAL,
        fs_div: FinancialStatementDivision | str = FinancialStatementDivision.CONSOLIDATED,
    ) -> FinancialStatementsCollection:
        """재무제표 정보를 조회합니다 (캐시 적용).

        Args:
            corp_code: 고유번호 (8자리).
            bsns_year: 사업연도.
            reprt_code: 보고서 코드.
            fs_div: 재무제표 구분.

        Returns:
            FinancialStatementsCollection 객체.
        """
        reprt_code_value = reprt_code.value if isinstance(reprt_code, ReportCode) else reprt_code
        fs_div_value = (
            fs_div.value if isinstance(fs_div, FinancialStatementDivision) else fs_div
        )

        cache_key = self._make_key(
            "financial_statements", corp_code, bsns_year, reprt_code_value, fs_div_value
        )

        # 캐시 조회
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug("캐시 히트 - financial_statements: %s/%s", corp_code, bsns_year)
            return FinancialStatementsCollection.model_validate(cached)

        # API 호출
        result = await self._client.get_financial_statements(
            corp_code, bsns_year, reprt_code, fs_div
        )

        # 캐시 저장
        await self._cache.set(
            cache_key,
            result.model_dump(),
            ttl=CacheTTL.FINANCIAL_STATEMENTS,
        )

        return result

    async def get_major_shareholders(
        self, corp_code: str
    ) -> list[DartMajorShareholder]:
        """최대주주 현황을 조회합니다 (캐시 적용).

        Args:
            corp_code: 고유번호 (8자리).

        Returns:
            최대주주 정보 리스트.
        """
        cache_key = self._make_key("shareholders", corp_code)

        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug("캐시 히트 - shareholders: %s", corp_code)
            return [DartMajorShareholder.model_validate(item) for item in cached]

        result = await self._client.get_major_shareholders(corp_code)

        await self._cache.set(
            cache_key,
            [item.model_dump() for item in result],
            ttl=CacheTTL.COMPANY_INFO,
        )

        return result

    async def get_dividend(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: ReportCode | str = ReportCode.ANNUAL,
    ) -> list[DartDividend]:
        """배당 현황을 조회합니다 (캐시 적용).

        Args:
            corp_code: 고유번호 (8자리).
            bsns_year: 사업연도.
            reprt_code: 보고서 코드.

        Returns:
            배당 정보 리스트.
        """
        reprt_code_value = reprt_code.value if isinstance(reprt_code, ReportCode) else reprt_code
        cache_key = self._make_key("dividend", corp_code, bsns_year, reprt_code_value)

        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug("캐시 히트 - dividend: %s/%s", corp_code, bsns_year)
            return [DartDividend.model_validate(item) for item in cached]

        result = await self._client.get_dividend(corp_code, bsns_year, reprt_code)

        await self._cache.set(
            cache_key,
            [item.model_dump() for item in result],
            ttl=CacheTTL.COMPANY_INFO,
        )

        return result
