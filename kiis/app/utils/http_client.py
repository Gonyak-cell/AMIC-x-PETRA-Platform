import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
BACKOFF_BASE = 2.0


class AsyncHTTPClient:
    """재시도 및 exponential backoff를 지원하는 비동기 HTTP 클라이언트"""

    def __init__(
        self,
        base_url: str = "",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._headers = headers or {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers=self._headers,
                follow_redirects=True,
            )
        return self._client

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
    ) -> httpx.Response:
        client = await self._get_client()
        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                )
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                last_exception = e
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
                    raise
                wait_time = BACKOFF_BASE**attempt
                logger.warning(
                    "Request failed (attempt %d/%d): %s. Retrying in %.1fs",
                    attempt + 1,
                    self.max_retries,
                    str(e),
                    wait_time,
                )
                await asyncio.sleep(wait_time)

        raise last_exception  # type: ignore[misc]

    async def get(self, url: str, *, params: dict | None = None) -> httpx.Response:
        return await self.request("GET", url, params=params)

    async def post(self, url: str, *, json: dict | None = None, data: dict | None = None) -> httpx.Response:
        return await self.request("POST", url, json=json, data=data)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
