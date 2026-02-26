"""LLM 응답에서 JSON을 추출하는 공통 유틸리티."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_UNSET = object()


def _repair_json(text: str) -> str:
    """잘린/불완전한 JSON 문자열을 복구한다.

    Gemini 등 일부 모델은 JSON 응답이 잘리거나 trailing comma가 포함됨.
    """
    s = text.strip()

    # 1) trailing comma 제거: ,} → } / ,] → ]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # 2) 잘린 JSON 복구: 열린 괄호/중괄호를 닫아줌
    open_braces = s.count("{") - s.count("}")
    open_brackets = s.count("[") - s.count("]")

    # 잘린 문자열 닫기: 마지막 열린 따옴표 확인
    in_string = False
    escaped = False
    for ch in s:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string

    if in_string:
        s += '"'

    # 열린 괄호 닫기
    if open_braces > 0:
        s += "}" * open_braces
    if open_brackets > 0:
        s += "]" * open_brackets

    return s


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

    text = text.strip()

    # 1차: 직접 파싱 시도
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2차: JSON 복구 후 재시도
    try:
        repaired = _repair_json(text)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 3차: 텍스트에서 첫 번째 JSON 객체/배열 추출 시도
    for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                try:
                    return json.loads(_repair_json(m.group()))
                except json.JSONDecodeError:
                    pass

    # 최종 실패
    ctx = f" ({context})" if context else ""
    logger.warning("JSON 파싱 실패%s: 원문 %d자", ctx, len(raw))
    if fallback is not _UNSET:
        return fallback
    raise json.JSONDecodeError(f"JSON 추출 실패{ctx}", text, 0)
