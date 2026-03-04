"""FDDSlotFillPromptBuilder — FDD 슬롯 채우기 전용 프롬프트 빌더.

YAML 템플릿의 L3 슬롯만 LLM에 요청하는 FDD 특화 프롬프트를 조립한다.
기존 자유 생성 방식과 달리, JSON 형태로 슬롯별 짧은 텍스트만 생성한다.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.report.slot_fill.loader import SectionTemplate, SlotDefinition

logger = logging.getLogger(__name__)

FDD_SLOT_FILL_SYSTEM_PREAMBLE = (
    "## Role\n"
    "You fill empty slots in a pre-written Financial Due Diligence report. "
    "Each slot requires a short, focused piece of text.\n\n"
    "## Rules\n"
    "1. Respond ONLY in JSON format. No other text.\n"
    "2. Reference ONLY the provided data — NEVER invent or calculate numbers.\n"
    "3. Write in English. Use 'million KRW' for currency amounts.\n"
    "4. Maintain professional FDD tone: objective, concise, data-driven.\n"
    "5. Follow slot type constraints:\n"
    "   - sentence: 1-2 sentences\n"
    "   - paragraph: 2-4 sentences\n"
    "   - bullet_list: '- ' prefixed items\n"
    "   - number: numeric expression\n"
    "6. Match the surrounding boilerplate text tone and style.\n"
    "7. Do NOT use phrases like 'calculated', 'computed', or 'sum is'. "
    "Describe already-computed results; do not attempt calculations.\n"
)


class FDDSlotFillPromptBuilder:
    """FDD L3 슬롯 채우기 전용 프롬프트를 조립한다.

    Usage:
        builder = FDDSlotFillPromptBuilder()
        system = builder.build_system_prompt(industry_context="...")
        user = builder.build_user_prompt(template, fdd_data)
    """

    def build_system_prompt(self, *, industry_context: str = "") -> str:
        """슬롯 채우기용 시스템 프롬프트를 조립한다."""
        parts = [FDD_SLOT_FILL_SYSTEM_PREAMBLE]
        if industry_context:
            parts.append(f"\n## Industry Context\n{industry_context}\n")
        return "\n".join(parts)

    def build_user_prompt(
        self,
        template: SectionTemplate,
        data: dict[str, Any],
    ) -> str:
        """슬롯 채우기용 유저 프롬프트를 조립한다.

        Prompt structure:
        1. Deal basic info
        2. Boilerplate context (body preview)
        3. Per-slot instructions (hint + relevant data + max_tokens)
        4. JSON response format
        """
        l3_slots = template.l3_slots
        if not l3_slots:
            return ""

        parts: list[str] = []

        # 1. Deal info
        deal_name = data.get("deal_name", "N/A")
        industry = data.get("industry_name", "N/A")
        parts.append(
            f"## Deal Information\n- Deal: {deal_name}\n- Industry: {industry}"
        )

        # 2. Boilerplate context
        parts.append(f"\n## Boilerplate Context (section: {template.section_id})")
        body_preview = self._extract_body_context(template.body)
        parts.append(body_preview)

        # 3. Per-slot instructions
        parts.append("\n## Slots to Fill")
        for i, (slot_name, slot_def) in enumerate(l3_slots.items(), 1):
            slot_data = self._extract_slot_data(slot_def, data)
            parts.append(
                f"\n### Slot {i}: {slot_name}\n"
                f"- Type: {slot_def.slot_type}\n"
                f"- Max tokens: {slot_def.max_tokens}\n"
                f"- Hint: {slot_def.hint}"
            )
            if slot_data:
                parts.append("- Relevant data:")
                for key, value in slot_data.items():
                    parts.append(f"  - {key}: {value}")

        # 4. JSON response format
        slot_keys = list(l3_slots.keys())
        example_json = ", ".join(f'"{k}": "..."' for k in slot_keys)
        parts.append(
            f"\n## Response Format\nRespond with JSON only:\n{{{example_json}}}"
        )

        return "\n".join(parts)

    # -------------------------------------------------------------------
    # Internal
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
        data: dict[str, Any],
    ) -> dict[str, str]:
        """슬롯의 data_keys에 따라 관련 데이터를 추출한다."""
        result: dict[str, str] = {}
        for data_key in slot_def.data_keys:
            value = _resolve_nested(data, data_key)
            if value is None:
                continue

            if isinstance(value, dict):
                # Flatten dict for display
                items = []
                for k, v in value.items():
                    items.append(f"{k}: {v}")
                result[data_key] = "; ".join(items)
            elif isinstance(value, list):
                if len(value) <= 5:
                    result[data_key] = str(value)
                else:
                    result[data_key] = f"[{len(value)} items] " + str(value[:3]) + "..."
            elif isinstance(value, float):
                if abs(value) < 1:
                    result[data_key] = f"{value:.1%}"
                else:
                    result[data_key] = f"{value:,.1f}"
            else:
                result[data_key] = str(value)

        return result


def _resolve_nested(obj: Any, path: str) -> Any:
    """dotted notation으로 중첩 dict/객체의 필드를 조회한다."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if part.isdigit():
            idx = int(part)
            if isinstance(current, (list, tuple)) and idx < len(current):
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current
