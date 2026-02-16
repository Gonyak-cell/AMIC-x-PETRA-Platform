"""컨텍스트 검색 + 리랭킹 모듈 (T-N05).

> 마지막 수정: 2026-02-10 11:52:29

Embedder + VectorStore를 조합하여 섹션별 관련 컨텍스트를 검색한다.
MMR(Maximal Marginal Relevance) 리랭킹으로 다양성을 보장한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.narrative_generator.exceptions import RetrievalError
from src.narrative_generator.rag.embedder import TextEmbedder
from src.narrative_generator.rag.vector_store import ScoredChunk, VectorStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievedContext:
    """검색된 컨텍스트 항목.

    Attributes:
        text: 컨텍스트 텍스트.
        score: 유사도 점수 (0.0~1.0).
        source: 출처 정보.
        metadata: 추가 메타데이터.
    """

    text: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MMR 리랭킹
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """두 벡터 간 코사인 유사도를 계산한다."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _mmr_rerank(
    query_embedding: list[float],
    candidates: list[ScoredChunk],
    candidate_embeddings: list[list[float]],
    top_k: int,
    lambda_param: float = 0.7,
) -> list[ScoredChunk]:
    """MMR (Maximal Marginal Relevance) 리랭킹.

    관련성(relevance)과 다양성(diversity)을 균형있게 선택한다.

    Args:
        query_embedding: 쿼리 임베딩 벡터.
        candidates: 후보 청크 리스트.
        candidate_embeddings: 후보 청크의 임베딩 벡터 리스트.
        top_k: 선택할 최대 청크 수.
        lambda_param: 관련성 vs 다양성 가중치 (0~1, 높을수록 관련성 중시).

    Returns:
        리랭킹된 ScoredChunk 리스트.
    """
    if not candidates:
        return []

    if len(candidates) <= top_k:
        return candidates

    selected: list[int] = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_score = float("-inf")
        best_idx = -1

        for idx in remaining:
            # 관련성: 쿼리와의 유사도
            relevance = _cosine_similarity(query_embedding, candidate_embeddings[idx])

            # 다양성: 이미 선택된 청크들과의 최대 유사도
            max_sim_to_selected = 0.0
            for sel_idx in selected:
                sim = _cosine_similarity(
                    candidate_embeddings[idx],
                    candidate_embeddings[sel_idx],
                )
                max_sim_to_selected = max(max_sim_to_selected, sim)

            # MMR 점수
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx >= 0:
            selected.append(best_idx)
            remaining.remove(best_idx)

    return [candidates[i] for i in selected]


# ---------------------------------------------------------------------------
# ContextRetriever
# ---------------------------------------------------------------------------


class ContextRetriever:
    """컨텍스트 검색 엔진.

    Embedder + VectorStore를 조합하여 섹션별 관련 컨텍스트를 검색한다.

    Args:
        embedder: TextEmbedder 인스턴스.
        vector_store: VectorStore 인스턴스.
        top_k: 기본 검색 결과 수.
        mmr_lambda: MMR 리랭킹 lambda 파라미터.
    """

    def __init__(
        self,
        embedder: TextEmbedder,
        vector_store: VectorStore,
        top_k: int = 5,
        mmr_lambda: float = 0.7,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._top_k = top_k
        self._mmr_lambda = mmr_lambda

    def retrieve(
        self,
        query: str,
        *,
        section_id: str = "",
        industry: str = "",
        namespace: str = "",
        top_k: int | None = None,
        use_mmr: bool = True,
    ) -> list[RetrievedContext]:
        """관련 컨텍스트를 검색한다.

        Args:
            query: 검색 쿼리 텍스트.
            section_id: 섹션 ID (메타데이터 필터링용).
            industry: 산업 분류 (메타데이터 필터링용).
            namespace: Pinecone 네임스페이스 (기업별 격리).
            top_k: 반환할 최대 결과 수. None이면 기본값 사용.
            use_mmr: MMR 리랭킹 적용 여부.

        Returns:
            RetrievedContext 리스트 (관련도 내림차순).

        Raises:
            RetrievalError: 검색 실패 시.
        """
        effective_top_k = top_k or self._top_k

        try:
            # 1. 쿼리 임베딩 생성
            query_embedding = self._embedder.embed_text(query)

            # 2. 메타데이터 필터 구성
            filter_dict = self._build_filter(section_id, industry)

            # 3. VectorStore 검색 (MMR 적용 시 더 많이 가져옴)
            fetch_k = effective_top_k * 3 if use_mmr else effective_top_k
            scored_chunks = self._vector_store.query(
                embedding=query_embedding,
                top_k=fetch_k,
                namespace=namespace,
                filter_dict=filter_dict,
            )

            if not scored_chunks:
                logger.info(
                    "검색 결과 없음: query='%s', section='%s', industry='%s'",
                    query[:50],
                    section_id,
                    industry,
                )
                return []

            # 4. MMR 리랭킹 (선택적)
            if use_mmr and len(scored_chunks) > effective_top_k:
                # 후보 임베딩 생성 (배치)
                candidate_texts = [c.text for c in scored_chunks]
                candidate_embeddings = self._embedder.embed_batch(candidate_texts)

                scored_chunks = _mmr_rerank(
                    query_embedding=query_embedding,
                    candidates=scored_chunks,
                    candidate_embeddings=candidate_embeddings,
                    top_k=effective_top_k,
                    lambda_param=self._mmr_lambda,
                )
            else:
                scored_chunks = scored_chunks[:effective_top_k]

            # 5. RetrievedContext로 변환
            results = [
                RetrievedContext(
                    text=chunk.text,
                    score=chunk.score,
                    source=chunk.metadata.get("source", ""),
                    metadata=chunk.metadata,
                )
                for chunk in scored_chunks
            ]

            logger.info(
                "검색 완료: %d 결과, query='%s', section='%s'",
                len(results),
                query[:50],
                section_id,
            )
            return results

        except Exception as exc:
            if isinstance(exc, RetrievalError):
                raise
            raise RetrievalError(
                query=query,
                original_error=str(exc),
            ) from exc

    @staticmethod
    def _build_filter(
        section_id: str,
        industry: str,
    ) -> Optional[dict[str, Any]]:
        """메타데이터 필터 딕셔너리를 구성한다."""
        conditions: dict[str, Any] = {}

        if section_id:
            conditions["section_type"] = section_id
        if industry:
            conditions["industry"] = industry

        if not conditions:
            return None

        # 조건이 1개면 단순 필터, 2개 이상이면 $and 조합
        if len(conditions) == 1:
            return conditions

        return {"$and": [{k: v} for k, v in conditions.items()]}
