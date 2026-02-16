"""산업별 프롬프트 변형 서브패키지."""

from src.narrative_generator.prompts.industry_variants.general import GeneralVariant
from src.narrative_generator.prompts.industry_variants.logistics import (
    LogisticsVariant,
)

__all__ = ["GeneralVariant", "LogisticsVariant"]
