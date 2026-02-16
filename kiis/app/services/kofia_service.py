import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.schemas.fund import FundDetailResponse, FundItem, FundListItem, FundManagerItem
from app.utils.cache import cache
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# 펀드 유형 자동 분류 키워드
BLIND_FUND_KEYWORDS = ["블라인드", "일반", "성장", "벤처", "기술", "투자조합", "신기술"]
PROJECT_FUND_KEYWORDS = ["프로젝트", "특정", "목적", "인수", "PF"]

# KOFIA DIS WebSquare 서비스 엔드포인트
DIS_SERVICE_PATH = "/websquare/engine/proworks/callServletService.jsp"


class KOFIAService:
    """KOFIA 펀드 데이터 수집 서비스

    KOFIA DIS 전자공시서비스에서 펀드 정보를 수집한다.
    - 펀드 설정액, 운용보수, 운용 전문인력 현황
    - 펀드 유형 자동 구분 (블라인드/프로젝트)
    - 빈티지 연도 및 만기 임박 알림 로직
    """

    def __init__(self) -> None:
        self.client = AsyncHTTPClient(
            base_url=settings.KOFIA_DIS_BASE_URL,
            timeout=30.0,
            headers={
                "User-Agent": "KIIS/0.1.0",
                "Content-Type": "text/xml; charset=utf-8",
                "Accept": "application/json, text/xml, */*",
            },
        )
        self.rate_limiter = TokenBucketRateLimiter(
            per_minute=settings.KOFIA_RATE_LIMIT_PER_MINUTE,
            per_day=settings.KOFIA_RATE_LIMIT_PER_DAY,
        )

    async def _request(self, service_id: str, params: dict | None = None) -> dict:
        """Rate limiting + delay가 적용된 KOFIA DIS 요청

        Args:
            service_id: KOFIA DIS 서비스 ID
            params: 요청 파라미터

        Returns:
            응답 JSON dict
        """
        await self.rate_limiter.acquire()
        await asyncio.sleep(settings.KOFIA_REQUEST_DELAY)

        if params is None:
            params = {}

        # WebSquare POST 요청 (form data 방식)
        form_data = {"svcId": service_id, **params}

        try:
            response = await self.client.post(DIS_SERVICE_PATH, data=form_data)
            return response.json()
        except Exception as e:
            logger.error("KOFIA DIS request failed (service=%s): %s", service_id, e)
            raise ExternalAPIError(source="KOFIA", message=str(e)) from e

    @staticmethod
    def classify_fund_type(fund_name: str) -> str:
        """펀드명으로 블라인드/프로젝트 펀드를 자동 구분한다.

        Args:
            fund_name: 펀드명

        Returns:
            "blind" 또는 "project"
        """
        for keyword in PROJECT_FUND_KEYWORDS:
            if keyword in fund_name:
                return "project"
        for keyword in BLIND_FUND_KEYWORDS:
            if keyword in fund_name:
                return "blind"
        return "blind"

    @staticmethod
    def calculate_maturity_alert(
        established_date: date | None,
        maturity_date: date | None = None,
    ) -> tuple[int | None, bool]:
        """빈티지 연도와 회수 집중 구간 여부를 계산한다.

        회수 집중 구간: 설정 후 7~10년차 (일반적 VC/PEF 회수 시기)
        만기일이 있으면 만기 2년 전부터도 알림.

        Args:
            established_date: 펀드 설정일
            maturity_date: 펀드 만기일

        Returns:
            (vintage_year, is_maturity_alert)
        """
        if not established_date:
            return None, False

        vintage_year = established_date.year
        today = date.today()
        fund_age = today.year - vintage_year

        # 7~10년차: 회수 집중 구간
        is_alert = 7 <= fund_age <= 10

        # 만기일 기준: 만기 2년 이내
        if maturity_date and not is_alert:
            remaining_days = (maturity_date - today).days
            if 0 < remaining_days <= 730:  # 2년 = 730일
                is_alert = True

        return vintage_year, is_alert

    def _parse_fund_list(self, data: dict) -> tuple[list[FundListItem], int]:
        """KOFIA 응답에서 펀드 목록을 파싱한다."""
        items_raw = data.get("result", [])
        total = int(data.get("totalCount", len(items_raw)))

        items = []
        for row in items_raw:
            fund_name = row.get("fundNm", "")
            fund_type = self.classify_fund_type(fund_name)

            established_str = row.get("establishedDt", "")
            established_date = _parse_date(established_str)
            maturity_str = row.get("maturityDt", "")
            maturity_date = _parse_date(maturity_str)

            vintage_year, is_maturity_alert = self.calculate_maturity_alert(established_date, maturity_date)

            items.append(
                FundListItem(
                    fund_code=row.get("fundCd", ""),
                    fund_name=fund_name,
                    fund_type=fund_type,
                    company_name=row.get("companyNm", ""),
                    total_amount=_parse_decimal(row.get("totalAmt")),
                    vintage_year=vintage_year,
                    is_maturity_alert=is_maturity_alert,
                )
            )

        return items, total

    def _parse_fund_detail(self, data: dict) -> FundItem:
        """KOFIA 응답에서 펀드 상세 정보를 파싱한다."""
        row = data.get("result", data)
        fund_name = row.get("fundNm", "")
        fund_type = self.classify_fund_type(fund_name)

        established_date = _parse_date(row.get("establishedDt", ""))
        maturity_date = _parse_date(row.get("maturityDt", ""))
        vintage_year, is_maturity_alert = self.calculate_maturity_alert(established_date, maturity_date)

        return FundItem(
            fund_code=row.get("fundCd", ""),
            fund_name=fund_name,
            fund_type=fund_type,
            fund_category=row.get("fundCategory", ""),
            company_name=row.get("companyNm", ""),
            company_code=row.get("companyCd", ""),
            total_amount=_parse_decimal(row.get("totalAmt")),
            management_fee_rate=_parse_decimal(row.get("mgmtFeeRate")),
            performance_fee_rate=_parse_decimal(row.get("perfFeeRate")),
            established_date=established_date,
            maturity_date=maturity_date,
            vintage_year=vintage_year,
            is_maturity_alert=is_maturity_alert,
            description=row.get("fundDesc", ""),
            source_url=row.get("sourceUrl", ""),
        )

    @staticmethod
    def _parse_managers(data: dict) -> list[FundManagerItem]:
        """KOFIA 응답에서 운용 전문인력을 파싱한다."""
        items_raw = data.get("result", [])
        managers = []

        for row in items_raw:
            managers.append(
                FundManagerItem(
                    manager_name=row.get("managerNm", ""),
                    position=row.get("position", ""),
                    role=row.get("role", ""),
                    career_years=_parse_int(row.get("careerYears")),
                    education=row.get("education", ""),
                    certifications=row.get("certifications", ""),
                    appointed_date=_parse_date(row.get("appointedDt", "")),
                    resigned_date=_parse_date(row.get("resignedDt", "")),
                    is_active=row.get("isActive", True),
                )
            )

        return managers

    @cache(ttl=21600, prefix="kofia")  # 6시간 캐시
    async def search_funds(
        self,
        *,
        company_name: str | None = None,
        fund_type: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[FundListItem], int]:
        """펀드 목록을 검색한다.

        Args:
            company_name: 운용사명 검색어
            fund_type: 펀드 유형 필터 (blind/project)
            page: 페이지 번호
            size: 페이지당 건수

        Returns:
            (펀드 목록, 전체 건수)
        """
        params: dict = {"pageIndex": str(page), "pageUnit": str(size)}
        if company_name:
            params["companyNm"] = company_name

        data = await self._request("SDIS01006001000", params)
        items, total = self._parse_fund_list(data)

        # 클라이언트 측 필터: 펀드 유형
        if fund_type:
            items = [f for f in items if f.fund_type == fund_type]

        return items, total

    @cache(ttl=21600, prefix="kofia")  # 6시간 캐시
    async def get_fund_detail(self, fund_code: str) -> FundDetailResponse:
        """펀드 상세 정보를 조회한다.

        Args:
            fund_code: 펀드 표준코드

        Returns:
            FundDetailResponse (펀드 정보 + 운용인력 목록)
        """
        # 펀드 기본 정보
        fund_data = await self._request("SDIS01006001001", {"fundCd": fund_code})
        fund = self._parse_fund_detail(fund_data)

        # 운용 전문인력
        manager_data = await self._request("SDIS01008001000", {"fundCd": fund_code})
        managers = self._parse_managers(manager_data)

        return FundDetailResponse(fund=fund, managers=managers)

    async def get_fund_managers(
        self,
        *,
        company_name: str | None = None,
        fund_code: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[FundManagerItem], int]:
        """운용 전문인력 목록을 조회한다.

        Args:
            company_name: 운용사명 검색어
            fund_code: 펀드 코드 필터
            page: 페이지 번호
            size: 페이지당 건수

        Returns:
            (매니저 목록, 전체 건수)
        """
        params: dict = {"pageIndex": str(page), "pageUnit": str(size)}
        if company_name:
            params["companyNm"] = company_name
        if fund_code:
            params["fundCd"] = fund_code

        data = await self._request("SDIS01008001000", params)
        managers = self._parse_managers(data)
        total = int(data.get("totalCount", len(managers)))

        return managers, total

    async def close(self) -> None:
        """HTTP 클라이언트를 종료한다."""
        await self.client.close()


def _parse_date(value: str) -> date | None:
    """날짜 문자열을 date 객체로 변환한다. (YYYYMMDD 또는 YYYY-MM-DD)"""
    if not value or not value.strip():
        return None
    value = value.strip().replace("-", "")
    if len(value) != 8:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _parse_decimal(value: str | int | float | None) -> Decimal | None:
    """숫자 값을 Decimal로 변환한다."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _parse_int(value: str | int | None) -> int | None:
    """정수 값을 파싱한다."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
