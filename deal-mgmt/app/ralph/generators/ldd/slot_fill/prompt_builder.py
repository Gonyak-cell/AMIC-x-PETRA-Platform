"""LDD slot-fill 전용 프롬프트 빌더."""

from __future__ import annotations

from typing import Any

from app.ralph.generators.ldd.slot_fill.loader import SectionTemplate, SlotDefinition

LDD_SLOT_FILL_SYSTEM_PREAMBLE = (
    "## 역할\n"
    "당신은 이미 작성된 법률실사(LDD) 보고서의 빈 슬롯만 채우는 전문 작성자입니다.\n\n"
    "## 규칙\n"
    "1. 반드시 JSON 형식으로만 응답하십시오.\n"
    "2. 제공된 데이터와 문맥만 사용하고 새로운 사실을 만들지 마십시오.\n"
    "3. 한국어 법률실사 보고서 톤으로 간결하고 단정하게 작성하십시오.\n"
    "4. 슬롯 타입을 준수하십시오.\n"
    "5. 기존 부동문자 톤과 자연스럽게 이어지도록 작성하십시오.\n"
)


class LDDSlotFillPromptBuilder:
    """LDD L3 슬롯 채우기용 프롬프트를 조립한다."""

    def build_system_prompt(self, *, industry_context: str = "") -> str:
        parts = [LDD_SLOT_FILL_SYSTEM_PREAMBLE]
        if industry_context:
            parts.append(f"\n## 산업 컨텍스트\n{industry_context}\n")
        return "\n".join(parts)

    def build_user_prompt(self, template: SectionTemplate, data: dict[str, Any], *, industry_context: str = "") -> str:
        l3_slots = template.l3_slots
        if not l3_slots:
            return ""

        parts: list[str] = []
        parts.append(
            "## 보고서 정보\n"
            f"- 대상회사: {data.get('report', {}).get('target_company', '대상회사')}\n"
            f"- 보고서유형: {data.get('report', {}).get('report_type', 'FULL')}\n"
            f"- 섹션: {data.get('section', {}).get('title', '')}\n"
            f"- 항목: {data.get('item', {}).get('name', '')}"
        )

        parts.append(f"\n## 부동문자 맥락 (section: {template.section_id})")
        parts.append(self._extract_body_context(template.body))

        parts.append("\n## 채워야 할 슬롯")
        for idx, (slot_name, slot_def) in enumerate(l3_slots.items(), 1):
            slot_data = self._extract_slot_data(slot_def, data)
            parts.append(
                f"\n### 슬롯 {idx}: {slot_name}\n"
                f"- 타입: {slot_def.slot_type}\n"
                f"- 최대 토큰: {slot_def.max_tokens}\n"
                f"- 힌트: {slot_def.hint}"
            )
            if slot_data:
                parts.append("- 관련 데이터:")
                for key, value in slot_data.items():
                    parts.append(f"  - {key}: {value}")

        slot_keys = list(l3_slots.keys())
        example_json = ", ".join(f'"{k}": "..."' for k in slot_keys)
        parts.append(f"\n## 응답 형식\nJSON only:\n{{{example_json}}}")

        if industry_context:
            parts.append(f"\n## 추가 산업 컨텍스트\n{industry_context}")

        return "\n".join(parts)

    @staticmethod
    def _extract_body_context(body: str, max_chars: int = 500) -> str:
        if len(body) <= max_chars:
            return body
        return body[:max_chars] + "..."

    @staticmethod
    def _extract_slot_data(slot_def: SlotDefinition, data: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for data_key in slot_def.data_keys:
            value = _resolve_nested(data, data_key)
            if value is None:
                continue
            if isinstance(value, dict):
                result[data_key] = "; ".join(f"{k}: {v}" for k, v in value.items())
            elif isinstance(value, list):
                result[data_key] = str(value[:5]) if len(value) <= 5 else f"[{len(value)} items] {value[:3]}..."
            else:
                result[data_key] = str(value)
        return result


def _resolve_nested(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
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
