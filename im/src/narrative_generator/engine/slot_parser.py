"""SlotResponseParser — LLM 슬롯 채우기 응답 파서.

> 마지막 수정: 2026-02-17

LLM이 JSON 형식으로 응답한 슬롯 값을 파싱하고 검증한다.
3단계 폴백: JSON 파싱 → regex 추출 → 단일 슬롯 매핑.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SlotResponseParser:
    """LLM 응답에서 슬롯 값을 추출한다.

    Usage:
        parser = SlotResponseParser()
        slots = parser.parse(
            response='{"company_intro": "...", "revenue_highlight": "..."}',
            expected_slots=["company_intro", "revenue_highlight"],
        )
    """

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

        Args:
            response: LLM 응답 원문.
            expected_slots: 기대하는 슬롯 이름 리스트.

        Returns:
            {슬롯명: 텍스트} 딕셔너리.
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
                "JSON 파싱 실패, 단일 슬롯 폴백: slot=%s", expected_slots[0],
            )
            return {expected_slots[0]: response.strip()}

        logger.error(
            "슬롯 파싱 완전 실패: expected=%s, response_preview=%s",
            expected_slots,
            response[:200],
        )
        return {}

    # -------------------------------------------------------------------
    # 파싱 전략
    # -------------------------------------------------------------------

    @staticmethod
    def _try_json_parse(text: str) -> dict[str, Any] | None:
        """표준 JSON 파싱을 시도한다."""
        text = text.strip()
        # JSON 객체 부분만 추출
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_code_block_extract(text: str) -> dict[str, Any] | None:
        """```json ... ``` 코드 블록에서 JSON을 추출한다."""
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
        """키-값 패턴으로 슬롯 값을 추출한다.

        "slot_name": "value" 패턴을 찾는다.
        """
        result: dict[str, str] = {}
        for slot in expected_slots:
            # "slot_name": "value" 또는 "slot_name": 'value'
            pattern = rf'"{re.escape(slot)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                result[slot] = match.group(1)
                continue

            # slot_name: value (줄 단위)
            pattern = rf"{re.escape(slot)}\s*[:=]\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text)
            if match:
                result[slot] = match.group(1).strip().strip("'\"")

        return result if result else None

    # -------------------------------------------------------------------
    # 검증 / 정제
    # -------------------------------------------------------------------

    @staticmethod
    def _has_expected_keys(
        result: dict[str, Any],
        expected_slots: list[str],
    ) -> bool:
        """결과에 기대 슬롯 키가 포함되어 있는지 확인한다."""
        return any(k in result for k in expected_slots)

    @staticmethod
    def _sanitize(
        result: dict[str, Any],
        expected_slots: list[str],
    ) -> dict[str, str]:
        """결과를 정제하여 문자열 값만 반환한다."""
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
