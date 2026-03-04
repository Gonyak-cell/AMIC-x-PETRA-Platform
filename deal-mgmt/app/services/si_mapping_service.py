"""SI 매핑 서비스 — KSIC 기반 전략적 투자자 후보 자동 매핑."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.core.config import settings
from app.core.exceptions import CompanyNotFoundError
from app.core.security import make_service_token
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction, BuyerCandidateStatus, BuyerType
from app.models.io_transaction import IOTransaction
from app.models.ksic_io_mapping import KsicIoMapping
from app.models.si_company import SICompany
from app.models.vc_company import VcCompany
from app.models.vc_industry_coefficient import VcIndustryCoefficient
from app.schemas.si_mapping import (
    BulkAddBuyersResponse,
    CompanyOverview,
    DeepDiveDisclosure,
    DeepDiveResponse,
    FinancialSummary,
    KsicSuggestion,
    SanctionItem,
    SICandidateOut,
    SICompanyOut,
    SIDataStats,
    SIMappingResponse,
    ValueChainPanel,
    VcChainCompany,
    VcChainPanel,
    VcCompanyLookupResult,
    VcDataStats,
    VcIndustrySuggestion,
    VcMappingByRegResponse,
    VcMappingResponse,
)
from app.services import audit_service

# KIIS DART API 호출용 재사용 클라이언트 (모듈 레벨 싱글턴)
_kiis_http_client: httpx.AsyncClient | None = None
_kiis_http_lock = asyncio.Lock()


async def _get_kiis_http_client() -> httpx.AsyncClient:
    """KIIS DART API 호출용 httpx.AsyncClient 싱글턴."""
    global _kiis_http_client
    if _kiis_http_client is None or _kiis_http_client.is_closed:
        async with _kiis_http_lock:
            if _kiis_http_client is None or _kiis_http_client.is_closed:
                _kiis_http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=10.0),
                )
    return _kiis_http_client


async def close_kiis_dart_client() -> None:
    """lifespan shutdown — KIIS DART API httpx 클라이언트 커넥션 정리."""
    global _kiis_http_client
    async with _kiis_http_lock:
        if _kiis_http_client is not None and not _kiis_http_client.is_closed:
            await _kiis_http_client.aclose()
        _kiis_http_client = None


logger = logging.getLogger(__name__)


# ── 데이터 통계 ───────────────────────────────────────────
async def get_data_stats(db: AsyncSession) -> SIDataStats:
    """참조 테이블 시딩 상태 반환.

    SICompany 관련 4개 COUNT를 단일 집계 쿼리로 병합 (6→3회 DB 왕복).
    """
    # SICompany: 4개 COUNT를 단일 쿼리로 병합
    si_agg = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count(SICompany.revenue).label("with_revenue"),
                func.count(SICompany.fina_stat_synced_at).label("with_fina"),
                func.count(SICompany.corp_basic_synced_at).label("with_corp"),
            ).select_from(SICompany)
        )
    ).one()
    si_count = si_agg.total
    rev_count = si_agg.with_revenue
    fina_stat_count = si_agg.with_fina
    corp_basic_count = si_agg.with_corp

    # 별도 테이블 COUNT (각 1회)
    mapping_count = (await db.execute(select(func.count()).select_from(KsicIoMapping))).scalar() or 0
    io_count = (await db.execute(select(func.count()).select_from(IOTransaction))).scalar() or 0

    return SIDataStats(
        si_companies_count=si_count,
        ksic_io_mappings_count=mapping_count,
        io_transactions_count=io_count,
        revenue_count=rev_count,
        fina_stat_count=fina_stat_count,
        corp_basic_count=corp_basic_count,
        is_seeded=si_count > 0 and mapping_count > 0 and io_count > 0,
    )


# ── KSIC 자동완성 ─────────────────────────────────────────
def _strip_ksic_prefix(code: str) -> str:
    """KSIC 대분류 알파벳 접두사 제거 (J58211 → 58211).

    단일 알파벳 + 4~5자리 숫자 패턴만 strip (표준 KSIC 세분류/세세분류).
    C10 같은 짧은 코드는 그대로 유지.
    """
    m = re.match(r"^[A-Za-z](\d{4,5})$", code)
    return m.group(1) if m else code


async def search_ksic(db: AsyncSession, query: str, limit: int = 20) -> list[KsicSuggestion]:
    """KSIC 코드/이름 검색 — 자동완성용."""
    if not query or len(query) < 1:
        return []
    q = query.strip()
    # 검색용: 선행 알파벳 제거 (J58 → 58, ILIKE '%58%'로 58211 등 매칭)
    cleaned = re.sub(r"^[A-Za-z]+", "", q)
    cleaned = cleaned if cleaned else q  # 알파벳만 입력 시 원본 유지 (이름 검색용)
    escaped = cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    q = (
        select(KsicIoMapping.ksic_code, KsicIoMapping.ksic_name)
        .where(
            KsicIoMapping.ksic_code.ilike(pattern, escape="\\") | KsicIoMapping.ksic_name.ilike(pattern, escape="\\")
        )
        .distinct()
        .limit(limit)
    )
    result = await db.execute(q)
    return [KsicSuggestion(code=row[0], name=row[1] or "") for row in result.all()]


# ── 핵심: SI 매핑 ─────────────────────────────────────────
async def map_si_candidates(
    db: AsyncSession,
    ksic_codes: list[str],
    top_n: int = 5,
    max_companies_per_panel: int = 50,
    min_revenue: Decimal | None = None,
    require_investment_history: bool = False,
) -> SIMappingResponse:
    """KSIC 코드 기반 SI 후보 매핑 — 동종업계 + Value Chain.

    성능 최적화: 기업 테이블을 1회만 로딩하여 인메모리 KSIC 인덱스를 구축한 후,
    이후 모든 KSIC→기업 검색은 dict 참조로 수행 (DB 쿼리 ~33 → ~5).
    """
    # 대분류 알파벳 접두사 제거 (J58211 → 58211)
    ksic_codes = [c for c in (_strip_ksic_prefix(c) for c in ksic_codes) if c]

    # ── Step 0: 1회 전체 로딩 + 인메모리 인덱스 ─────────
    all_companies = await _load_filtered_companies(db, min_revenue, require_investment_history)
    ksic_index, sorted_keys = _build_ksic_index(all_companies)

    # ── Step 1: Direct Peers (동종업계) — dict 참조 ──────
    direct_companies = _lookup_by_ksic(ksic_index, sorted_keys, ksic_codes)

    # ── Step 2: Bridge (KSIC → IO 코드) ──────────────────
    q_bridge = (
        select(KsicIoMapping.io_code, KsicIoMapping.io_name).where(KsicIoMapping.ksic_code.in_(ksic_codes)).distinct()
    )
    bridge_result = await db.execute(q_bridge)
    target_io_map = {row[0]: row[1] or "" for row in bridge_result.all()}
    target_io_codes = list(target_io_map.keys())

    if not target_io_codes:
        return SIMappingResponse(
            target_ksic_codes=ksic_codes,
            target_io_codes=[],
            direct_peers=[SICompanyOut.model_validate(c) for c in direct_companies],
            backward_chain=[],
            forward_chain=[],
            all_candidates=_build_flat_candidates(direct_companies, [], [], ksic_codes),
        )

    # ── Step 3: Backward (공급자) — batch IN + 인덱스 ────
    backward_panels = await _get_value_chain(
        db,
        target_io_codes,
        direction="backward",
        top_n=top_n,
        ksic_index=ksic_index,
        sorted_keys=sorted_keys,
        max_companies=max_companies_per_panel,
    )

    # ── Step 4: Forward (수요자) — batch IN + 인덱스 ─────
    forward_panels = await _get_value_chain(
        db,
        target_io_codes,
        direction="forward",
        top_n=top_n,
        ksic_index=ksic_index,
        sorted_keys=sorted_keys,
        max_companies=max_companies_per_panel,
    )

    # ── Step 5: 결과 조합 ─────────────────────────────────
    direct_out = [SICompanyOut.model_validate(c) for c in direct_companies]
    all_candidates = _build_flat_candidates(direct_companies, backward_panels, forward_panels, ksic_codes)

    logger.info(
        "SI 매핑 완료: ksic_count=%d, 전체=%d, direct=%d, backward=%d, forward=%d",
        len(ksic_codes),
        len(all_candidates),
        len(direct_out),
        len(backward_panels),
        len(forward_panels),
    )

    return SIMappingResponse(
        target_ksic_codes=ksic_codes,
        target_io_codes=target_io_codes,
        direct_peers=direct_out,
        backward_chain=backward_panels,
        forward_chain=forward_panels,
        all_candidates=all_candidates,
    )


# ── 기업명 검색 ──────────────────────────────────────────
async def find_si_company_by_name(
    db: AsyncSession,
    company_name: str,
) -> SICompany | None:
    """기업명으로 SI 기업 검색 (정확 매칭)."""
    result = await db.execute(select(SICompany).where(SICompany.company_name == company_name).limit(1))
    return result.scalar_one_or_none()


# ── 일괄 BuyerCandidate 등록 ─────────────────────────────
async def bulk_add_to_buyers(
    db: AsyncSession,
    txn_id: uuid.UUID,
    si_company_ids: list[uuid.UUID],
    actor_email: str | None = None,
) -> BulkAddBuyersResponse:
    """SI 매핑 결과를 BuyerCandidate로 일괄 등록."""
    logger.info("BuyerCandidate 일괄 등록 시작: txn_id=%s, 요청=%d건", txn_id, len(si_company_ids))
    # SI 기업 조회
    q = select(SICompany).where(SICompany.id.in_(si_company_ids))
    result = await db.execute(q)
    si_companies = list(result.scalars().all())

    # 이미 등록된 기업명 확인 (중복 방지)
    existing_q = select(BuyerCandidate.company_name).where(BuyerCandidate.transaction_id == txn_id)
    existing_result = await db.execute(existing_q)
    existing_names = {row[0] for row in existing_result.all()}

    added_ids: list[uuid.UUID] = []
    skipped = 0

    # 1) 모든 BuyerCandidate를 생성하고 add (flush 없이)
    new_buyers: list[tuple[BuyerCandidate, SICompany]] = []
    for si in si_companies:
        if si.company_name in existing_names:
            skipped += 1
            continue
        buyer = BuyerCandidate(
            transaction_id=txn_id,
            company_name=si.company_name,
            buyer_type=BuyerType.STRATEGIC,
            status=BuyerCandidateStatus.IDENTIFIED,
            notes=f"SI 자동 매핑으로 추가됨 (KSIC: {si.ksic_codes})",
            extra_data={"si_company_id": str(si.id)},
        )
        db.add(buyer)
        new_buyers.append((buyer, si))
        existing_names.add(si.company_name)

    # 2) 한 번에 flush → ID 할당 (N회 → 1회)
    if new_buyers:
        await db.flush()

    # 3) 배치 audit 기록
    for buyer, si in new_buyers:
        await audit_service.record(
            db,
            entity_type="BuyerCandidate",
            entity_id=buyer.id,
            action=AuditAction.CREATE,
            actor_email=actor_email,
            new_value={"company_name": si.company_name, "source": "SI_MAPPING"},
        )
        added_ids.append(buyer.id)

    await db.commit()

    logger.info(
        "BuyerCandidate 일괄 등록 완료: txn_id=%s, 추가=%d건, 중복스킵=%d건",
        txn_id,
        len(added_ids),
        skipped,
    )
    return BulkAddBuyersResponse(
        added_count=len(added_ids),
        skipped_count=skipped,
        buyer_ids=added_ids,
    )


# ── 딥다이브 ───────────────────────────────────────────────
async def get_deep_dive(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> DeepDiveResponse:
    """SI 기업 딥다이브 — KIIS DART API를 통해 기업개황·재무·공시 조회.

    KIIS API 접근 불가 시에도 SI 기업 기본 정보는 반환 (dart_available=False).
    """

    # 1. SI 기업 조회
    result = await db.execute(select(SICompany).where(SICompany.id == company_id))
    si_company = result.scalar_one_or_none()
    if not si_company:
        raise CompanyNotFoundError(company_id)

    company_out = SICompanyOut.model_validate(si_company)

    # 2. DB 기업기본정보가 있으면 바로 CompanyOverview 구성 (DART 호출 생략)
    if si_company.corp_basic_synced_at is not None:
        overview = CompanyOverview(
            corp_code=si_company.corp_code or "",
            corp_name=si_company.company_name,
            ceo_nm=si_company.representative or "",
            est_dt=si_company.founded_date or "",
            induty_code=(si_company.ksic_codes or [""])[0] if si_company.ksic_codes else "",
            adres=si_company.address or "",
            hm_url=si_company.homepage or "",
        )
        base_response = DeepDiveResponse(
            company=company_out,
            overview=overview,
            dart_available=False,
        )
    else:
        base_response = DeepDiveResponse(company=company_out)

    # 3. KIIS DART API로 corp_code 매핑 시도 (서비스 토큰 사용)
    kiis_base = settings.KIIS_API_URL.rstrip("/")

    try:
        token = await make_service_token(audience="kiis-dart")
        headers = {"Authorization": f"Bearer {token}"}
        client = await _get_kiis_http_client()
        # 기업명으로 DART 기업 검색 → corp_code 획득
        search_resp = await client.get(
            f"{kiis_base}/dart/companies",
            headers=headers,
            params={"search": si_company.company_name, "size": 5},
        )
        if search_resp.status_code != 200:
            logger.warning(
                "KIIS DART 기업검색 실패: status=%d, company=%s",
                search_resp.status_code,
                si_company.company_name,
            )
            return base_response

        search_data = search_resp.json()
        items = search_data.get("items", [])
        if not items:
            logger.info("DART에서 '%s' 검색 결과 없음", si_company.company_name)
            return base_response

        # jurir_no 또는 기업명 정확 매칭으로 corp_code 특정
        corp_code = _match_corp_code(items, si_company)
        if not corp_code:
            logger.info("DART corp_code 매칭 실패: %s", si_company.company_name)
            return base_response

        # 3. 병렬 호출: 기업개황 + 재무제표(최근 3년) + 공시 + 제재
        overview_task = client.get(
            f"{kiis_base}/dart/companies/{corp_code}",
            headers=headers,
        )
        current_year = datetime.now(UTC).year
        financial_tasks = [
            client.get(
                f"{kiis_base}/dart/companies/{corp_code}/financials",
                headers=headers,
                params={"bsns_year": str(year), "reprt_code": "11011", "fs_div": "CFS"},
            )
            for year in range(current_year, current_year - 3, -1)
        ]
        disclosure_task = client.get(
            f"{kiis_base}/dart/disclosures",
            headers=headers,
            params={"corp_code": corp_code, "pblntf_ty": "B", "size": 10},
        )
        sanctions_task = client.get(
            f"{kiis_base}/dart/sanctions",
            headers=headers,
            params={"corp_code": corp_code},
        )

        responses = await asyncio.gather(
            overview_task,
            *financial_tasks,
            disclosure_task,
            sanctions_task,
            return_exceptions=True,
        )

        # 4. 결과 파싱
        overview = _parse_overview(responses[0])
        financials = _parse_financials(responses[1:4])
        disclosures = _parse_disclosures(responses[4])
        sanctions = _parse_sanctions(responses[5])

        return DeepDiveResponse(
            company=company_out,
            overview=overview,
            financials=financials,
            disclosures=disclosures,
            sanctions=sanctions,
            dart_available=True,
        )

    except (httpx.HTTPError, RuntimeError, json.JSONDecodeError) as exc:
        logger.warning("KIIS DART API 접근 실패: %s", exc)
        return base_response


def _match_corp_code(items: list[dict], si_company: SICompany) -> str | None:
    """DART 검색 결과에서 SI 기업과 매칭되는 corp_code 반환."""
    # 정확 이름 매칭 우선
    for item in items:
        if item.get("corp_name") == si_company.company_name:
            return item.get("corp_code")
    # 정확 매칭 실패 → None (오매칭 방지)
    logger.info("DART corp_code 정확 매칭 실패: %s (후보 %d건)", si_company.company_name, len(items))
    return None


def _parse_overview(resp: httpx.Response | BaseException) -> CompanyOverview | None:
    """기업개황 응답 파싱."""
    if isinstance(resp, BaseException) or resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except json.JSONDecodeError:
        logger.warning("기업개황 JSON 파싱 실패")
        return None
    return CompanyOverview(
        corp_code=data.get("corp_code", ""),
        corp_name=data.get("corp_name", ""),
        ceo_nm=data.get("ceo_nm", ""),
        est_dt=data.get("est_dt", ""),
        induty_code=data.get("induty_code", ""),
        adres=data.get("adres", ""),
        hm_url=data.get("hm_url", ""),
    )


def _parse_financials(
    responses: list[httpx.Response | BaseException],
) -> list[FinancialSummary]:
    """재무제표 응답 3개 파싱 → 연도별 요약."""
    summaries: list[FinancialSummary] = []
    for resp in responses:
        if isinstance(resp, BaseException) or resp.status_code != 200:
            continue
        try:
            data = resp.json()
        except json.JSONDecodeError:
            logger.warning("재무제표 JSON 파싱 실패")
            continue
        items = data.get("items", [])
        if not items:
            continue

        bsns_year = items[0].get("bsns_year", "")
        revenue = _extract_amount(items, "매출액")
        op_income = _extract_amount(items, "영업이익")
        net_income = _extract_amount(items, "당기순이익")
        total_assets = _extract_amount(items, "자산총계")

        summaries.append(
            FinancialSummary(
                bsns_year=bsns_year,
                revenue=revenue,
                operating_income=op_income,
                net_income=net_income,
                total_assets=total_assets,
            )
        )
    return summaries


def _extract_amount(items: list[dict], account_name: str) -> Decimal | None:
    """재무제표 항목에서 특정 계정의 당기금액 추출 (Decimal 정밀도 보존)."""
    for item in items:
        if account_name in item.get("account_nm", ""):
            raw = item.get("thstrm_amount", "").replace(",", "")
            if raw and raw != "-":
                try:
                    return Decimal(raw)
                except (InvalidOperation, ValueError):
                    logger.debug("금액 파싱 실패: account=%s, raw=%r", account_name, raw)
    return None


def _parse_disclosures(
    resp: httpx.Response | BaseException,
) -> list[DeepDiveDisclosure]:
    """공시 응답 파싱."""
    if isinstance(resp, BaseException) or resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except json.JSONDecodeError:
        logger.warning("공시 JSON 파싱 실패")
        return []
    return [
        DeepDiveDisclosure(
            rcept_dt=item.get("rcept_dt", ""),
            report_nm=item.get("report_nm", ""),
            rcept_no=item.get("rcept_no", ""),
        )
        for item in data.get("items", [])
    ]


def _parse_sanctions(
    resp: httpx.Response | BaseException,
) -> list[SanctionItem]:
    """제재 내역 응답 파싱.

    KIIS 응답 필드: sanctions_date, sanctions_type, sanctions_detail.
    DART raw 필드는 다를 수 있으므로 여러 변형을 fallback으로 처리.
    """
    if isinstance(resp, BaseException) or resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except json.JSONDecodeError:
        logger.warning("제재 JSON 파싱 실패")
        return []
    return [
        SanctionItem(
            date=item.get("sanctions_date", item.get("sanction_date", item.get("date", ""))),
            type=item.get("sanctions_type", item.get("sanction_type", item.get("type", ""))),
            content=item.get("sanctions_detail", item.get("sanction_content", item.get("content", ""))),
        )
        for item in data.get("items", None) or data.get("list", [])
    ]


# ── 내부 헬퍼 ─────────────────────────────────────────────
_MAX_COMPANIES_FOR_MAPPING: int = 5_000


async def _load_filtered_companies(
    db: AsyncSession,
    min_revenue: Decimal | None,
    require_investment_history: bool,
) -> list[SICompany]:
    """조건 필터를 적용하여 SI 기업을 1회만 로딩 (상한: 5,000건).

    메타데이터 컬럼(jurir_no, fina_base_date 등)은 defer로 제외하여
    전송 데이터량을 줄인다.
    """

    q = select(SICompany).options(
        defer(SICompany.jurir_no),
        defer(SICompany.corp_code),
        defer(SICompany.fina_base_date),
        defer(SICompany.fina_report_code),
        defer(SICompany.fina_report_name),
        defer(SICompany.fina_stat_synced_at),
        defer(SICompany.corp_basic_synced_at),
        defer(SICompany.corp_basic_base_date),
    )
    if min_revenue is not None:
        q = q.where(SICompany.revenue >= min_revenue)
    if require_investment_history:
        q = q.where(SICompany.has_investment_history.is_(True))
    q = q.limit(_MAX_COMPANIES_FOR_MAPPING)
    result = await db.execute(q)
    return list(result.scalars().all())


def _build_ksic_index(
    companies: list[SICompany],
) -> tuple[dict[str, list[SICompany]], tuple[str, ...]]:
    """기업 목록으로부터 {KSIC코드: [기업,...]} 인메모리 인덱스 + 정렬 키 구축.

    방어 코드: ksic_codes가 str(이중 직렬화)인 경우 json.loads로 복원 시도.
    sorted_keys는 bisect 접두사 매칭에 사용되며, 1회만 정렬한다.
    """
    index: dict[str, list[SICompany]] = {}
    for c in companies:
        codes = c.ksic_codes
        if not codes:
            continue
        # 방어: 이중 직렬화로 str이 된 경우 복원
        if isinstance(codes, str):
            try:
                codes = json.loads(codes)
            except (json.JSONDecodeError, TypeError):
                logger.warning("ksic_codes JSON 파싱 실패: company_id=%s", c.id)
                continue
            if not isinstance(codes, list):
                logger.warning("ksic_codes가 list가 아님: company_id=%s", c.id)
                continue
        for code in codes:
            if isinstance(code, str) and code:
                normalized = _strip_ksic_prefix(code)
                index.setdefault(normalized, []).append(c)
    return index, tuple(sorted(index.keys()))


def _lookup_by_ksic(
    ksic_index: dict[str, list[SICompany]],
    sorted_keys: tuple[str, ...],
    ksic_codes: list[str],
) -> list[SICompany]:
    """인메모리 인덱스에서 KSIC 코드에 매칭되는 기업 조회 (중복 제거).

    매칭 전략 (우선순위 순):
    1. 정확 매칭: 인덱스에 코드가 있으면 바로 반환
    2. 접두사 매칭: 입력 코드가 인덱스 키의 접두사이면 매칭
       예) 입력 "24" → 인덱스 "24110", "24231" 등 모두 매칭
    3. 역접두사 매칭: 인덱스 키가 입력 코드의 접두사이면 매칭
       예) 입력 "24110123" → 인덱스 "24110" 매칭

    성능 최적화: 정렬된 키 + bisect로 접두사 매칭 O(K*N) → O(K*(logN+M)).
    """
    import bisect as _bisect

    seen: set[uuid.UUID] = set()
    matched: list[SICompany] = []

    for code in ksic_codes:
        # 1. 정확 매칭
        for c in ksic_index.get(code, []):
            if c.id not in seen:
                seen.add(c.id)
                matched.append(c)

        if len(code) < 3:
            continue

        # 2. 접두사 매칭: index_code가 code로 시작 (bisect로 범위 탐색)
        lo = _bisect.bisect_left(sorted_keys, code)
        for i in range(lo, len(sorted_keys)):
            k = sorted_keys[i]
            if not k.startswith(code):
                break
            if k == code:
                continue  # 이미 정확 매칭에서 처리
            for c in ksic_index[k]:
                if c.id not in seen:
                    seen.add(c.id)
                    matched.append(c)

        # 3. 역접두사 매칭: code가 index_code로 시작 (최소 3글자)
        for length in range(3, len(code)):
            prefix = code[:length]
            if prefix != code and prefix in ksic_index:
                for c in ksic_index[prefix]:
                    if c.id not in seen:
                        seen.add(c.id)
                        matched.append(c)

    return matched


async def _get_value_chain(
    db: AsyncSession,
    target_io_codes: list[str],
    direction: Literal["backward", "forward"],
    top_n: int,
    ksic_index: dict[str, list[SICompany]],
    sorted_keys: tuple[str, ...],
    max_companies: int = 50,
) -> list[ValueChainPanel]:
    """전방/후방 Value Chain IO 코드 상위 N개 + 기업 매핑.

    최적화: IO→KSIC 역변환을 batch IN 쿼리 1회로 수행하고,
    KSIC→기업 검색은 인메모리 인덱스를 참조 (DB 쿼리 0).
    """
    if direction == "backward":
        q = (
            select(
                IOTransaction.source_io_code,
                IOTransaction.source_io_name,
                func.sum(IOTransaction.transaction_value).label("total_value"),
            )
            .where(IOTransaction.target_io_code.in_(target_io_codes))
            .where(~IOTransaction.source_io_code.in_(target_io_codes))
            .group_by(IOTransaction.source_io_code, IOTransaction.source_io_name)
            .order_by(literal_column("total_value").desc())
            .limit(top_n)
        )
    else:
        q = (
            select(
                IOTransaction.target_io_code,
                IOTransaction.target_io_name,
                func.sum(IOTransaction.transaction_value).label("total_value"),
            )
            .where(IOTransaction.source_io_code.in_(target_io_codes))
            .where(~IOTransaction.target_io_code.in_(target_io_codes))
            .group_by(IOTransaction.target_io_code, IOTransaction.target_io_name)
            .order_by(literal_column("total_value").desc())
            .limit(top_n)
        )

    result = await db.execute(q)
    rows = result.all()

    if not rows:
        return []

    # batch IO→KSIC 역변환 (N+1 → 1 쿼리)
    chain_io_codes = [row[0] for row in rows]
    reverse_q = (
        select(KsicIoMapping.io_code, KsicIoMapping.ksic_code)
        .where(KsicIoMapping.io_code.in_(chain_io_codes))
        .distinct()
    )
    reverse_result = await db.execute(reverse_q)
    io_to_ksic: dict[str, list[str]] = {}
    for io_code, ksic_code in reverse_result.all():
        io_to_ksic.setdefault(io_code, []).append(ksic_code)

    # 패널 조립 (인덱스 참조, DB 쿼리 0) — 매출 내림차순 정렬 + 기업 수 제한
    panels = []
    for io_code, io_name, total_val in rows:
        related_ksic = io_to_ksic.get(io_code, [])
        # sorted()로 새 리스트 생성 — 인메모리 인덱스 원본 보호
        companies = sorted(
            _lookup_by_ksic(ksic_index, sorted_keys, related_ksic),
            key=lambda c: c.revenue if c.revenue is not None else -1,
            reverse=True,
        )[:max_companies]

        panels.append(
            ValueChainPanel(
                io_code=io_code,
                io_name=io_name or "",
                transaction_value=total_val if total_val else Decimal("0"),
                companies=[SICompanyOut.model_validate(c) for c in companies],
            )
        )

    return panels


def _build_flat_candidates(
    direct_companies: list[SICompany],
    backward_panels: list[ValueChainPanel],
    forward_panels: list[ValueChainPanel],
    ksic_codes: list[str],
) -> list[SICandidateOut]:
    """모든 결과를 플랫 리스트로 합치기 (중복 제거)."""
    seen_ids: set[uuid.UUID] = set()
    candidates: list[SICandidateOut] = []

    # Direct peers
    for c in direct_companies:
        if c.id not in seen_ids:
            seen_ids.add(c.id)
            candidates.append(
                SICandidateOut(
                    company=SICompanyOut.model_validate(c),
                    relation="DIRECT",
                )
            )

    # Backward
    for panel in backward_panels:
        for c in panel.companies:
            if c.id not in seen_ids:
                seen_ids.add(c.id)
                candidates.append(
                    SICandidateOut(
                        company=c,
                        relation="BACKWARD",
                        io_code=panel.io_code,
                        io_name=panel.io_name,
                        transaction_value=panel.transaction_value,
                    )
                )

    # Forward
    for panel in forward_panels:
        for c in panel.companies:
            if c.id not in seen_ids:
                seen_ids.add(c.id)
                candidates.append(
                    SICandidateOut(
                        company=c,
                        relation="FORWARD",
                        io_code=panel.io_code,
                        io_name=panel.io_name,
                        transaction_value=panel.transaction_value,
                    )
                )

    return candidates


# ══════════════════════════════════════════════════════════
# ValueChain (VC) 매핑 — 1,574 세부 업종 투입산출 계수표 기반
# ══════════════════════════════════════════════════════════


async def get_vc_data_stats(db: AsyncSession) -> VcDataStats:
    """ValueChain 데이터 시딩 상태 반환 (단일 DB 왕복)."""

    coeff_sub = select(func.count()).select_from(VcIndustryCoefficient).correlate(None).scalar_subquery()

    agg = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count(VcCompany.revenue).label("with_revenue"),
                coeff_sub.label("coeff_total"),
            ).select_from(VcCompany)
        )
    ).one()

    coeff_count = agg.coeff_total or 0
    return VcDataStats(
        vc_companies_count=agg.total,
        vc_coefficients_count=coeff_count,
        revenue_count=agg.with_revenue,
        is_seeded=agg.total > 0 and coeff_count > 0,
    )


async def search_vc_industries(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> list[VcIndustrySuggestion]:
    """업종명(1,574) 자동완성 — VcCompany.industry_name DISTINCT LIKE 검색."""

    if not query or len(query) < 1:
        return []

    escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"

    q = (
        select(
            VcCompany.industry_name,
            func.count().label("cnt"),
        )
        .where(VcCompany.industry_name.ilike(pattern, escape="\\"))
        .group_by(VcCompany.industry_name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = await db.execute(q)
    return [VcIndustrySuggestion(industry_name=row[0], company_count=row[1]) for row in result.all()]


async def map_vc_candidates(
    db: AsyncSession,
    target_industry_name: str,
    min_revenue: Decimal = Decimal("100"),
    top_n: int = 20,
) -> VcMappingResponse:
    """업종명 기반 Value Chain 매핑 — 1,574 세부 업종 수준.

    Args:
        db: DB 세션
        target_industry_name: 타겟 업종명 (1,574 중 하나)
        min_revenue: 최소 매출액 (억원, 기본 100억)
        top_n: 전방/후방/경쟁 각각의 최대 반환 건수

    Returns:
        전방(고객) / 후방(공급) / 경쟁(동종) 매핑 결과
    """

    _t0 = time.monotonic()

    # 1. 전방 (고객): source=타겟 → 계수 높은 target 업종 top_n개
    forward_q = (
        select(VcIndustryCoefficient.target_industry, VcIndustryCoefficient.coefficient)
        .where(
            VcIndustryCoefficient.source_industry == target_industry_name,
            VcIndustryCoefficient.target_industry != target_industry_name,
        )
        .order_by(VcIndustryCoefficient.coefficient.desc())
        .limit(top_n)
    )
    forward_rows = (await db.execute(forward_q)).all()

    # 2. 후방 (공급): target=타겟 → 계수 높은 source 업종 top_n개
    backward_q = (
        select(VcIndustryCoefficient.source_industry, VcIndustryCoefficient.coefficient)
        .where(
            VcIndustryCoefficient.target_industry == target_industry_name,
            VcIndustryCoefficient.source_industry != target_industry_name,
        )
        .order_by(VcIndustryCoefficient.coefficient.desc())
        .limit(top_n)
    )
    backward_rows = (await db.execute(backward_q)).all()

    # 3. 경쟁: 같은 세부 업종(1,574), 매출 min_revenue↑, 내림차순 top_n개
    competitor_q = (
        select(VcCompany)
        .where(
            VcCompany.industry_name == target_industry_name,
            VcCompany.revenue.isnot(None),
            VcCompany.revenue >= min_revenue,
        )
        .order_by(VcCompany.revenue.desc())
        .limit(top_n)
    )
    competitor_rows = (await db.execute(competitor_q)).scalars().all()

    competitors = [VcChainCompany.model_validate(c) for c in competitor_rows]

    # 4. 전방/후방 업종에 속한 기업 조회 (매출 min_revenue↑)
    related_industries: list[str] = []
    forward_industry_map: dict[str, Decimal] = {}
    backward_industry_map: dict[str, Decimal] = {}

    for industry, coeff in forward_rows:
        related_industries.append(industry)
        forward_industry_map[industry] = coeff

    for industry, coeff in backward_rows:
        related_industries.append(industry)
        backward_industry_map[industry] = coeff

    # 업종별 기업 조회 — batch IN 쿼리
    # 전방/후방이 같은 업종을 포함할 수 있으므로 중복 제거 후 limit 계산
    industry_companies: dict[str, list[VcChainCompany]] = {}
    if related_industries:
        unique_related = list(dict.fromkeys(related_industries))
        companies_q = (
            select(VcCompany)
            .where(
                VcCompany.industry_name.in_(unique_related),
                VcCompany.revenue.isnot(None),
                VcCompany.revenue >= min_revenue,
            )
            .order_by(VcCompany.revenue.desc())
            .limit(top_n * len(unique_related))
        )
        company_rows = (await db.execute(companies_q)).scalars().all()

        # 업종별 그룹핑 + 기업 수 제한
        for c in company_rows:
            if c.industry_name not in industry_companies:
                industry_companies[c.industry_name] = []
            if len(industry_companies[c.industry_name]) < top_n:
                industry_companies[c.industry_name].append(VcChainCompany.model_validate(c))

    # 5. 패널 조립
    forward_chains = [
        VcChainPanel(
            industry_name=industry,
            coefficient=coeff,
            companies=industry_companies.get(industry, []),
        )
        for industry, coeff in forward_rows
    ]

    backward_chains = [
        VcChainPanel(
            industry_name=industry,
            coefficient=coeff,
            companies=industry_companies.get(industry, []),
        )
        for industry, coeff in backward_rows
    ]

    elapsed = time.monotonic() - _t0
    logger.info(
        "VC 매핑 완료: target=%s, forward=%d, backward=%d, competitors=%d, elapsed=%.2fs",
        target_industry_name,
        len(forward_chains),
        len(backward_chains),
        len(competitors),
        elapsed,
    )

    return VcMappingResponse(
        target_industry=target_industry_name,
        forward_chains=forward_chains,
        backward_chains=backward_chains,
        competitors=competitors,
        total_forward=len(forward_chains),
        total_backward=len(backward_chains),
        total_competitors=len(competitors),
    )


# ══════════════════════════════════════════════════════════
# 등록번호 기반 VC 매핑 — 법인등록번호/사업자등록번호 → 업종 → VC 매핑
# ══════════════════════════════════════════════════════════

_REG_NO_STRIP_RE = re.compile(r"[\s\-]")


def _normalize_reg_no(value: str) -> str:
    """등록번호에서 하이픈·공백 제거 후 반환."""
    return _REG_NO_STRIP_RE.sub("", value)


async def find_vc_company_by_registration(
    db: AsyncSession,
    corp_reg_no: str | None = None,
    biz_reg_no: str | None = None,
) -> VcCompany | None:
    """법인등록번호 또는 사업자등록번호로 VcCompany 조회.

    corp_reg_no 우선, 없으면 biz_reg_no로 fallback.
    등록번호 포맷(하이픈 유무)을 정규화하여 검색.
    """
    if corp_reg_no:
        normalized = _normalize_reg_no(corp_reg_no)
        result = await db.execute(
            select(VcCompany).where(func.replace(VcCompany.corp_reg_no, "-", "") == normalized).limit(1)
        )
        company = result.scalar_one_or_none()
        if company is not None:
            return company

    if biz_reg_no:
        normalized = _normalize_reg_no(biz_reg_no)
        result = await db.execute(
            select(VcCompany).where(func.replace(VcCompany.biz_reg_no, "-", "") == normalized).limit(1)
        )
        return result.scalar_one_or_none()

    return None


async def map_vc_by_registration(
    db: AsyncSession,
    corp_reg_no: str | None = None,
    biz_reg_no: str | None = None,
    min_revenue: Decimal = Decimal("100"),
    top_n: int = 20,
) -> VcMappingByRegResponse:
    """등록번호 → 기업 조회 → VC 매핑 실행.

    Returns:
        VcMappingByRegResponse: 조회된 기업 정보 + 전방/후방/경쟁 매핑 결과

    Raises:
        CompanyNotFoundError: 등록번호에 해당하는 기업이 없을 때
    """
    company = await find_vc_company_by_registration(db, corp_reg_no, biz_reg_no)
    if company is None:
        raise CompanyNotFoundError(
            f"등록번호에 해당하는 기업을 찾을 수 없습니다: 법인={corp_reg_no}, 사업자={biz_reg_no}"
        )

    mapping = await map_vc_candidates(
        db,
        target_industry_name=company.industry_name,
        min_revenue=min_revenue,
        top_n=top_n,
    )

    return VcMappingByRegResponse(
        company=VcCompanyLookupResult.model_validate(company),
        mapping=mapping,
    )


async def bulk_add_vc_to_buyers(
    db: AsyncSession,
    txn_id: uuid.UUID,
    vc_company_ids: list[int],
    actor_email: str | None = None,
) -> BulkAddBuyersResponse:
    """VC 매핑 결과를 BuyerCandidate로 일괄 등록."""
    logger.info(
        "VC BuyerCandidate 일괄 등록 시작: txn_id=%s, 요청=%d건",
        txn_id,
        len(vc_company_ids),
    )

    q = select(VcCompany).where(VcCompany.id.in_(vc_company_ids))
    result = await db.execute(q)
    vc_companies = list(result.scalars().all())

    existing_q = select(BuyerCandidate.company_name).where(BuyerCandidate.transaction_id == txn_id)
    existing_result = await db.execute(existing_q)
    existing_names = {row[0] for row in existing_result.all()}

    added_ids: list[uuid.UUID] = []
    skipped = 0

    new_buyers: list[tuple[BuyerCandidate, VcCompany]] = []
    for vc in vc_companies:
        if vc.company_name in existing_names:
            skipped += 1
            continue
        buyer = BuyerCandidate(
            transaction_id=txn_id,
            company_name=vc.company_name,
            buyer_type=BuyerType.STRATEGIC,
            status=BuyerCandidateStatus.IDENTIFIED,
            notes=f"VC 매핑으로 추가됨 (업종: {vc.industry_name})",
            extra_data={"vc_company_id": vc.id, "industry_name": vc.industry_name},
        )
        db.add(buyer)
        new_buyers.append((buyer, vc))
        existing_names.add(vc.company_name)

    if new_buyers:
        await db.flush()

    for buyer, vc in new_buyers:
        await audit_service.record(
            db,
            entity_type="BuyerCandidate",
            entity_id=buyer.id,
            action=AuditAction.CREATE,
            actor_email=actor_email,
            new_value={"company_name": vc.company_name, "source": "VC_MAPPING"},
        )
        added_ids.append(buyer.id)

    await db.commit()

    logger.info(
        "VC BuyerCandidate 일괄 등록 완료: txn_id=%s, 추가=%d건, 중복스킵=%d건",
        txn_id,
        len(added_ids),
        skipped,
    )
    return BulkAddBuyersResponse(
        added_count=len(added_ids),
        skipped_count=skipped,
        buyer_ids=added_ids,
    )
