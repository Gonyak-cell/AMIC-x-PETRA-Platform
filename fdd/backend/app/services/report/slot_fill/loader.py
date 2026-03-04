"""TemplateLoader — YAML 템플릿 로딩 및 데이터 모델.

YAML 파일에서 SectionTemplate을 로드하고, 슬롯 정의(SlotDefinition)와
조건부 블록(ConditionalBlock)을 파싱한다.
"""

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
    """개별 슬롯 정의.

    Attributes:
        name: 슬롯 이름 (YAML key).
        level: L1(고정) / L2(단순 치환) / L3(LLM 생성) / L4(조건부).
        source: L2 슬롯의 데이터 필드 경로 (dotted notation).
        slot_type: L3 슬롯의 출력 형태.
        hint: L3 슬롯의 LLM 가이드 힌트.
        max_tokens: L3 슬롯의 최대 토큰 수.
        data_keys: L3 슬롯이 참조할 데이터 필드 경로 리스트.
        default: 데이터 없을 때 기본값.
        format_spec: L2 슬롯의 포맷 지정 (예: "currency_million", "ratio").
    """

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
    """L4 조건부 블록.

    Attributes:
        condition: 조건식 (예: "industry == 'tech'").
        insert_after: 이 슬롯 뒤에 삽입.
        text: 삽입할 부동문자 텍스트 ({{slot}} 포함 가능).
    """

    condition: str
    insert_after: str
    text: str


@dataclass
class SectionTemplate:
    """하나의 FDD 섹션 템플릿.

    Attributes:
        section_id: 섹션 식별자 (executive_summary, qoe_analysis 등).
        version: 템플릿 버전.
        source_reference: 참조 보고서 출처.
        slots: 슬롯 정의 맵 {슬롯명: SlotDefinition}.
        body: 부동문자 + {{slot}} 마커가 포함된 본문 텍스트.
        conditional_blocks: L4 조건부 블록 리스트.
        includes: 포함할 베이스 템플릿 블록 이름 리스트.
    """

    section_id: str = ""
    version: str = "1.0"
    source_reference: str = ""
    slots: dict[str, SlotDefinition] = field(default_factory=dict)
    body: str = ""
    conditional_blocks: list[ConditionalBlock] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)

    @property
    def l2_slots(self) -> dict[str, SlotDefinition]:
        return {k: v for k, v in self.slots.items() if v.level == "L2"}

    @property
    def l3_slots(self) -> dict[str, SlotDefinition]:
        return {k: v for k, v in self.slots.items() if v.level == "L3"}

    @property
    def l4_blocks(self) -> list[ConditionalBlock]:
        return self.conditional_blocks


@dataclass
class BaseBlocks:
    """_base.yaml에서 로드된 공통 부동문자 블록.

    Attributes:
        blocks: {블록명: 텍스트} 딕셔너리.
    """

    blocks: dict[str, str] = field(default_factory=dict)

    def get(self, name: str, default: str = "") -> str:
        return self.blocks.get(name, default)


class TemplateLoader:
    """YAML 파일에서 SectionTemplate 및 BaseBlocks를 로드한다.

    Args:
        template_dir: YAML 파일이 위치한 디렉터리 경로.
    """

    def __init__(self, template_dir: str | Path) -> None:
        self._dir = Path(template_dir)

    def load_base(self) -> BaseBlocks:
        """_base.yaml을 로드하여 BaseBlocks를 반환한다."""
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
        """섹션 YAML을 로드하여 SectionTemplate을 반환한다."""
        path = self._dir / f"{section_id}.yaml"
        if not path.exists():
            return None

        raw = self._read_yaml(path)
        return self._parse_template(raw)

    def load_all_sections(self) -> dict[str, SectionTemplate]:
        """디렉터리 내 모든 섹션 YAML을 로드한다."""
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

    def load_industry_override(
        self,
        section_id: str,
        industry: str,
    ) -> SectionTemplate | None:
        """산업별 오버라이드 YAML을 로드한다."""
        path = self._dir / "industry_variants" / industry / f"{section_id}.yaml"
        if not path.exists():
            return None

        raw = self._read_yaml(path)
        return self._parse_template(raw)

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

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
        )
