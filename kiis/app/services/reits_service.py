import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup, Tag

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.schemas.reits import (
    REITsAssetItem,
    REITsDetailResponse,
    REITsItem,
    REITsListItem,
)
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# 리츠 유형 자동 분류 키워드
SELF_MANAGED_KEYWORDS = ["자기관리"]
ENTRUSTED_KEYWORDS = ["위탁관리", "기업구조조정"]

# 자산 유형 매핑 (자산명 키워드 → 유형 코드)
ASSET_TYPE_MAP = {
    "오피스": "office",
    "사무실": "office",
    "업무시설": "office",
    "물류": "logistics",
    "창고": "logistics",
    "주거": "residential",
    "주택": "residential",
    "아파트": "residential",
    "리테일": "retail",
    "상가": "retail",
    "판매시설": "retail",
    "호텔": "hotel",
    "숙박": "hotel",
    "리조트": "hotel",
}

# 부동산 자산 비율 최소 기준 (70%)
REAL_ESTATE_MIN_RATIO = Decimal("70.0")

# HTML 파싱 CSS 셀렉터 (사이트 구조 변경 시 코드 수정 없이 대응)
SELECTORS = {
    "list_table": "table.tbl_list tbody tr",
    "detail_info": "table.tbl_view",
    "asset_table": "table.tbl_asset tbody tr",
}


class REITsService:
    """리츠정보시스템 데이터 수집 서비스

    리츠정보시스템(reits.molit.go.kr)에서 리츠 데이터를 파싱한다.
    - 리츠 인가 현황, 자산 구성, 배당 정보
    - 자기관리/위탁관리 리츠 자동 분류
    - 부동산 자산 70% 미달 경고 기능
    """

    def __init__(self) -> None:
        self.client = AsyncHTTPClient(
            base_url=settings.REITS_BASE_URL,
            timeout=30.0,
            headers={
                "User-Agent": "KIIS/0.1.0",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
        )
        self.rate_limiter = TokenBucketRateLimiter(
            per_minute=settings.REITS_RATE_LIMIT_PER_MINUTE,
            per_day=settings.REITS_RATE_LIMIT_PER_DAY,
        )

    async def _fetch_html(self, path: str, params: dict | None = None) -> BeautifulSoup:
        """Rate limiting + delay가 적용된 HTML 페이지 요청

        Args:
            path: URL 경로
            params: 쿼리 파라미터

        Returns:
            BeautifulSoup 파싱 결과
        """
        await self.rate_limiter.acquire()
        await asyncio.sleep(settings.REITS_REQUEST_DELAY)

        try:
            response = await self.client.get(path, params=params)
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error("REITs page fetch failed (path=%s): %s", path, e)
            raise ExternalAPIError(source="REITs", message=str(e)) from e

    @staticmethod
    def classify_reits_type(reits_type_text: str, employee_count: int | None = None) -> str:
        """리츠 유형을 자동 분류한다.

        자기관리 리츠: 실체 회사 (임직원 상근), 과세 대상
        위탁관리 리츠: 명목 회사, 90% 이상 배당 시 법인세 공제

        Args:
            reits_type_text: 리츠 유형 텍스트
            employee_count: 임직원 수 (자기관리 검증용)

        Returns:
            "self_managed" 또는 "entrusted"
        """
        for keyword in SELF_MANAGED_KEYWORDS:
            if keyword in reits_type_text:
                return "self_managed"
        for keyword in ENTRUSTED_KEYWORDS:
            if keyword in reits_type_text:
                return "entrusted"
        # 임직원 수 기반 추정: 자기관리는 상근 임직원 보유
        if employee_count is not None and employee_count > 0:
            return "self_managed"
        return "entrusted"

    @staticmethod
    def check_asset_ratio_warning(real_estate_ratio: Decimal | None) -> bool:
        """부동산 자산 비율 70% 미달 여부를 확인한다.

        리츠는 부동산 자산 비율이 70% 이상이어야 한다.
        미달 시 경고(Flagging) 대상.

        Args:
            real_estate_ratio: 부동산 자산 비율 (%)

        Returns:
            True이면 경고 대상
        """
        if real_estate_ratio is None:
            return False
        return real_estate_ratio < REAL_ESTATE_MIN_RATIO

    @staticmethod
    def calculate_dividend_payout_ratio(
        total_dividend: Decimal | None,
        net_income: Decimal | None,
    ) -> Decimal | None:
        """배당성향(배당금/당기순이익)을 계산한다.

        Args:
            total_dividend: 배당금 총액
            net_income: 당기순이익

        Returns:
            배당성향 (%) 또는 None
        """
        if total_dividend is None or net_income is None:
            return None
        if net_income <= 0:
            return None
        return (total_dividend / net_income * 100).quantize(Decimal("0.01"))

    @staticmethod
    def classify_asset_type(asset_name: str) -> str:
        """자산명으로 자산 유형을 자동 분류한다.

        Args:
            asset_name: 자산명

        Returns:
            자산 유형 코드 (office/logistics/residential/retail/hotel/other)
        """
        for keyword, asset_type in ASSET_TYPE_MAP.items():
            if keyword in asset_name:
                return asset_type
        return "other"

    def _parse_reits_list(self, soup: BeautifulSoup) -> tuple[list[REITsListItem], int]:
        """HTML에서 리츠 목록을 파싱한다."""
        rows = soup.select(SELECTORS["list_table"])
        items = []

        for row in rows:
            cols = row.select("td")
            if len(cols) < 6:
                continue

            reits_code = _extract_text(cols[0])
            reits_name = _extract_text(cols[1])
            reits_type_text = _extract_text(cols[2])
            reits_type = self.classify_reits_type(reits_type_text)
            management_company = _extract_text(cols[3])
            total_assets = _parse_decimal(_extract_text(cols[4]))
            real_estate_ratio = _parse_decimal(_extract_text(cols[5]))
            has_warning = self.check_asset_ratio_warning(real_estate_ratio)

            status = "operating"
            is_listed = False
            if len(cols) > 6:
                status = _classify_status(_extract_text(cols[6]))
            if len(cols) > 7:
                is_listed = _is_listed(_extract_text(cols[7]))

            items.append(
                REITsListItem(
                    reits_code=reits_code,
                    reits_name=reits_name,
                    reits_type=reits_type,
                    management_company=management_company,
                    total_assets=total_assets,
                    real_estate_ratio=real_estate_ratio,
                    has_asset_ratio_warning=has_warning,
                    status=status,
                    is_listed=is_listed,
                )
            )

        return items, len(items)

    def _parse_reits_detail(self, soup: BeautifulSoup) -> REITsItem:
        """HTML에서 리츠 상세 정보를 파싱한다."""
        info: dict[str, str] = {}
        tables = soup.select(SELECTORS["detail_info"])

        for table in tables:
            for row in table.select("tr"):
                th = row.select_one("th")
                td = row.select_one("td")
                if th and td:
                    info[_extract_text(th)] = _extract_text(td)

        reits_type_text = info.get("리츠유형", "")
        employee_count = _parse_int(info.get("임직원수", ""))
        reits_type = self.classify_reits_type(reits_type_text, employee_count)

        total_assets = _parse_decimal(info.get("총자산", ""))
        real_estate_amount = _parse_decimal(info.get("부동산자산", ""))
        real_estate_ratio = _parse_decimal(info.get("부동산비율", ""))

        # 비율이 없으면 자산 금액 기반으로 직접 계산
        if real_estate_ratio is None and total_assets and real_estate_amount and total_assets > 0:
            real_estate_ratio = (real_estate_amount / total_assets * 100).quantize(Decimal("0.01"))

        net_income = _parse_decimal(info.get("당기순이익", ""))
        total_dividend = _parse_decimal(info.get("배당금", ""))
        dividend_payout_ratio = self.calculate_dividend_payout_ratio(total_dividend, net_income)

        return REITsItem(
            reits_code=info.get("리츠코드", ""),
            reits_name=info.get("리츠명", ""),
            reits_type=reits_type,
            management_company=info.get("자산관리회사", ""),
            establishment_date=_parse_date(info.get("설립인가일", "")),
            listing_date=_parse_date(info.get("상장일", "")),
            total_assets=total_assets,
            real_estate_amount=real_estate_amount,
            real_estate_ratio=real_estate_ratio,
            has_asset_ratio_warning=self.check_asset_ratio_warning(real_estate_ratio),
            dividend_rate=_parse_decimal(info.get("배당수익률", "")),
            dividend_payout_ratio=dividend_payout_ratio,
            net_income=net_income,
            total_dividend=total_dividend,
            employee_count=employee_count,
            status=_classify_status(info.get("상태", "")),
            is_listed=_is_listed(info.get("상장여부", "")),
            source_url=info.get("source_url", ""),
        )

    @staticmethod
    def _parse_assets(soup: BeautifulSoup) -> list[REITsAssetItem]:
        """HTML에서 자산 목록을 파싱한다."""
        rows = soup.select(SELECTORS["asset_table"])
        assets = []

        for row in rows:
            cols = row.select("td")
            if len(cols) < 3:
                continue

            asset_name = _extract_text(cols[0])
            asset_type = REITsService.classify_asset_type(asset_name)
            asset_value = _parse_decimal(_extract_text(cols[1]))
            asset_ratio = _parse_decimal(_extract_text(cols[2]))
            location = _extract_text(cols[3]) if len(cols) > 3 else ""
            acquisition_date = _parse_date(_extract_text(cols[4])) if len(cols) > 4 else None

            assets.append(
                REITsAssetItem(
                    asset_name=asset_name,
                    asset_type=asset_type,
                    asset_value=asset_value,
                    asset_ratio=asset_ratio,
                    location=location,
                    acquisition_date=acquisition_date,
                )
            )

        return assets

    async def search_reits(
        self,
        *,
        reits_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[REITsListItem], int]:
        """리츠 목록을 검색한다.

        Args:
            reits_type: 리츠 유형 필터 (self_managed/entrusted)
            status: 상태 필터 (authorized/operating/dissolved)
            page: 페이지 번호
            size: 페이지당 건수

        Returns:
            (리츠 목록, 전체 건수)
        """
        params = {"page": str(page), "size": str(size)}

        soup = await self._fetch_html("/reits/directInvest/reitsList.do", params)
        items, total = self._parse_reits_list(soup)

        # 클라이언트 측 필터
        if reits_type:
            items = [r for r in items if r.reits_type == reits_type]
        if status:
            items = [r for r in items if r.status == status]

        return items, total

    async def get_reits_detail(self, reits_code: str) -> REITsDetailResponse:
        """리츠 상세 정보를 조회한다.

        Args:
            reits_code: 리츠 코드

        Returns:
            REITsDetailResponse (리츠 정보 + 자산 목록)
        """
        soup = await self._fetch_html(
            "/reits/directInvest/reitsDetail.do",
            {"reitsCode": reits_code},
        )
        reits = self._parse_reits_detail(soup)
        assets = self._parse_assets(soup)

        return REITsDetailResponse(reits=reits, assets=assets)

    async def get_reits_assets(self, reits_code: str) -> list[REITsAssetItem]:
        """리츠 자산 목록을 조회한다.

        Args:
            reits_code: 리츠 코드

        Returns:
            자산 목록
        """
        soup = await self._fetch_html(
            "/reits/directInvest/reitsDetail.do",
            {"reitsCode": reits_code},
        )
        return self._parse_assets(soup)

    async def close(self) -> None:
        """HTTP 클라이언트를 종료한다."""
        await self.client.close()


def _extract_text(element: Tag | None) -> str:
    """BeautifulSoup 엘리먼트에서 텍스트를 추출한다."""
    if element is None:
        return ""
    return element.get_text(strip=True)


def _is_listed(text: str) -> bool:
    """상장 여부를 판별한다. '비상장'은 False."""
    if "비상장" in text or "미상장" in text:
        return False
    return "상장" in text


def _classify_status(status_text: str) -> str:
    """상태 텍스트를 코드로 변환한다."""
    if "해산" in status_text or "청산" in status_text:
        return "dissolved"
    if "영업" in status_text or "운영" in status_text:
        return "operating"
    return "authorized"


def _parse_date(value: str) -> date | None:
    """날짜 문자열을 date 객체로 변환한다. (YYYYMMDD, YYYY-MM-DD, YYYY.MM.DD)"""
    if not value or not value.strip():
        return None
    value = value.strip().replace("-", "").replace(".", "").replace("/", "")
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
        cleaned = str(value).replace(",", "").replace(" ", "").replace("백만원", "").replace("%", "")
        if not cleaned:
            return None
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _parse_int(value: str | int | None) -> int | None:
    """정수 값을 파싱한다."""
    if value is None or value == "":
        return None
    try:
        cleaned = str(value).replace(",", "").replace("명", "").replace("인", "").strip()
        return int(cleaned)
    except (ValueError, TypeError):
        return None
