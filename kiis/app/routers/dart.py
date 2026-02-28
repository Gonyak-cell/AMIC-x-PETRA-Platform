import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DARTAPIError, ExternalAPIError
from app.core.security import get_current_active_user, require_role
from app.models.company import Company
from app.schemas.corp_basic import CorpBasicInfoResponse
from app.schemas.dart import (
    CompanyInfo,
    CompanyListResponse,
    DisclosureListResponse,
    ElestockListResponse,
    ElestockSyncResponse,
    FinancialListResponse,
    FinancialStatementItem,
    HoldingSyncResponse,
    MajorHoldingListResponse,
    SanctionListResponse,
)
from app.schemas.fina_stat import FinaStatItem, SummaryFinancialResponse
from app.services.corp_basic_service import CorpBasicService
from app.services.dart_service import DARTService
from app.services.fina_stat_service import FinaStatService

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_dart_service() -> AsyncGenerator[DARTService, None]:
    service = DARTService()
    try:
        yield service
    finally:
        try:
            await service.close()
        except Exception:
            logger.warning("DARTService HTTP 클라이언트 종료 실패", exc_info=True)


# ── 헬퍼 ──


def _normalize_fina_to_dart(
    items: list[FinaStatItem], sj_div: str, bsns_year: str, corp_code: str
) -> list[FinancialStatementItem]:
    """OpenAPI FinaStatItem → DART FinancialStatementItem 형식 변환."""
    result = []
    for idx, item in enumerate(items):
        result.append(
            FinancialStatementItem(
                rcept_no="",
                reprt_code="",
                bsns_year=bsns_year,
                corp_code=corp_code,
                sj_div=sj_div,
                sj_nm="재무상태표" if sj_div == "BS" else "손익계산서",
                account_id=item.acit_id,
                account_nm=item.acit_nm,
                account_detail="",
                thstrm_nm=f"{bsns_year}년",
                thstrm_amount=item.crtm_acit_amt,
                frmtrm_nm=f"{int(bsns_year) - 1}년" if bsns_year.isdigit() else "",
                frmtrm_amount=item.pvtr_acit_amt,
                bfefrmtrm_nm=f"{int(bsns_year) - 2}년" if bsns_year.isdigit() else "",
                bfefrmtrm_amount=item.bpvtr_acit_amt,
                ord=str(idx + 1),
            )
        )
    return result


async def _get_jurir_no(db: AsyncSession, corp_code: str) -> str | None:
    """Company 테이블에서 법인등록번호(jurir_no)를 조회."""
    result = await db.execute(select(Company.jurir_no).where(Company.corp_code == corp_code))
    return result.scalar_one_or_none() or None


# ── 기업 목록/상세 ──


@router.get("/companies", response_model=CompanyListResponse, summary="기업 목록 조회")
async def list_companies(
    search: str | None = Query(None, max_length=200, description="기업명 검색어"),
    stock_only: bool = Query(False, description="상장사만 조회"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: DARTService = Depends(get_dart_service),
    _user=Depends(get_current_active_user),
):
    """DART에 등록된 기업 목록을 조회한다."""
    all_corps = await service.get_corp_codes()

    filtered = all_corps
    if search:
        filtered = [c for c in filtered if search in c.corp_name]
    if stock_only:
        filtered = [c for c in filtered if c.stock_code]

    total = len(filtered)
    start = (page - 1) * size
    end = start + size
    items = filtered[start:end]

    return CompanyListResponse(total=total, items=items)


@router.get("/companies/{corp_code}", response_model=CompanyInfo, summary="기업 개황 상세")
async def get_company(
    corp_code: str = Path(..., max_length=8, pattern=r"^\d{8}$"),
    service: DARTService = Depends(get_dart_service),
    _user=Depends(get_current_active_user),
):
    """특정 기업의 개황 정보를 조회한다."""
    result = await service.get_company_info(corp_code)
    return result


# ── 재무제표 (DART 우선 → OpenAPI 폴백) ──


@router.get(
    "/companies/{corp_code}/financials",
    response_model=FinancialListResponse,
    summary="재무제표 조회 (DART→OpenAPI 폴백)",
)
async def get_financials(
    corp_code: str = Path(..., max_length=8, pattern=r"^\d{8}$"),
    bsns_year: str = Query(..., max_length=4, description="사업연도 (YYYY)"),
    reprt_code: str = Query("11011", max_length=10, description="보고서 코드"),
    fs_div: str = Query("CFS", max_length=3, description="개별/연결 (CFS/OFS)"),
    dart_service: DARTService = Depends(get_dart_service),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
):
    """재무제표를 조회한다. DART API 우선, 실패 시 공공데이터 OpenAPI 폴백."""
    # 1) DART 시도
    try:
        items = await dart_service.get_financial_statements(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )
        if items:
            return FinancialListResponse(source="DART", items=items)
    except DARTAPIError as e:
        logger.info("DART 재무제표 실패 (%s): %s — OpenAPI 폴백", corp_code, e.message)
    except Exception as e:
        logger.warning("DART 재무제표 오류 (%s): %s", corp_code, e)

    # 2) OpenAPI 폴백 — jurir_no 조회
    jurir_no = await _get_jurir_no(db, corp_code)
    if not jurir_no:
        return FinancialListResponse(source="NONE", items=[])

    fina_service = FinaStatService()
    try:
        bs_items = await fina_service.get_balance_sheet(jurir_no, bsns_year)
        is_items = await fina_service.get_income_statement(jurir_no, bsns_year)
        normalized = _normalize_fina_to_dart(bs_items, "BS", bsns_year, corp_code)
        normalized += _normalize_fina_to_dart(is_items, "IS", bsns_year, corp_code)
        if normalized:
            return FinancialListResponse(source="DATA_GO_KR", items=normalized)
    except ExternalAPIError as e:
        logger.warning("OpenAPI 재무제표 실패 (%s): %s", corp_code, e.message)
    except Exception as e:
        logger.warning("OpenAPI 재무제표 오류 (%s): %s", corp_code, e)
    finally:
        await fina_service.close()

    return FinancialListResponse(source="NONE", items=[])


# ── 재무 요약 KPI ──


@router.get(
    "/companies/{corp_code}/financial-summary",
    response_model=SummaryFinancialResponse,
    summary="재무 요약 KPI",
)
async def get_financial_summary(
    corp_code: str = Path(..., max_length=8, pattern=r"^\d{8}$"),
    bsns_year: str = Query(..., max_length=4, description="사업연도 (YYYY)"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
):
    """매출/영업이익/순이익/총자산/부채비율 등 재무 요약 KPI를 조회한다."""
    jurir_no = await _get_jurir_no(db, corp_code)
    if not jurir_no:
        return SummaryFinancialResponse(source="NONE", biz_year=bsns_year)

    fina_service = FinaStatService()
    try:
        items = await fina_service.get_summary(jurir_no, bsns_year)
        # 연결재무제표 우선 선택
        target = None
        for item in items:
            if "Consolidated" in item.fncl_dcd or "연결" in item.fncl_dcd_nm:
                target = item
                break
        if not target and items:
            target = items[0]

        if target:
            return SummaryFinancialResponse(
                source="DATA_GO_KR",
                biz_year=bsns_year,
                sale_amt=target.sale_amt or None,
                bzop_pft=target.bzop_pft or None,
                crtm_npf=target.crtm_npf or None,
                tast_amt=target.tast_amt or None,
                tdbt_amt=target.tdbt_amt or None,
                tcpt_amt=target.tcpt_amt or None,
                cptl_amt=target.cptl_amt or None,
                debt_rto=target.debt_rto or None,
            )
    except ExternalAPIError as e:
        logger.warning("OpenAPI 요약재무 실패 (%s): %s", corp_code, e.message)
    except Exception as e:
        logger.warning("OpenAPI 요약재무 오류 (%s): %s", corp_code, e)
    finally:
        await fina_service.close()

    return SummaryFinancialResponse(source="NONE", biz_year=bsns_year)


# ── 기업 기본정보 (공공데이터포털) ──


@router.get(
    "/companies/{corp_code}/basic-info",
    response_model=CorpBasicInfoResponse,
    summary="기업 기본정보 (개요/업종/종업원 등)",
)
async def get_corp_basic_info(
    corp_code: str = Path(..., max_length=8, pattern=r"^\d{8}$"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
):
    """공공데이터포털 기업기본정보를 조회한다 (GetCorpBasicInfoService_V2)."""
    jurir_no = await _get_jurir_no(db, corp_code)
    if not jurir_no:
        return CorpBasicInfoResponse(outline=None)

    service = CorpBasicService()
    try:
        return await service.get_full_info(jurir_no)
    except ExternalAPIError as e:
        logger.warning("기업 기본정보 조회 실패 (%s): %s", corp_code, e.message)
        return CorpBasicInfoResponse(outline=None)
    except Exception as e:
        logger.warning("기업 기본정보 오류 (%s): %s", corp_code, e)
        return CorpBasicInfoResponse(outline=None)
    finally:
        await service.close()


# ── 공시 검색 ──


@router.get("/disclosures", response_model=DisclosureListResponse, summary="공시 검색")
async def search_disclosures(
    corp_code: str | None = Query(None, max_length=20, description="고유번호"),
    bgn_de: str | None = Query(None, max_length=8, pattern=r"^\d{8}$", description="시작일 (YYYYMMDD)"),
    end_de: str | None = Query(None, max_length=8, pattern=r"^\d{8}$", description="종료일 (YYYYMMDD)"),
    last_reprt_at: str | None = Query(None, max_length=1, description="최종보고서만 (Y/N)"),
    pblntf_ty: str | None = Query(None, max_length=10, description="공시유형"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: DARTService = Depends(get_dart_service),
    _user=Depends(get_current_active_user),
):
    """공시를 검색한다."""
    items, total_count, total_page = await service.search_disclosures(
        corp_code=corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
        last_reprt_at=last_reprt_at,
        pblntf_ty=pblntf_ty,
        page_no=page,
        page_count=size,
    )
    return DisclosureListResponse(
        page_no=page,
        page_count=size,
        total_count=total_count,
        total_page=total_page,
        items=items,
    )


@router.post("/sync-companies", summary="기업 목록 DB 동기화")
async def sync_companies(
    enrich: bool = Query(False, description="상장사 상세정보 enrichment 여부"),
    _user=Depends(require_role("admin")),
):
    """DART corpCode.xml에서 기업 목록을 가져와 DB에 동기화한다."""
    from app.tasks.company_sync import sync_companies_from_dart

    result = await sync_companies_from_dart(enrich_listed=enrich)
    return result


@router.get("/sanctions", response_model=SanctionListResponse, summary="제재 내역 조회")
async def get_sanctions(
    corp_code: str = Query(..., max_length=20, description="고유번호"),
    service: DARTService = Depends(get_dart_service),
    _user=Depends(get_current_active_user),
):
    """특정 기업의 제재 내역을 조회한다."""
    items = await service.get_sanctions(corp_code)
    return SanctionListResponse(items=items)


# ── 대량보유 ──


@router.get(
    "/major-holdings/{corp_code}",
    response_model=MajorHoldingListResponse,
    summary="대량보유상황보고서 조회",
)
async def get_major_holdings(
    corp_code: str = Path(..., max_length=8, pattern=r"^\d{8}$"),
    bgn_de: str | None = Query(None, max_length=8, pattern=r"^\d{8}$", description="시작일 (YYYYMMDD)"),
    end_de: str | None = Query(None, max_length=8, pattern=r"^\d{8}$", description="종료일 (YYYYMMDD)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: DARTService = Depends(get_dart_service),
    _user=Depends(get_current_active_user),
):
    """특정 기업의 대량보유상황보고서를 DART API에서 직접 조회한다."""
    items, total_count, total_page = await service.get_major_holdings(
        corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
        page_no=page,
        page_count=size,
    )
    return MajorHoldingListResponse(
        page_no=page,
        page_count=size,
        total_count=total_count,
        total_page=total_page,
        items=items,
    )


@router.post(
    "/holding-sync",
    response_model=HoldingSyncResponse,
    summary="대량보유 수동 동기화",
)
async def trigger_holding_sync(
    _user=Depends(get_current_active_user),
):
    """대량보유 수집 + 딜 신호 생성을 수동 실행한다."""
    from app.tasks.holding_sync import run_holding_sync

    result = await run_holding_sync(triggered_by=_user.email)
    return HoldingSyncResponse(**result)


# ── 임원소유보고 ──


@router.get(
    "/elestock/{corp_code}",
    response_model=ElestockListResponse,
    summary="임원·주요주주 소유보고 조회",
)
async def get_executive_holdings(
    corp_code: str = Path(..., max_length=8, pattern=r"^\d{8}$"),
    service: DARTService = Depends(get_dart_service),
    _user=Depends(get_current_active_user),
):
    """특정 기업의 임원·주요주주 소유보고를 DART API에서 직접 조회한다."""
    items = await service.get_executive_holdings(corp_code)
    return ElestockListResponse(items=items)


@router.post(
    "/elestock-sync",
    response_model=ElestockSyncResponse,
    summary="임원소유보고 수동 동기화",
)
async def trigger_elestock_sync(
    _user=Depends(get_current_active_user),
):
    """임원소유보고 수집 + 딜 신호 생성 + 원문 공시 연결을 수동 실행한다."""
    from app.tasks.elestock_sync import run_elestock_sync

    result = await run_elestock_sync(triggered_by=_user.email)
    return ElestockSyncResponse(**result)
