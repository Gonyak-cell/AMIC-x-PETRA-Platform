"""부동문자 템플릿 + 슬롯 채우기 시스템.

> 마지막 수정: 2026-02-17

YAML 기반 부동문자 프레임에 LLM 슬롯 채우기를 결합한 하이브리드 내러티브 생성 모듈.

슬롯 레벨:
  L1 — 완전 고정 (변환 없이 그대로)
  L2 — 단순 치환 (IMDocumentData 필드 직접 참조)
  L3 — LLM 슬롯 (업로드 자료/리서치 기반 LLM 생성)
  L4 — 조건부 블록 (산업/조건에 따라 부동문자 블록 삽입)
"""

from src.narrative_generator.templates.extractor import (
    ExtractionResult,
    TemplateExtractor,
)
from src.narrative_generator.templates.loader import (
    ConditionalBlock,
    SectionTemplate,
    SlotDefinition,
    TemplateLoader,
)
from src.narrative_generator.templates.registry import TemplateRegistry
from src.narrative_generator.templates.renderer import TemplateRenderer

__all__ = [
    "ConditionalBlock",
    "ExtractionResult",
    "SectionTemplate",
    "SlotDefinition",
    "TemplateExtractor",
    "TemplateLoader",
    "TemplateRegistry",
    "TemplateRenderer",
]
