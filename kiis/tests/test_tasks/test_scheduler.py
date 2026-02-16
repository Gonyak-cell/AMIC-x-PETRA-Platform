"""스케줄러 초기화/종료 테스트"""

from unittest.mock import AsyncMock, patch

import pytest

from app.tasks.scheduler import close_scheduler, get_scheduler, init_scheduler


class TestSchedulerLifecycle:
    """스케줄러 init/close lifecycle 테스트"""

    async def test_init_scheduler_disabled(self):
        """SCHEDULER_ENABLED=False이면 스케줄러를 생성하지 않는다."""
        with patch("app.tasks.scheduler.settings") as mock_settings:
            mock_settings.SCHEDULER_ENABLED = False

            await init_scheduler()
            assert get_scheduler() is None

    async def test_init_scheduler_enabled(self):
        """SCHEDULER_ENABLED=True이면 스케줄러를 생성하고 작업을 등록한다."""
        with (
            patch("app.tasks.scheduler.settings") as mock_settings,
            patch("app.tasks.scheduler.AsyncIOScheduler") as mock_scheduler_cls,
        ):
            mock_settings.SCHEDULER_ENABLED = True
            mock_settings.DART_SYNC_INTERVAL_HOURS = 1
            mock_settings.NEWS_COLLECT_INTERVAL_HOURS = 2
            mock_settings.REPUTATION_RECALC_HOUR = 3
            mock_settings.MANAGER_TRACKING_DAY_OF_WEEK = "mon"
            mock_settings.PORTFOLIO_CHECK_HOUR = 5
            mock_settings.WATCHLIST_ALERT_INTERVAL_HOURS = 6

            mock_scheduler = mock_scheduler_cls.return_value
            mock_scheduler.get_jobs.return_value = [None] * 6

            await init_scheduler()

            mock_scheduler.start.assert_called_once()
            assert mock_scheduler.add_job.call_count == 6

        # 정리
        await close_scheduler()

    async def test_close_scheduler_when_none(self):
        """스케줄러가 None이면 close_scheduler가 에러 없이 실행된다."""
        # _scheduler를 None으로 보장
        import app.tasks.scheduler as mod

        mod._scheduler = None
        await close_scheduler()  # 에러 없이 통과

    async def test_close_scheduler_calls_shutdown(self):
        """스케줄러가 존재하면 shutdown(wait=False)을 호출한다."""
        import app.tasks.scheduler as mod

        from unittest.mock import MagicMock

        mock_scheduler = MagicMock()
        mod._scheduler = mock_scheduler

        await close_scheduler()

        mock_scheduler.shutdown.assert_called_once_with(wait=False)
        assert mod._scheduler is None


class TestSchedulerJobRegistration:
    """등록된 작업 ID 검증"""

    async def test_job_ids(self):
        """6개 작업이 올바른 ID로 등록되는지 확인한다."""
        with (
            patch("app.tasks.scheduler.settings") as mock_settings,
            patch("app.tasks.scheduler.AsyncIOScheduler") as mock_scheduler_cls,
        ):
            mock_settings.SCHEDULER_ENABLED = True
            mock_settings.DART_SYNC_INTERVAL_HOURS = 1
            mock_settings.NEWS_COLLECT_INTERVAL_HOURS = 2
            mock_settings.REPUTATION_RECALC_HOUR = 3
            mock_settings.MANAGER_TRACKING_DAY_OF_WEEK = "mon"
            mock_settings.PORTFOLIO_CHECK_HOUR = 5
            mock_settings.WATCHLIST_ALERT_INTERVAL_HOURS = 6

            mock_scheduler = mock_scheduler_cls.return_value
            mock_scheduler.get_jobs.return_value = [None] * 6

            await init_scheduler()

            job_ids = [call.kwargs["id"] for call in mock_scheduler.add_job.call_args_list]
            expected = {"dart_sync", "news_collect", "reputation_recalc", "manager_tracking", "portfolio_check", "watchlist_alerts"}
            assert set(job_ids) == expected

        await close_scheduler()
