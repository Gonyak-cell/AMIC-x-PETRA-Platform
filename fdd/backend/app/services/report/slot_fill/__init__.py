"""FDD 부동문자 템플릿 + 슬롯 채우기 시스템.

YAML 기반 부동문자 프레임에 LLM 슬롯 채우기를 결합한 FDD 내러티브 생성 모듈.

슬롯 레벨:
  L1 — 완전 고정 (변환 없이 그대로)
  L2 — 단순 치환 (FDD 데이터 dict 필드 직접 참조)
  L3 — LLM 슬롯 (분석 데이터 기반 LLM 생성)
  L4 — 조건부 블록 (산업/조건에 따라 부동문자 블록 삽입)
"""

from app.services.report.slot_fill.loader import (
    BaseBlocks,
    ConditionalBlock,
    SectionTemplate,
    SlotDefinition,
    TemplateLoader,
)
from app.services.report.slot_fill.prompt_builder import FDDSlotFillPromptBuilder
from app.services.report.slot_fill.registry import TemplateRegistry
from app.services.report.slot_fill.renderer import FDDTemplateRenderer
from app.services.report.slot_fill.slot_parser import SlotResponseParser

__all__ = [
    "BaseBlocks",
    "ConditionalBlock",
    "FDDSlotFillPromptBuilder",
    "FDDTemplateRenderer",
    "SectionTemplate",
    "SlotDefinition",
    "SlotResponseParser",
    "TemplateLoader",
    "TemplateRegistry",
]
