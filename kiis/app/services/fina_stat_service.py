"""금융위원회 기업 재무정보 조회 서비스 (GetFinaStatInfoService_V2).

공공데이터포털 오픈API를 통해 요약재무제표, 재무상태표, 손익계산서를 조회한다.
키 파라미터: crno (법인등록번호 13자리) = Company 모델의 jurir_no
"""

import logging

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.schemas.fina_stat import FinaStatItem, SummaryFinancialItem
from app.utils.cache import cache
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

_BASE = "/1160100/service/GetFinaStatInfoService_V2"


class FinaStatService:
    """금융위원회 기업 재무정보 조회 서비스."""

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

    # ── 공통 요청/파싱 ──

    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """API 요청 공통 로직 (serviceKey, resultType 자동 주입)."""
        if not self._api_key:
            raise ExternalAPIError(
                source="data.go.kr",
                message="DATA_GO_KR_API_KEY가 설정되지 않았습니다.",
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

    def _parse_items(self, data: dict) -> list[dict]:
        """data.go.kr 공통 응답 파싱: response.body.items.item[] 추출."""
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

    def _check_result_code(self, data: dict) -> None:
        """응답 코드 검증."""
        header = data.get("response", {}).get("header", {})
        code = header.get("resultCode", "99")
        if code != "00":
            msg = header.get("resultMsg", "알 수 없는 오류")
            raise ExternalAPIError(source="data.go.kr", message=f"[{code}] {msg}")

    # ── API 메서드 ──

    @cache(ttl=86400, prefix="fina_stat:summary", model=SummaryFinancialItem)
    async def get_summary(self, crno: str, biz_year: str, num_of_rows: int = 10) -> list[SummaryFinancialItem]:
        """요약재무제표 조회 (getSummFinaStat_V2).

        매출, 영업이익, 순이익, 총자산, 부채비율 등 핵심 KPI를 반환한다.
        """
        data = await self._request(
            f"{_BASE}/getSummFinaStat_V2",
            params={
                "crno": crno,
                "bizYear": biz_year,
                "numOfRows": str(num_of_rows),
                "pageNo": "1",
            },
        )
        self._check_result_code(data)
        raw_items = self._parse_items(data)
        return [
            SummaryFinancialItem(
                bas_dt=item.get("basDt", ""),
                crno=item.get("crno", ""),
                biz_year=item.get("bizYear", ""),
                cur_cd=item.get("curCd", "KRW"),
                fncl_dcd=item.get("fnclDcd", ""),
                fncl_dcd_nm=item.get("fnclDcdNm", ""),
                sale_amt=item.get("enpSaleAmt", ""),
                bzop_pft=item.get("enpBzopPft", ""),
                icls_pal_clc_amt=item.get("iclsPalClcAmt", ""),
                crtm_npf=item.get("enpCrtmNpf", ""),
                tast_amt=item.get("enpTastAmt", ""),
                tdbt_amt=item.get("enpTdbtAmt", ""),
                tcpt_amt=item.get("enpTcptAmt", ""),
                cptl_amt=item.get("enpCptlAmt", ""),
                debt_rto=item.get("fnclDebtRto", ""),
            )
            for item in raw_items
        ]

    @cache(ttl=86400, prefix="fina_stat:bs", model=FinaStatItem)
    async def get_balance_sheet(self, crno: str, biz_year: str, num_of_rows: int = 100) -> list[FinaStatItem]:
        """재무상태표 조회 (getBs_V2)."""
        data = await self._request(
            f"{_BASE}/getBs_V2",
            params={
                "crno": crno,
                "bizYear": biz_year,
                "numOfRows": str(num_of_rows),
                "pageNo": "1",
            },
        )
        self._check_result_code(data)
        return self._parse_fina_items(data)

    @cache(ttl=86400, prefix="fina_stat:is", model=FinaStatItem)
    async def get_income_statement(self, crno: str, biz_year: str, num_of_rows: int = 100) -> list[FinaStatItem]:
        """손익계산서 조회 (getIncoStat_V2)."""
        data = await self._request(
            f"{_BASE}/getIncoStat_V2",
            params={
                "crno": crno,
                "bizYear": biz_year,
                "numOfRows": str(num_of_rows),
                "pageNo": "1",
            },
        )
        self._check_result_code(data)
        return self._parse_fina_items(data)

    def _parse_fina_items(self, data: dict) -> list[FinaStatItem]:
        """재무상태표/손익계산서 항목 파싱."""
        raw_items = self._parse_items(data)
        return [
            FinaStatItem(
                bas_dt=item.get("basDt", ""),
                crno=item.get("crno", ""),
                biz_year=item.get("bizYear", ""),
                cur_cd=item.get("curCd", "KRW"),
                fncl_dcd=item.get("fnclDcd", ""),
                fncl_dcd_nm=item.get("fnclDcdNm", ""),
                acit_id=item.get("acitId", ""),
                acit_nm=item.get("acitNm", ""),
                thqr_acit_amt=item.get("thqrAcitAmt", ""),
                crtm_acit_amt=item.get("crtmAcitAmt", ""),
                lsqt_acit_amt=item.get("lsqtAcitAmt", ""),
                pvtr_acit_amt=item.get("pvtrAcitAmt", ""),
                bpvtr_acit_amt=item.get("bpvtrAcitAmt", ""),
            )
            for item in raw_items
        ]
