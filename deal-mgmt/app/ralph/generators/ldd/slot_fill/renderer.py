"""LDDTemplateRenderer — 부동문자 + slot-fill 조합 렌더러."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.ralph.generators.ldd.slot_fill.loader import BaseBlocks, ConditionalBlock, SectionTemplate

logger = logging.getLogger(__name__)

_SLOT_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_BLOCK_REF_PATTERN = re.compile(r"\{\{\s*@(\w+)\s*\}\}")


class LDDTemplateRenderer:
    """LDD 전용 slot-fill 렌더러."""

    def render(
        self,
        template: SectionTemplate,
        data: dict[str, Any],
        llm_slots: dict[str, str] | None = None,
        *,
        industry: str = "",
        base_blocks: BaseBlocks | None = None,
    ) -> str:
        llm_slots = llm_slots or {}
        text = template.body

        if base_blocks:
            text = self._resolve_base_refs(text, base_blocks)

        if template.conditional_blocks:
            text = self._apply_conditional_blocks(
                text,
                template.conditional_blocks,
                industry,
                data,
                base_blocks=base_blocks,
            )

        text = self._resolve_l2_slots(text, template, data)
        text = self._resolve_l3_slots(text, template, llm_slots)
        text = self._cleanup_unresolved(text, template)
        text = self._normalize_whitespace(text)
        return text

    def _resolve_l2_slots(self, text: str, template: SectionTemplate, data: dict[str, Any]) -> str:
        for slot_name, slot_def in template.l2_slots.items():
            value = self._resolve_data_path(data, slot_def.source)
            if value is None:
                value = slot_def.default
            else:
                value = self._format_l2_value(value, slot_def.format_spec)
            pattern = re.compile(r"\{\{\s*" + re.escape(slot_name) + r"\s*\}\}")
            text = pattern.sub(str(value), text)
        return text

    @staticmethod
    def _resolve_data_path(data: dict[str, Any], path: str) -> Any:
        if not path:
            return None

        current: Any = data
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

    @staticmethod
    def _format_l2_value(value: Any, format_spec: str) -> str:
        if value is None:
            return ""
        if format_spec == "count_items" and isinstance(value, (list, tuple)):
            return str(len(value))
        if format_spec == "comma_list" and isinstance(value, list):
            return ", ".join(str(v) for v in value if v)
        if format_spec == "confidence_pct":
            try:
                return f"{float(value) * 100:.0f}%"
            except (TypeError, ValueError):
                return str(value)
        if isinstance(value, list):
            return ", ".join(str(v) for v in value if v)
        return str(value)

    @staticmethod
    def _resolve_l3_slots(text: str, template: SectionTemplate, llm_slots: dict[str, str]) -> str:
        for slot_name in template.l3_slots:
            pattern = re.compile(r"\{\{\s*" + re.escape(slot_name) + r"\s*\}\}")
            text = pattern.sub(llm_slots.get(slot_name, ""), text)
        return text

    def _apply_conditional_blocks(
        self,
        text: str,
        blocks: list[ConditionalBlock],
        industry: str,
        data: dict[str, Any],
        *,
        base_blocks: BaseBlocks | None = None,
    ) -> str:
        for block in blocks:
            if self._evaluate_condition(block.condition, industry, data):
                block_text = block.text
                if base_blocks:
                    block_text = self._resolve_base_refs(block_text, base_blocks)
                insert_pattern = re.compile(r"\{\{\s*" + re.escape(block.insert_after) + r"\s*\}\}")
                match = insert_pattern.search(text)
                if match:
                    text = insert_pattern.sub(match.group(0) + " " + block_text, text, count=1)
                else:
                    text += "\n\n" + block_text
        return text

    def _evaluate_condition(self, condition: str, industry: str, data: dict[str, Any]) -> bool:
        condition = condition.strip()
        if not condition:
            return False

        if condition.startswith("industry"):
            return self._evaluate_comparison(condition, {"industry": industry, **data})

        if any(op in condition for op in ("==", "!=", ">=", "<=", ">", "<", " in ")):
            return self._evaluate_comparison(condition, data)

        return bool(self._resolve_data_path(data, condition))

    def _evaluate_comparison(self, condition: str, data: dict[str, Any]) -> bool:
        in_match = re.fullmatch(r"([\w.]+)\s+in\s+\(([^)]+)\)", condition)
        if in_match:
            key = in_match.group(1)
            candidates = [part.strip().strip("'\"") for part in in_match.group(2).split(",")]
            return str(self._resolve_data_path(data, key)) in candidates

        for op in ("==", "!=", ">=", "<=", ">", "<"):
            if op not in condition:
                continue
            left, right = [part.strip() for part in condition.split(op, 1)]
            left_value = self._resolve_data_path(data, left)
            right_value = self._parse_literal(right)
            try:
                if op == "==":
                    return left_value == right_value
                if op == "!=":
                    return left_value != right_value
                if op == ">=":
                    return float(left_value) >= float(right_value)
                if op == "<=":
                    return float(left_value) <= float(right_value)
                if op == ">":
                    return float(left_value) > float(right_value)
                if op == "<":
                    return float(left_value) < float(right_value)
            except (TypeError, ValueError):
                return False

        logger.warning("Unrecognized LDD L4 condition: %s", condition)
        return False

    @staticmethod
    def _parse_literal(raw: str) -> Any:
        if raw.lower() == "true":
            return True
        if raw.lower() == "false":
            return False
        if raw.lower() == "none":
            return None
        if raw.startswith(("'", '"')) and raw.endswith(("'", '"')):
            return raw[1:-1]
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw

    @staticmethod
    def _resolve_base_refs(text: str, base_blocks: BaseBlocks) -> str:
        def _replacer(match: re.Match) -> str:
            return base_blocks.get(match.group(1), "")

        return _BLOCK_REF_PATTERN.sub(_replacer, text)

    @staticmethod
    def _cleanup_unresolved(text: str, template: SectionTemplate) -> str:
        def _replacer(match: re.Match) -> str:
            slot_name = match.group(1)
            slot_def = template.slots.get(slot_name)
            if slot_def and slot_def.default:
                return slot_def.default
            return ""

        return _SLOT_PATTERN.sub(_replacer, text)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" +\n", "\n", text)
        text = re.sub(r"  +", " ", text)
        return text.strip()
