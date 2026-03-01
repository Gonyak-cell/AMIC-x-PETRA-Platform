"""SlotFillPromptBuilder — 슬롯 채우기 전용 프롬프트 빌더.

> 마지막 수정: 2026-02-17

YAML 템플릿의 L3 슬롯만 LLM에 요청하는 특화된 프롬프트를 조립한다.
기존 자유 생성 방식과 달리, JSON 형태로 슬롯별 짧은 텍스트만 생성한다.
"""

from __future__ import annotations

import logging
from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.prompts.base import (
    _format_financial_dict,
    _format_value,
)
from src.narrative_generator.templates.loader import SectionTemplate, SlotDefinition

logger = logging.getLogger(__name__)

SLOT_FILL_SYSTEM_PREAMBLE = (
    "## 역할\n"
    "당신은 이미 작성된 Investment Memorandum(IM) 문서의 빈 슬롯을 채우는 "
    "전문 작성자입니다.\n\n"
    "## 핵심 규칙\n"
    "1. 반드시 JSON 형식으로만 응답하십시오. 다른 텍스트를 포함하지 마십시오.\n"
    "2. 각 슬롯의 힌트와 최대 토큰 수를 준수하십시오.\n"
    "3. 모든 수치는 반드시 제공된 데이터에서만 인용하십시오.\n"
    "4. 금액은 '억원' 단위, 비율은 소수점 첫째자리 %로 표기하십시오.\n"
    "5. 한국어로 작성하되, 금융 전문 용어는 영문 약어를 병기하십시오.\n"
    "6. 부동문자(고정 텍스트) 맥락에 자연스럽게 이어지는 톤으로 작성하십시오.\n"
    "7. 슬롯 타입에 맞게 작성하십시오:\n"
    "   - sentence: 1~2문장\n"
    "   - paragraph: 2~4문장\n"
    "   - bullet_list: '- ' 접두사 항목 나열\n"
    "   - number: 숫자 또는 수치 표현\n"
)


class SlotFillPromptBuilder:
    """L3 슬롯 채우기 전용 프롬프트를 조립한다.

    Usage:
        builder = SlotFillPromptBuilder()
        system = builder.build_system_prompt(industry_context="SaaS 특화...")
        user = builder.build_user_prompt(template, data, industry_context)
    """

    def build_system_prompt(self, *, industry_context: str = "") -> str:
        """슬롯 채우기용 시스템 프롬프트를 조립한다.

        Args:
            industry_context: 산업별 추가 컨텍스트.

        Returns:
            시스템 프롬프트 문자열.
        """
        parts = [SLOT_FILL_SYSTEM_PREAMBLE]
        if industry_context:
            parts.append(f"\n## 산업 컨텍스트\n{industry_context}\n")
        return "\n".join(parts)

    def build_user_prompt(
        self,
        template: SectionTemplate,
        data: IMDocumentData,
        *,
        industry_context: str = "",
    ) -> str:
        """슬롯 채우기용 유저 프롬프트를 조립한다.

        프롬프트 구조:
        1. 기업 기본 정보
        2. 부동문자 맥락 (body에서 {{slot}} 주변 텍스트)
        3. 각 L3 슬롯별 요청 (힌트 + 관련 데이터 + 맥스 토큰)
        4. JSON 응답 형식 지시

        Args:
            template: 섹션 템플릿.
            data: IM 문서 통합 데이터.
            industry_context: 산업별 컨텍스트.

        Returns:
            유저 프롬프트 문자열.
        """
        l3_slots = template.l3_slots
        if not l3_slots:
            return ""

        parts: list[str] = []

        # 1. 기업 기본 정보
        parts.append(f"## 기업 정보\n- 기업명: {data.company_name_kr}")
        if data.company_name_en:
            parts.append(f"- 영문명: {data.company_name_en}")

        # 2. 부동문자 맥락
        parts.append(f"\n## 부동문자 맥락 (섹션: {template.section_id})")
        body_preview = self._extract_body_context(template.body)
        parts.append(body_preview)

        # 3. 슬롯별 요청
        parts.append("\n## 채워야 할 슬롯")
        for i, (slot_name, slot_def) in enumerate(l3_slots.items(), 1):
            slot_data = self._extract_slot_data(slot_def, data)
            parts.append(
                f"\n### 슬롯 {i}: {slot_name}\n"
                f"- 타입: {slot_def.slot_type}\n"
                f"- 최대 토큰: {slot_def.max_tokens}\n"
                f"- 힌트: {slot_def.hint}"
            )
            if slot_data:
                parts.append("- 관련 데이터:")
                for key, value in slot_data.items():
                    parts.append(f"  - {key}: {value}")

        # 4. JSON 응답 형식
        slot_keys = list(l3_slots.keys())
        example_json = ", ".join(f'"{k}": "..."' for k in slot_keys)
        parts.append(
            f"\n## 응답 형식\n"
            f"다음 JSON 형식으로만 응답하십시오:\n"
            f"{{{example_json}}}"
        )

        return "\n".join(parts)

    # -------------------------------------------------------------------
    # 내부 메서드
    # -------------------------------------------------------------------

    @staticmethod
    def _extract_body_context(body: str, max_chars: int = 500) -> str:
        """body에서 슬롯 주변 맥락을 추출한다."""
        if len(body) <= max_chars:
            return body
        return body[:max_chars] + "..."

    @staticmethod
    def _extract_slot_data(
        slot_def: SlotDefinition,
        data: IMDocumentData,
    ) -> dict[str, str]:
        """슬롯의 data_keys에 따라 관련 데이터를 추출한다."""
        result: dict[str, str] = {}
        for data_key in slot_def.data_keys:
            value = _resolve_nested(data, data_key)
            if value is None:
                continue

            # 재무 데이터 (dict) → 포맷팅
            if isinstance(value, dict) and all(
                isinstance(v, (int, float)) for v in value.values()
            ):
                result[data_key] = _format_financial_dict(value)
            elif isinstance(value, dict):
                result[data_key] = _format_value(value)
            elif isinstance(value, list):
                result[data_key] = _format_value(value)
            elif isinstance(value, float):
                if abs(value) < 1:
                    result[data_key] = f"{value:.1%}"
                else:
                    result[data_key] = f"{value:,.1f}"
            else:
                result[data_key] = str(value)

        return result


def _resolve_nested(obj: Any, path: str) -> Any:
    """dotted notation으로 중첩 객체의 필드를 조회한다."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current
