import io
import logging
import xml.etree.ElementTree as ET
import zipfile

from app.core.config import settings
from app.core.exceptions import DARTAPIError
from app.schemas.dart import (
    CompanyInfo,
    CompanyListItem,
    DisclosureItem,
    FinancialStatementItem,
    SanctionItem,
)
from app.utils.cache import cache
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# DART 상태 코드 매핑
DART_STATUS_MESSAGES = {
    "000": "정상",
    "010": "등록되지 않은 키입니다",
    "011": "사용할 수 없는 키입니다 (사용제한)",
    "013": "조회된 데이터가 없습니다",
    "020": "요청 파라미터가 부적절합니다",
    "100": "필드의 부적절한 값입니다",
    "800": "시스템 점검 중입니다",
    "900": "정의되지 않은 오류입니다",
}


class DARTService:
    """Open DART API 연동 서비스"""

    def __init__(self):
        self.api_key = settings.DART_API_KEY
        self.client = AsyncHTTPClient(
            base_url=settings.DART_BASE_URL,
            timeout=30.0,
            headers={"User-Agent": "KIIS/0.1.0"},
        )
        self.rate_limiter = TokenBucketRateLimiter(
            per_minute=settings.DART_RATE_LIMIT_PER_MINUTE,
            per_day=settings.DART_RATE_LIMIT_PER_DAY,
        )

    def _check_response(self, data: dict) -> None:
        """DART API 응답 상태 코드를 검증한다."""
        status = data.get("status", "900")
        if status != "000":
            message = data.get("message", DART_STATUS_MESSAGES.get(status, "알 수 없는 오류"))
            raise DARTAPIError(status_code=status, message=message)

    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """Rate limiting이 적용된 DART API 요청"""
        await self.rate_limiter.acquire()
        if params is None:
            params = {}
        params["crtfc_key"] = self.api_key

        response = await self.client.get(endpoint, params=params)
        try:
            data = response.json()
        except Exception:
            raise DARTAPIError(
                status_code="900",
                message=f"DART API가 비정상 응답을 반환했습니다 (status={response.status_code})",
            )
        self._check_response(data)
        return data

    async def get_corp_codes(self) -> list[CompanyListItem]:
        """기업 고유번호 목록 (ZIP → XML 파싱)"""
        await self.rate_limiter.acquire()

        response = await self.client.get(
            "/corpCode.xml",
            params={"crtfc_key": self.api_key},
        )

        # ZIP 파일 → XML 파싱
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                if not zf.namelist():
                    raise DARTAPIError(status_code="900", message="DART corpCode.xml ZIP이 비어있습니다")
                xml_filename = zf.namelist()[0]
                with zf.open(xml_filename) as xml_file:
                    tree = ET.parse(xml_file)
        except zipfile.BadZipFile as e:
            raise DARTAPIError(status_code="900", message=f"DART corpCode.xml ZIP 파싱 실패: {e}")
        except ET.ParseError as e:
            raise DARTAPIError(status_code="900", message=f"DART corpCode.xml XML 파싱 실패: {e}")

        root = tree.getroot()
        items = []
        for corp in root.findall("list"):
            corp_code = corp.findtext("corp_code", "")
            corp_name = corp.findtext("corp_name", "")
            stock_code = corp.findtext("stock_code", "").strip()
            modify_date = corp.findtext("modify_date", "")
            items.append(
                CompanyListItem(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    modify_date=modify_date,
                )
            )

        return items

    @cache(ttl=86400, prefix="dart", model=CompanyInfo)  # 24시간 캐시
    async def get_company_info(self, corp_code: str) -> CompanyInfo:
        """기업 개황 조회"""
        data = await self._request("/company.json", {"corp_code": corp_code})
        return CompanyInfo(**data)

    @cache(ttl=3600, prefix="dart")  # 1시간 캐시
    async def search_disclosures(
        self,
        *,
        corp_code: str | None = None,
        bgn_de: str | None = None,
        end_de: str | None = None,
        last_reprt_at: str | None = None,
        pblntf_ty: str | None = None,
        page_no: int = 1,
        page_count: int = 20,
    ) -> tuple[list[DisclosureItem], int, int]:
        """공시 검색

        Returns:
            (공시 목록, 전체 건수, 전체 페이지수)
        """
        params: dict = {"page_no": str(page_no), "page_count": str(page_count)}
        if corp_code:
            params["corp_code"] = corp_code
        if bgn_de:
            params["bgn_de"] = bgn_de
        if end_de:
            params["end_de"] = end_de
        if last_reprt_at:
            params["last_reprt_at"] = last_reprt_at
        if pblntf_ty:
            params["pblntf_ty"] = pblntf_ty

        data = await self._request("/list.json", params)

        items = [DisclosureItem(**item) for item in data.get("list", [])]
        total_count = int(data.get("total_count", 0))
        total_page = int(data.get("total_page", 0))

        return items, total_count, total_page

    @cache(ttl=43200, prefix="dart")  # 12시간 캐시
    async def get_financial_statements(
        self,
        *,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011",
        fs_div: str = "CFS",
    ) -> list[FinancialStatementItem]:
        """재무제표 조회 (전체 단일회사)"""
        data = await self._request(
            "/fnlttSinglAcntAll.json",
            {
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code,
                "fs_div": fs_div,
            },
        )
        return [FinancialStatementItem(**item) for item in data.get("list", [])]

    async def get_sanctions(self, corp_code: str) -> list[SanctionItem]:
        """제재 내역 조회"""
        data = await self._request("/exctSttus.json", {"corp_code": corp_code})
        return [SanctionItem(**item) for item in data.get("list", [])]

    async def close(self) -> None:
        await self.client.close()
