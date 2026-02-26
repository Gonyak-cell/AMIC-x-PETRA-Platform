"""LDD 법률 인용 시스템.

수동 큐레이션된 한국법 조항 + 판례를 기반으로
LLM 프롬프트에 법률 컨텍스트를 주입하고,
생성된 인용을 검증한다.
"""

from app.ralph.generators.ldd.legal_citations.citation_db import (
    CitationDB,
    PrecedentEntry,
    StatuteEntry,
)
from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import (
    CitationPromptInjector,
)

__all__ = [
    "CitationDB",
    "CitationPromptInjector",
    "PrecedentEntry",
    "StatuteEntry",
]
