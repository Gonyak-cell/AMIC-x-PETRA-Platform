"""Webhook 서비스 (T-I18).

> 마지막 수정: 2026-02-10 23:30:00

문서 생성 완료/실패 시 외부 웹훅을 호출한다.
3회 재시도, 5초 타임아웃.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WebhookService:
    """웹훅 호출 서비스."""

    @staticmethod
    async def trigger(
        url: str,
        payload: dict[str, Any],
        retries: int = 3,
        timeout: float = 5.0,
    ) -> bool:
        """웹훅 URL에 POST 요청을 전송한다.

        Args:
            url: 웹훅 URL.
            payload: JSON 페이로드.
            retries: 재시도 횟수.
            timeout: 타임아웃 (초).

        Returns:
            성공 여부.
        """
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                logger.info("웹훅 전송 성공: url=%s", url)
                return True
            except (httpx.HTTPError, Exception) as e:
                logger.warning(
                    "웹훅 전송 실패 (attempt %d/%d): %s",
                    attempt + 1,
                    retries,
                    e,
                )
        logger.error("웹훅 전송 최종 실패: url=%s", url)
        return False
