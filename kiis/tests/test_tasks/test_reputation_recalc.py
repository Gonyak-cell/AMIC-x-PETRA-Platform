"""평판 재계산 태스크 테스트"""

from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.reputation_recalc import run_reputation_recalc


class FakeSession:
    """async context manager를 흉내내는 페이크 DB 세션"""

    def __init__(self, execute_returns=None):
        self._execute_returns = execute_returns or []
        self._call_idx = 0
        self.commit = AsyncMock()

    async def execute(self, stmt):
        if self._call_idx < len(self._execute_returns):
            result = self._execute_returns[self._call_idx]
            self._call_idx += 1
            return result
        return MagicMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class TestRunReputationRecalc:
    """run_reputation_recalc 태스크 테스트"""

    async def test_recalc_success(self):
        """평판 재계산이 성공적으로 실행된다."""
        with (
            patch("app.tasks.reputation_recalc.async_session_factory") as mock_factory,
            patch("app.tasks.reputation_recalc.ReputationService") as mock_rep_cls,
            patch("app.tasks.reputation_recalc.AlertService"),
        ):
            mock_rep = mock_rep_cls.return_value
            mock_score = MagicMock()
            mock_score.status_tag = "Stable"
            mock_rep.calculate_reputation = AsyncMock(return_value=mock_score)

            # 첫 세션: companies 조회
            query_result = MagicMock()
            query_result.all.return_value = [(1, "00100001", "기업A"), (2, "00100002", "기업B")]
            query_session = FakeSession(execute_returns=[query_result])

            # 각 기업별 세션: prev_status 조회
            prev_result = MagicMock()
            prev_result.scalar_one_or_none.return_value = "Stable"

            sessions = [query_session, FakeSession(execute_returns=[prev_result]), FakeSession(execute_returns=[prev_result])]
            idx = [0]

            def make_session():
                s = sessions[idx[0]]
                idx[0] += 1
                return s

            mock_factory.side_effect = make_session

            result = await run_reputation_recalc()

        assert result["total"] == 2
        assert result["recalculated"] == 2
        assert result["errors"] == 0

    async def test_recalc_status_change_detected(self):
        """상태 변경(Stable→Risk) 시 status_changes가 카운트된다."""
        with (
            patch("app.tasks.reputation_recalc.async_session_factory") as mock_factory,
            patch("app.tasks.reputation_recalc.ReputationService") as mock_rep_cls,
            patch("app.tasks.reputation_recalc.AlertService"),
            patch("app.tasks.reputation_recalc._notify_watchlist_subscribers", new_callable=AsyncMock) as mock_notify,
        ):
            mock_rep = mock_rep_cls.return_value
            mock_score = MagicMock()
            mock_score.status_tag = "Risk"
            mock_rep.calculate_reputation = AsyncMock(return_value=mock_score)

            query_result = MagicMock()
            query_result.all.return_value = [(1, "00100001", "기업A")]
            query_session = FakeSession(execute_returns=[query_result])

            prev_result = MagicMock()
            prev_result.scalar_one_or_none.return_value = "Stable"
            work_session = FakeSession(execute_returns=[prev_result])

            sessions = [query_session, work_session]
            idx = [0]

            def make_session():
                s = sessions[idx[0]]
                idx[0] += 1
                return s

            mock_factory.side_effect = make_session

            result = await run_reputation_recalc()

        assert result["status_changes"] == 1
        mock_notify.assert_called_once()

    async def test_recalc_error_isolation(self):
        """한 기업 실패 시에도 나머지는 처리된다."""
        with (
            patch("app.tasks.reputation_recalc.async_session_factory") as mock_factory,
            patch("app.tasks.reputation_recalc.ReputationService") as mock_rep_cls,
            patch("app.tasks.reputation_recalc.AlertService"),
        ):
            mock_rep = mock_rep_cls.return_value

            async def calc_side_effect(db, corp_code):
                if corp_code == "00100001":
                    raise RuntimeError("NLP error")
                score = MagicMock()
                score.status_tag = "Stable"
                return score

            mock_rep.calculate_reputation = AsyncMock(side_effect=calc_side_effect)

            query_result = MagicMock()
            query_result.all.return_value = [(1, "00100001", "기업A"), (2, "00100002", "기업B")]
            query_session = FakeSession(execute_returns=[query_result])

            prev_result = MagicMock()
            prev_result.scalar_one_or_none.return_value = None

            sessions = [query_session, FakeSession(execute_returns=[prev_result]), FakeSession(execute_returns=[prev_result])]
            idx = [0]

            def make_session():
                s = sessions[idx[0]]
                idx[0] += 1
                return s

            mock_factory.side_effect = make_session

            result = await run_reputation_recalc()

        assert result["total"] == 2
        assert result["recalculated"] == 1
        assert result["errors"] == 1
