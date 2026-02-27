"""SI 매핑 서비스 — KSIC 기반 전략적 투자자 후보 자동 매핑."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import httpx
from fastapi import HTTPException
from jose import jwt as jose_jwt
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction, BuyerCandidateStatus, BuyerType
from app.models.io_transaction import IOTransaction
from app.models.ksic_io_mapping import KsicIoMapping
from app.models.si_company import SICompany
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
)
from app.services import audit_service

logger = logging.getLogger(__name__)


# ── 데이터 통계 ───────────────────────────────────────────
async def get_data_stats(db: AsyncSession) -> SIDataStats:
    """참조 테이블 시딩 상태 반환."""
    si_count = (await db.execute(select(func.count()).select_from(SICompany))).scalar() or 0
    mapping_count = (await db.execute(select(func.count()).select_from(KsicIoMapping))).scalar() or 0
    io_count = (await db.execute(select(func.count()).select_from(IOTransaction))).scalar() or 0
    rev_count = (await db.execute(select(func.count()).where(SICompany.revenue.isnot(None)))).scalar() or 0
    return SIDataStats(
        si_companies_count=si_count,
        ksic_io_mappings_count=mapping_count,
        io_transactions_count=io_count,
        revenue_count=rev_count,
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
        .where(KsicIoMapping.ksic_code.ilike(pattern) | KsicIoMapping.ksic_name.ilike(pattern))
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
    min_revenue: float | None = None,
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
    ksic_index = _build_ksic_index(all_companies)

    # ── Step 1: Direct Peers (동종업계) — dict 참조 ──────
    direct_companies = _lookup_by_ksic(ksic_index, ksic_codes)

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
        max_companies=max_companies_per_panel,
    )

    # ── Step 4: Forward (수요자) — batch IN + 인덱스 ─────
    forward_panels = await _get_value_chain(
        db,
        target_io_codes,
        direction="forward",
        top_n=top_n,
        ksic_index=ksic_index,
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


# ── 일괄 BuyerCandidate 등록 ─────────────────────────────
async def bulk_add_to_buyers(
    db: AsyncSession,
    txn_id: uuid.UUID,
    si_company_ids: list[uuid.UUID],
    actor_email: str | None = None,
) -> BulkAddBuyersResponse:
    """SI 매핑 결과를 BuyerCandidate로 일괄 등록."""
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

    return BulkAddBuyersResponse(
        added_count=len(added_ids),
        skipped_count=skipped,
        buyer_ids=added_ids,
    )


# ── 서비스 간 통신 토큰 ──────────────────────────────────
def _make_service_token() -> str:
    """내부 서비스 간 통신용 단기 JWT 토큰 생성 (30초 TTL)."""
    from app.core.config import settings
    from app.core.security import get_jwt_secret

    payload = {
        "sub": "deal-mgmt-service",
        "iss": "deal-mgmt",
        "exp": datetime.now(UTC) + timedelta(seconds=30),
        "scope": "internal",
    }
    return jose_jwt.encode(payload, get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)


# ── 딥다이브 ───────────────────────────────────────────────
async def get_deep_dive(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> DeepDiveResponse:
    """SI 기업 딥다이브 — KIIS DART API를 통해 기업개황·재무·공시 조회.

    KIIS API 접근 불가 시에도 SI 기업 기본 정보는 반환 (dart_available=False).
    """
    from app.core.config import settings

    # 1. SI 기업 조회
    result = await db.execute(select(SICompany).where(SICompany.id == company_id))
    si_company = result.scalar_one_or_none()
    if not si_company:
        raise HTTPException(status_code=404, detail="SI 기업을 찾을 수 없습니다")

    company_out = SICompanyOut.model_validate(si_company)
    base_response = DeepDiveResponse(company=company_out)

    # 2. KIIS DART API로 corp_code 매핑 시도 (서비스 토큰 사용)
    kiis_base = settings.KIIS_API_URL.rstrip("/")
    token = _make_service_token()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            # 기업명으로 DART 기업 검색 → corp_code 획득
            search_resp = await client.get(
                f"{kiis_base}/dart/companies",
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
            overview_task = client.get(f"{kiis_base}/dart/companies/{corp_code}")
            financial_tasks = [
                client.get(
                    f"{kiis_base}/dart/companies/{corp_code}/financials",
                    params={"bsns_year": str(year), "reprt_code": "11011", "fs_div": "CFS"},
                )
                for year in range(2025, 2022, -1)
            ]
            disclosure_task = client.get(
                f"{kiis_base}/dart/disclosures",
                params={"corp_code": corp_code, "pblntf_ty": "B", "size": 10},
            )
            sanctions_task = client.get(
                f"{kiis_base}/dart/sanctions",
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

    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.warning("KIIS DART API 연결 실패: %s", exc)
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
    data = resp.json()
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
        data = resp.json()
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


def _extract_amount(items: list[dict], account_name: str) -> float | None:
    """재무제표 항목에서 특정 계정의 당기금액 추출."""
    for item in items:
        if account_name in item.get("account_nm", ""):
            raw = item.get("thstrm_amount", "").replace(",", "")
            if raw and raw != "-":
                try:
                    return float(raw)
                except ValueError:
                    logger.debug("금액 파싱 실패: account=%s, raw=%r", account_name, raw)
    return None


def _parse_disclosures(
    resp: httpx.Response | BaseException,
) -> list[DeepDiveDisclosure]:
    """공시 응답 파싱."""
    if isinstance(resp, BaseException) or resp.status_code != 200:
        return []
    data = resp.json()
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
    data = resp.json()
    return [
        SanctionItem(
            date=item.get("sanctions_date", item.get("sanction_date", item.get("date", ""))),
            type=item.get("sanctions_type", item.get("sanction_type", item.get("type", ""))),
            content=item.get("sanctions_detail", item.get("sanction_content", item.get("content", ""))),
        )
        for item in data.get("items", None) or data.get("list", [])
    ]


# ── 내부 헬퍼 ─────────────────────────────────────────────
async def _load_filtered_companies(
    db: AsyncSession,
    min_revenue: float | None,
    require_investment_history: bool,
) -> list[SICompany]:
    """조건 필터를 적용하여 SI 기업을 1회만 로딩."""
    q = select(SICompany)
    if min_revenue is not None:
        q = q.where(SICompany.revenue >= min_revenue)
    if require_investment_history:
        q = q.where(SICompany.has_investment_history.is_(True))
    result = await db.execute(q)
    return list(result.scalars().all())


def _build_ksic_index(companies: list[SICompany]) -> dict[str, list[SICompany]]:
    """기업 목록으로부터 {KSIC코드: [기업,...]} 인메모리 인덱스 구축.

    방어 코드: ksic_codes가 str(이중 직렬화)인 경우 json.loads로 복원 시도.
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
                index.setdefault(code, []).append(c)
    return index


def _lookup_by_ksic(
    ksic_index: dict[str, list[SICompany]],
    ksic_codes: list[str],
) -> list[SICompany]:
    """인메모리 인덱스에서 KSIC 코드에 매칭되는 기업 조회 (중복 제거).

    매칭 전략 (우선순위 순):
    1. 정확 매칭: 인덱스에 코드가 있으면 바로 반환
    2. 접두사 매칭: 입력 코드가 인덱스 키의 접두사이면 매칭
       예) 입력 "24" → 인덱스 "24110", "24231" 등 모두 매칭
    3. 역접두사 매칭: 인덱스 키가 입력 코드의 접두사이면 매칭
       예) 입력 "24110123" → 인덱스 "24110" 매칭

    NOTE: seed_company_data.py의 load_master_dict()에서 적재 시 접두사 정규화를
    수행하지만, 모든 코드가 정규화되지 않을 수 있어 조회 시점에서도 접두사 매칭을
    수행하는 2중 안전망 설계.
    """
    seen: set[uuid.UUID] = set()
    matched: list[SICompany] = []

    for code in ksic_codes:
        # 1. 정확 매칭
        for c in ksic_index.get(code, []):
            if c.id not in seen:
                seen.add(c.id)
                matched.append(c)

        # 2 & 3. 접두사/역접두사 매칭 (코드 길이 2+ 제한)
        if len(code) >= 2:
            for index_code, companies in ksic_index.items():
                if index_code == code:
                    continue  # 이미 정확 매칭에서 처리
                if index_code.startswith(code) or code.startswith(index_code):
                    for c in companies:
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
            .order_by(text("total_value DESC"))
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
            .order_by(text("total_value DESC"))
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
            _lookup_by_ksic(ksic_index, related_ksic),
            key=lambda c: c.revenue if c.revenue is not None else -1,
            reverse=True,
        )[:max_companies]

        panels.append(
            ValueChainPanel(
                io_code=io_code,
                io_name=io_name or "",
                transaction_value=float(total_val) if total_val else 0.0,
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
