"""DART Open API 클라이언트.

Open DART(전자공시시스템) API와 통신하는 비동기 HTTP 클라이언트.
Rate limiting, Circuit Breaker, 재시도 로직을 통합하여 안정적인 API 호출을 제공합니다.

사용 예시:
    async with DartAPIClient(api_key="YOUR_API_KEY") as client:
        info = await client.get_company_info("00126380")
        financials = await client.get_financial_statements(
            corp_code="00126380",
            bsns_year="2024",
            reprt_code=ReportCode.ANNUAL,
            fs_div=FinancialStatementDivision.CONSOLIDATED,
        )
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any, TypeVar

import httpx

from src.data_ingestor.dart.endpoints import (
    DART_BASE_URL,
    BusinessReportEndpoints,
    DartDefaults,
    DartStatusCode,
    DisclosureEndpoints,
    FinancialEndpoints,
    FinancialStatementDivision,
    ReportCode,
    ShareholdingEndpoints,
)
from src.data_ingestor.dart.models import (
    DartCompanyInfo,
    DartDividend,
    DartFinancialStatement,
    DartMajorShareholder,
    DartSearchResult,
    FinancialStatementsCollection,
)
from src.data_ingestor.dart.rate_limiter import (
    DART_CIRCUIT_BREAKER,
    DART_RATE_LIMITER,
    DART_RETRY_CONFIG,
    CircuitBreakerError,
)
from src.data_ingestor.exceptions import (
    DartAuthenticationError,
    DartNetworkError,
    DartNotFoundError,
    DartRateLimitError,
    DartResponseError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DartAPIClient:
    """Open DART API 비동기 클라이언트.

    API 키 인증, Rate Limiting (100 calls/min), Circuit Breaker,
    자동 재시도를 지원하는 완전한 DART API 클라이언트입니다.

    Attributes:
        api_key: DART API 키. 환경변수 DART_API_KEY에서도 로드 가능.
        timeout: 요청 타임아웃 (초). 기본값 30초.
        connect_timeout: 연결 타임아웃 (초). 기본값 10초.

    Example:
        >>> async with DartAPIClient() as client:
        ...     company = await client.get_company_info("00126380")
        ...     print(company.corp_name)
        삼성전자
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = DartDefaults.REQUEST_TIMEOUT,
        connect_timeout: float = DartDefaults.CONNECT_TIMEOUT,
        max_retries: int = DartDefaults.MAX_RETRIES,
    ) -> None:
        """DartAPIClient 초기화.

        Args:
            api_key: DART API 키. None이면 환경변수 DART_API_KEY 사용.
            timeout: 전체 요청 타임아웃 (초).
            connect_timeout: 연결 타임아웃 (초).
            max_retries: 최대 재시도 횟수.

        Raises:
            DartAuthenticationError: API 키가 없는 경우.
        """
        self._api_key = api_key or os.getenv("DART_API_KEY")
        if not self._api_key:
            raise DartAuthenticationError(
                api_key_hint="환경변수 DART_API_KEY를 설정하거나 api_key 인자를 전달하세요."
            )

        self._timeout = timeout
        self._connect_timeout = connect_timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._rate_limiter = DART_RATE_LIMITER
        self._circuit_breaker = DART_CIRCUIT_BREAKER
        self._retry_config = DART_RETRY_CONFIG

    async def __aenter__(self) -> DartAPIClient:
        """비동기 컨텍스트 매니저 진입."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        """비동기 컨텍스트 매니저 종료."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트가 초기화되었는지 확인하고 반환."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=DART_BASE_URL,
                timeout=httpx.Timeout(self._timeout, connect=self._connect_timeout),
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """HTTP 클라이언트 연결 종료."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def is_connected(self) -> bool:
        """클라이언트가 연결되어 있는지 확인."""
        return self._client is not None and not self._client.is_closed

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """DART API에 GET 요청을 보내고 JSON 응답을 반환.

        Rate limiting, circuit breaker, 재시도 로직을 적용합니다.

        Args:
            endpoint: API 엔드포인트 경로 (예: "/company.json").
            params: 쿼리 파라미터.

        Returns:
            API 응답 JSON 딕셔너리.

        Raises:
            DartAuthenticationError: API 키 인증 실패.
            DartRateLimitError: Rate limit 초과.
            DartNotFoundError: 요청한 리소스를 찾을 수 없음.
            DartResponseError: API 응답 오류.
            DartNetworkError: 네트워크 연결 실패.
        """
        client = await self._ensure_client()

        # 파라미터에 API 키 추가
        request_params = {"crtfc_key": self._api_key}
        if params:
            request_params.update(params)

        last_exception: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                # Rate limiting
                await self._rate_limiter.acquire()

                # Circuit breaker check
                if self._circuit_breaker.state.name == "OPEN":
                    raise CircuitBreakerError("Circuit breaker is open")

                # HTTP 요청
                logger.debug("DART API 요청: %s (시도 %d/%d)", endpoint, attempt + 1, self._max_retries + 1)
                response = await client.get(endpoint, params=request_params)

                # 응답 처리
                return await self._handle_response(response, endpoint)

            except CircuitBreakerError as e:
                raise DartNetworkError(original_error=e)

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning("DART API 타임아웃: %s (시도 %d/%d)", endpoint, attempt + 1, self._max_retries + 1)
                await self._circuit_breaker._on_failure()

                if attempt < self._max_retries:
                    delay = self._retry_config.get_delay(attempt)
                    logger.info("%.2f초 후 재시도...", delay)
                    await asyncio.sleep(delay)
                    continue

            except httpx.NetworkError as e:
                last_exception = e
                logger.warning("DART API 네트워크 오류: %s (시도 %d/%d)", endpoint, attempt + 1, self._max_retries + 1)
                await self._circuit_breaker._on_failure()

                if attempt < self._max_retries:
                    delay = self._retry_config.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue

            except DartRateLimitError:
                # Rate limit은 재시도하지 않고 바로 전파
                raise

            except DartAuthenticationError:
                # 인증 오류는 재시도하지 않음
                raise

        # 모든 재시도 실패
        raise DartNetworkError(original_error=last_exception)

    async def _handle_response(
        self,
        response: httpx.Response,
        endpoint: str,
    ) -> dict[str, Any]:
        """HTTP 응답을 처리하고 적절한 예외를 발생.

        Args:
            response: httpx 응답 객체.
            endpoint: 요청한 엔드포인트 (에러 메시지용).

        Returns:
            JSON 응답 딕셔너리.

        Raises:
            DartAuthenticationError: 인증 실패.
            DartRateLimitError: Rate limit 초과.
            DartNotFoundError: 데이터 없음.
            DartResponseError: 기타 API 오류.
        """
        # HTTP 상태 코드 확인
        if response.status_code != 200:
            await self._circuit_breaker._on_failure()
            raise DartResponseError(
                status_code=response.status_code,
                response_body=f"endpoint: {endpoint}",
            )

        # JSON 파싱
        try:
            data = response.json()
        except Exception as e:
            await self._circuit_breaker._on_failure()
            raise DartResponseError(
                status_code=response.status_code,
                response_body=f"JSON 파싱 실패: {e}",
            )

        # DART API 상태 코드 확인
        status = data.get("status", "")

        if status == DartStatusCode.SUCCESS:
            await self._circuit_breaker._on_success()
            return data

        if status == DartStatusCode.NO_DATA:
            # NO_DATA는 성공이지만 데이터가 없는 경우
            await self._circuit_breaker._on_success()
            raise DartNotFoundError(
                resource_type="데이터",
                identifier=endpoint,
            )

        if status in (DartStatusCode.INVALID_KEY, DartStatusCode.DISABLED_KEY, DartStatusCode.BLOCKED_IP):
            raise DartAuthenticationError(api_key_hint=endpoint)

        if status == DartStatusCode.RATE_LIMIT_EXCEEDED:
            raise DartRateLimitError(retry_after=60)

        # 기타 오류
        await self._circuit_breaker._on_failure()
        raise DartResponseError(
            status_code=int(status) if status.isdigit() else 0,
            response_body=DartStatusCode.get_message(status),
        )

    # ===== T-D07: Company Info =====

    async def get_company_info(self, corp_code: str) -> DartCompanyInfo:
        """기업 개황 정보를 조회합니다.

        Args:
            corp_code: 고유번호 (8자리).

        Returns:
            DartCompanyInfo: 기업 정보 모델.

        Raises:
            DartNotFoundError: 해당 기업을 찾을 수 없음.
            DartResponseError: API 응답 오류.

        Example:
            >>> company = await client.get_company_info("00126380")
            >>> print(f"{company.corp_name} ({company.stock_code})")
            삼성전자 (005930)
        """
        data = await self._request(
            DisclosureEndpoints.COMPANY,
            params={"corp_code": corp_code},
        )

        return DartCompanyInfo.model_validate(data)

    async def search_company(self, company_name: str) -> list[DartSearchResult]:
        """기업명으로 기업을 검색합니다.

        Note:
            현재 DART API는 직접적인 검색 API를 제공하지 않습니다.
            이 메서드는 기업코드 ZIP 파일을 다운로드하여 로컬에서 검색합니다.
            (TODO: 구현 예정)

        Args:
            company_name: 검색할 기업명 (부분 일치).

        Returns:
            검색 결과 리스트.
        """
        # TODO: corp_code.zip 다운로드 및 검색 구현
        logger.warning("search_company는 아직 구현되지 않았습니다.")
        return []

    # ===== T-D08: Financial Statements =====

    async def get_financial_statements(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: ReportCode | str = ReportCode.ANNUAL,
        fs_div: FinancialStatementDivision | str = FinancialStatementDivision.CONSOLIDATED,
    ) -> FinancialStatementsCollection:
        """재무제표 정보를 조회합니다.

        Args:
            corp_code: 고유번호 (8자리).
            bsns_year: 사업연도 (예: "2024").
            reprt_code: 보고서 코드. ReportCode enum 또는 문자열.
            fs_div: 재무제표 구분. FinancialStatementDivision enum 또는 문자열.

        Returns:
            FinancialStatementsCollection: 재무제표 항목 컬렉션.

        Raises:
            DartNotFoundError: 해당 재무제표를 찾을 수 없음.
            DartResponseError: API 응답 오류.

        Example:
            >>> fs = await client.get_financial_statements(
            ...     corp_code="00126380",
            ...     bsns_year="2024",
            ...     reprt_code=ReportCode.ANNUAL,
            ...     fs_div=FinancialStatementDivision.CONSOLIDATED,
            ... )
            >>> revenue = fs.get_by_account("매출액")
            >>> print(f"매출액: {revenue.current_amount:,}원")
        """
        # Enum 처리
        if isinstance(reprt_code, ReportCode):
            reprt_code_value = reprt_code.value
        else:
            reprt_code_value = reprt_code

        if isinstance(fs_div, FinancialStatementDivision):
            fs_div_value = fs_div.value
        else:
            fs_div_value = fs_div

        data = await self._request(
            FinancialEndpoints.SINGLE_COMPANY_ACCOUNT,
            params={
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code_value,
                "fs_div": fs_div_value,
            },
        )

        # 응답에서 list 추출
        items_data = data.get("list", [])
        items = [DartFinancialStatement.model_validate(item) for item in items_data]

        return FinancialStatementsCollection(
            corp_code=corp_code,
            bsns_year=bsns_year,
            fs_div=fs_div_value,
            items=items,
        )

    async def get_full_financial_statements(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: ReportCode | str = ReportCode.ANNUAL,
        fs_div: FinancialStatementDivision | str = FinancialStatementDivision.CONSOLIDATED,
    ) -> FinancialStatementsCollection:
        """전체 재무제표 정보를 조회합니다 (상세 계정 포함).

        단일 계정 API보다 더 상세한 계정 과목을 반환합니다.

        Args:
            corp_code: 고유번호 (8자리).
            bsns_year: 사업연도 (예: "2024").
            reprt_code: 보고서 코드.
            fs_div: 재무제표 구분.

        Returns:
            FinancialStatementsCollection: 상세 재무제표 항목 컬렉션.
        """
        if isinstance(reprt_code, ReportCode):
            reprt_code_value = reprt_code.value
        else:
            reprt_code_value = reprt_code

        if isinstance(fs_div, FinancialStatementDivision):
            fs_div_value = fs_div.value
        else:
            fs_div_value = fs_div

        data = await self._request(
            FinancialEndpoints.SINGLE_COMPANY_FULL,
            params={
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code_value,
                "fs_div": fs_div_value,
            },
        )

        items_data = data.get("list", [])
        items = [DartFinancialStatement.model_validate(item) for item in items_data]

        return FinancialStatementsCollection(
            corp_code=corp_code,
            bsns_year=bsns_year,
            fs_div=fs_div_value,
            items=items,
        )

    # ===== T-D09: Major Shareholders =====

    async def get_major_shareholders(self, corp_code: str) -> list[DartMajorShareholder]:
        """최대주주 현황을 조회합니다.

        Args:
            corp_code: 고유번호 (8자리).

        Returns:
            최대주주 정보 리스트.

        Raises:
            DartNotFoundError: 해당 정보를 찾을 수 없음.
            DartResponseError: API 응답 오류.

        Example:
            >>> shareholders = await client.get_major_shareholders("00126380")
            >>> for sh in shareholders[:3]:
            ...     print(f"{sh.repror}: {sh.share_ratio:.2f}%")
        """
        data = await self._request(
            ShareholdingEndpoints.MAJOR_STOCK,
            params={"corp_code": corp_code},
        )

        items_data = data.get("list", [])
        return [DartMajorShareholder.model_validate(item) for item in items_data]

    async def get_executive_shareholding(self, corp_code: str) -> list[dict[str, Any]]:
        """임원 주요주주 소유현황을 조회합니다.

        Args:
            corp_code: 고유번호 (8자리).

        Returns:
            임원 주주 정보 리스트.
        """
        data = await self._request(
            ShareholdingEndpoints.EXECUTIVE_STOCK,
            params={"corp_code": corp_code},
        )

        return data.get("list", [])

    # ===== Business Report APIs =====

    async def get_dividend(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: ReportCode | str = ReportCode.ANNUAL,
    ) -> list[DartDividend]:
        """배당 현황을 조회합니다.

        Args:
            corp_code: 고유번호 (8자리).
            bsns_year: 사업연도.
            reprt_code: 보고서 코드.

        Returns:
            배당 정보 리스트.
        """
        if isinstance(reprt_code, ReportCode):
            reprt_code_value = reprt_code.value
        else:
            reprt_code_value = reprt_code

        data = await self._request(
            BusinessReportEndpoints.DIVIDEND,
            params={
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code_value,
            },
        )

        items_data = data.get("list", [])
        return [DartDividend.model_validate(item) for item in items_data]

    async def get_employee_info(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: ReportCode | str = ReportCode.ANNUAL,
    ) -> list[dict[str, Any]]:
        """직원 현황을 조회합니다.

        Args:
            corp_code: 고유번호 (8자리).
            bsns_year: 사업연도.
            reprt_code: 보고서 코드.

        Returns:
            직원 정보 리스트.
        """
        if isinstance(reprt_code, ReportCode):
            reprt_code_value = reprt_code.value
        else:
            reprt_code_value = reprt_code

        data = await self._request(
            BusinessReportEndpoints.EMPLOYEES,
            params={
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code_value,
            },
        )

        return data.get("list", [])

    async def get_executives(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: ReportCode | str = ReportCode.ANNUAL,
    ) -> list[dict[str, Any]]:
        """임원 현황을 조회합니다.

        Args:
            corp_code: 고유번호 (8자리).
            bsns_year: 사업연도.
            reprt_code: 보고서 코드.

        Returns:
            임원 정보 리스트.
        """
        if isinstance(reprt_code, ReportCode):
            reprt_code_value = reprt_code.value
        else:
            reprt_code_value = reprt_code

        data = await self._request(
            BusinessReportEndpoints.EXECUTIVES,
            params={
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code_value,
            },
        )

        return data.get("list", [])
