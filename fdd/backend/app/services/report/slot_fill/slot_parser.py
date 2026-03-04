"""SlotResponseParser — LLM 슬롯 채우기 응답 파서.

LLM이 JSON 형식으로 응답한 슬롯 값을 파싱하고 검증한다.
3단계 폴백: JSON 파싱 -> regex 추출 -> 단일 슬롯 매핑.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SlotResponseParser:
    """LLM 응답에서 슬롯 값을 추출한다."""

    def parse(
        self,
        response: str,
        expected_slots: list[str],
    ) -> dict[str, str]:
        """LLM 응답을 파싱하여 슬롯 값 딕셔너리를 반환한다.

        3단계 폴백:
        1. 표준 JSON 파싱
        2. JSON 블록 추출 (```json ... ```)
        3. 키-값 regex 추출
        """
        if not response or not expected_slots:
            return {}

        # Stage 1: 표준 JSON
        result = self._try_json_parse(response)
        if result and self._has_expected_keys(result, expected_slots):
            return self._sanitize(result, expected_slots)

        # Stage 2: JSON 코드 블록 추출
        result = self._try_code_block_extract(response)
        if result and self._has_expected_keys(result, expected_slots):
            return self._sanitize(result, expected_slots)

        # Stage 3: regex 키-값 추출
        result = self._try_regex_extract(response, expected_slots)
        if result:
            return self._sanitize(result, expected_slots)

        # 최후 폴백: 단일 슬롯이면 전체 응답 매핑
        if len(expected_slots) == 1:
            logger.warning(
                "JSON parse failed, single-slot fallback: slot=%s",
                expected_slots[0],
            )
            return {expected_slots[0]: response.strip()}

        logger.error(
            "Slot parsing failed completely: expected=%s, response_preview=%s",
            expected_slots,
            response[:200],
        )
        return {}

    # -------------------------------------------------------------------
    # Parsing strategies
    # -------------------------------------------------------------------

    @staticmethod
    def _try_json_parse(text: str) -> dict[str, Any] | None:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_code_block_extract(text: str) -> dict[str, Any] | None:
        pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_regex_extract(
        text: str,
        expected_slots: list[str],
    ) -> dict[str, str] | None:
        result: dict[str, str] = {}
        for slot in expected_slots:
            pattern = rf'"{re.escape(slot)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                result[slot] = match.group(1)
                continue

            pattern = rf"{re.escape(slot)}\s*[:=]\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text)
            if match:
                result[slot] = match.group(1).strip().strip("'\"")

        return result if result else None

    # -------------------------------------------------------------------
    # Validation / Sanitization
    # -------------------------------------------------------------------

    @staticmethod
    def _has_expected_keys(
        result: dict[str, Any],
        expected_slots: list[str],
    ) -> bool:
        return any(k in result for k in expected_slots)

    @staticmethod
    def _sanitize(
        result: dict[str, Any],
        expected_slots: list[str],
    ) -> dict[str, str]:
        sanitized: dict[str, str] = {}
        for slot in expected_slots:
            value = result.get(slot)
            if value is None:
                continue
            if isinstance(value, str):
                sanitized[slot] = value.strip()
            elif isinstance(value, list):
                sanitized[slot] = "\n".join(f"- {v}" for v in value)
            else:
                sanitized[slot] = str(value)
        return sanitized
