"""Pinecone 벡터 스토어 모듈 (T-N03).

> 마지막 수정: 2026-02-10 11:52:29

Pinecone 인덱스에 대한 CRUD 래퍼.
기업별 네임스페이스 격리 및 메타데이터 필터링을 지원한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.narrative_generator.config import NarrativeConfig, get_config
from src.narrative_generator.exceptions import ConfigurationError, VectorStoreError
from src.narrative_generator.rag.chunker import DocumentChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoredChunk:
    """검색 결과 청크 (유사도 점수 포함).

    Attributes:
        chunk_id: 청크 식별자.
        text: 청크 텍스트.
        score: 유사도 점수 (0.0~1.0).
        metadata: 메타데이터.
    """

    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# VectorStore
# ---------------------------------------------------------------------------


class VectorStore:
    """Pinecone 벡터 DB 래퍼.

    Args:
        config: NarrativeConfig 인스턴스. None이면 get_config() 사용.
        index: 주입된 Pinecone Index 객체 (테스트용). None이면 자동 생성.

    Raises:
        ConfigurationError: Pinecone API 키가 설정되지 않은 경우.
    """

    def __init__(
        self,
        config: NarrativeConfig | None = None,
        index: Any | None = None,
    ) -> None:
        self._config = config or get_config()

        if index is not None:
            self._index = index
        else:
            if not self._config.has_pinecone:
                raise ConfigurationError(
                    "pinecone_api_key",
                    "Pinecone API 키가 설정되지 않았습니다",
                )
            try:
                from pinecone import Pinecone

                pc = Pinecone(api_key=self._config.pinecone_api_key)
                self._index = pc.Index(self._config.pinecone_index_name)
            except ImportError as exc:
                raise ConfigurationError(
                    "pinecone",
                    f"pinecone-client 패키지가 설치되지 않았습니다: {exc}",
                ) from exc
            except Exception as exc:
                raise VectorStoreError(
                    operation="index_connect",
                    original_error=str(exc),
                ) from exc

    def upsert(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        namespace: str = "",
    ) -> int:
        """청크 + 임베딩을 Pinecone에 저장한다.

        Args:
            chunks: 저장할 DocumentChunk 리스트.
            embeddings: 대응하는 임베딩 벡터 리스트.
            namespace: Pinecone 네임스페이스 (기업별 격리용, 예: corp_code).

        Returns:
            업서트된 벡터 수.

        Raises:
            VectorStoreError: 업서트 실패 시.
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                operation="upsert",
                original_error=(
                    f"chunks({len(chunks)})와 embeddings({len(embeddings)}) "
                    f"길이가 일치하지 않습니다"
                ),
            )

        if not chunks:
            return 0

        try:
            vectors = []
            for chunk, embedding in zip(chunks, embeddings):
                metadata = {
                    **chunk.metadata,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                }
                vectors.append(
                    {
                        "id": chunk.chunk_id,
                        "values": embedding,
                        "metadata": metadata,
                    }
                )

            # Pinecone 배치 제한 (100개씩)
            batch_size = 100
            total_upserted = 0
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i : i + batch_size]
                response = self._index.upsert(
                    vectors=batch,
                    namespace=namespace,
                )
                total_upserted += response.get("upserted_count", len(batch))

            logger.info(
                "Pinecone 업서트 완료: %d 벡터, namespace='%s'",
                total_upserted,
                namespace,
            )
            return total_upserted

        except Exception as exc:
            raise VectorStoreError(
                operation="upsert",
                original_error=str(exc),
            ) from exc

    def query(
        self,
        embedding: list[float],
        top_k: int = 5,
        namespace: str = "",
        filter_dict: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """유사도 검색을 수행한다.

        Args:
            embedding: 쿼리 임베딩 벡터.
            top_k: 반환할 최대 결과 수.
            namespace: Pinecone 네임스페이스.
            filter_dict: 메타데이터 필터 (예: {"industry": "tech"}).

        Returns:
            ScoredChunk 리스트 (유사도 내림차순).

        Raises:
            VectorStoreError: 검색 실패 시.
        """
        try:
            query_params: dict[str, Any] = {
                "vector": embedding,
                "top_k": top_k,
                "include_metadata": True,
                "namespace": namespace,
            }
            if filter_dict:
                query_params["filter"] = filter_dict

            response = self._index.query(**query_params)

            results: list[ScoredChunk] = []
            for match in response.get("matches", []):
                metadata = match.get("metadata", {})
                text = metadata.pop("text", "")
                results.append(
                    ScoredChunk(
                        chunk_id=match["id"],
                        text=text,
                        score=match.get("score", 0.0),
                        metadata=metadata,
                    )
                )

            return results

        except Exception as exc:
            raise VectorStoreError(
                operation="query",
                original_error=str(exc),
            ) from exc

    def delete(
        self,
        chunk_ids: list[str] | None = None,
        namespace: str = "",
        delete_all: bool = False,
    ) -> None:
        """벡터를 삭제한다.

        Args:
            chunk_ids: 삭제할 청크 ID 리스트. None이면 delete_all과 함께 사용.
            namespace: Pinecone 네임스페이스.
            delete_all: True이면 네임스페이스의 모든 벡터를 삭제.

        Raises:
            VectorStoreError: 삭제 실패 시.
        """
        try:
            if delete_all:
                self._index.delete(delete_all=True, namespace=namespace)
                logger.info("Pinecone 전체 삭제: namespace='%s'", namespace)
            elif chunk_ids:
                self._index.delete(ids=chunk_ids, namespace=namespace)
                logger.info(
                    "Pinecone 삭제: %d 벡터, namespace='%s'",
                    len(chunk_ids),
                    namespace,
                )
        except Exception as exc:
            raise VectorStoreError(
                operation="delete",
                original_error=str(exc),
            ) from exc
