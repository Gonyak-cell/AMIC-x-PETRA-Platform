"""문서 청킹 모듈 (T-N04).

> 마지막 수정: 2026-02-10 11:52:29

토큰 기반 오버랩 청킹을 수행한다.
문단 → 문장 단위로 분할 후, 설정된 chunk_size/overlap에 따라 청크를 생성한다.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from src.narrative_generator.exceptions import ChunkingError

# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentChunk:
    """문서 청크.

    Attributes:
        chunk_id: 고유 청크 식별자 (텍스트 해시 기반).
        text: 청크 텍스트.
        token_count: 토큰 수.
        metadata: 원본 문서 메타데이터 + 청크 위치 정보.
    """

    chunk_id: str
    text: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 토큰 카운터 (tiktoken 선택적 의존성)
# ---------------------------------------------------------------------------


def _count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """tiktoken으로 토큰 수를 계산한다.

    tiktoken이 없으면 근사치(문자 수 / 3.5)를 사용한다.

    Args:
        text: 토큰 수를 계산할 텍스트.
        encoding_name: tiktoken 인코딩 이름.

    Returns:
        토큰 수.
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except ImportError:
        # tiktoken 미설치 시 근사치 사용
        return max(1, int(len(text) / 3.5))


def _generate_chunk_id(text: str, index: int) -> str:
    """텍스트 해시 기반 청크 ID를 생성한다."""
    content = f"{text}:{index}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 문장 분할
# ---------------------------------------------------------------------------

_SENTENCE_PATTERN = re.compile(r"(?<=[.!?。])\s+|(?<=\n)\s*")


def _split_into_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분할한다.

    한국어/영어 모두 지원. 마침표, 느낌표, 물음표, 줄바꿈 기준.

    Args:
        text: 분할할 텍스트.

    Returns:
        문장 리스트 (빈 문자열 제외).
    """
    # 문단 우선 분할
    paragraphs = text.split("\n\n")
    sentences: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 문장 분할
        parts = _SENTENCE_PATTERN.split(para)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)

    return sentences


# ---------------------------------------------------------------------------
# DocumentChunker
# ---------------------------------------------------------------------------


class DocumentChunker:
    """토큰 기반 오버랩 문서 청킹.

    문장 단위로 분할 후, chunk_size 토큰 내에서 문장을 모아 청크를 구성한다.
    인접 청크 사이에 overlap 토큰만큼 겹침을 둔다.

    Args:
        chunk_size: 청크 최대 토큰 수 (기본 512).
        chunk_overlap: 청크 간 오버랩 토큰 수 (기본 64).
        encoding_name: tiktoken 인코딩 이름 (기본 "cl100k_base").
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        encoding_name: str = "cl100k_base",
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ChunkingError(
                f"chunk_overlap({chunk_overlap})은 chunk_size({chunk_size})보다 작아야 합니다"
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._encoding_name = encoding_name

    @property
    def chunk_size(self) -> int:
        """최대 청크 토큰 수."""
        return self._chunk_size

    @property
    def chunk_overlap(self) -> int:
        """청크 간 오버랩 토큰 수."""
        return self._chunk_overlap

    def chunk(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """텍스트를 청크로 분할한다.

        Args:
            text: 분할할 텍스트.
            metadata: 모든 청크에 공통 적용할 메타데이터.

        Returns:
            DocumentChunk 리스트.

        Raises:
            ChunkingError: 입력 텍스트가 비어 있는 경우.
        """
        if not text or not text.strip():
            return []

        base_metadata = metadata or {}
        sentences = _split_into_sentences(text)

        if not sentences:
            return []

        chunks: list[DocumentChunk] = []
        current_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = _count_tokens(sentence, self._encoding_name)

            # 단일 문장이 chunk_size를 초과하면 그대로 하나의 청크로
            if sentence_tokens > self._chunk_size:
                # 현재 버퍼에 남은 문장이 있으면 먼저 청크 생성
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    chunks.append(self._make_chunk(chunk_text, len(chunks), base_metadata))
                    current_sentences = []
                    current_tokens = 0

                # 긴 문장 자체를 청크로
                chunks.append(self._make_chunk(sentence, len(chunks), base_metadata))
                continue

            # 현재 버퍼 + 새 문장이 chunk_size 초과 시 청크 생성
            if current_tokens + sentence_tokens > self._chunk_size and current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append(self._make_chunk(chunk_text, len(chunks), base_metadata))

                # 오버랩: 뒤에서부터 overlap 토큰만큼 유지
                overlap_sentences: list[str] = []
                overlap_tokens = 0
                for s in reversed(current_sentences):
                    s_tokens = _count_tokens(s, self._encoding_name)
                    if overlap_tokens + s_tokens > self._chunk_overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tokens

                current_sentences = overlap_sentences
                current_tokens = overlap_tokens

            current_sentences.append(sentence)
            current_tokens += sentence_tokens

        # 마지막 남은 문장들을 청크로
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(self._make_chunk(chunk_text, len(chunks), base_metadata))

        return chunks

    def _make_chunk(
        self,
        text: str,
        index: int,
        base_metadata: dict[str, Any],
    ) -> DocumentChunk:
        """DocumentChunk 인스턴스를 생성한다."""
        token_count = _count_tokens(text, self._encoding_name)
        chunk_id = _generate_chunk_id(text, index)
        metadata = {
            **base_metadata,
            "chunk_index": index,
            "token_count": token_count,
        }
        return DocumentChunk(
            chunk_id=chunk_id,
            text=text,
            token_count=token_count,
            metadata=metadata,
        )
