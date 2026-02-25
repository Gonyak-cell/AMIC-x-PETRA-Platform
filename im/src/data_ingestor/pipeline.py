"""E2E 데이터 수집 파이프라인.

DART API, 웹 크롤링 데이터를 자동으로 수집하고 통합하는 파이프라인.
에러 복구 전략(REQUIRED/IMPORTANT/OPTIONAL)에 따라 부분 실패를 허용합니다.

사용 예시:
    config = PipelineConfig(dart_api_key="YOUR_KEY")
    async with DataCollectionPipeline(config) as pipeline:
        result = await pipeline.collect("00126380")
        if result.is_success:
            im_data = result.data
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from src.api.core.log_decorators import log_error_with_input
from src.data_ingestor.aggregator import DataAggregator, IMDocumentData
from src.data_ingestor.cache import CacheConfig, CacheManager, CachedDartClient
from src.data_ingestor.dart.client import DartAPIClient
from src.data_ingestor.dart.endpoints import FinancialStatementDivision, ReportCode
from src.data_ingestor.exceptions import PipelineError

if TYPE_CHECKING:
    from src.data_ingestor.crawler.company_crawler import CompanyWebInfo
    from src.data_ingestor.crawler.news_crawler import NewsArticle
    from src.data_ingestor.dart.models import (
        DartCompanyInfo,
        DartDividend,
        DartMajorShareholder,
        FinancialStatementsCollection,
    )

logger = logging.getLogger(__name__)


# ============================================================================
# 데이터 클래스
# ============================================================================


class DataPriority(Enum):
    """데이터 우선순위."""

    REQUIRED = "required"
    """필수 데이터. 실패 시 파이프라인 중단."""

    IMPORTANT = "important"
    """중요 데이터. 실패 시 경고, 계속 진행."""

    OPTIONAL = "optional"
    """선택 데이터. 실패 시 경고, 계속 진행."""


@dataclass
class StepResult:
    """파이프라인 단계 실행 결과."""

    step_name: str
    """단계명."""

    success: bool
    """성공 여부."""

    priority: DataPriority
    """데이터 우선순위."""

    error: str | None = None
    """에러 메시지 (실패 시)."""

    duration_ms: float = 0.0
    """실행 시간 (밀리초)."""


@dataclass
class CollectionResult:
    """데이터 수집 결과."""

    data: IMDocumentData | None = None
    """수집된 IM 문서 데이터. 실패 시 None."""

    steps: list[StepResult] = field(default_factory=list)
    """각 단계의 실행 결과."""

    warnings: list[str] = field(default_factory=list)
    """경고 메시지 리스트."""

    errors: list[str] = field(default_factory=list)
    """에러 메시지 리스트."""

    duration_ms: float = 0.0
    """전체 실행 시간 (밀리초)."""

    @property
    def is_success(self) -> bool:
        """필수 데이터가 모두 성공했는지 여부."""
        required_steps = [s for s in self.steps if s.priority == DataPriority.REQUIRED]
        return all(s.success for s in required_steps) and self.data is not None

    @property
    def summary(self) -> str:
        """결과 요약 문자열."""
        total = len(self.steps)
        succeeded = sum(1 for s in self.steps if s.success)
        failed = total - succeeded
        return (
            f"수집 완료: {succeeded}/{total} 단계 성공, "
            f"{failed} 실패, {len(self.warnings)} 경고 "
            f"({self.duration_ms:.0f}ms)"
        )


@dataclass
class PipelineConfig:
    """파이프라인 설정."""

    dart_api_key: str
    """DART API 키."""

    financial_years: int = 3
    """수집할 재무제표 연도 수."""

    base_year: int | None = None
    """기준 연도. None이면 현재 연도."""

    include_shareholders: bool = True
    """주주 정보 수집 여부."""

    include_dividends: bool = True
    """배당 정보 수집 여부."""

    include_news: bool = True
    """뉴스 수집 여부."""

    include_web_info: bool = True
    """웹사이트 정보 수집 여부."""

    news_days: int = 30
    """뉴스 검색 기간 (일)."""

    news_count: int = 20
    """수집할 뉴스 기사 수."""

    enable_cache: bool = True
    """캐시 사용 여부."""

    cache_config: CacheConfig | None = None
    """캐시 설정. None이면 기본 설정 사용."""

    timeout: float = 300.0
    """전체 파이프라인 타임아웃 (초)."""


# ============================================================================
# DataCollectionPipeline
# ============================================================================


class DataCollectionPipeline:
    """E2E 데이터 수집 파이프라인.

    DART API와 웹 크롤링을 통합하여 IM 문서 데이터를 수집합니다.
    에러 복구 전략에 따라 부분 실패를 허용하며,
    캐싱을 통해 반복 호출 시 성능을 향상시킵니다.

    Example:
        >>> config = PipelineConfig(dart_api_key="YOUR_KEY")
        >>> async with DataCollectionPipeline(config) as pipeline:
        ...     result = await pipeline.collect("00126380")
        ...     if result.is_success:
        ...         print(result.data.company.corp_name)
    """

    def __init__(self, config: PipelineConfig) -> None:
        """DataCollectionPipeline 초기화.

        Args:
            config: 파이프라인 설정.
        """
        self._config = config
        self._cache: CacheManager | None = None
        self._dart_client: DartAPIClient | None = None
        self._cached_client: CachedDartClient | None = None

    async def __aenter__(self) -> DataCollectionPipeline:
        """비동기 컨텍스트 매니저 진입."""
        # DART 클라이언트 초기화
        self._dart_client = DartAPIClient(api_key=self._config.dart_api_key)
        await self._dart_client.__aenter__()

        # 캐시 초기화
        if self._config.enable_cache:
            cache_config = self._config.cache_config or CacheConfig()
            self._cache = CacheManager(cache_config)
            await self._cache.__aenter__()
            self._cached_client = CachedDartClient(
                client=self._dart_client,
                cache=self._cache,
            )

        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """비동기 컨텍스트 매니저 종료."""
        if self._cache is not None:
            await self._cache.close()
            self._cache = None

        if self._dart_client is not None:
            await self._dart_client.close()
            self._dart_client = None

        self._cached_client = None

    @property
    def _client(self) -> Any:
        """활성 DART 클라이언트 (캐시 래퍼 또는 원본)."""
        if self._cached_client is not None:
            return self._cached_client
        return self._dart_client

    @log_error_with_input
    async def collect(self, corp_code: str) -> CollectionResult:
        """기업 데이터를 수집합니다.

        Args:
            corp_code: DART 고유번호 (8자리).

        Returns:
            CollectionResult: 수집 결과.
        """
        result = CollectionResult()
        start_time = time.time()

        logger.info("데이터 수집 시작: %s", corp_code)

        try:
            # Phase 1: DART 기업정보 (REQUIRED)
            company_info = await self._fetch_company_info(corp_code, result)
            if company_info is None:
                # REQUIRED 실패 → 즉시 중단
                result.duration_ms = (time.time() - start_time) * 1000
                return result

            # Phase 2: DART 나머지 + 크롤링 (병렬)
            dart_data, crawl_data = await self._collect_parallel(
                corp_code, company_info, result
            )

            # Phase 3: DataAggregator로 통합
            result.data = await self._aggregate(
                company_info, dart_data, crawl_data, result
            )

        except asyncio.TimeoutError:
            result.errors.append(f"파이프라인 타임아웃: {self._config.timeout}초 초과")
            logger.error("파이프라인 타임아웃: %s", corp_code)
        except Exception as e:
            result.errors.append(f"파이프라인 예외: {e}")
            logger.error("파이프라인 예외: %s - %s", corp_code, e)

        result.duration_ms = (time.time() - start_time) * 1000
        logger.info("데이터 수집 완료: %s (%s)", corp_code, result.summary)

        return result

    async def _safe_step(
        self,
        name: str,
        priority: DataPriority,
        coro: Any,
        result: CollectionResult,
    ) -> Any | None:
        """단계를 안전하게 실행합니다.

        try/except로 감싸고 StepResult에 기록합니다.

        Args:
            name: 단계명.
            priority: 우선순위.
            coro: 실행할 코루틴.
            result: 결과를 기록할 CollectionResult.

        Returns:
            코루틴 결과 또는 None (실패 시).
        """
        start_time = time.time()
        try:
            value = await coro
            duration_ms = (time.time() - start_time) * 1000

            result.steps.append(
                StepResult(
                    step_name=name,
                    success=True,
                    priority=priority,
                    duration_ms=duration_ms,
                )
            )
            logger.info("단계 성공: %s (%.0fms)", name, duration_ms)
            return value

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"{name}: {e}"

            result.steps.append(
                StepResult(
                    step_name=name,
                    success=False,
                    priority=priority,
                    error=str(e),
                    duration_ms=duration_ms,
                )
            )

            if priority == DataPriority.REQUIRED:
                result.errors.append(error_msg)
                logger.error("필수 단계 실패: %s", error_msg)
            elif priority == DataPriority.IMPORTANT:
                result.warnings.append(error_msg)
                logger.warning("중요 단계 실패: %s", error_msg)
            else:
                result.warnings.append(error_msg)
                logger.warning("선택 단계 실패: %s", error_msg)

            return None

    async def _fetch_company_info(
        self,
        corp_code: str,
        result: CollectionResult,
    ) -> DartCompanyInfo | None:
        """DART 기업정보를 조회합니다 (REQUIRED).

        Args:
            corp_code: 고유번호.
            result: CollectionResult.

        Returns:
            DartCompanyInfo 또는 None (실패 시).
        """
        return await self._safe_step(
            "DART 기업정보",
            DataPriority.REQUIRED,
            self._client.get_company_info(corp_code),
            result,
        )

    async def _collect_parallel(
        self,
        corp_code: str,
        company_info: DartCompanyInfo,
        result: CollectionResult,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """DART 나머지 데이터와 크롤링 데이터를 병렬 수집합니다.

        Args:
            corp_code: 고유번호.
            company_info: 기업정보 (homepage_url 참조).
            result: CollectionResult.

        Returns:
            (dart_data, crawl_data) 튜플.
        """
        dart_data: dict[str, Any] = {}
        crawl_data: dict[str, Any] = {}

        # 병렬 태스크 수집
        tasks: list[tuple[str, Any]] = []

        # 재무제표 태스크들
        base_year = self._config.base_year or datetime.now().year
        for offset in range(self._config.financial_years):
            year = base_year - offset
            task_name = f"fs_{year}"
            tasks.append((
                task_name,
                self._fetch_financial_statements(corp_code, str(year), result),
            ))

        # 주주정보
        if self._config.include_shareholders:
            tasks.append((
                "shareholders",
                self._fetch_shareholders(corp_code, result),
            ))

        # 배당정보
        if self._config.include_dividends:
            tasks.append((
                "dividends",
                self._fetch_dividends(corp_code, str(base_year), result),
            ))

        # 뉴스
        if self._config.include_news:
            tasks.append((
                "news",
                self._fetch_news(company_info, result),
            ))

        # 웹사이트 정보
        if self._config.include_web_info and getattr(company_info, "hm_url", None):
            tasks.append((
                "web_info",
                self._fetch_web_info(company_info, result),
            ))

        # 병렬 실행 (return_exceptions=True로 개별 실패 격리)
        task_names = [name for name, _ in tasks]
        coros = [coro for _, coro in tasks]

        results = await asyncio.gather(*coros, return_exceptions=True)

        # 결과 분배
        for name, value in zip(task_names, results):
            if isinstance(value, Exception):
                result.warnings.append(f"{name}: 예기치 않은 오류 — {value}")
                logger.warning("병렬 단계 예외: %s — %s", name, value)
                value = None
            if name.startswith("fs_"):
                if value is not None:
                    dart_data.setdefault("financials", []).append(value)
            elif name == "shareholders":
                dart_data["shareholders"] = value
            elif name == "dividends":
                dart_data["dividends"] = value
            elif name == "news":
                crawl_data["news"] = value
            elif name == "web_info":
                crawl_data["web_info"] = value

        return dart_data, crawl_data

    async def _fetch_financial_statements(
        self,
        corp_code: str,
        bsns_year: str,
        result: CollectionResult,
    ) -> FinancialStatementsCollection | None:
        """재무제표를 조회합니다 (IMPORTANT).

        Args:
            corp_code: 고유번호.
            bsns_year: 사업연도.
            result: CollectionResult.

        Returns:
            FinancialStatementsCollection 또는 None.
        """
        return await self._safe_step(
            f"DART 재무제표 {bsns_year}",
            DataPriority.IMPORTANT,
            self._client.get_financial_statements(
                corp_code,
                bsns_year,
                ReportCode.ANNUAL,
                FinancialStatementDivision.CONSOLIDATED,
            ),
            result,
        )

    async def _fetch_shareholders(
        self,
        corp_code: str,
        result: CollectionResult,
    ) -> list[DartMajorShareholder] | None:
        """주주정보를 조회합니다 (OPTIONAL).

        Args:
            corp_code: 고유번호.
            result: CollectionResult.

        Returns:
            주주 정보 리스트 또는 None.
        """
        return await self._safe_step(
            "DART 주주정보",
            DataPriority.OPTIONAL,
            self._client.get_major_shareholders(corp_code),
            result,
        )

    async def _fetch_dividends(
        self,
        corp_code: str,
        bsns_year: str,
        result: CollectionResult,
    ) -> list[DartDividend] | None:
        """배당정보를 조회합니다 (OPTIONAL).

        Args:
            corp_code: 고유번호.
            bsns_year: 사업연도.
            result: CollectionResult.

        Returns:
            배당 정보 리스트 또는 None.
        """
        return await self._safe_step(
            "DART 배당정보",
            DataPriority.OPTIONAL,
            self._client.get_dividend(corp_code, bsns_year, ReportCode.ANNUAL),
            result,
        )

    async def _fetch_news(
        self,
        company_info: DartCompanyInfo,
        result: CollectionResult,
    ) -> list[NewsArticle] | None:
        """뉴스를 수집합니다 (OPTIONAL).

        Args:
            company_info: 기업정보 (corp_name으로 검색).
            result: CollectionResult.

        Returns:
            뉴스 기사 리스트 또는 None.
        """
        from src.data_ingestor.crawler.news_crawler import NewsCrawler

        async def _do_fetch() -> list[NewsArticle]:
            crawler = NewsCrawler()
            try:
                return await crawler.search(
                    company_info.corp_name,
                    days=self._config.news_days,
                    count=self._config.news_count,
                )
            finally:
                await crawler.close()

        return await self._safe_step(
            "뉴스 크롤링",
            DataPriority.OPTIONAL,
            _do_fetch(),
            result,
        )

    async def _fetch_web_info(
        self,
        company_info: DartCompanyInfo,
        result: CollectionResult,
    ) -> CompanyWebInfo | None:
        """웹사이트 정보를 수집합니다 (OPTIONAL).

        Args:
            company_info: 기업정보 (hm_url로 크롤링).
            result: CollectionResult.

        Returns:
            CompanyWebInfo 또는 None.
        """
        from src.data_ingestor.crawler.company_crawler import CompanyCrawler

        homepage_url = getattr(company_info, "hm_url", None) or ""
        if not homepage_url:
            return None

        async def _do_fetch() -> CompanyWebInfo:
            crawler = CompanyCrawler()
            try:
                return await crawler.extract_company_info(homepage_url)
            finally:
                await crawler.close()

        return await self._safe_step(
            "웹사이트 크롤링",
            DataPriority.OPTIONAL,
            _do_fetch(),
            result,
        )

    async def _aggregate(
        self,
        company_info: DartCompanyInfo,
        dart_data: dict[str, Any],
        crawl_data: dict[str, Any],
        result: CollectionResult,
    ) -> IMDocumentData | None:
        """수집된 데이터를 통합합니다.

        Args:
            company_info: DART 기업정보.
            dart_data: DART에서 수집한 데이터.
            crawl_data: 크롤링으로 수집한 데이터.
            result: CollectionResult.

        Returns:
            IMDocumentData 또는 None (통합 실패 시).
        """
        try:
            aggregator = DataAggregator()

            # 기업정보
            aggregator.add_dart_company(company_info)

            # 재무제표
            financials_list = dart_data.get("financials", [])
            for i, fs in enumerate(financials_list):
                aggregator.add_dart_financials(
                    fs, is_historical=(i > 0)
                )

            # 주주정보
            shareholders = dart_data.get("shareholders")
            if shareholders:
                aggregator.add_dart_shareholders(shareholders)

            # 배당정보
            dividends = dart_data.get("dividends")
            if dividends:
                aggregator.add_dart_dividends(dividends)

            # 뉴스
            news = crawl_data.get("news")
            if news:
                aggregator.add_news_articles(news)

            # 웹사이트 정보
            web_info = crawl_data.get("web_info")
            if web_info:
                aggregator.add_company_web_info(web_info)

            # 빌드
            return aggregator.build()

        except Exception as e:
            result.errors.append(f"데이터 통합 실패: {e}")
            logger.error("데이터 통합 실패: %s", e)
            return None
