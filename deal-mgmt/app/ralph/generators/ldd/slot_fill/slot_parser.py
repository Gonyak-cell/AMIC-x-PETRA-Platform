"""SlotResponseParser — LDD LLM 슬롯 응답 파서."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SlotResponseParser:
    """LLM 응답에서 슬롯 값을 파싱한다."""

    def parse(self, response: str, expected_slots: list[str]) -> dict[str, str]:
        if not response or not expected_slots:
            return {}

        result = self._try_json_parse(response)
        if result and self._has_expected_keys(result, expected_slots):
            return self._sanitize(result, expected_slots)

        result = self._try_code_block_extract(response)
        if result and self._has_expected_keys(result, expected_slots):
            return self._sanitize(result, expected_slots)

        result = self._try_regex_extract(response, expected_slots)
        if result:
            return self._sanitize(result, expected_slots)

        if len(expected_slots) == 1:
            logger.warning("LDD slot parsing fallback: slot=%s", expected_slots[0])
            return {expected_slots[0]: response.strip()}

        logger.error(
            "LDD slot parsing failed: expected=%s, response_preview=%s",
            expected_slots,
            response[:200],
        )
        return {}

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
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_regex_extract(text: str, expected_slots: list[str]) -> dict[str, str] | None:
        result: dict[str, str] = {}
        for slot in expected_slots:
            quoted = rf'"{re.escape(slot)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(quoted, text, re.DOTALL)
            if match:
                result[slot] = match.group(1)
                continue

            loose = rf"{re.escape(slot)}\s*[:=]\s*(.+?)(?:\n|$)"
            match = re.search(loose, text)
            if match:
                result[slot] = match.group(1).strip().strip("'\"")

        return result or None

    @staticmethod
    def _has_expected_keys(result: dict[str, Any], expected_slots: list[str]) -> bool:
        return any(k in result for k in expected_slots)

    @staticmethod
    def _sanitize(result: dict[str, Any], expected_slots: list[str]) -> dict[str, str]:
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
