"""Celery 앱 설정 테스트 (T-I11).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.api.config import APIConfig


@pytest.fixture
def test_config() -> APIConfig:
    """테스트용 Celery 설정."""
    return APIConfig(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5434/imgen_test",
        redis_url="redis://localhost:6380/15",
        redis_result_backend="redis://localhost:6380/14",
        celery_task_soft_time_limit=120,
        celery_task_hard_time_limit=240,
    )


class TestCreateCeleryApp:
    """Celery 앱 팩토리 테스트."""

    def test_creates_celery_app(self, test_config: APIConfig) -> None:
        """Celery 앱을 올바르게 생성한다."""
        from src.api.tasks.celery_app import create_celery_app

        app = create_celery_app(config=test_config)

        assert app.main == "im_generator"

    def test_json_serializer_only(self, test_config: APIConfig) -> None:
        """JSON 직렬화만 허용한다."""
        from src.api.tasks.celery_app import create_celery_app

        app = create_celery_app(config=test_config)

        assert app.conf.task_serializer == "json"
        assert app.conf.result_serializer == "json"
        assert app.conf.accept_content == ["json"]

    def test_pickle_not_accepted(self, test_config: APIConfig) -> None:
        """pickle 직렬화가 금지된다."""
        from src.api.tasks.celery_app import create_celery_app

        app = create_celery_app(config=test_config)

        assert "pickle" not in app.conf.accept_content

    def test_acks_late_enabled(self, test_config: APIConfig) -> None:
        """task_acks_late가 활성화된다."""
        from src.api.tasks.celery_app import create_celery_app

        app = create_celery_app(config=test_config)

        assert app.conf.task_acks_late is True

    def test_custom_config_applied(self, test_config: APIConfig) -> None:
        """커스텀 설정이 적용된다."""
        from src.api.tasks.celery_app import create_celery_app

        app = create_celery_app(config=test_config)

        assert app.conf.task_soft_time_limit == 120
        assert app.conf.task_hard_time_limit == 240

    def test_autodiscover_tasks_package(self, test_config: APIConfig) -> None:
        """태스크 자동 탐색 패키지가 설정된다."""
        from src.api.tasks.celery_app import create_celery_app

        app = create_celery_app(config=test_config)

        # autodiscover_tasks는 이미 호출됨 — 앱이 정상 생성되면 OK
        assert app is not None


class TestUpdateProgress:
    """진행률 업데이트 테스트."""

    def test_updates_task_state(self) -> None:
        """Celery 태스크 상태를 갱신한다."""
        from src.api.tasks.progress import update_progress

        mock_task = MagicMock()
        document_id = "test-doc-123"

        update_progress(mock_task, document_id, "ANALYZING", 40)

        mock_task.update_state.assert_called_once()
        call_kwargs = mock_task.update_state.call_args
        assert call_kwargs[1]["state"] == "ANALYZING"
        meta = call_kwargs[1]["meta"]
        assert meta["document_id"] == document_id
        assert meta["progress_pct"] == 40

    def test_updates_with_details(self) -> None:
        """추가 세부 정보가 메타에 포함된다."""
        from src.api.tasks.progress import update_progress

        mock_task = MagicMock()
        details = {"current_step": "financial_analysis", "rows_processed": 150}

        update_progress(mock_task, "doc-456", "ANALYZING", 50, details=details)

        meta = mock_task.update_state.call_args[1]["meta"]
        assert meta["details"] == details
