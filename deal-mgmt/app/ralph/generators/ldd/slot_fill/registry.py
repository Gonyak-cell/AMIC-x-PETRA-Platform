"""TemplateRegistry — LDD YAML 템플릿 캐시 및 오버라이드 관리."""

from __future__ import annotations

import logging
from pathlib import Path

from app.ralph.generators.ldd.slot_fill.loader import BaseBlocks, SectionTemplate, TemplateLoader

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """LDD 템플릿 레지스트리."""

    def __init__(self, template_dir: str | Path) -> None:
        self._loader = TemplateLoader(template_dir)
        self._cache: dict[str, SectionTemplate] = {}
        self._industry_cache: dict[str, SectionTemplate] = {}
        self._base: BaseBlocks | None = None
        self._loaded = False

    def load_all(self) -> None:
        """모든 템플릿을 로드한다."""
        self._base = self._loader.load_base()
        self._cache = self._loader.load_all_sections()
        self._loaded = True
        logger.info(
            "LDD slot-fill templates loaded: %d sections, base blocks=%d",
            len(self._cache),
            len(self._base.blocks) if self._base else 0,
        )

    def has(self, section_id: str) -> bool:
        self._ensure_loaded()
        return section_id in self._cache

    def get(self, section_id: str, *, industry: str = "") -> SectionTemplate | None:
        self._ensure_loaded()
        base_tpl = self._cache.get(section_id)
        if base_tpl is None:
            return None

        if not industry:
            return base_tpl

        cache_key = f"{industry}:{section_id}"
        if cache_key in self._industry_cache:
            return self._industry_cache[cache_key]

        override = self._loader.load_industry_override(section_id, industry)
        if override is None:
            return base_tpl

        merged = self._merge_templates(base_tpl, override)
        self._industry_cache[cache_key] = merged
        return merged

    @property
    def base_blocks(self) -> BaseBlocks:
        self._ensure_loaded()
        return self._base or BaseBlocks()

    @property
    def section_ids(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.keys())

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load_all()

    @staticmethod
    def _merge_templates(base: SectionTemplate, override: SectionTemplate) -> SectionTemplate:
        merged_slots = dict(base.slots)
        merged_slots.update(override.slots)
        merged_cbs = list(base.conditional_blocks) + list(override.conditional_blocks)
        return SectionTemplate(
            section_id=base.section_id,
            version=override.version or base.version,
            source_reference=override.source_reference or base.source_reference,
            slots=merged_slots,
            body=override.body or base.body,
            conditional_blocks=merged_cbs,
            includes=override.includes or base.includes,
        )
