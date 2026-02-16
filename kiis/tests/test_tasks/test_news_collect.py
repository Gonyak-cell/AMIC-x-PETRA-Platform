"""뉴스 자동 수집 태스크 테스트"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.news_collect import run_news_collect


class TestRunNewsCollect:
    """run_news_collect 태스크 테스트"""

    async def test_collect_success(self):
        """뉴스 수집이 성공적으로 실행된다."""
        mock_result1 = MagicMock()
        mock_result1.collected = 5
        mock_result2 = MagicMock()
        mock_result2.collected = 3

        with (
            patch("app.tasks.news_collect.async_session_factory") as mock_factory,
            patch("app.tasks.news_collect.NewsService") as mock_svc_cls,
        ):
            mock_svc = mock_svc_cls.return_value
            mock_svc.collect_all = AsyncMock(return_value=[mock_result1, mock_result2])

            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await run_news_collect()

        assert result["sources"] == 2
        assert result["total_collected"] == 8

    async def test_collect_exception(self):
        """뉴스 수집 중 예외가 발생해도 결과를 반환한다."""
        with (
            patch("app.tasks.news_collect.async_session_factory") as mock_factory,
            patch("app.tasks.news_collect.NewsService") as mock_svc_cls,
        ):
            mock_svc = mock_svc_cls.return_value
            mock_svc.collect_all = AsyncMock(side_effect=RuntimeError("RSS error"))

            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await run_news_collect()

        assert result["sources"] == 0
        assert result["total_collected"] == 0
