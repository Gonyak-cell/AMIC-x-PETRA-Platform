from fastapi import APIRouter, Depends, Query

from app.schemas.dart import (
    CompanyInfo,
    CompanyListResponse,
    DisclosureListResponse,
    FinancialListResponse,
    SanctionListResponse,
)
from app.services.dart_service import DARTService

router = APIRouter()


def get_dart_service() -> DARTService:
    return DARTService()


@router.get("/companies", response_model=CompanyListResponse, summary="기업 목록 조회")
async def list_companies(
    search: str | None = Query(None, max_length=200, description="기업명 검색어"),
    stock_only: bool = Query(False, description="상장사만 조회"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: DARTService = Depends(get_dart_service),
):
    """DART에 등록된 기업 목록을 조회한다.

    고유번호 ZIP 파일을 파싱하여 기업 목록을 반환한다.
    검색어 또는 상장사 필터를 적용할 수 있다.
    """
    all_corps = await service.get_corp_codes()

    # 필터 적용
    filtered = all_corps
    if search:
        filtered = [c for c in filtered if search in c.corp_name]
    if stock_only:
        filtered = [c for c in filtered if c.stock_code]

    total = len(filtered)
    start = (page - 1) * size
    end = start + size
    items = filtered[start:end]

    await service.close()
    return CompanyListResponse(total=total, items=items)


@router.get("/companies/{corp_code}", response_model=CompanyInfo, summary="기업 개황 상세")
async def get_company(
    corp_code: str,
    service: DARTService = Depends(get_dart_service),
):
    """특정 기업의 개황 정보를 조회한다."""
    result = await service.get_company_info(corp_code)
    await service.close()
    return result


@router.get("/companies/{corp_code}/financials", response_model=FinancialListResponse, summary="재무제표 조회")
async def get_financials(
    corp_code: str,
    bsns_year: str = Query(..., max_length=4, description="사업연도 (YYYY)"),
    reprt_code: str = Query("11011", max_length=10, description="보고서 코드"),
    fs_div: str = Query("CFS", max_length=3, description="개별/연결 (CFS/OFS)"),
    service: DARTService = Depends(get_dart_service),
):
    """특정 기업의 재무제표를 조회한다."""
    items = await service.get_financial_statements(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )
    await service.close()
    return FinancialListResponse(items=items)


@router.get("/disclosures", response_model=DisclosureListResponse, summary="공시 검색")
async def search_disclosures(
    corp_code: str | None = Query(None, max_length=20, description="고유번호"),
    bgn_de: str | None = Query(None, max_length=8, description="시작일 (YYYYMMDD)"),
    end_de: str | None = Query(None, max_length=8, description="종료일 (YYYYMMDD)"),
    last_reprt_at: str | None = Query(None, max_length=1, description="최종보고서만 (Y/N)"),
    pblntf_ty: str | None = Query(None, max_length=10, description="공시유형"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: DARTService = Depends(get_dart_service),
):
    """공시를 검색한다. 날짜, 기업코드, 공시유형 등으로 필터링할 수 있다."""
    items, total_count, total_page = await service.search_disclosures(
        corp_code=corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
        last_reprt_at=last_reprt_at,
        pblntf_ty=pblntf_ty,
        page_no=page,
        page_count=size,
    )
    await service.close()
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
):
    """DART corpCode.xml에서 기업 목록을 가져와 DB에 동기화한다.

    enrich=True이면 상장사 대상 corp_cls, stock_name 등 상세정보도 갱신한다.
    """
    from app.tasks.company_sync import sync_companies_from_dart

    result = await sync_companies_from_dart(enrich_listed=enrich)
    return result


@router.get("/sanctions", response_model=SanctionListResponse, summary="제재 내역 조회")
async def get_sanctions(
    corp_code: str = Query(..., max_length=20, description="고유번호"),
    service: DARTService = Depends(get_dart_service),
):
    """특정 기업의 제재 내역을 조회한다."""
    items = await service.get_sanctions(corp_code)
    await service.close()
    return SanctionListResponse(items=items)
