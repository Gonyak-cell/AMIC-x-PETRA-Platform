"""Redis 기반 Rate Limit 미들웨어.

인증 엔드포인트(로그인 등)에 대해 IP 기반 요청 빈도를 제한한다.
Redis가 사용 불가능한 경우 fakeredis로 폴백한다.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP 기반 요청 빈도 제한 미들웨어.

    지정된 경로에 대해 슬라이딩 윈도우 방식으로 요청 횟수를 제한한다.

    Args:
        app: ASGI 앱
        redis_url: Redis 연결 URL
        max_requests: 윈도우 내 최대 요청 수
        window_seconds: 윈도우 크기 (초)
        paths: 제한을 적용할 URL 경로 목록
    """

    def __init__(
        self,
        app,
        redis_url: str = "redis://localhost:6379/0",
        max_requests: int = 5,
        window_seconds: int = 60,
        paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.paths = paths or ["/api/v1/auth/login"]
        self._redis = None

    async def _get_redis(self):
        """Redis 클라이언트를 가져온다. 연결 실패 시 fakeredis로 폴백한다."""
        if self._redis is not None:
            return self._redis

        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            # 연결 테스트
            await self._redis.ping()
            logger.info("RateLimitMiddleware: Redis 연결 성공")
        except Exception:
            logger.warning("RateLimitMiddleware: Redis 연결 실패, fakeredis로 폴백")
            try:
                import fakeredis.aioredis

                self._redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
            except ImportError:
                logger.warning("RateLimitMiddleware: fakeredis 미설치, 인메모리 폴백 사용")
                self._redis = _InMemoryStore()

        return self._redis

    async def dispatch(self, request: Request, call_next):
        """요청을 처리하며, 제한 대상 경로인 경우 빈도를 검사한다."""
        # 제한 대상 경로가 아니면 바로 통과
        if request.url.path not in self.paths:
            return await call_next(request)

        # IP 주소 추출
        client_ip = request.client.host if request.client else "unknown"
        redis_key = f"rate_limit:{request.url.path}:{client_ip}"

        redis_client = await self._get_redis()

        try:
            current_count = await redis_client.get(redis_key)
            current_count = int(current_count) if current_count else 0

            if current_count >= self.max_requests:
                # TTL을 확인하여 Retry-After 헤더 설정
                ttl = await redis_client.ttl(redis_key)
                retry_after = max(ttl, 1) if ttl and ttl > 0 else self.window_seconds

                logger.warning(
                    "Rate limit 초과: IP=%s, path=%s, count=%d",
                    client_ip,
                    request.url.path,
                    current_count,
                )

                return JSONResponse(
                    status_code=429,
                    content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
                    headers={"Retry-After": str(retry_after)},
                )

            # 카운터 증가
            pipe = redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, self.window_seconds)
            await pipe.execute()

        except Exception:
            # Redis 오류 시 요청을 차단하지 않고 통과시킨다
            logger.exception("RateLimitMiddleware: Redis 오류 발생, 요청 통과")

        return await call_next(request)


class _InMemoryStore:
    """Redis/fakeredis가 모두 불가능할 때 사용하는 최소한의 인메모리 저장소."""

    _CLEANUP_INTERVAL = 60  # 60초마다 만료 키 정리

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._last_cleanup: float = time.time()

    def _maybe_cleanup(self) -> None:
        """주기적으로 만료된 키를 일괄 제거한다."""
        now = time.time()
        if now - self._last_cleanup < self._CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        expired = [k for k, v in self._data.items() if now > v["expires_at"]]
        for k in expired:
            del self._data[k]

    async def get(self, key: str) -> str | None:
        self._maybe_cleanup()
        entry = self._data.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires_at"]:
            del self._data[key]
            return None
        return str(entry["value"])

    async def ttl(self, key: str) -> int:
        entry = self._data.get(key)
        if entry is None:
            return -2
        remaining = int(entry["expires_at"] - time.time())
        return max(remaining, 0)

    async def incr(self, key: str) -> int:
        entry = self._data.get(key)
        if entry is None or time.time() > entry["expires_at"]:
            self._data[key] = {"value": 1, "expires_at": time.time() + 3600}
            return 1
        entry["value"] += 1
        return entry["value"]

    async def expire(self, key: str, seconds: int) -> bool:
        entry = self._data.get(key)
        if entry is not None:
            entry["expires_at"] = time.time() + seconds
            return True
        return False

    def pipeline(self) -> "_InMemoryPipeline":
        return _InMemoryPipeline(self)


class _InMemoryPipeline:
    """_InMemoryStore용 파이프라인 에뮬레이션."""

    def __init__(self, store: _InMemoryStore):
        self._store = store
        self._commands: list[tuple[str, tuple]] = []

    def incr(self, key: str):
        self._commands.append(("incr", (key,)))
        return self

    def expire(self, key: str, seconds: int):
        self._commands.append(("expire", (key, seconds)))
        return self

    async def execute(self) -> list:
        results = []
        for cmd, args in self._commands:
            method = getattr(self._store, cmd)
            result = await method(*args)
            results.append(result)
        self._commands.clear()
        return results
