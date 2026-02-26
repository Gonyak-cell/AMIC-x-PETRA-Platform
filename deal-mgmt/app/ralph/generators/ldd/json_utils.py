"""LLM 응답에서 JSON을 추출하는 공통 유틸리티."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_UNSET = object()


def extract_json(
    raw: str,
    *,
    context: str = "",
    fallback: Any = _UNSET,
) -> Any:
    """LLM 응답 문자열에서 JSON 블록을 추출하여 파싱한다.

    Args:
        raw: LLM 원본 응답 텍스트.
        context: 파싱 실패 시 경고 로그에 포함할 컨텍스트 문자열.
        fallback: 파싱 실패 시 반환할 기본값.
            지정하지 않으면 JSONDecodeError를 그대로 raise한다.

    Returns:
        파싱된 JSON 객체(dict/list 등).
        파싱 실패 시 fallback이 지정되어 있으면 해당 값을 반환.
    """
    text = raw.strip()

    # ```json ... ``` 또는 ``` ... ``` 블록 추출
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        ctx = f" ({context})" if context else ""
        logger.warning("JSON 파싱 실패%s: %s", ctx, exc)
        if fallback is not _UNSET:
            return fallback
        raise
