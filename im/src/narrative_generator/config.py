"""Narrative Generator 설정 (T-N01).

> 마지막 수정: 2026-02-11 21:38:33

Pydantic BaseSettings 기반으로 OpenAI, Anthropic, Google, Pinecone,
LLM, RAG 설정을 통합 관리한다.
환경변수 또는 .env 파일에서 값을 로드한다.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class NarrativeConfig(BaseSettings):
    """Narrative Generator 통합 설정.

    환경변수 매핑:
        OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT,
        PINECONE_INDEX_NAME, NARRATIVE_MODEL_NAME, NARRATIVE_TEMPERATURE, ...

    Examples:
        >>> config = NarrativeConfig()  # .env에서 자동 로드
        >>> config = get_config()       # 캐싱된 싱글턴
    """

    # ── OpenAI ──
    openai_api_key: str = Field(
        default="",
        description="OpenAI API 키",
    )

    # ── Anthropic ──
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API 키",
    )
    anthropic_model_name: str = Field(
        default="claude-sonnet-4-20250514",
        description="Anthropic 기본 모델명",
    )

    # ── Google Gemini ──
    google_api_key: str = Field(
        default="",
        description="Google AI API 키",
    )
    google_model_name: str = Field(
        default="gemini-2.0-flash",
        description="Google Gemini 기본 모델명",
    )

    # ── Pinecone ──
    pinecone_api_key: str = Field(
        default="",
        description="Pinecone API 키",
    )
    pinecone_environment: str = Field(
        default="us-east-1",
        description="Pinecone 환경 (리전)",
    )
    pinecone_index_name: str = Field(
        default="im-narratives",
        description="Pinecone 인덱스 이름",
    )

    # ── LLM ──
    narrative_model_name: str = Field(
        default="gpt-4o",
        description="내러티브 생성용 LLM 모델명",
    )
    narrative_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="LLM 생성 온도 (낮을수록 결정적)",
    )
    narrative_max_tokens: int = Field(
        default=4096,
        gt=0,
        description="LLM 최대 응답 토큰 수",
    )

    # ── Embedding ──
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="임베딩 모델명",
    )
    embedding_dimension: int = Field(
        default=1536,
        gt=0,
        description="임베딩 벡터 차원",
    )

    # ── RAG ──
    chunk_size: int = Field(
        default=512,
        gt=0,
        description="문서 청크 크기 (토큰 수)",
    )
    chunk_overlap: int = Field(
        default=64,
        ge=0,
        description="청크 간 오버랩 토큰 수",
    )
    retrieval_top_k: int = Field(
        default=5,
        gt=0,
        description="RAG 검색 시 반환할 최대 청크 수",
    )

    # ── Fact Check ──
    fact_check_enabled: bool = Field(
        default=True,
        description="팩트 체크 활성화 여부",
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="신뢰도 점수 경고 임계값",
    )

    # ── Multi-Model Routing ──
    llm_routing_map: str = Field(
        default="",
        description=(
            "섹션별 LLM 프로바이더 매핑 (JSON 형식). "
            "빈 문자열이면 DEFAULT_ROUTING 사용. "
            '예: {"executive_summary":"anthropic","financial_analysis":"openai"}'
        ),
    )
    llm_fallback_order: str = Field(
        default="openai,anthropic,google",
        description="LLM 프로바이더 폴백 우선순위 (쉼표 구분)",
    )

    # ── General ──
    default_language: str = Field(
        default="ko",
        description="기본 내러티브 언어 (ko / en)",
    )
    default_industry: Optional[str] = Field(
        default=None,
        description="기본 산업 분류 (tech, healthcare, manufacturing, financial_services)",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_less_than_chunk_size(cls, v: int, info: object) -> int:
        """overlap이 chunk_size보다 작은지 검증."""
        # NOTE: info.data에서 chunk_size 접근 (pydantic v2)
        data = getattr(info, "data", {})
        chunk_size = data.get("chunk_size", 512)
        if v >= chunk_size:
            msg = f"chunk_overlap({v})은 chunk_size({chunk_size})보다 작아야 합니다"
            raise ValueError(msg)
        return v

    @property
    def has_openai(self) -> bool:
        """OpenAI API 키가 설정되었는지 확인."""
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        """Anthropic API 키가 설정되었는지 확인."""
        return bool(self.anthropic_api_key)

    @property
    def has_google(self) -> bool:
        """Google AI API 키가 설정되었는지 확인."""
        return bool(self.google_api_key)

    @property
    def has_pinecone(self) -> bool:
        """Pinecone API 키가 설정되었는지 확인."""
        return bool(self.pinecone_api_key)

    def get_routing_map(self) -> dict[str, str] | None:
        """환경변수에서 파싱된 라우팅 맵을 반환한다."""
        if not self.llm_routing_map:
            return None
        try:
            return json.loads(self.llm_routing_map)
        except json.JSONDecodeError:
            logger.warning("LLM_ROUTING_MAP 파싱 실패: %s", self.llm_routing_map)
            return None

    def get_fallback_order(self) -> list[str]:
        """폴백 우선순위 리스트를 반환한다."""
        return [p.strip() for p in self.llm_fallback_order.split(",") if p.strip()]


@lru_cache(maxsize=1)
def get_config() -> NarrativeConfig:
    """캐싱된 NarrativeConfig 싱글턴을 반환한다.

    Returns:
        NarrativeConfig 인스턴스 (.env에서 로드).
    """
    return NarrativeConfig()
