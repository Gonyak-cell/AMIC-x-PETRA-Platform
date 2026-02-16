"""Narrative Generator — RAG 기반 IM 내러티브 생성 모듈.

> 마지막 수정: 2026-02-10 11:52:29

IMDocumentData의 재무/시장/딜 데이터를 LLM+RAG로 변환하여
14개 섹션별 내러티브 텍스트를 생성한다.

파이프라인: 데이터 추출 → RAG 검색 → 프롬프트 조립 → LLM 생성 → Fact Check

사용 예시::

    from src.narrative_generator import NarrativeOrchestrator, NarrativeResult
    from src.design_renderer.im_document import IMDocumentData

    orchestrator = NarrativeOrchestrator()
    result: NarrativeResult = orchestrator.generate(im_data, industry="tech")
    im_data.narratives = result.narratives  # Design Renderer에 공급
"""

# ── Config ──
from src.narrative_generator.config import NarrativeConfig, get_config

# ── Engine (메인 진입점) ──
from src.narrative_generator.engine.orchestrator import (
    NarrativeOrchestrator,
    NarrativeResult,
)
from src.narrative_generator.engine.structured_output import (
    NumericClaim,
    SectionNarrative,
    extract_numeric_claims,
    parse_narrative_response,
)
from src.narrative_generator.engine.token_budget import (
    BudgetCheckResult,
    TokenBudgetManager,
    count_tokens,
)

# ── RAG ──
from src.narrative_generator.rag.chunker import DocumentChunk, DocumentChunker
from src.narrative_generator.rag.embedder import TextEmbedder
from src.narrative_generator.rag.retriever import ContextRetriever, RetrievedContext
from src.narrative_generator.rag.vector_store import ScoredChunk, VectorStore

# ── Prompts ──
from src.narrative_generator.prompts import (
    INDUSTRY_VARIANTS,
    BasePrompt,
    PromptRegistry,
    create_default_registry,
    get_industry_variant,
)

# ── Fact Checker ──
from src.narrative_generator.fact_checker.confidence import (
    ConfidenceResult,
    ConfidenceScorer,
)
from src.narrative_generator.fact_checker.consistency import (
    ConsistencyChecker,
    ConsistencyReport,
)
from src.narrative_generator.fact_checker.validator import (
    FactCheckReport,
    FactValidator,
)

# ── Korean Finance ──
from src.narrative_generator.korean_finance.terminology import (
    FINANCIAL_TERMS,
    TermCategory,
    TermEntry,
    get_industry_terms,
    get_term,
    to_english,
    to_korean,
)
from src.narrative_generator.korean_finance.tone_adapter import (
    FACTUAL_OPTIMISM,
    ToneAdapter,
    ToneCheckResult,
    ToneProfile,
)

# ── Exceptions ──
from src.narrative_generator.exceptions import (
    ChunkingError,
    ConfigurationError,
    ConsistencyError,
    EmbeddingError,
    FactCheckError,
    LLMAPIError,
    LLMError,
    NarrativeGeneratorError,
    NumericClaimError,
    PromptBuildError,
    PromptError,
    PromptNotFoundError,
    RAGError,
    RetrievalError,
    TokenBudgetExceededError,
    VectorStoreError,
)

__version__ = "0.5.0"

__all__ = [
    # Config
    "NarrativeConfig",
    "get_config",
    # Engine
    "NarrativeOrchestrator",
    "NarrativeResult",
    "SectionNarrative",
    "NumericClaim",
    "extract_numeric_claims",
    "parse_narrative_response",
    "TokenBudgetManager",
    "BudgetCheckResult",
    "count_tokens",
    # RAG
    "DocumentChunker",
    "DocumentChunk",
    "TextEmbedder",
    "VectorStore",
    "ScoredChunk",
    "ContextRetriever",
    "RetrievedContext",
    # Prompts
    "BasePrompt",
    "PromptRegistry",
    "create_default_registry",
    "get_industry_variant",
    "INDUSTRY_VARIANTS",
    # Fact Checker
    "FactValidator",
    "FactCheckReport",
    "ConsistencyChecker",
    "ConsistencyReport",
    "ConfidenceScorer",
    "ConfidenceResult",
    # Korean Finance
    "FINANCIAL_TERMS",
    "TermEntry",
    "TermCategory",
    "get_term",
    "to_korean",
    "to_english",
    "get_industry_terms",
    "ToneAdapter",
    "ToneProfile",
    "ToneCheckResult",
    "FACTUAL_OPTIMISM",
    # Exceptions
    "NarrativeGeneratorError",
    "ConfigurationError",
    "RAGError",
    "EmbeddingError",
    "VectorStoreError",
    "ChunkingError",
    "RetrievalError",
    "PromptError",
    "PromptNotFoundError",
    "PromptBuildError",
    "LLMError",
    "LLMAPIError",
    "TokenBudgetExceededError",
    "FactCheckError",
    "NumericClaimError",
    "ConsistencyError",
]
