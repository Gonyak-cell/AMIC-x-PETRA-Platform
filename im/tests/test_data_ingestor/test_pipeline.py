"""E2E 파이프라인 테스트."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data_ingestor.cache import CacheConfig
from src.data_ingestor.exceptions import PipelineError
from src.data_ingestor.pipeline import (
    CollectionResult,
    DataCollectionPipeline,
    DataPriority,
    PipelineConfig,
    StepResult,
)


# ============================================================================
# DataPriority 테스트
# ============================================================================


class TestDataPriority:
    """DataPriority enum 테스트."""

    def test_required_value(self) -> None:
        assert DataPriority.REQUIRED.value == "required"

    def test_important_value(self) -> None:
        assert DataPriority.IMPORTANT.value == "important"

    def test_optional_value(self) -> None:
        assert DataPriority.OPTIONAL.value == "optional"


# ============================================================================
# StepResult 테스트
# ============================================================================


class TestStepResult:
    """StepResult 테스트."""

    def test_success_step(self) -> None:
        step = StepResult(
            step_name="테스트 단계",
            success=True,
            priority=DataPriority.REQUIRED,
            duration_ms=100.0,
        )
        assert step.success
        assert step.error is None
        assert step.duration_ms == 100.0

    def test_failed_step(self) -> None:
        step = StepResult(
            step_name="실패 단계",
            success=False,
            priority=DataPriority.IMPORTANT,
            error="연결 실패",
            duration_ms=50.0,
        )
        assert not step.success
        assert step.error == "연결 실패"

    def test_default_values(self) -> None:
        step = StepResult(
            step_name="기본",
            success=True,
            priority=DataPriority.OPTIONAL,
        )
        assert step.error is None
        assert step.duration_ms == 0.0


# ============================================================================
# CollectionResult 테스트
# ============================================================================


class TestCollectionResult:
    """CollectionResult 테스트."""

    def test_empty_result(self) -> None:
        result = CollectionResult()
        assert result.data is None
        assert result.steps == []
        assert result.warnings == []
        assert result.errors == []
        assert result.duration_ms == 0.0

    def test_is_success_all_required_pass(self) -> None:
        """필수 단계가 모두 성공하면 is_success = True."""
        result = CollectionResult()
        result.data = MagicMock()  # data가 있어야 함
        result.steps = [
            StepResult("기업정보", True, DataPriority.REQUIRED),
            StepResult("재무제표", True, DataPriority.IMPORTANT),
            StepResult("뉴스", False, DataPriority.OPTIONAL),
        ]
        assert result.is_success

    def test_is_success_required_fail(self) -> None:
        """필수 단계가 실패하면 is_success = False."""
        result = CollectionResult()
        result.data = MagicMock()
        result.steps = [
            StepResult("기업정보", False, DataPriority.REQUIRED),
            StepResult("재무제표", True, DataPriority.IMPORTANT),
        ]
        assert not result.is_success

    def test_is_success_no_data(self) -> None:
        """data가 None이면 is_success = False."""
        result = CollectionResult()
        result.data = None
        result.steps = [
            StepResult("기업정보", True, DataPriority.REQUIRED),
        ]
        assert not result.is_success

    def test_is_success_no_required_steps(self) -> None:
        """필수 단계가 없고 data가 있으면 is_success = True."""
        result = CollectionResult()
        result.data = MagicMock()
        result.steps = [
            StepResult("뉴스", False, DataPriority.OPTIONAL),
        ]
        assert result.is_success

    def test_summary(self) -> None:
        """summary 문자열 생성 테스트."""
        result = CollectionResult()
        result.duration_ms = 1500.0
        result.warnings = ["경고1"]
        result.steps = [
            StepResult("단계1", True, DataPriority.REQUIRED),
            StepResult("단계2", False, DataPriority.OPTIONAL),
            StepResult("단계3", True, DataPriority.IMPORTANT),
        ]
        summary = result.summary
        assert "2/3" in summary  # 2 성공 / 3 전체
        assert "1 실패" in summary
        assert "1 경고" in summary
        assert "1500ms" in summary


# ============================================================================
# PipelineConfig 테스트
# ============================================================================


class TestPipelineConfig:
    """PipelineConfig 테스트."""

    def test_default_config(self) -> None:
        config = PipelineConfig(dart_api_key="test_key")
        assert config.dart_api_key == "test_key"
        assert config.financial_years == 3
        assert config.base_year is None
        assert config.include_shareholders is True
        assert config.include_dividends is True
        assert config.include_news is True
        assert config.include_web_info is True
        assert config.news_days == 30
        assert config.news_count == 20
        assert config.enable_cache is True
        assert config.cache_config is None
        assert config.timeout == 300.0

    def test_custom_config(self) -> None:
        config = PipelineConfig(
            dart_api_key="custom_key",
            financial_years=5,
            base_year=2025,
            include_news=False,
            include_web_info=False,
            enable_cache=False,
        )
        assert config.financial_years == 5
        assert config.base_year == 2025
        assert config.include_news is False
        assert config.include_web_info is False
        assert config.enable_cache is False


# ============================================================================
# DataCollectionPipeline 테스트
# ============================================================================


def _make_mock_company_info(
    corp_code: str = "00126380",
    corp_name: str = "삼성전자",
    hm_url: str = "https://www.samsung.com",
) -> MagicMock:
    """모킹된 DartCompanyInfo 생성."""
    company = MagicMock()
    company.corp_code = corp_code
    company.corp_name = corp_name
    company.corp_name_eng = "Samsung Electronics"
    company.stock_code = "005930"
    company.ceo_nm = "한종희"
    company.corp_cls = "Y"
    company.hm_url = hm_url
    company.ir_url = None
    company.adres = "경기도 수원시"
    company.phn_no = "031-200-1114"
    company.fax_no = None
    company.induty_code = "264"
    company.est_dt = "19690113"
    company.acc_mt = "12"
    return company


def _make_mock_financial_statements(
    corp_code: str = "00126380",
    bsns_year: str = "2025",
) -> MagicMock:
    """모킹된 FinancialStatementsCollection 생성."""
    fs = MagicMock()
    fs.corp_code = corp_code
    fs.bsns_year = bsns_year
    fs.fs_div = "CFS"
    fs.items = []
    fs.model_dump.return_value = {"corp_code": corp_code, "items": []}
    fs.get_by_account.return_value = None
    return fs


class TestDataCollectionPipeline:
    """DataCollectionPipeline 테스트."""

    @pytest.fixture
    def config(self) -> PipelineConfig:
        """기본 파이프라인 설정."""
        return PipelineConfig(
            dart_api_key="test_key",
            financial_years=3,
            base_year=2025,
            include_news=False,
            include_web_info=False,
            enable_cache=False,
        )

    @pytest.fixture
    def config_with_cache(self) -> PipelineConfig:
        """캐시 활성화된 파이프라인 설정."""
        return PipelineConfig(
            dart_api_key="test_key",
            financial_years=2,
            base_year=2025,
            include_news=False,
            include_web_info=False,
            enable_cache=True,
            cache_config=CacheConfig(enable_redis=False),
        )

    @pytest.mark.asyncio
    async def test_collect_all_success(self, config: PipelineConfig) -> None:
        """모든 단계 성공 시 테스트."""
        mock_company = _make_mock_company_info()
        mock_fs_2025 = _make_mock_financial_statements(bsns_year="2025")
        mock_fs_2024 = _make_mock_financial_statements(bsns_year="2024")
        mock_fs_2023 = _make_mock_financial_statements(bsns_year="2023")
        mock_shareholders = [
            MagicMock(repror="이재용", share_count=100, share_ratio=5.0)
        ]
        mock_dividends = [MagicMock()]

        with patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.side_effect = [
                mock_fs_2025,
                mock_fs_2024,
                mock_fs_2023,
            ]
            mock_client.get_major_shareholders.return_value = mock_shareholders
            mock_client.get_dividend.return_value = mock_dividends

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            assert result.is_success
            assert result.data is not None
            assert len(result.errors) == 0
            # 기업정보 + 재무제표 3건 + 주주 + 배당 = 6 단계
            assert len(result.steps) == 6
            assert all(s.success for s in result.steps)

    @pytest.mark.asyncio
    async def test_collect_company_info_failure(self, config: PipelineConfig) -> None:
        """기업정보 실패 시 즉시 중단 테스트."""
        with patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.side_effect = Exception("API 오류")

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            assert not result.is_success
            assert result.data is None
            assert len(result.errors) > 0
            # 기업정보 실패 → Phase 2 진행하지 않음
            assert len(result.steps) == 1

    @pytest.mark.asyncio
    async def test_collect_financial_partial_failure(
        self, config: PipelineConfig
    ) -> None:
        """일부 재무제표 실패 시 계속 진행 테스트."""
        mock_company = _make_mock_company_info()
        mock_fs_2025 = _make_mock_financial_statements(bsns_year="2025")
        mock_shareholders = [
            MagicMock(repror="이재용", share_count=100, share_ratio=5.0)
        ]
        mock_dividends = [MagicMock()]

        with patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.side_effect = [
                mock_fs_2025,
                Exception("2024 데이터 없음"),
                Exception("2023 데이터 없음"),
            ]
            mock_client.get_major_shareholders.return_value = mock_shareholders
            mock_client.get_dividend.return_value = mock_dividends

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            # 기업정보는 성공했으므로 data가 있어야 함
            assert result.is_success
            assert result.data is not None
            # 재무제표 2건 실패 → warnings에 기록
            assert len(result.warnings) == 2

    @pytest.mark.asyncio
    async def test_collect_optional_failure(self, config: PipelineConfig) -> None:
        """선택 데이터 실패 시 계속 진행 테스트."""
        mock_company = _make_mock_company_info()
        mock_fs = _make_mock_financial_statements()

        with patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.return_value = mock_fs
            mock_client.get_major_shareholders.side_effect = Exception("주주정보 없음")
            mock_client.get_dividend.side_effect = Exception("배당정보 없음")

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            assert result.is_success
            assert result.data is not None
            # 주주/배당 실패 → warnings
            assert len(result.warnings) == 2

    @pytest.mark.asyncio
    async def test_collect_with_cache(self, config_with_cache: PipelineConfig) -> None:
        """캐시 활성화된 파이프라인 테스트."""
        mock_company = _make_mock_company_info()
        mock_company.model_dump.return_value = {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "corp_cls": "Y",
        }
        mock_fs = _make_mock_financial_statements()

        with patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.return_value = mock_fs
            mock_client.get_major_shareholders.return_value = []
            mock_client.get_dividend.return_value = []

            async with DataCollectionPipeline(config_with_cache) as pipeline:
                result = await pipeline.collect("00126380")

            assert result.is_success

    @pytest.mark.asyncio
    async def test_collect_no_shareholders_dividends(self) -> None:
        """주주/배당 수집 비활성화 테스트."""
        config = PipelineConfig(
            dart_api_key="test_key",
            financial_years=1,
            base_year=2025,
            include_shareholders=False,
            include_dividends=False,
            include_news=False,
            include_web_info=False,
            enable_cache=False,
        )

        mock_company = _make_mock_company_info()
        mock_fs = _make_mock_financial_statements()

        with patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.return_value = mock_fs

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            assert result.is_success
            # 기업정보 + 재무제표 1건 = 2 단계
            assert len(result.steps) == 2
            mock_client.get_major_shareholders.assert_not_called()
            mock_client.get_dividend.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_with_news(self) -> None:
        """뉴스 크롤링 포함 테스트."""
        config = PipelineConfig(
            dart_api_key="test_key",
            financial_years=1,
            base_year=2025,
            include_shareholders=False,
            include_dividends=False,
            include_news=True,
            include_web_info=False,
            enable_cache=False,
        )

        mock_company = _make_mock_company_info()
        mock_fs = _make_mock_financial_statements()

        with (
            patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient,
            patch(
                "src.data_ingestor.pipeline.DataCollectionPipeline._fetch_news"
            ) as mock_fetch_news,
        ):
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.return_value = mock_fs
            mock_fetch_news.return_value = []

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            assert result.is_success
            mock_fetch_news.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_with_web_info(self) -> None:
        """웹사이트 크롤링 포함 테스트."""
        config = PipelineConfig(
            dart_api_key="test_key",
            financial_years=1,
            base_year=2025,
            include_shareholders=False,
            include_dividends=False,
            include_news=False,
            include_web_info=True,
            enable_cache=False,
        )

        mock_company = _make_mock_company_info(hm_url="https://www.samsung.com")
        mock_fs = _make_mock_financial_statements()

        with (
            patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient,
            patch(
                "src.data_ingestor.pipeline.DataCollectionPipeline._fetch_web_info"
            ) as mock_fetch_web,
        ):
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.return_value = mock_fs
            mock_fetch_web.return_value = None

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            assert result.is_success
            mock_fetch_web.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_duration_tracking(self, config: PipelineConfig) -> None:
        """실행 시간 추적 테스트."""
        mock_company = _make_mock_company_info()
        mock_fs = _make_mock_financial_statements()

        with patch("src.data_ingestor.pipeline.DartAPIClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client.get_company_info.return_value = mock_company
            mock_client.get_financial_statements.return_value = mock_fs
            mock_client.get_major_shareholders.return_value = []
            mock_client.get_dividend.return_value = []

            async with DataCollectionPipeline(config) as pipeline:
                result = await pipeline.collect("00126380")

            assert result.duration_ms > 0
            assert all(s.duration_ms >= 0 for s in result.steps)


# ============================================================================
# 안전 단계 (_safe_step) 테스트
# ============================================================================


class TestSafeStep:
    """_safe_step 메서드 테스트."""

    @pytest.fixture
    def pipeline(self) -> DataCollectionPipeline:
        config = PipelineConfig(
            dart_api_key="test_key",
            enable_cache=False,
        )
        return DataCollectionPipeline(config)

    @pytest.mark.asyncio
    async def test_safe_step_success(self, pipeline: DataCollectionPipeline) -> None:
        """성공 단계 기록 테스트."""
        result = CollectionResult()

        async def _success_coro() -> str:
            return "data"

        value = await pipeline._safe_step(
            "테스트", DataPriority.REQUIRED, _success_coro(), result
        )

        assert value == "data"
        assert len(result.steps) == 1
        assert result.steps[0].success
        assert result.steps[0].step_name == "테스트"
        assert result.steps[0].priority == DataPriority.REQUIRED

    @pytest.mark.asyncio
    async def test_safe_step_required_failure(
        self, pipeline: DataCollectionPipeline
    ) -> None:
        """REQUIRED 실패 시 errors에 기록."""
        result = CollectionResult()

        async def _fail_coro() -> str:
            raise ValueError("필수 데이터 오류")

        value = await pipeline._safe_step(
            "필수 단계", DataPriority.REQUIRED, _fail_coro(), result
        )

        assert value is None
        assert len(result.steps) == 1
        assert not result.steps[0].success
        assert len(result.errors) == 1
        assert "필수 단계" in result.errors[0]

    @pytest.mark.asyncio
    async def test_safe_step_important_failure(
        self, pipeline: DataCollectionPipeline
    ) -> None:
        """IMPORTANT 실패 시 warnings에 기록."""
        result = CollectionResult()

        async def _fail_coro() -> str:
            raise ValueError("중요 데이터 오류")

        value = await pipeline._safe_step(
            "중요 단계", DataPriority.IMPORTANT, _fail_coro(), result
        )

        assert value is None
        assert len(result.warnings) == 1
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_safe_step_optional_failure(
        self, pipeline: DataCollectionPipeline
    ) -> None:
        """OPTIONAL 실패 시 warnings에 기록."""
        result = CollectionResult()

        async def _fail_coro() -> str:
            raise ValueError("선택 데이터 오류")

        value = await pipeline._safe_step(
            "선택 단계", DataPriority.OPTIONAL, _fail_coro(), result
        )

        assert value is None
        assert len(result.warnings) == 1
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_safe_step_duration_tracking(
        self, pipeline: DataCollectionPipeline
    ) -> None:
        """단계 실행 시간 측정 테스트."""
        result = CollectionResult()

        async def _slow_coro() -> str:
            await asyncio.sleep(0.05)
            return "data"

        await pipeline._safe_step(
            "느린 단계", DataPriority.OPTIONAL, _slow_coro(), result
        )

        assert result.steps[0].duration_ms >= 40  # 최소 40ms


# ============================================================================
# 예외 클래스 테스트
# ============================================================================


class TestPipelineError:
    """PipelineError 테스트."""

    def test_pipeline_error(self) -> None:
        error = PipelineError("파이프라인 오류")
        assert str(error) == "파이프라인 오류"
        assert error.message == "파이프라인 오류"

    def test_pipeline_error_with_details(self) -> None:
        error = PipelineError("오류", details={"corp_code": "00126380"})
        assert error.details == {"corp_code": "00126380"}
