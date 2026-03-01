"""BasePrompt 및 PromptRegistry 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

기본 레지스트리 생성, 프롬프트 조회, 미등록 섹션 예외, 데이터 추출을 테스트한다.
"""

from __future__ import annotations

import pytest

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.exceptions import PromptNotFoundError
from src.narrative_generator.prompts import create_default_registry
from src.narrative_generator.prompts.base import BasePrompt
from src.narrative_generator.prompts.section_prompts.core import ExecutiveSummaryPrompt


# ---------------------------------------------------------------------------
# TestCreateDefaultRegistry
# ---------------------------------------------------------------------------


class TestCreateDefaultRegistry:
    """create_default_registry 함수 테스트."""

    def test_default_registry_contains_15_prompts(self) -> None:
        """기본 레지스트리가 15개 프롬프트를 포함하는지 확인한다."""
        registry = create_default_registry()
        all_prompts = registry.get_all()

        assert len(all_prompts) == 15

    def test_registry_get_executive_summary(self) -> None:
        """executive_summary 프롬프트가 올바르게 조회되는지 확인한다."""
        registry = create_default_registry()
        prompt = registry.get("executive_summary")

        assert isinstance(prompt, BasePrompt)
        assert isinstance(prompt, ExecutiveSummaryPrompt)
        assert prompt.section_id == "executive_summary"

    def test_registry_get_nonexistent_raises_error(self) -> None:
        """미등록 section_id 조회 시 PromptNotFoundError가 발생한다."""
        registry = create_default_registry()

        with pytest.raises(PromptNotFoundError) as exc_info:
            registry.get("nonexistent")

        assert "nonexistent" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TestExecutiveSummaryPrompt
# ---------------------------------------------------------------------------


class TestExecutiveSummaryPrompt:
    """ExecutiveSummaryPrompt 데이터 추출 테스트."""

    def test_extract_data_returns_expected_keys(
        self, sample_im_data: IMDocumentData
    ) -> None:
        """extract_data가 매출액, 영업이익, 당기순이익, EBITDA 키를 반환한다."""
        prompt = ExecutiveSummaryPrompt()
        extracted = prompt.extract_data(sample_im_data)

        assert isinstance(extracted, dict)
        assert "매출액" in extracted
        assert "영업이익" in extracted
        assert "당기순이익" in extracted
        assert "EBITDA" in extracted

        # 투자 하이라이트
        assert "투자 하이라이트" in extracted
        assert isinstance(extracted["투자 하이라이트"], list)
        assert len(extracted["투자 하이라이트"]) == 3

        # 딜 구조 (sample_im_data에 deal_structure가 있으므로)
        assert "거래유형" in extracted
