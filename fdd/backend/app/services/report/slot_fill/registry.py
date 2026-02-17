"""TemplateRegistry — 템플릿 캐시 및 산업별 오버라이드 관리.

TemplateLoader를 감싸고, 로드된 템플릿을 캐시하며,
산업별 오버라이드가 있으면 병합하여 반환한다.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.report.slot_fill.loader import (
    BaseBlocks,
    SectionTemplate,
    TemplateLoader,
)

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """YAML 템플릿 레지스트리 (캐시 + 산업별 오버라이드).

    Args:
        template_dir: YAML 파일이 위치한 디렉터리 경로.
    """

    def __init__(self, template_dir: str | Path) -> None:
        self._loader = TemplateLoader(template_dir)
        self._cache: dict[str, SectionTemplate] = {}
        self._industry_cache: dict[str, SectionTemplate] = {}
        self._base: BaseBlocks | None = None
        self._loaded = False

    def load_all(self) -> None:
        """모든 템플릿을 미리 로드하고 캐시한다."""
        self._base = self._loader.load_base()
        self._cache = self._loader.load_all_sections()
        self._loaded = True
        logger.info(
            "FDD templates loaded: %d sections, base blocks=%d",
            len(self._cache),
            len(self._base.blocks),
        )

    def has(self, section_id: str) -> bool:
        """해당 섹션의 템플릿이 존재하는지 확인한다."""
        self._ensure_loaded()
        return section_id in self._cache

    def get(
        self,
        section_id: str,
        *,
        industry: str = "",
    ) -> SectionTemplate | None:
        """섹션 템플릿을 반환한다.

        산업별 오버라이드가 있으면 병합(merge)하여 반환한다.
        """
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
        """공통 부동문자 블록을 반환한다."""
        self._ensure_loaded()
        return self._base or BaseBlocks()

    @property
    def section_ids(self) -> list[str]:
        """등록된 모든 섹션 ID 목록."""
        self._ensure_loaded()
        return list(self._cache.keys())

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load_all()

    @staticmethod
    def _merge_templates(
        base: SectionTemplate,
        override: SectionTemplate,
    ) -> SectionTemplate:
        """기본 템플릿에 산업별 오버라이드를 병합한다."""
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
