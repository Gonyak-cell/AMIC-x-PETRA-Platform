"""OpenAI 임베딩 모듈 (T-N02).

> 마지막 수정: 2026-02-10 11:52:29

OpenAI text-embedding-3-small을 래핑하여 텍스트 임베딩 벡터를 생성한다.
재시도 로직(exponential backoff)과 배치 처리를 지원한다.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from src.narrative_generator.config import NarrativeConfig, get_config
from src.narrative_generator.exceptions import ConfigurationError, EmbeddingError

logger = logging.getLogger(__name__)


class TextEmbedder:
    """OpenAI 임베딩 래퍼.

    Args:
        config: NarrativeConfig 인스턴스. None이면 get_config() 사용.
        client: 주입된 OpenAI 클라이언트 (테스트용). None이면 자동 생성.

    Raises:
        ConfigurationError: OpenAI API 키가 설정되지 않은 경우.
    """

    # 배치 당 최대 텍스트 수 (OpenAI 제한)
    MAX_BATCH_SIZE = 2048

    def __init__(
        self,
        config: NarrativeConfig | None = None,
        client: Any | None = None,
    ) -> None:
        self._config = config or get_config()
        self._model = self._config.embedding_model
        self._dimension = self._config.embedding_dimension

        if client is not None:
            self._client = client
        else:
            if not self._config.has_openai:
                raise ConfigurationError(
                    "openai_api_key",
                    "OpenAI API 키가 설정되지 않았습니다",
                )
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self._config.openai_api_key)
            except ImportError as exc:
                raise ConfigurationError(
                    "openai",
                    f"openai 패키지가 설치되지 않았습니다: {exc}",
                ) from exc

    @property
    def model(self) -> str:
        """사용 중인 임베딩 모델명."""
        return self._model

    @property
    def dimension(self) -> int:
        """임베딩 벡터 차원."""
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """단일 텍스트의 임베딩 벡터를 생성한다.

        Args:
            text: 임베딩할 텍스트.

        Returns:
            float 리스트 (임베딩 벡터).

        Raises:
            EmbeddingError: API 호출 실패 시.
        """
        if not text or not text.strip():
            return [0.0] * self._dimension

        return self._embed_with_retry([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트의 임베딩 벡터를 배치로 생성한다.

        Args:
            texts: 임베딩할 텍스트 리스트.

        Returns:
            임베딩 벡터 리스트의 리스트.

        Raises:
            EmbeddingError: API 호출 실패 시.
        """
        if not texts:
            return []

        # 빈 텍스트 처리
        non_empty_indices: list[int] = []
        non_empty_texts: list[str] = []
        for i, t in enumerate(texts):
            if t and t.strip():
                non_empty_indices.append(i)
                non_empty_texts.append(t)

        if not non_empty_texts:
            return [[0.0] * self._dimension for _ in texts]

        # 배치 분할 처리
        all_embeddings: list[list[float]] = []
        for start in range(0, len(non_empty_texts), self.MAX_BATCH_SIZE):
            batch = non_empty_texts[start : start + self.MAX_BATCH_SIZE]
            batch_embeddings = self._embed_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

        # 원래 인덱스에 맞게 재배치
        result: list[list[float]] = [[0.0] * self._dimension for _ in texts]
        for idx, embedding in zip(non_empty_indices, all_embeddings):
            result[idx] = embedding

        return result

    def _embed_with_retry(
        self,
        texts: list[str],
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> list[list[float]]:
        """재시도 로직이 포함된 임베딩 API 호출.

        Exponential backoff (1초 → 2초 → 4초).

        Args:
            texts: 임베딩할 텍스트 리스트.
            max_retries: 최대 재시도 횟수.
            base_delay: 기본 대기 시간 (초).

        Returns:
            임베딩 벡터 리스트.

        Raises:
            EmbeddingError: 최대 재시도 후에도 실패 시.
        """
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = self._client.embeddings.create(
                    input=texts,
                    model=self._model,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "임베딩 API 호출 실패 (시도 %d/%d): %s — %0.1f초 후 재시도",
                        attempt + 1,
                        max_retries + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        total_chars = sum(len(t) for t in texts)
        raise EmbeddingError(
            text_length=total_chars,
            original_error=str(last_error),
        )
