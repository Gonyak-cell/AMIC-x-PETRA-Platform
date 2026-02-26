"""금융위원회 기업기본정보 조회 서비스 (GetCorpBasicInfoService_V2).

공공데이터포털 오픈API를 통해 기업 개요, 계열회사, 종속기업을 조회한다.
키 파라미터: crno (법인등록번호 13자리) = Company 모델의 jurir_no

오퍼레이션:
  1. getCorpOutline_V2   — 기업개요조회
  2. getAffiliate_V2     — 계열회사조회
  3. getConsSubsComp_V2  — 연결대상종속기업조회
"""

import logging

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.schemas.corp_basic import (
    AffiliateItem,
    CorpBasicInfoResponse,
    CorpOutlineItem,
    SubsidiaryItem,
)
from app.utils.cache import cache
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

_BASE = "/1160100/service/GetCorpBasicInfoService_V2"


class CorpBasicService:
    """금융위원회 기업기본정보 조회 서비스."""

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

    def _check_result_code(self, data: dict) -> None:
        """응답 코드 검증."""
        header = data.get("response", {}).get("header", {})
        code = header.get("resultCode", "99")
        if code != "00":
            msg = header.get("resultMsg", "알 수 없는 오류")
            raise ExternalAPIError(source="data.go.kr", message=f"[{code}] {msg}")

    # ── API 메서드 ──

    @cache(ttl=86400, prefix="corp_basic:outline", model=CorpOutlineItem)
    async def get_outline(self, crno: str) -> CorpOutlineItem | None:
        """기업 개요 조회 (getCorpOutline_V2)."""
        data = await self._request(
            f"{_BASE}/getCorpOutline_V2",
            params={"crno": crno, "numOfRows": "1", "pageNo": "1"},
        )
        self._check_result_code(data)
        raw_items = self._parse_items(data)
        if not raw_items:
            return None

        item = raw_items[0]
        return CorpOutlineItem(
            crno=item.get("crno", ""),
            corp_nm=item.get("corpNm", ""),
            corp_nm_en=item.get("corpEnsnNm", ""),
            pban_cmp_nm=item.get("enpPbanCmpyNm", ""),
            rep_nm=item.get("enpRprFnm", ""),
            mkt_dcd=item.get("corpRegMrktDcd", ""),
            mkt_dcd_nm=item.get("corpRegMrktDcdNm", ""),
            bzno=item.get("bzno", ""),
            ozpno=item.get("enpOzpno", ""),
            bsadr=item.get("enpBsadr", ""),
            dtadr=item.get("enpDtadr", ""),
            hmpg_url=item.get("enpHmpgUrl", ""),
            tlno=item.get("enpTlno", ""),
            fxno=item.get("enpFxno", ""),
            sic_nm=item.get("sicNm", ""),
            est_dt=item.get("enpEstbDt", ""),
            stac_mm=item.get("enpStacMm", ""),
            xchg_lstg_dt=item.get("enpXchgLstgDt", ""),
            kosdaq_lstg_dt=item.get("enpKosdaqLstgDt", ""),
            krx_lstg_dt=item.get("enpKrxLstgDt", ""),
            smenp_yn=item.get("smenpYn", ""),
            mntr_bnk_nm=item.get("enpMntrBnkNm", ""),
            emp_cnt=item.get("enpEmpeCnt", ""),
            avg_cnwk_term=item.get("empeAvgCnwkTermCtt", ""),
            avg_slry_amt=item.get("enpPn1AvgSlryAmt", ""),
            audpn_nm=item.get("actnAudpnNm", ""),
            audt_opnn=item.get("audtRptOpnnCtt", ""),
            main_biz_nm=item.get("enpMainBizNm", ""),
            fss_corp_unq_no=item.get("fssCorpUnqNo", ""),
        )

    @cache(ttl=86400, prefix="corp_basic:affiliates", model=AffiliateItem)
    async def get_affiliates(self, crno: str) -> list[AffiliateItem]:
        """계열회사 조회 (getAffiliate_V2)."""
        data = await self._request(
            f"{_BASE}/getAffiliate_V2",
            params={"crno": crno, "numOfRows": "100", "pageNo": "1"},
        )
        self._check_result_code(data)
        raw_items = self._parse_items(data)
        return [
            AffiliateItem(
                bas_dt=item.get("basDt", ""),
                crno=item.get("crno", ""),
                afil_cmpy_nm=item.get("afilCmpyNm", ""),
                afil_cmpy_crno=item.get("afilCmpyCrno", ""),
                lstg_yn=item.get("lstgYn", ""),
            )
            for item in raw_items
        ]

    @cache(ttl=86400, prefix="corp_basic:subsidiaries", model=SubsidiaryItem)
    async def get_subsidiaries(self, crno: str) -> list[SubsidiaryItem]:
        """연결대상 종속기업 조회 (getConsSubsComp_V2)."""
        data = await self._request(
            f"{_BASE}/getConsSubsComp_V2",
            params={"crno": crno, "numOfRows": "100", "pageNo": "1"},
        )
        self._check_result_code(data)
        raw_items = self._parse_items(data)
        return [
            SubsidiaryItem(
                bas_dt=item.get("basDt", ""),
                crno=item.get("crno", ""),
                sbrd_enp_nm=item.get("sbrdEnpNm", ""),
                sbrd_enp_estb_dt=item.get("sbrdEnpEstbDt", ""),
                # API 응답에서 sbrdEnpAdr 또는 sbrdEnpadr 두 가지 케이스 대응
                sbrd_enp_adr=item.get("sbrdEnpAdr", item.get("sbrdEnpadr", "")),
                sbrd_enp_main_biz=item.get("sbrdEnpMainBizCtt", ""),
                sbrd_enp_tast_amt=item.get("sbrdEnpLtstEbzyrTastAmt", ""),
                dnt_rlt_bsis=item.get("dntRltBsisCtt", ""),
                main_sbrd_enp_yn=item.get("mainSbrdEnpYnCtt", ""),
            )
            for item in raw_items
        ]

    async def get_full_info(self, crno: str) -> CorpBasicInfoResponse:
        """기업 기본정보 통합 조회 (개요 + 계열회사 + 종속기업)."""
        outline = await self.get_outline(crno)

        # 계열회사/종속기업은 실패해도 outline만 반환
        affiliates: list[AffiliateItem] = []
        subsidiaries: list[SubsidiaryItem] = []
        try:
            affiliates = await self.get_affiliates(crno)
        except Exception as e:
            logger.warning("계열회사 조회 실패 (%s): %s", crno, e)
        try:
            subsidiaries = await self.get_subsidiaries(crno)
        except Exception as e:
            logger.warning("종속기업 조회 실패 (%s): %s", crno, e)

        return CorpBasicInfoResponse(
            outline=outline,
            affiliates=affiliates,
            subsidiaries=subsidiaries,
        )
