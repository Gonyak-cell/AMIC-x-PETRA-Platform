from fastapi import APIRouter, Depends, Query

from app.schemas.fund import FundDetailResponse, FundListResponse, FundManagerListResponse
from app.services.kofia_service import KOFIAService

router = APIRouter()


def get_kofia_service() -> KOFIAService:
    return KOFIAService()


@router.get("/funds", response_model=FundListResponse, summary="펀드 목록 조회")
async def list_funds(
    company_name: str | None = Query(None, description="운용사명 검색"),
    fund_type: str | None = Query(None, description="펀드 유형 (blind/project)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: KOFIAService = Depends(get_kofia_service),
):
    """KOFIA 펀드 목록을 조회한다.

    운용사명, 펀드 유형(블라인드/프로젝트)으로 필터링할 수 있다.
    회수 집중 구간(7~10년차) 펀드는 is_maturity_alert=true로 표시된다.
    """
    items, total = await service.search_funds(
        company_name=company_name,
        fund_type=fund_type,
        page=page,
        size=size,
    )
    await service.close()
    return FundListResponse(total=total, page=page, size=size, items=items)


@router.get("/funds/{fund_code}", response_model=FundDetailResponse, summary="펀드 상세 정보")
async def get_fund(
    fund_code: str,
    service: KOFIAService = Depends(get_kofia_service),
):
    """특정 펀드의 상세 정보를 조회한다. 운용 전문인력 목록을 포함한다."""
    result = await service.get_fund_detail(fund_code)
    await service.close()
    return result


@router.get("/managers", response_model=FundManagerListResponse, summary="운용 전문인력 목록")
async def list_managers(
    company_name: str | None = Query(None, description="운용사명 검색"),
    fund_code: str | None = Query(None, description="펀드 코드 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: KOFIAService = Depends(get_kofia_service),
):
    """운용 전문인력 목록을 조회한다. 운용사명 또는 펀드 코드로 필터링할 수 있다."""
    items, total = await service.get_fund_managers(
        company_name=company_name,
        fund_code=fund_code,
        page=page,
        size=size,
    )
    await service.close()
    return FundManagerListResponse(total=total, items=items)
