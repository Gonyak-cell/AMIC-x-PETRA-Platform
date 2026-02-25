"""공공데이터포털 (data.go.kr) 자산운용사 정보 서비스.

두 API를 조합하여 사모펀드 GP 정보를 제공:
1. 금융통계자산운용사정보 — AUM, 펀드수, 재무현황
2. 금융회사기본정보 — 기본 프로필 (설립일, 주소, 연락처)
"""

import logging
from decimal import Decimal, InvalidOperation

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.schemas.public_data import GPRegistryItem
from app.utils.cache import cache
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# 금융통계자산운용사정보 API 경로
_ASSET_MGMT_BASE = "/1160100/service/GetAsseManaCompInfoService"
_ASSET_MGMT_GENERAL = f"{_ASSET_MGMT_BASE}/getGeneralSttus"
_ASSET_MGMT_FINANCIAL = f"{_ASSET_MGMT_BASE}/getFinSttus"

# 금융회사기본정보 API 경로
_FN_CO_BASE = "/1160100/service/GetFnCoBasiInfoService"
_FN_CO_OUTLINE = f"{_FN_CO_BASE}/getFnCoOutl"


def _safe_decimal(value: str | None) -> Decimal | None:
    if not value or value.strip() in ("", "-", "0"):
        return None
    try:
        return Decimal(value.strip().replace(",", ""))
    except InvalidOperation:
        return None


def _safe_int(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


class PublicDataService:
    """공공데이터포털 자산운용사 정보 조회 서비스."""

    def __init__(self) -> None:
        self.client = AsyncHTTPClient(
            base_url=settings.DATA_GO_KR_BASE_URL,
            timeout=30.0,
        )
        self.rate_limiter = TokenBucketRateLimiter(
            per_minute=settings.DATA_GO_KR_RATE_LIMIT_PER_MINUTE,
            per_day=settings.DATA_GO_KR_RATE_LIMIT_PER_DAY,
        )
        self._api_key = settings.DATA_GO_KR_API_KEY

    async def close(self) -> None:
        await self.client.close()

    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """API 요청 공통 로직."""
        if not self._api_key:
            raise ExternalAPIError(
                source="data.go.kr",
                message="DATA_GO_KR_API_KEY가 설정되지 않았습니다. .env에 추가하세요.",
            )
        await self.rate_limiter.acquire()
        if params is None:
            params = {}
        params["serviceKey"] = self._api_key
        params["resultType"] = "json"
        try:
            response = await self.client.get(endpoint, params=params)
            data = response.json()
            return data
        except Exception as e:
            raise ExternalAPIError(source="data.go.kr", message=str(e)) from e

    @cache(ttl=86400, prefix="public_data:gp_general")
    async def _get_gp_general_list(self, page: int = 1, size: int = 100) -> dict:
        """금융통계자산운용사정보 — 일반현황 조회."""
        return await self._request(
            _ASSET_MGMT_GENERAL,
            params={"numOfRows": str(size), "pageNo": str(page)},
        )

    @cache(ttl=86400, prefix="public_data:gp_financial")
    async def _get_gp_financial_list(self, page: int = 1, size: int = 100) -> dict:
        """금융통계자산운용사정보 — 재무현황 조회."""
        return await self._request(
            _ASSET_MGMT_FINANCIAL,
            params={"numOfRows": str(size), "pageNo": str(page)},
        )

    @cache(ttl=86400, prefix="public_data:fn_co")
    async def _get_fn_co_list(self, page: int = 1, size: int = 100) -> dict:
        """금융회사기본정보 조회."""
        return await self._request(
            _FN_CO_OUTLINE,
            params={"numOfRows": str(size), "pageNo": str(page)},
        )

    def _parse_items(self, data: dict) -> list[dict]:
        """data.go.kr 공통 응답 파싱: body.items.item 추출."""
        try:
            body = data.get("response", {}).get("body", {})
            items = body.get("items", {})
            if isinstance(items, dict):
                item_list = items.get("item", [])
            elif isinstance(items, list):
                item_list = items
            else:
                return []
            if isinstance(item_list, dict):
                return [item_list]
            return item_list if isinstance(item_list, list) else []
        except (AttributeError, TypeError):
            return []

    def _parse_total(self, data: dict) -> int:
        """총 건수 추출."""
        try:
            return int(data.get("response", {}).get("body", {}).get("totalCount", 0))
        except (TypeError, ValueError):
            return 0

    async def search_gp_registry(
        self,
        company_name: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[GPRegistryItem], int]:
        """자산운용사 등록 정보를 검색한다.

        금융통계자산운용사정보 + 금융회사기본정보 API를 조합하여 결과를 반환한다.
        """
        if not self._api_key:
            logger.warning("DATA_GO_KR_API_KEY 미설정 — 빈 결과 반환")
            return [], 0

        # 일반현황 데이터 (AUM, 펀드수, 임직원수 등)
        general_data = await self._get_gp_general_list(page=1, size=500)
        general_items = self._parse_items(general_data)

        # 재무현황 데이터 (자본금, 총자산, 영업수익)
        financial_data = await self._get_gp_financial_list(page=1, size=500)
        financial_items = self._parse_items(financial_data)

        # 금융회사기본정보 (설립일, 주소, 연락처)
        fn_co_data = await self._get_fn_co_list(page=1, size=500)
        fn_co_items = self._parse_items(fn_co_data)

        # 재무 데이터를 회사명으로 인덱싱
        financial_map: dict[str, dict] = {}
        for item in financial_items:
            name = item.get("fncoNm", "").strip()
            if name:
                financial_map[name] = item

        # 금융회사 기본정보를 회사명으로 인덱싱
        fn_co_map: dict[str, dict] = {}
        for item in fn_co_items:
            name = item.get("fncoNm", "").strip()
            if name:
                fn_co_map[name] = item

        # 일반현황 기반으로 통합
        results: list[GPRegistryItem] = []
        for item in general_items:
            name = item.get("fncoNm", "").strip()
            if not name:
                continue

            # 회사명 검색 필터
            if company_name and company_name.lower() not in name.lower():
                continue

            financial = financial_map.get(name, {})
            fn_co = fn_co_map.get(name, {})

            results.append(
                GPRegistryItem(
                    company_name=name,
                    company_name_en=fn_co.get("fncoEnNm", ""),
                    finance_company_code=item.get("fncoNo", ""),
                    business_registration_no=fn_co.get("brno", ""),
                    corporation_registration_no=fn_co.get("crno", ""),
                    established_date=fn_co.get("estbDt", ""),
                    address=fn_co.get("bnAdrs", ""),
                    phone=fn_co.get("rprsTelno", ""),
                    employee_count=_safe_int(item.get("empcnt")),
                    capital=_safe_decimal(financial.get("cptlAmt")),
                    total_assets=_safe_decimal(financial.get("totalAsset")),
                    aum=_safe_decimal(item.get("oprtAssetAmt")),
                    fund_count=_safe_int(item.get("fundCnt")),
                    operating_revenue=_safe_decimal(financial.get("oprtRevnAmt")),
                    authorization_date=item.get("authorizDt", ""),
                    data_date=item.get("baseYm", ""),
                )
            )

        # 정렬: AUM 기준 내림차순 (None은 뒤로)
        results.sort(key=lambda x: x.aum or Decimal(0), reverse=True)

        total = len(results)
        start = (page - 1) * size
        end = start + size
        return results[start:end], total

    async def get_gp_by_name(self, company_name: str) -> GPRegistryItem | None:
        """정확한 회사명으로 운용사 1건을 조회한다."""
        if not self._api_key:
            logger.warning("DATA_GO_KR_API_KEY 미설정 — None 반환")
            return None
        items, _ = await self.search_gp_registry(company_name=company_name, page=1, size=10)
        for item in items:
            if item.company_name == company_name:
                return item
        return items[0] if items else None
