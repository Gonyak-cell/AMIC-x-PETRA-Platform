import asyncio
import calendar
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.schemas.fund import (
    FundDetailResponse,
    FundItem,
    FundListItem,
    FundManagerItem,
    GPListItem,
)
from app.utils.cache import cache
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# 펀드 유형 자동 분류 키워드
BLIND_FUND_KEYWORDS = ["블라인드", "일반", "성장", "벤처", "기술", "투자조합", "신기술"]
PROJECT_FUND_KEYWORDS = ["프로젝트", "특정", "목적", "인수", "PF"]

# 법률 유형 분류 키워드
PROFESSIONAL_PRIVATE_KEYWORDS = ["전문투자형", "기관전용", "적격투자자", "전문사모"]
PUBLIC_FUND_KEYWORDS = ["공모", "일반투자자"]

# 자산 클래스 분류 키워드 (우선순위순: 구체적 → 일반적)
ASSET_CLASS_KEYWORDS: dict[str, list[str]] = {
    "real_estate": ["부동산", "리얼에스테이트", "real estate", "REF"],
    "infra": ["인프라", "infrastructure", "SOC", "사회기반"],
    "mezzanine": ["메자닌", "CB", "BW", "전환사채", "교환사채"],
    "fund_of_funds": ["재간접", "FoF", "모태", "모태펀드"],
    "pef": ["PEF", "인수", "경영참여", "바이아웃", "buyout"],
    "vc": ["벤처", "VC", "기술", "신기술", "창업"],
}

# KOFIA DIS ProFrame XML 엔드포인트
PROFRAME_PATH = "/proframeWeb/XMLSERVICES/"


def _build_proframe_xml(
    app_name: str,
    svc_name: str,
    fn_name: str,
    dto_name: str,
    fields: dict[str, str],
) -> str:
    """ProFrame XML 요청 메시지를 생성한다.

    KOFIA DIS는 WebSquare/ProFrame 프로토콜을 사용한다.
    callServletService.jsp는 WAF가 차단하므로 proframeWeb/XMLSERVICES/ 엔드포인트를 사용한다.
    """
    field_xml = "\n".join(f"    <{k}>{v}</{k}>" for k, v in fields.items())
    return f"""<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmAppName>{app_name}</pfmAppName>
    <pfmSvcName>{svc_name}</pfmSvcName>
    <pfmFnName>{fn_name}</pfmFnName>
  </proframeHeader>
  <systemHeader></systemHeader>
    <{dto_name}>
{field_xml}
</{dto_name}>
</message>"""


def _parse_proframe_response(xml_text: str) -> tuple[list[dict[str, str]], int]:
    """ProFrame XML 응답을 파싱하여 데이터 목록과 총 개수를 반환한다.

    응답 형식:
    - <selectMeta> 태그: DISCondFuncListDTO 기반 서비스 (기준가격, 보수수수료 등)
    - <list> 태그: 전용 DTO 기반 서비스 (운용사 조회 등)
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        logger.error("Failed to parse ProFrame XML response")
        return [], 0

    # 에러 응답 체크
    resp_code = root.findtext(".//pfmResponseCode", "")
    if resp_code and resp_code.startswith("COMS"):
        msg = root.findtext(".//pfmResponseBasc", "")
        logger.warning("ProFrame error %s: %s", resp_code, msg)
        return [], 0

    total = int(root.findtext(".//dbio_total_count_", "0"))

    items: list[dict[str, str]] = []

    # selectMeta 태그 (DISCondFuncListDTO 기반)
    for meta in root.iter("selectMeta"):
        row: dict[str, str] = {}
        for child in meta:
            if child.text and child.text.strip():
                row[child.tag] = child.text.strip()
        if row:
            items.append(row)

    # list 태그 (전용 DTO 기반)
    if not items:
        for lst in root.iter("list"):
            row = {}
            for child in lst:
                if child.text and child.text.strip():
                    row[child.tag] = child.text.strip()
            if row:
                items.append(row)

    return items, total


class KOFIAService:
    """KOFIA 펀드 데이터 수집 서비스

    KOFIA DIS 전자공시서비스에서 펀드 정보를 수집한다.
    - ProFrame XML 프로토콜 사용 (/proframeWeb/XMLSERVICES/)
    - DISFundStdPriceSO: 펀드 기준가격 (목록 조회)
    - DISFundFeeCmsSO: 펀드 보수수수료
    - DISNewEstSO: 신규설정펀드 현황
    - DISMngCompInqSO: 운용사 조회
    """

    def __init__(self) -> None:
        self.client = AsyncHTTPClient(
            base_url=settings.KOFIA_DIS_BASE_URL,
            timeout=60.0,
            headers={"Content-Type": "text/xml; charset=utf-8"},
        )
        self.rate_limiter = TokenBucketRateLimiter(
            per_minute=settings.KOFIA_RATE_LIMIT_PER_MINUTE,
            per_day=settings.KOFIA_RATE_LIMIT_PER_DAY,
        )
        self._latest_std_dt: str | None = None
        self._latest_fee_dt: str | None = None

    async def _request_proframe(
        self,
        app_name: str,
        svc_name: str,
        fn_name: str,
        dto_name: str,
        fields: dict[str, str],
    ) -> tuple[list[dict[str, str]], int]:
        """ProFrame XML 요청을 전송하고 파싱된 결과를 반환한다."""
        await self.rate_limiter.acquire()
        await asyncio.sleep(settings.KOFIA_REQUEST_DELAY)

        xml_body = _build_proframe_xml(app_name, svc_name, fn_name, dto_name, fields)

        try:
            response = await self.client.post(PROFRAME_PATH, data=xml_body.encode("utf-8"))
            return _parse_proframe_response(response.text)
        except Exception as e:
            logger.error("KOFIA ProFrame request failed (%s/%s): %s", svc_name, fn_name, e)
            raise ExternalAPIError(source="KOFIA", message=str(e)) from e

    async def _get_latest_standard_date(self) -> str:
        """KOFIA의 최신 기준일(영업일)을 조회한다.

        DISComStdYMDSO/select로 최신 기준가격 산출 영업일을 가져온다.
        캐시하여 세션 내 반복 호출을 방지한다.
        """
        if self._latest_std_dt:
            return self._latest_std_dt

        items, _ = await self._request_proframe(
            "FS-DIS2", "DISComStdYMDSO", "select",
            "DISComStdYMDDTO", {"codeDesc": "D_RD"},
        )
        if items:
            self._latest_std_dt = items[0].get("standardDt", "")

        if not self._latest_std_dt:
            # 폴백: 오늘 날짜
            self._latest_std_dt = datetime.now().strftime("%Y%m%d")

        return self._latest_std_dt

    async def _get_latest_fee_date(self) -> str:
        """보수수수료 데이터의 최신 기준일을 조회한다.

        보수수수료(DISFundFeeCmsSO)는 월별 갱신이며 각 월의 마지막 영업일이 기준일이다.
        현재 월 → 직전 월 순으로 마지막 영업일을 시도하여 데이터가 존재하는 날짜를 반환한다.
        """
        if self._latest_fee_dt:
            return self._latest_fee_dt

        today = date.today()

        # 최근 2개월의 마지막 영업일 후보 생성
        for months_back in range(3):
            # 대상 월 계산
            year = today.year
            month = today.month - months_back
            if month <= 0:
                month += 12
                year -= 1

            # 해당 월의 마지막 날
            last_day = calendar.monthrange(year, month)[1]
            candidate = date(year, month, last_day)

            # 주말이면 금요일로 조정
            while candidate.weekday() >= 5:  # 5=Sat, 6=Sun
                candidate -= timedelta(days=1)

            dt_str = candidate.strftime("%Y%m%d")

            # 실제로 데이터가 있는지 빠르게 확인 (1건만 조회)
            items, total = await self._request_proframe(
                "FS-DIS2", "DISFundFeeCmsSO", "select",
                "DISCondFuncDTO", {
                    "tmpV30": dt_str,
                    "tmpV11": "",
                    "tmpV12": "",
                    "tmpV3": "",
                    "tmpV5": "",
                    "tmpV4": "",
                },
            )
            if items:
                logger.info("Fee standard date found: %s (%d items)", dt_str, len(items))
                self._latest_fee_dt = dt_str
                return self._latest_fee_dt

        # 폴백: 가격 기준일 사용
        self._latest_fee_dt = await self._get_latest_standard_date()
        return self._latest_fee_dt

    # ─── 분류 유틸리티 ────────────────────────────────

    @staticmethod
    def classify_fund_type(fund_name: str) -> str:
        """펀드명으로 블라인드/프로젝트 펀드를 자동 구분한다."""
        for keyword in PROJECT_FUND_KEYWORDS:
            if keyword in fund_name:
                return "project"
        for keyword in BLIND_FUND_KEYWORDS:
            if keyword in fund_name:
                return "blind"
        return "blind"

    @staticmethod
    def classify_legal_type(fund_name: str) -> str:
        """펀드명으로 법률 유형을 자동 구분한다."""
        for keyword in PROFESSIONAL_PRIVATE_KEYWORDS:
            if keyword in fund_name:
                return "professional_private"
        for keyword in PUBLIC_FUND_KEYWORDS:
            if keyword in fund_name:
                return "public"
        return "general_private"

    @staticmethod
    def classify_asset_class(fund_name: str, fund_category: str = "") -> str:
        """펀드명과 카테고리로 자산 클래스를 자동 구분한다."""
        text = f"{fund_name} {fund_category}"
        for asset_class, keywords in ASSET_CLASS_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    return asset_class
        return "pef"

    @staticmethod
    def determine_fund_status(is_active: bool, is_maturity_alert: bool) -> str:
        """펀드 상태를 결정한다."""
        if not is_active:
            return "liquidated"
        if is_maturity_alert:
            return "harvest"
        return "active"

    @staticmethod
    def calculate_maturity_alert(
        established_date: date | None,
        maturity_date: date | None = None,
    ) -> tuple[int | None, bool]:
        """빈티지 연도와 회수 집중 구간 여부를 계산한다."""
        if not established_date:
            return None, False

        vintage_year = established_date.year
        today = date.today()
        fund_age = today.year - vintage_year

        is_alert = 7 <= fund_age <= 10

        if maturity_date and not is_alert:
            remaining_days = (maturity_date - today).days
            if 0 < remaining_days <= 730:
                is_alert = True

        return vintage_year, is_alert

    # ─── 파싱 ────────────────────────────────────────

    def _parse_fund_list_from_proframe(
        self, items: list[dict[str, str]]
    ) -> list[FundListItem]:
        """DISFundStdPriceSO 응답을 FundListItem 목록으로 변환한다.

        필드 매핑 (DISFundStdPriceSO/select):
            tmpV1: companyNm (회사명)
            tmpV2: fundNm (펀드명)
            tmpV3: fundType (펀드유형, e.g., "혼합주식형")
            tmpV4: establishedDt (설정일, YYYYMMDD)
            tmpV5: totalAmount (설정액, 백만원)
            tmpV6: stdPrice (기준가격, 원)
            tmpV12: standardCode (펀드 표준코드)
            tmpV13: companyCd (회사코드)
            tmpV14: standardDt (기준일)
        """
        result: list[FundListItem] = []

        for row in items:
            fund_name = row.get("tmpV2", "")
            fund_type = self.classify_fund_type(fund_name)
            fund_category = row.get("tmpV3", "")

            established_date = _parse_date(row.get("tmpV4", ""))
            vintage_year, is_maturity_alert = self.calculate_maturity_alert(established_date)
            legal_type = self.classify_legal_type(fund_name)
            asset_class = self.classify_asset_class(fund_name, fund_category)
            fund_status = self.determine_fund_status(True, is_maturity_alert)

            # 설정액: 백만원 단위 → 원 단위로 변환
            total_amount_raw = _parse_decimal(row.get("tmpV5"))
            total_amount = total_amount_raw * Decimal("1000000") if total_amount_raw else None

            result.append(
                FundListItem(
                    fund_code=row.get("tmpV12", ""),
                    fund_name=fund_name,
                    fund_type=fund_type,
                    legal_type=legal_type,
                    asset_class=asset_class,
                    fund_status=fund_status,
                    company_name=row.get("tmpV1", ""),
                    total_amount=total_amount,
                    vintage_year=vintage_year,
                    is_maturity_alert=is_maturity_alert,
                )
            )

        return result

    def _parse_fund_detail_from_proframe(
        self,
        price_row: dict[str, str],
        fee_row: dict[str, str] | None = None,
    ) -> FundItem:
        """DISFundStdPriceSO + DISFundFeeCmsSO 응답을 FundItem으로 변환한다.

        보수 필드 매핑 (DISFundFeeCmsSO/select):
            tmpV5: managementFee (운용보수, %)
            tmpV9: totalExpenseRatio (총비용비율, %)
            tmpV15: standardCode (표준코드)
        """
        fund_name = price_row.get("tmpV2", "")
        fund_type = self.classify_fund_type(fund_name)
        established_date = _parse_date(price_row.get("tmpV4", ""))
        vintage_year, is_maturity_alert = self.calculate_maturity_alert(established_date)

        total_amount_raw = _parse_decimal(price_row.get("tmpV5"))
        total_amount = total_amount_raw * Decimal("1000000") if total_amount_raw else None

        mgmt_fee = None
        perf_fee = None
        if fee_row:
            mgmt_fee = _parse_decimal(fee_row.get("tmpV5"))
            perf_fee = _parse_decimal(fee_row.get("tmpV11"))

        return FundItem(
            fund_code=price_row.get("tmpV12", ""),
            fund_name=fund_name,
            fund_type=fund_type,
            fund_category=price_row.get("tmpV3", ""),
            company_name=price_row.get("tmpV1", ""),
            company_code=price_row.get("tmpV13", ""),
            total_amount=total_amount,
            management_fee_rate=mgmt_fee,
            performance_fee_rate=perf_fee,
            established_date=established_date,
            maturity_date=None,
            vintage_year=vintage_year,
            is_maturity_alert=is_maturity_alert,
            description="",
            source_url="",
        )

    # ─── 필터 / 정렬 ────────────────────────────────

    _ALLOWED_SORT_FIELDS = {"total_amount", "vintage_year", "fund_name", "company_name"}
    _ALLOWED_GP_SORT_FIELDS = {"total_aum", "fund_count", "company_name"}

    @staticmethod
    def _apply_filters(
        items: list[FundListItem],
        *,
        fund_name: str | None = None,
        fund_types: list[str] | None = None,
        legal_types: list[str] | None = None,
        asset_classes: list[str] | None = None,
        fund_statuses: list[str] | None = None,
        vintage_from: int | None = None,
        vintage_to: int | None = None,
        amount_min: int | None = None,
        amount_max: int | None = None,
    ) -> list[FundListItem]:
        """KOFIA 응답에 로컬 필터를 적용한다."""
        result = items

        if fund_types:
            result = [f for f in result if f.fund_type in fund_types]

        if legal_types:
            result = [f for f in result if f.legal_type in legal_types]

        if asset_classes:
            result = [f for f in result if f.asset_class in asset_classes]

        if fund_statuses:
            result = [f for f in result if f.fund_status in fund_statuses]

        if fund_name:
            keyword = fund_name.lower()
            result = [f for f in result if keyword in f.fund_name.lower()]

        if vintage_from is not None:
            result = [f for f in result if f.vintage_year is not None and f.vintage_year >= vintage_from]

        if vintage_to is not None:
            result = [f for f in result if f.vintage_year is not None and f.vintage_year <= vintage_to]

        if amount_min is not None:
            threshold = Decimal(amount_min) * Decimal("100000000")
            result = [f for f in result if f.total_amount is not None and f.total_amount >= threshold]

        if amount_max is not None:
            threshold = Decimal(amount_max) * Decimal("100000000")
            result = [f for f in result if f.total_amount is not None and f.total_amount <= threshold]

        return result

    @staticmethod
    def _apply_sort(
        items: list[FundListItem],
        *,
        sort_by: str,
        sort_order: str = "desc",
    ) -> list[FundListItem]:
        """펀드 목록을 정렬한다. None 값은 정렬 방향과 무관하게 항상 뒤로 밀린다."""
        reverse = sort_order != "asc"

        with_val = [f for f in items if getattr(f, sort_by, None) is not None]
        without_val = [f for f in items if getattr(f, sort_by, None) is None]

        with_val.sort(key=lambda f: getattr(f, sort_by), reverse=reverse)
        return with_val + without_val

    # ─── 공개 API ────────────────────────────────────

    @cache(ttl=21600, prefix="kofia")
    async def search_funds(
        self,
        *,
        company_name: str | None = None,
        fund_name: str | None = None,
        fund_types: list[str] | None = None,
        legal_types: list[str] | None = None,
        asset_classes: list[str] | None = None,
        fund_statuses: list[str] | None = None,
        vintage_from: int | None = None,
        vintage_to: int | None = None,
        amount_min: int | None = None,
        amount_max: int | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[FundListItem], int]:
        """펀드 목록을 검색한다.

        DISFundStdPriceSO/select 서비스를 사용하여 전체 펀드 기준가격 목록을 조회한 뒤
        서비스 레이어에서 필터링/정렬/페이징을 수행한다.

        ProFrame DISCondFuncDTO 입력 필드:
            tmpV30: standardDt (기준일, YYYYMMDD)
            tmpV11: companyCd (회사코드, 선택)
            tmpV7: fundNm (펀드명 검색, 선택)
            tmpV3: fundType (펀드유형코드, 선택)
        """
        items_raw = await self._get_all_fund_prices()
        items = self._parse_fund_list_from_proframe(items_raw)

        # 운용사명 필터 (서비스 레이어)
        if company_name:
            keyword = company_name.lower()
            items = [f for f in items if keyword in f.company_name.lower()]

        # 서비스 레이어 필터
        items = self._apply_filters(
            items,
            fund_name=fund_name,
            fund_types=fund_types,
            legal_types=legal_types,
            asset_classes=asset_classes,
            fund_statuses=fund_statuses,
            vintage_from=vintage_from,
            vintage_to=vintage_to,
            amount_min=amount_min,
            amount_max=amount_max,
        )

        # 정렬
        if sort_by and sort_by in self._ALLOWED_SORT_FIELDS:
            items = self._apply_sort(items, sort_by=sort_by, sort_order=sort_order)

        filtered_total = len(items)

        # 페이지네이션
        start = (page - 1) * size
        items = items[start : start + size]

        return items, filtered_total

    async def get_gp_list(
        self,
        *,
        company_name: str | None = None,
        asset_class: str | None = None,
        sort_by: str = "total_aum",
        sort_order: str = "desc",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[GPListItem], int]:
        """운용사(GP) 목록을 집계하여 반환한다.

        기존 KOFIA 펀드 캐시 데이터를 company_name별로 그룹화한 뒤
        AUM 합산, 펀드 수, 자산 클래스, 빈티지 범위 등을 집계한다.
        추가 KOFIA API 호출 없이 메모리 그룹화만 수행한다.
        """
        items_raw = await self._get_all_fund_prices()
        funds = self._parse_fund_list_from_proframe(items_raw)

        # company_code 매핑 구축 (tmpV13 = 회사코드)
        code_map: dict[str, str] = {}
        for row in items_raw:
            cn = row.get("tmpV1", "")
            cc = row.get("tmpV13", "")
            if cn and cc:
                code_map[cn] = cc

        # company_name별 그룹화
        groups: dict[str, list[FundListItem]] = {}
        for f in funds:
            groups.setdefault(f.company_name, []).append(f)

        # 운용사명 필터
        if company_name:
            keyword = company_name.lower()
            groups = {k: v for k, v in groups.items() if keyword in k.lower()}

        # 자산 클래스 필터 (쉼표 구분 복수 선택)
        if asset_class:
            target_classes = set(ac.strip() for ac in asset_class.split(",") if ac.strip())
            groups = {
                k: v for k, v in groups.items()
                if target_classes & set(f.asset_class for f in v)
            }

        # GP 집계
        gp_items: list[GPListItem] = []
        for gp_name, gp_funds in groups.items():
            fund_count = len(gp_funds)
            active_count = sum(1 for f in gp_funds if f.fund_status == "active")
            total_aum = sum(
                f.total_amount for f in gp_funds
                if f.total_amount is not None
            ) or None

            asset_classes = sorted(set(f.asset_class for f in gp_funds if f.asset_class))
            vintages = [f.vintage_year for f in gp_funds if f.vintage_year is not None]
            vintage_range = None
            if vintages:
                mn, mx = min(vintages), max(vintages)
                vintage_range = str(mn) if mn == mx else f"{mn}~{mx}"

            has_alert = any(f.is_maturity_alert for f in gp_funds)

            gp_items.append(GPListItem(
                company_name=gp_name,
                company_code=code_map.get(gp_name, ""),
                fund_count=fund_count,
                active_fund_count=active_count,
                total_aum=total_aum,
                asset_classes=asset_classes,
                vintage_range=vintage_range,
                has_maturity_alert=has_alert,
            ))

        # 정렬
        if sort_by in self._ALLOWED_GP_SORT_FIELDS:
            reverse = sort_order != "asc"
            with_val = [g for g in gp_items if getattr(g, sort_by, None) is not None]
            without_val = [g for g in gp_items if getattr(g, sort_by, None) is None]
            with_val.sort(key=lambda g: getattr(g, sort_by), reverse=reverse)
            gp_items = with_val + without_val

        total = len(gp_items)

        # 페이지네이션
        start = (page - 1) * size
        gp_items = gp_items[start : start + size]

        return gp_items, total

    @cache(ttl=21600, prefix="kofia")
    async def get_fund_detail(self, fund_code: str) -> FundDetailResponse:
        """펀드 상세 정보를 조회한다.

        DISFundStdPriceSO에서 전체 펀드 목록을 가져온 뒤 fund_code로 필터링한다.
        DISFundFeeCmsSO에서 보수 정보를 추가로 조회한다.

        Note: ProFrame API는 개별 펀드 조회를 지원하지 않으므로 전체 목록에서 검색한다.
        search_funds와 동일한 캐시 키 접두사를 사용하여 데이터를 공유한다.
        """
        price_items = await self._get_all_fund_prices()

        # 펀드 코드로 필터 (tmpV12 = 표준코드)
        price_row = next(
            (r for r in price_items if r.get("tmpV12", "") == fund_code),
            None,
        )

        if not price_row:
            raise ExternalAPIError(
                source="KOFIA",
                message=f"Fund not found: {fund_code}",
            )

        # 보수 정보 (별도 조회 — 월별 기준일 사용)
        fee_row = await self._get_fund_fee(fund_code)

        fund = self._parse_fund_detail_from_proframe(price_row, fee_row)
        return FundDetailResponse(fund=fund, managers=[])

    @cache(ttl=21600, prefix="kofia:all_prices")
    async def _get_all_fund_prices(self) -> list[dict[str, str]]:
        """전체 펀드 기준가격 목록을 캐시하여 반환한다."""
        std_dt = await self._get_latest_standard_date()
        fields = {
            "tmpV30": std_dt,
            "tmpV3": "",
            "tmpV4": "",
            "tmpV7": "",
            "tmpV5": "",
            "tmpV11": "",
            "tmpV12": "",
            "tmpV50": "",
            "tmpV51": "",
        }
        items, _ = await self._request_proframe(
            "FS-DIS2", "DISFundStdPriceSO", "select",
            "DISCondFuncDTO", fields,
        )
        return items

    @cache(ttl=21600, prefix="kofia:all_fees")
    async def _get_all_fund_fees(self) -> list[dict[str, str]]:
        """전체 펀드 보수수수료 목록을 캐시하여 반환한다.

        보수수수료는 월별 갱신이므로 _get_latest_fee_date()로 별도 기준일을 사용한다.
        """
        fee_dt = await self._get_latest_fee_date()
        fee_fields = {
            "tmpV30": fee_dt,
            "tmpV11": "",
            "tmpV12": "",
            "tmpV3": "",
            "tmpV5": "",
            "tmpV4": "",
        }
        items, _ = await self._request_proframe(
            "FS-DIS2", "DISFundFeeCmsSO", "select",
            "DISCondFuncDTO", fee_fields,
        )
        return items

    async def _get_fund_fee(self, fund_code: str) -> dict[str, str] | None:
        """특정 펀드의 보수수수료 정보를 조회한다."""
        try:
            fee_items = await self._get_all_fund_fees()
            # tmpV15 = 표준코드 (보수수수료 응답)
            return next(
                (r for r in fee_items if r.get("tmpV15", "") == fund_code),
                None,
            )
        except Exception as e:
            logger.warning("Failed to fetch fund fee for %s: %s", fund_code, e)
            return None

    async def _resolve_company_code(self, company_name: str) -> str:
        """운용사명으로 회사코드를 조회한다."""
        std_dt = await self._get_latest_standard_date()
        items, _ = await self._request_proframe(
            "FS-DIS2", "DISMngCompInqSO", "select",
            "DISMngCompInqListDTO", {"option": "P", "standardDt": std_dt},
        )
        keyword = company_name.lower()
        for item in items:
            name = item.get("koreanNm", "")
            if keyword in name.lower():
                return item.get("manageCompCd", "")
        return ""

    async def get_fund_managers(
        self,
        *,
        company_name: str | None = None,
        fund_code: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[FundManagerItem], int]:
        """운용 전문인력 목록을 조회한다.

        현재 KOFIA DIS ProFrame API에서 운용인력 전용 서비스를 발견하지 못하여
        빈 목록을 반환한다. 추후 서비스 발견 시 업데이트 예정.
        """
        logger.info("Fund manager query not yet supported via ProFrame API")
        return [], 0

    async def close(self) -> None:
        """HTTP 클라이언트를 종료한다."""
        self._latest_std_dt = None
        self._latest_fee_dt = None
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
