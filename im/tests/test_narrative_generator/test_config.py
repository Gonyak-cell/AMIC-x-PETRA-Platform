"""NarrativeConfig 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

기본값, has_openai/has_pinecone 프로퍼티, chunk_overlap 검증을 테스트한다.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.narrative_generator.config import NarrativeConfig


# ---------------------------------------------------------------------------
# TestNarrativeConfig
# ---------------------------------------------------------------------------


class TestNarrativeConfig:
    """NarrativeConfig 설정 테스트."""

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """기본 설정값이 올바르게 지정되는지 확인한다.

        .env 파일의 영향을 받지 않도록 관련 환경변수를 제거한다.
        """
        # .env에서 로드된 환경변수 영향 제거
        for env_var in (
            "OPENAI_API_KEY",
            "PINECONE_API_KEY",
            "PINECONE_ENVIRONMENT",
            "PINECONE_INDEX_NAME",
            "NARRATIVE_MODEL_NAME",
            "NARRATIVE_TEMPERATURE",
            "NARRATIVE_MAX_TOKENS",
            "EMBEDDING_MODEL",
            "EMBEDDING_DIMENSION",
            "CHUNK_SIZE",
            "CHUNK_OVERLAP",
            "RETRIEVAL_TOP_K",
            "FACT_CHECK_ENABLED",
            "CONFIDENCE_THRESHOLD",
            "DEFAULT_LANGUAGE",
            "DEFAULT_INDUSTRY",
        ):
            monkeypatch.delenv(env_var, raising=False)

        config = NarrativeConfig(
            _env_file=None,
            openai_api_key="",
            pinecone_api_key="",
        )

        assert config.narrative_model_name == "gpt-4o"
        assert config.narrative_temperature == 0.3
        assert config.narrative_max_tokens == 4096
        assert config.embedding_model == "text-embedding-3-small"
        assert config.embedding_dimension == 1536
        assert config.chunk_size == 512
        assert config.chunk_overlap == 64
        assert config.retrieval_top_k == 5
        assert config.fact_check_enabled is True
        assert config.confidence_threshold == 0.7
        assert config.default_language == "ko"
        assert config.default_industry is None
        assert config.pinecone_environment == "us-east-1"
        assert config.pinecone_index_name == "im-narratives"

    @pytest.mark.parametrize(
        "openai_key, pinecone_key, expected_openai, expected_pinecone",
        [
            ("", "", False, False),
            ("sk-test-key", "", True, False),
            ("", "pc-test-key", False, True),
            ("sk-test-key", "pc-test-key", True, True),
        ],
        ids=[
            "둘다_미설정",
            "OpenAI만_설정",
            "Pinecone만_설정",
            "둘다_설정",
        ],
    )
    def test_has_openai_and_has_pinecone_properties(
        self,
        openai_key: str,
        pinecone_key: str,
        expected_openai: bool,
        expected_pinecone: bool,
    ) -> None:
        """has_openai/has_pinecone 프로퍼티가 API 키 유무를 올바르게 반영하는지 확인한다."""
        config = NarrativeConfig(
            openai_api_key=openai_key,
            pinecone_api_key=pinecone_key,
        )
        assert config.has_openai is expected_openai
        assert config.has_pinecone is expected_pinecone

    def test_chunk_overlap_must_be_less_than_chunk_size(self) -> None:
        """chunk_overlap이 chunk_size 이상이면 ValidationError가 발생한다."""
        with pytest.raises(ValidationError, match="chunk_overlap"):
            NarrativeConfig(
                openai_api_key="",
                pinecone_api_key="",
                chunk_size=100,
                chunk_overlap=100,
            )

        with pytest.raises(ValidationError, match="chunk_overlap"):
            NarrativeConfig(
                openai_api_key="",
                pinecone_api_key="",
                chunk_size=100,
                chunk_overlap=200,
            )
