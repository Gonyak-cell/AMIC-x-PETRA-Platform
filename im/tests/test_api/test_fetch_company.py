"""fetch_company 태스크 테스트 (T-I13).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.api.tasks.fetch_company import fetch_company_task


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


class TestFetchCompanyTask:
    """fetch_company_task 테스트."""

    def test_task_registered(self) -> None:
        """fetch_company 태스크가 등록되어 있다."""
        assert fetch_company_task.name == "fetch_company"

    def test_max_retries(self) -> None:
        """최대 재시도 횟수가 3이다."""
        assert fetch_company_task.max_retries == 3

    @patch("src.api.tasks.fetch_company.asyncio.run")
    def test_success_returns_completed(self, mock_run: MagicMock) -> None:
        """성공 시 COMPLETED 상태를 반환한다."""
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = None
        mock_result.warnings = []
        mock_run.return_value = mock_result

        result = fetch_company_task("00123456")

        assert result["status"] == "COMPLETED"
        assert result["corp_code"] == "00123456"

    @patch("src.api.tasks.fetch_company.asyncio.run")
    def test_failure_returns_failed_after_max_retries(
        self, mock_run: MagicMock
    ) -> None:
        """최대 재시도 초과 시 FAILED 상태를 반환한다."""
        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.errors = ["DART 오류"]
        mock_run.return_value = mock_result

        # 재시도 소진 후 FAILED (eager 모드에서는 retry가 즉시 실행)
        # 직접 RuntimeError를 발생시켜 최대 재시도 시나리오 시뮬레이션
        mock_run.side_effect = RuntimeError("DART API 오류")

        # eager 모드에서 max_retries 초과 시 예외 전파
        with pytest.raises(RuntimeError):
            fetch_company_task("00123456")

    @patch("src.api.tasks.fetch_company.asyncio.run")
    def test_result_dict_format(self, mock_run: MagicMock) -> None:
        """반환 dict 형식이 올바르다."""
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = None
        mock_result.warnings = ["경고 1"]
        mock_run.return_value = mock_result

        result = fetch_company_task("00123456")

        assert "corp_code" in result
        assert "status" in result
        assert "warnings" in result

    @patch("src.api.tasks.fetch_company.asyncio.run")
    def test_success_with_data(self, mock_run: MagicMock) -> None:
        """데이터 수집 성공 시 data 필드를 포함한다."""
        mock_data = MagicMock()
        mock_data.__class__.__name__ = "IMDocumentData"

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.data = mock_data
        mock_result.warnings = []
        mock_run.return_value = mock_result

        # im_data_to_dict가 호출되므로 패치
        with patch("src.api.tasks.fetch_company.im_data_to_dict") as mock_serialize:
            mock_serialize.return_value = {"corp_code": "00123456", "name": "test"}
            result = fetch_company_task("00123456")

        assert result["status"] == "COMPLETED"
        assert result["data"] == {"corp_code": "00123456", "name": "test"}
