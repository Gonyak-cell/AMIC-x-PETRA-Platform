"""narrative 태스크 테스트 (T-I14).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.api.tasks.narrative import generate_narrative_task

_ORCHESTRATOR_PATH = "src.narrative_generator.engine.orchestrator.NarrativeOrchestrator"


@pytest.fixture(autouse=True)
def _celery_eager():
    """Celery를 eager 모드로 설정한다."""
    from src.api.tasks.celery_app import celery_app

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
    yield
    celery_app.conf.update(
        task_always_eager=False,
        task_eager_propagates=False,
    )


class TestGenerateNarrativeTask:
    """generate_narrative_task 테스트."""

    def test_task_registered(self) -> None:
        """generate_narrative 태스크가 등록되어 있다."""
        assert generate_narrative_task.name == "generate_narrative"

    def test_max_retries(self) -> None:
        """최대 재시도 횟수가 2이다."""
        assert generate_narrative_task.max_retries == 2

    def test_soft_time_limit(self) -> None:
        """soft_time_limit이 180초이다."""
        assert generate_narrative_task.soft_time_limit == 180

    @patch(_ORCHESTRATOR_PATH)
    @patch("src.api.tasks.narrative.dict_to_im_data")
    def test_success_returns_completed(
        self,
        mock_dict_to_im: MagicMock,
        mock_orchestrator_cls: MagicMock,
    ) -> None:
        """성공 시 COMPLETED 상태를 반환한다."""
        mock_data = MagicMock()
        mock_dict_to_im.return_value = mock_data

        mock_section = MagicMock()
        mock_section.text = "생성된 내러티브 텍스트"
        mock_orchestrator = MagicMock()
        mock_orchestrator.generate_section.return_value = mock_section
        mock_orchestrator_cls.return_value = mock_orchestrator

        result = generate_narrative_task({"corp_code": "00123456"}, "executive_summary")

        assert result["status"] == "COMPLETED"
        assert result["section_id"] == "executive_summary"
        assert result["narrative"] == "생성된 내러티브 텍스트"

    @patch("src.api.tasks.narrative.dict_to_im_data")
    def test_failure_propagates_in_eager(self, mock_dict_to_im: MagicMock) -> None:
        """실패 시 eager 모드에서 예외가 전파된다."""
        mock_dict_to_im.side_effect = RuntimeError("LLM API 오류")

        with pytest.raises(RuntimeError, match="LLM API"):
            generate_narrative_task({"corp_code": "00123456"}, "executive_summary")

    @patch(_ORCHESTRATOR_PATH)
    @patch("src.api.tasks.narrative.dict_to_im_data")
    def test_result_dict_format(
        self,
        mock_dict_to_im: MagicMock,
        mock_orchestrator_cls: MagicMock,
    ) -> None:
        """반환 dict 형식이 올바르다."""
        mock_dict_to_im.return_value = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "텍스트"
        mock_orchestrator_cls.return_value.generate_section.return_value = mock_result

        result = generate_narrative_task({"corp_code": "00123456"}, "company_overview")

        assert "section_id" in result
        assert "narrative" in result
        assert "status" in result
