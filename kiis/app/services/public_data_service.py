"""공공데이터포털 (data.go.kr) 자산운용사 정보 서비스.

두 API를 조합하여 사모펀드 GP 정보를 제공:
1. 금융통계자산운용사정보 — AUM, 펀드수, 재무현황
2. 금융회사기본정보 — 기본 프로필 (설립일, 주소, 연락처)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.models.company import Company, CompanyAlias
from app.schemas.public_data import GPRegistryItem
from app.utils.cache import cache
from app.utils.entity_resolver import EntityResolver, normalize_company_name
from app.utils.http_client import AsyncHTTPClient
from app.utils.numeric import safe_decimal, safe_int
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# 금융통계자산운용사정보 API 경로
_ASSET_MGMT_BASE = "/1160100/service/GetAsseManaCompInfoService"
_ASSET_MGMT_GENERAL = f"{_ASSET_MGMT_BASE}/getGeneralSttus"
_ASSET_MGMT_FINANCIAL = f"{_ASSET_MGMT_BASE}/getFinSttus"

# 금융회사기본정보 API 경로
_FN_CO_BASE = "/1160100/service/GetFnCoBasiInfoService"
_FN_CO_OUTLINE = f"{_FN_CO_BASE}/getFnCoOutl"


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

        # 3개 API 병렬 호출 (각각 캐시 데코레이터 적용)
        import asyncio as _asyncio

        general_data, financial_data, fn_co_data = await _asyncio.gather(
            self._get_gp_general_list(page=1, size=500),
            self._get_gp_financial_list(page=1, size=500),
            self._get_fn_co_list(page=1, size=500),
        )
        general_items = self._parse_items(general_data)
        financial_items = self._parse_items(financial_data)
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
                    employee_count=safe_int(item.get("empcnt")),
                    capital=safe_decimal(financial.get("cptlAmt")),
                    total_assets=safe_decimal(financial.get("totalAsset")),
                    aum=safe_decimal(item.get("oprtAssetAmt")),
                    fund_count=safe_int(item.get("fundCnt")),
                    operating_revenue=safe_decimal(financial.get("oprtRevnAmt")),
                    authorization_date=item.get("authorizDt", ""),
                    data_date=item.get("baseYm", ""),
                )
            )

        # 정렬: AUM 기준 내림차순 (None은 뒤로)
        results.sort(key=lambda x: x.aum or Decimal("0"), reverse=True)

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

    # ──────────────────────────────────────────────
    # GP 프로파일 DB 동기화 (Phase 1)
    # ──────────────────────────────────────────────

    async def sync_gp_profiles(self, db: AsyncSession) -> GPSyncResult:
        """공공데이터 GP 레지스트리를 Company 테이블에 동기화한다.

        1. 전체 GP 목록 API 조회
        2. EntityResolver로 기존 Company 매칭
        3. 매칭 → GP 컬럼 업데이트
        4. 미매칭 → 신규 Company 생성 (is_gp=True, corp_code=None)
        5. CompanyAlias 자동 등록
        """
        result = GPSyncResult()

        if not self._api_key:
            logger.warning("DATA_GO_KR_API_KEY 미설정 — 동기화 스킵")
            return result

        # 전체 GP 목록 조회 (페이지네이션 없이 전량)
        all_items, _ = await self.search_gp_registry(page=1, size=9999)
        result.total_api_items = len(all_items)
        logger.info("공공데이터 GP %d건 조회 완료", len(all_items))

        resolver = EntityResolver()
        now = datetime.now(UTC)

        for item in all_items:
            try:
                await self._sync_single_gp(db, resolver, item, now, result)
            except Exception:
                logger.exception("GP 동기화 실패: %s", item.company_name)
                result.errors.append(item.company_name)

        await db.commit()
        logger.info(
            "GP 동기화 완료: 업데이트 %d, 신규 %d, 별칭 %d, 에러 %d",
            result.updated,
            result.created,
            result.aliases_added,
            len(result.errors),
        )
        return result

    async def _sync_single_gp(
        self,
        db: AsyncSession,
        resolver: EntityResolver,
        item: GPRegistryItem,
        now: datetime,
        result: GPSyncResult,
    ) -> None:
        """단일 GP 항목을 Company에 동기화한다."""
        # 1. EntityResolver로 기존 Company 매칭
        match_result = await resolver.resolve(db, item.company_name)
        matched = match_result.get("match")

        if matched:
            # 기존 Company 업데이트
            stmt = select(Company).where(Company.corp_code == matched["corp_code"])
            # corp_code가 None인 경우 corp_name으로 매칭
            if matched["corp_code"] is None:
                stmt = select(Company).where(func.lower(Company.corp_name) == func.lower(matched["corp_name"]))
            db_result = await db.execute(stmt)
            company = db_result.scalar_one_or_none()

            if company:
                self._update_gp_fields(company, item, now)
                result.updated += 1
                return

        # 2. finance_company_code로 직접 매칭 시도
        if item.finance_company_code:
            stmt = select(Company).where(Company.finance_company_code == item.finance_company_code)
            db_result = await db.execute(stmt)
            company = db_result.scalar_one_or_none()
            if company:
                self._update_gp_fields(company, item, now)
                result.updated += 1
                return

        # 3. 신규 Company 생성
        company = Company(
            corp_code=None,
            corp_name=item.company_name,
            corp_name_eng=item.company_name_en or None,
            bizr_no=item.business_registration_no or None,
            jurir_no=item.corporation_registration_no or None,
            adres=item.address or None,
            phn_no=item.phone or None,
            est_dt=item.established_date or None,
            is_gp=True,
            finance_company_code=item.finance_company_code or None,
            gp_authorization_date=item.authorization_date or None,
            gp_aum=item.aum,
            gp_fund_count=item.fund_count,
            gp_employee_count=item.employee_count,
            gp_strategy_tags={"sources": ["public_data"], "strategies": []},
            gp_profile_synced_at=now,
        )
        db.add(company)
        await db.flush()
        result.created += 1

        # 정규화 별칭 자동 등록
        normalized = normalize_company_name(item.company_name)
        if normalized and normalized != item.company_name:
            alias = CompanyAlias(
                alias_name=normalized,
                company_id=company.id,
                is_manual=False,
            )
            db.add(alias)
            result.aliases_added += 1

    @staticmethod
    def _update_gp_fields(company: Company, item: GPRegistryItem, now: datetime) -> None:
        """Company의 GP 프로파일 필드를 업데이트한다."""
        company.is_gp = True
        if item.finance_company_code:
            company.finance_company_code = item.finance_company_code
        if item.authorization_date:
            company.gp_authorization_date = item.authorization_date
        # gp_aum: 기존 값이 없는 경우에만 덮어씀 (FreeSIS 등 다른 소스 값 보호)
        if item.aum is not None and company.gp_aum is None:
            company.gp_aum = item.aum
        if item.fund_count is not None:
            company.gp_fund_count = item.fund_count
        if item.employee_count is not None:
            company.gp_employee_count = item.employee_count
        if item.address and not company.adres:
            company.adres = item.address
        if item.phone and not company.phn_no:
            company.phn_no = item.phone
        if item.established_date and not company.est_dt:
            company.est_dt = item.established_date

        # gp_strategy_tags에 public_data 소스 머지 (dict 복사로 mutation safety 확보)
        tags = dict(company.gp_strategy_tags or {})
        sources = list(tags.get("sources", []))
        if "public_data" not in sources:
            sources.append("public_data")
        tags["sources"] = sources
        if "strategies" not in tags:
            tags["strategies"] = []
        company.gp_strategy_tags = tags

        company.gp_profile_synced_at = now


async def search_gp_companies(
    db: AsyncSession,
    *,
    company_name: str | None = None,
    source: str | None = None,
    strategy: str | None = None,
    sort_by: str = "aum",
    page: int = 1,
    size: int = 20,
) -> tuple[list[Company], int]:
    """Company 테이블에서 GP(is_gp=True)를 통합 조회한다.

    FreeSIS, KVIC, 공공데이터포털 등 여러 소스에서 동기화된 GP를
    source/strategy 필터와 정렬로 조회한다.
    """
    stmt = select(Company).where(Company.is_gp.is_(True))

    if company_name:
        stmt = stmt.where(Company.corp_name.ilike(f"%{company_name}%"))

    if source:
        stmt = stmt.where(cast(Company.gp_strategy_tags, String).contains(f'"{source}"'))

    if strategy:
        stmt = stmt.where(cast(Company.gp_strategy_tags, String).contains(f'"{strategy}"'))

    if sort_by == "fund_count":
        stmt = stmt.order_by(Company.gp_fund_count.desc().nulls_last())
    elif sort_by == "company_name":
        stmt = stmt.order_by(Company.corp_name.asc())
    elif sort_by == "commitment":
        stmt = stmt.order_by(Company.gp_total_commitment.desc().nulls_last())
    else:
        stmt = stmt.order_by(Company.gp_aum.desc().nulls_last())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


@dataclass
class GPSyncResult:
    """GP 동기화 결과."""

    total_api_items: int = 0
    created: int = 0
    updated: int = 0
    aliases_added: int = 0
    errors: list[str] = field(default_factory=list)
