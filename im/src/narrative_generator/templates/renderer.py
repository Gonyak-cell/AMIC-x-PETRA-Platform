"""TemplateRenderer — L1/L2/L3/L4 슬롯 조합 엔진.

> 마지막 수정: 2026-02-17

SectionTemplate의 body에서:
  L1 — 부동문자 그대로 유지
  L2 — IMDocumentData 필드로 직접 치환
  L3 — LLM이 생성한 텍스트로 치환
  L4 — 조건부 블록 삽입

최종 텍스트를 조합하여 반환한다.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.templates.loader import (
    BaseBlocks,
    ConditionalBlock,
    SectionTemplate,
)

logger = logging.getLogger(__name__)

# {{slot_name}} 패턴
_SLOT_PATTERN = re.compile(r"\{\{(\w+)\}\}")

# {{@block_name}} 패턴 (베이스 블록 참조)
_BLOCK_REF_PATTERN = re.compile(r"\{\{@(\w+)\}\}")


class TemplateRenderer:
    """부동문자 + 슬롯 조합 렌더러.

    Usage:
        renderer = TemplateRenderer()
        text = renderer.render(
            template=section_template,
            data=im_document_data,
            llm_slots={"company_intro": "...", "revenue_highlight": "..."},
            industry="tech",
            base_blocks=base_blocks,
        )
    """

    def render(
        self,
        template: SectionTemplate,
        data: IMDocumentData,
        llm_slots: dict[str, str] | None = None,
        *,
        industry: str = "",
        base_blocks: BaseBlocks | None = None,
    ) -> str:
        """템플릿을 렌더링하여 최종 텍스트를 반환한다.

        Args:
            template: 섹션 템플릿.
            data: IM 문서 통합 데이터.
            llm_slots: LLM이 채운 L3 슬롯 값 {슬롯명: 텍스트}.
            industry: 산업 식별자 (L4 조건부 블록 평가용).
            base_blocks: 공통 부동문자 블록 (_base.yaml).

        Returns:
            최종 렌더링된 텍스트.
        """
        llm_slots = llm_slots or {}
        text = template.body

        # Step 1: 베이스 블록 참조 치환 ({{@block_name}})
        if base_blocks:
            text = self._resolve_base_refs(text, base_blocks)

        # Step 2: L4 조건부 블록 삽입
        if template.conditional_blocks:
            text = self._apply_conditional_blocks(
                text, template.conditional_blocks, industry, data,
            )

        # Step 3: L2 단순 치환
        text = self._resolve_l2_slots(text, template, data)

        # Step 4: L3 LLM 슬롯 치환
        text = self._resolve_l3_slots(text, template, llm_slots)

        # Step 5: 미해결 슬롯 정리 (기본값 또는 빈 문자열)
        text = self._cleanup_unresolved(text, template)

        # Step 6: 여분 공백/줄바꿈 정리
        text = self._normalize_whitespace(text)

        return text

    # -------------------------------------------------------------------
    # L2: IMDocumentData 필드 직접 치환
    # -------------------------------------------------------------------

    def _resolve_l2_slots(
        self,
        text: str,
        template: SectionTemplate,
        data: IMDocumentData,
    ) -> str:
        """L2 슬롯을 IMDocumentData 필드값으로 치환한다."""
        for slot_name, slot_def in template.l2_slots.items():
            value = self._resolve_data_path(data, slot_def.source)
            if value is None:
                value = slot_def.default
            else:
                value = self._format_l2_value(value, slot_def.format_spec)

            placeholder = "{{" + slot_name + "}}"
            text = text.replace(placeholder, str(value))

        return text

    def _resolve_data_path(self, data: IMDocumentData, path: str) -> Any:
        """dotted notation 경로로 IMDocumentData 필드를 조회한다.

        예:
          "company_overview.established_date" → data.company_overview.established_date
          "contacts.0.name" → data.contacts[0].name (리스트 인덱싱 지원)
        """
        if not path:
            return None

        parts = path.split(".")
        current: Any = data
        for part in parts:
            if current is None:
                return None
            # 숫자면 리스트 인덱싱
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

    @staticmethod
    def _format_l2_value(value: Any, format_spec: str) -> str:
        """L2 값을 지정 포맷으로 변환한다."""
        if value is None:
            return ""

        if format_spec == "currency":
            if isinstance(value, (int, float)):
                if abs(value) >= 1e8:
                    return f"{value / 1e8:,.0f}억원"
                elif abs(value) >= 1e6:
                    return f"{value / 1e6:,.0f}백만원"
                return f"{value:,.0f}원"

        if format_spec == "percent":
            if isinstance(value, (int, float)):
                return f"{value:.1%}"

        if format_spec == "date":
            return str(value)

        if format_spec == "count":
            if isinstance(value, (int, float)):
                return f"{int(value):,}명"

        if format_spec == "comma":
            if isinstance(value, (int, float)):
                return f"{value:,}"

        # dict → "연도: 값" 형식
        if isinstance(value, dict):
            parts = []
            for k in sorted(value.keys()):
                v = value[k]
                if isinstance(v, (int, float)) and abs(v) >= 1e8:
                    parts.append(f"{k}년: {v / 1e8:,.1f}억원")
                elif isinstance(v, (int, float)):
                    parts.append(f"{k}년: {v:,.0f}")
                else:
                    parts.append(f"{k}년: {v}")
            return ", ".join(parts)

        # list → 쉼표 구분
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)

        # Enum → .value
        if hasattr(value, "value"):
            return str(value.value)

        return str(value)

    # -------------------------------------------------------------------
    # L3: LLM 슬롯 치환
    # -------------------------------------------------------------------

    @staticmethod
    def _resolve_l3_slots(
        text: str,
        template: SectionTemplate,
        llm_slots: dict[str, str],
    ) -> str:
        """L3 슬롯을 LLM 생성 텍스트로 치환한다."""
        for slot_name in template.l3_slots:
            value = llm_slots.get(slot_name, "")
            placeholder = "{{" + slot_name + "}}"
            text = text.replace(placeholder, value)
        return text

    # -------------------------------------------------------------------
    # L4: 조건부 블록 삽입
    # -------------------------------------------------------------------

    def _apply_conditional_blocks(
        self,
        text: str,
        blocks: list[ConditionalBlock],
        industry: str,
        data: IMDocumentData,
    ) -> str:
        """조건부 블록을 평가하고 텍스트에 삽입한다."""
        for block in blocks:
            if self._evaluate_condition(block.condition, industry, data):
                insert_placeholder = "{{" + block.insert_after + "}}"
                if insert_placeholder in text:
                    # insert_after 슬롯 바로 뒤에 삽입
                    text = text.replace(
                        insert_placeholder,
                        insert_placeholder + " " + block.text,
                    )
                else:
                    # 본문 끝에 추가
                    text += "\n\n" + block.text

        return text

    @staticmethod
    def _evaluate_condition(
        condition: str,
        industry: str,
        data: IMDocumentData,
    ) -> bool:
        """L4 조건식을 평가한다.

        간단한 조건식만 지원:
          - "industry == 'tech'"
          - "industry != 'general'"
          - "industry in ('tech', 'financial_services')"
          - "has_segment_revenue"
          - "has_deal_structure"
        """
        condition = condition.strip()

        # industry == 'xxx'
        if condition.startswith("industry"):
            if "==" in condition:
                target = condition.split("==")[1].strip().strip("'\"")
                return industry == target
            if "!=" in condition:
                target = condition.split("!=")[1].strip().strip("'\"")
                return industry != target
            if "in" in condition:
                # industry in ('tech', 'healthcare')
                match = re.search(r"\(([^)]+)\)", condition)
                if match:
                    items = [s.strip().strip("'\"") for s in match.group(1).split(",")]
                    return industry in items

        # has_xxx 플래그
        if condition == "has_segment_revenue":
            return data.segment_revenue is not None
        if condition == "has_deal_structure":
            return data.deal_structure is not None
        if condition == "has_market_data":
            return data.market_data is not None
        if condition == "has_valuation_data":
            return data.valuation_data is not None

        logger.warning("평가 불가능한 L4 조건: %s", condition)
        return False

    # -------------------------------------------------------------------
    # 베이스 블록 참조 / 정리
    # -------------------------------------------------------------------

    @staticmethod
    def _resolve_base_refs(text: str, base_blocks: BaseBlocks) -> str:
        """{{@block_name}} 참조를 베이스 블록 텍스트로 치환한다."""
        def _replacer(match: re.Match) -> str:
            block_name = match.group(1)
            return base_blocks.get(block_name, "")
        return _BLOCK_REF_PATTERN.sub(_replacer, text)

    @staticmethod
    def _cleanup_unresolved(text: str, template: SectionTemplate) -> str:
        """미해결 슬롯을 기본값 또는 빈 문자열로 치환한다."""
        def _replacer(match: re.Match) -> str:
            slot_name = match.group(1)
            slot_def = template.slots.get(slot_name)
            if slot_def and slot_def.default:
                return slot_def.default
            return ""
        return _SLOT_PATTERN.sub(_replacer, text)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """연속 공백/줄바꿈을 정리한다."""
        # 3개 이상 연속 줄바꿈 → 2개로
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 줄 끝 공백 제거
        text = re.sub(r" +\n", "\n", text)
        # 문장 내 연속 공백 → 단일 공백
        text = re.sub(r"  +", " ", text)
        return text.strip()
