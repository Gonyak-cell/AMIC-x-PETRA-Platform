"""TemplateLoader — LDD YAML 템플릿 로더 및 데이터 모델."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)

SlotLevel = Literal["L1", "L2", "L3", "L4"]
SlotType = Literal["sentence", "paragraph", "bullet_list", "number"]


@dataclass(frozen=True)
class SlotDefinition:
    """개별 슬롯 정의."""

    name: str
    level: SlotLevel
    source: str = ""
    slot_type: SlotType = "sentence"
    hint: str = ""
    max_tokens: int = 80
    data_keys: tuple[str, ...] = ()
    default: str = ""
    format_spec: str = ""

    @property
    def is_llm_slot(self) -> bool:
        return self.level == "L3"

    @property
    def is_data_slot(self) -> bool:
        return self.level == "L2"


@dataclass(frozen=True)
class ConditionalBlock:
    """조건부 부동문자 블록."""

    condition: str
    insert_after: str
    text: str


@dataclass
class SectionTemplate:
    """LDD 단일 섹션 템플릿."""

    section_id: str = ""
    version: str = "1.0"
    source_reference: str = ""
    slots: dict[str, SlotDefinition] = field(default_factory=dict)
    body: str = ""
    conditional_blocks: list[ConditionalBlock] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    section_preamble: dict[str, int] = field(default_factory=dict)

    @property
    def l2_slots(self) -> dict[str, SlotDefinition]:
        return {k: v for k, v in self.slots.items() if v.level == "L2"}

    @property
    def l3_slots(self) -> dict[str, SlotDefinition]:
        return {k: v for k, v in self.slots.items() if v.level == "L3"}


@dataclass
class BaseBlocks:
    """공통 부동문자 블록."""

    blocks: dict[str, str] = field(default_factory=dict)

    def get(self, name: str, default: str = "") -> str:
        return self.blocks.get(name, default)


class TemplateLoader:
    """YAML 템플릿을 로드한다."""

    def __init__(self, template_dir: str | Path) -> None:
        self._dir = Path(template_dir)

    def load_base(self) -> BaseBlocks:
        """_base.yaml을 로드한다."""
        path = self._dir / "_base.yaml"
        if not path.exists():
            logger.warning("_base.yaml not found: %s", path)
            return BaseBlocks()

        raw = self._read_yaml(path)
        blocks: dict[str, str] = {}
        for block in raw.get("blocks", []):
            name = block.get("name", "")
            text = block.get("text", "")
            if name:
                blocks[name] = text
        return BaseBlocks(blocks=blocks)

    def load_section(self, section_id: str) -> SectionTemplate | None:
        """개별 섹션 템플릿을 로드한다."""
        path = self._dir / f"{section_id}.yaml"
        if not path.exists():
            return None
        raw = self._read_yaml(path)
        return self._parse_template(raw)

    def load_all_sections(self) -> dict[str, SectionTemplate]:
        """디렉터리 내 모든 섹션 템플릿을 로드한다."""
        templates: dict[str, SectionTemplate] = {}
        for path in sorted(self._dir.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            raw = self._read_yaml(path)
            if raw:
                tpl = self._parse_template(raw)
                if tpl.section_id:
                    templates[tpl.section_id] = tpl
        return templates

    def load_industry_override(self, section_id: str, industry: str) -> SectionTemplate | None:
        """산업별 오버라이드 템플릿을 로드한다."""
        path = self._dir / "industry_variants" / industry / f"{section_id}.yaml"
        if not path.exists():
            return None
        raw = self._read_yaml(path)
        return self._parse_template(raw)

    def _read_yaml(self, path: Path) -> dict[str, Any]:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.error("YAML load failed: %s — %s", path, exc)
            return {}

    def _parse_template(self, raw: dict[str, Any]) -> SectionTemplate:
        slots: dict[str, SlotDefinition] = {}
        for slot_name, slot_raw in raw.get("slots", {}).items():
            if not isinstance(slot_raw, dict):
                continue
            data_keys = slot_raw.get("data_keys", [])
            if isinstance(data_keys, list):
                data_keys = tuple(data_keys)
            else:
                data_keys = ()

            slots[slot_name] = SlotDefinition(
                name=slot_name,
                level=slot_raw.get("level", "L1"),
                source=slot_raw.get("source", ""),
                slot_type=slot_raw.get("type", "sentence"),
                hint=slot_raw.get("hint", ""),
                max_tokens=slot_raw.get("max_tokens", 80),
                data_keys=data_keys,
                default=slot_raw.get("default", ""),
                format_spec=slot_raw.get("format", ""),
            )

        conditional_blocks: list[ConditionalBlock] = []
        for cb_raw in raw.get("conditional_blocks", []):
            if not isinstance(cb_raw, dict):
                continue
            conditional_blocks.append(
                ConditionalBlock(
                    condition=cb_raw.get("condition", ""),
                    insert_after=cb_raw.get("insert_after", ""),
                    text=cb_raw.get("text", ""),
                )
            )

        return SectionTemplate(
            section_id=raw.get("section_id", ""),
            version=raw.get("version", "1.0"),
            source_reference=raw.get("source_reference", ""),
            slots=slots,
            body=raw.get("body", ""),
            conditional_blocks=conditional_blocks,
            includes=raw.get("includes", []),
            section_preamble={
                str(k): int(v)
                for k, v in raw.get("section_preamble", {}).items()
                if isinstance(k, str) and isinstance(v, (int, float)) and int(v) > 0
            },
        )
