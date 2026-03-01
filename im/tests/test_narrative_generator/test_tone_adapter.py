"""ToneAdapter 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

시스템 지시문 반환, 적절한 톤 검사, 부적절한 톤 검사를 테스트한다.
"""

from __future__ import annotations

from src.narrative_generator.korean_finance.tone_adapter import (
    ToneAdapter,
    ToneCheckResult,
)


# ---------------------------------------------------------------------------
# TestToneAdapter
# ---------------------------------------------------------------------------


class TestToneAdapter:
    """ToneAdapter 톤 관리 테스트."""

    def test_get_system_instruction_returns_non_empty(self) -> None:
        """get_system_instruction이 비어있지 않은 문자열을 반환한다."""
        adapter = ToneAdapter()
        instruction = adapter.get_system_instruction()

        assert isinstance(instruction, str)
        assert len(instruction) > 0
        # 톤 가이드라인 핵심 내용 포함 확인
        assert "Factual Optimism" in instruction

    def test_check_tone_appropriate_text(self) -> None:
        """부정적 마커가 없는 적절한 텍스트는 is_appropriate=True를 반환한다."""
        adapter = ToneAdapter()
        text = (
            "테스트기업은 견조한 성장세를 유지하고 있으며, "
            "안정적인 수익 구조를 바탕으로 지속적인 시장 확대를 추진하고 있습니다."
        )

        result = adapter.check_tone(text)

        assert isinstance(result, ToneCheckResult)
        assert result.is_appropriate is True
        assert len(result.negative_markers_found) == 0
        # 긍정적 마커 탐지 확인
        assert len(result.positive_markers_found) > 0

    def test_check_tone_inappropriate_text(self) -> None:
        """부정적 마커('획기적')가 포함된 텍스트는 is_appropriate=False를 반환한다."""
        adapter = ToneAdapter()
        text = (
            "테스트기업은 획기적인 기술 혁신을 통해 "
            "압도적인 시장 지배력을 확보하였습니다."
        )

        result = adapter.check_tone(text)

        assert isinstance(result, ToneCheckResult)
        assert result.is_appropriate is False
        assert len(result.negative_markers_found) >= 1
        # '획기적'과 '압도적' 두 마커 모두 탐지
        assert "획기적" in result.negative_markers_found
        assert "압도적" in result.negative_markers_found
