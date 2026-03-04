"""FDDTemplateRenderer — FDD 전용 L1/L2/L3/L4 슬롯 조합 엔진.

SectionTemplate의 body에서:
  L1 — 부동문자 그대로 유지
  L2 — FDD 데이터 dict 필드로 직접 치환
  L3 — LLM이 생성한 텍스트로 치환
  L4 — 조건부 블록 삽입 (산업/데이터 조건)

최종 텍스트를 조합하여 반환한다.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

from app.services.report.slot_fill.loader import (
    BaseBlocks,
    ConditionalBlock,
    SectionTemplate,
)

logger = logging.getLogger(__name__)

# {{slot_name}} 패턴
_SLOT_PATTERN = re.compile(r"\{\{(\w+)\}\}")

# {{@block_name}} 패턴 (베이스 블록 참조)
_BLOCK_REF_PATTERN = re.compile(r"\{\{@(\w+)\}\}")


class FDDTemplateRenderer:
    """FDD 전용 부동문자 + 슬롯 조합 렌더러.

    Usage:
        renderer = FDDTemplateRenderer()
        text = renderer.render(
            template=section_template,
            data=fdd_data_dict,
            llm_slots={"qoe_summary": "...", "overall_assessment": "..."},
            industry="tech",
            base_blocks=base_blocks,
        )
    """

    def render(
        self,
        template: SectionTemplate,
        data: dict[str, Any],
        llm_slots: dict[str, str] | None = None,
        *,
        industry: str = "",
        base_blocks: BaseBlocks | None = None,
    ) -> str:
        """템플릿을 렌더링하여 최종 텍스트를 반환한다.

        Args:
            template: 섹션 템플릿.
            data: FDD 분석 데이터 dict.
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
                text,
                template.conditional_blocks,
                industry,
                data,
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
    # L2: FDD 데이터 dict 필드 직접 치환
    # -------------------------------------------------------------------

    def _resolve_l2_slots(
        self,
        text: str,
        template: SectionTemplate,
        data: dict[str, Any],
    ) -> str:
        """L2 슬롯을 FDD 데이터 dict 필드값으로 치환한다."""
        for slot_name, slot_def in template.l2_slots.items():
            value = self._resolve_data_path(data, slot_def.source)
            if value is None:
                value = slot_def.default
            else:
                value = self._format_l2_value(value, slot_def.format_spec)

            placeholder = "{{" + slot_name + "}}"
            text = text.replace(placeholder, str(value))

        return text

    @staticmethod
    def _resolve_data_path(data: dict[str, Any], path: str) -> Any:
        """dotted notation 경로로 dict 필드를 조회한다.

        Examples:
          "deal_name" -> data["deal_name"]
          "qoe.reported_ebitda" -> data["qoe"]["reported_ebitda"]
          "issues.0.title" -> data["issues"][0]["title"]
        """
        if not path:
            return None

        parts = path.split(".")
        current: Any = data
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

    @staticmethod
    def _format_l2_value(value: Any, format_spec: str) -> str:
        """L2 값을 지정 포맷으로 변환한다."""
        if value is None:
            return ""

        if format_spec == "currency_million":
            # 이미 포맷된 문자열이면 그대로 반환
            if isinstance(value, str):
                return value
            if isinstance(value, (int, float, Decimal)):
                return f"{int(value):,}"

        if format_spec == "currency_display":
            if isinstance(value, str):
                return f"{value} million KRW"
            if isinstance(value, (int, float, Decimal)):
                return f"{int(value):,} million KRW"

        if format_spec == "ratio":
            if isinstance(value, (int, float, Decimal)):
                return f"{float(value):.1%}"

        if format_spec == "count":
            if isinstance(value, (int, float)):
                return str(int(value))

        if format_spec == "count_items":
            if isinstance(value, (list, tuple)):
                return str(len(value))

        # list -> comma separated
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)

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
        data: dict[str, Any],
    ) -> str:
        """조건부 블록을 평가하고 텍스트에 삽입한다."""
        for block in blocks:
            if self._evaluate_condition(block.condition, industry, data):
                insert_placeholder = "{{" + block.insert_after + "}}"
                if insert_placeholder in text:
                    text = text.replace(
                        insert_placeholder,
                        insert_placeholder + " " + block.text,
                    )
                else:
                    text += "\n\n" + block.text

        return text

    @staticmethod
    def _evaluate_condition(
        condition: str,
        industry: str,
        data: dict[str, Any],
    ) -> bool:
        """L4 조건식을 평가한다.

        Supported conditions:
          - "industry == 'tech'"
          - "industry != 'general'"
          - "industry in ('tech', 'financial_services')"
          - "has_qoe", "has_nwc", "has_debt", "has_issues"
          - "adjustment_ratio_high"
          - "has_high_severity_issues"
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
                match = re.search(r"\(([^)]+)\)", condition)
                if match:
                    items = [s.strip().strip("'\"") for s in match.group(1).split(",")]
                    return industry in items

        # FDD 데이터 조건
        if condition == "has_qoe":
            return data.get("qoe") is not None
        if condition == "has_nwc":
            return data.get("nwc") is not None
        if condition == "has_debt":
            return data.get("debt") is not None
        if condition == "has_issues":
            return len(data.get("issues", [])) > 0
        if condition == "has_high_severity_issues":
            issues = data.get("issues", [])
            return any(i.get("severity") in ("critical", "high") for i in issues)
        if condition == "adjustment_ratio_high":
            qoe = data.get("qoe")
            if qoe and qoe.get("adjustment_ratio"):
                try:
                    return float(qoe["adjustment_ratio"]) > 0.15
                except (ValueError, TypeError):
                    pass
            return False

        logger.warning("Unrecognized L4 condition: %s", condition)
        return False

    # -------------------------------------------------------------------
    # Base refs / Cleanup
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
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" +\n", "\n", text)
        text = re.sub(r"  +", " ", text)
        return text.strip()
