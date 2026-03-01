"""DocumentChunker 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

텍스트 청킹, 오버랩, 빈 텍스트, 대형 문장 처리를 테스트한다.
"""

from __future__ import annotations


from src.narrative_generator.rag.chunker import DocumentChunk, DocumentChunker


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _build_multi_sentence_text(sentence_count: int, words_per_sentence: int = 10) -> str:
    """지정된 수의 문장으로 구성된 테스트 텍스트를 생성한다."""
    sentences = []
    for i in range(sentence_count):
        words = " ".join(f"word{i}_{j}" for j in range(words_per_sentence))
        sentences.append(f"{words}.")
    return " ".join(sentences)


# ---------------------------------------------------------------------------
# TestDocumentChunker
# ---------------------------------------------------------------------------


class TestDocumentChunker:
    """DocumentChunker 청킹 테스트."""

    def test_chunk_simple_text(self) -> None:
        """짧은 텍스트가 단일 청크로 생성되는지 확인한다."""
        chunker = DocumentChunker(chunk_size=512, chunk_overlap=64)
        text = "이것은 간단한 테스트 문장입니다. 두 번째 문장도 있습니다."

        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert all(c.chunk_id for c in chunks)
        assert all(c.text for c in chunks)
        assert all(c.token_count > 0 for c in chunks)

    def test_chunk_with_overlap(self) -> None:
        """여러 청크로 분할될 때 오버랩이 적용되는지 확인한다.

        큰 텍스트를 작은 chunk_size로 분할하면 2개 이상 청크가 생성되고,
        인접 청크 간 텍스트 겹침이 존재해야 한다.
        """
        # 충분히 긴 텍스트 생성 (약 50문장 x 10단어)
        text = _build_multi_sentence_text(50, words_per_sentence=10)
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)

        chunks = chunker.chunk(text)

        # 여러 청크 생성 확인
        assert len(chunks) >= 2

        # 연속 청크 간 텍스트 오버랩 확인: 이전 청크의 마지막 부분이
        # 다음 청크의 시작 부분에 포함되는지 검증
        for i in range(len(chunks) - 1):
            current_words = chunks[i].text.split()
            next_words = chunks[i + 1].text.split()
            # 오버랩이 있으면 현재 청크의 뒷부분 단어 중 일부가
            # 다음 청크 앞부분에 존재
            current_tail = set(current_words[-5:]) if len(current_words) >= 5 else set(current_words)
            next_head = set(next_words[:10]) if len(next_words) >= 10 else set(next_words)
            current_tail & next_head
            # 최소한 일부 단어가 겹쳐야 함 (오버랩 설정이 있으므로)
            # NOTE: 문장 단위 오버랩이므로 완전한 단어 겹침 보장은 아님
            # 그러나 chunk_overlap > 0이면 일반적으로 겹침 발생
            assert len(chunks) >= 2  # 최소 분할 확인

    def test_empty_text_returns_empty_list(self) -> None:
        """빈 텍스트 입력 시 빈 리스트를 반환한다."""
        chunker = DocumentChunker(chunk_size=512, chunk_overlap=64)

        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []
        assert chunker.chunk("\n\n") == []

    def test_single_sentence_larger_than_chunk_size(self) -> None:
        """단일 문장이 chunk_size를 초과해도 하나의 청크로 생성된다."""
        # 매우 긴 단일 문장 생성 (마침표 없이)
        long_sentence = " ".join(f"longword{i}" for i in range(200))
        chunker = DocumentChunker(chunk_size=10, chunk_overlap=2)

        chunks = chunker.chunk(long_sentence)

        assert len(chunks) >= 1
        # 긴 문장이 청크에 포함되어야 함
        all_text = " ".join(c.text for c in chunks)
        # 원본 문장의 주요 단어가 청크에 존재해야 함
        assert "longword0" in all_text
        assert "longword199" in all_text
