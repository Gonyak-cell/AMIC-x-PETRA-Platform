from fastapi import APIRouter, Depends, Query

from app.schemas.fund import FundDetailResponse, FundListResponse, FundManagerListResponse, GPListResponse
from app.services.kofia_service import KOFIAService

router = APIRouter()


def get_kofia_service() -> KOFIAService:
    return KOFIAService()


@router.get("/gp", response_model=GPListResponse, summary="운용사(GP) 목록 조회")
async def list_gps(
    company_name: str | None = Query(None, description="운용사명 검색"),
    asset_class: str | None = Query(None, description="자산 클래스 필터 — 쉼표 구분 복수 선택"),
    sort_by: str = Query("total_aum", description="정렬 기준 (total_aum/fund_count/company_name)"),
    sort_order: str = Query("desc", description="정렬 방향 (asc/desc)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: KOFIAService = Depends(get_kofia_service),
):
    """운용사(GP) 목록을 집계하여 조회한다.

    KOFIA 펀드 데이터를 운용사별로 그룹화하여 펀드 수, AUM, 자산 클래스 등을 집계한다.
    """
    items, total = await service.get_gp_list(
        company_name=company_name,
        asset_class=asset_class,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        size=size,
    )
    await service.close()
    return GPListResponse(total=total, page=page, size=size, items=items)


@router.get("/funds", response_model=FundListResponse, summary="펀드 목록 조회")
async def list_funds(
    company_name: str | None = Query(None, description="운용사명 검색"),
    fund_name: str | None = Query(None, description="펀드명 검색"),
    fund_type: str | None = Query(None, description="펀드 유형 — 쉼표 구분 복수 선택 (blind,project)"),
    legal_type: str | None = Query(None, description="법률 유형 — 쉼표 구분 복수 선택 (professional_private,general_private,public)"),
    asset_class: str | None = Query(None, description="자산 클래스 — 쉼표 구분 복수 선택 (vc,pef,real_estate,infra,mezzanine,fund_of_funds)"),
    fund_status: str | None = Query(None, description="펀드 상태 — 쉼표 구분 복수 선택 (active,harvest,liquidated)"),
    vintage_from: int | None = Query(None, description="빈티지 연도 시작"),
    vintage_to: int | None = Query(None, description="빈티지 연도 종료"),
    amount_min: int | None = Query(None, ge=0, description="설정액 최소 (억원)"),
    amount_max: int | None = Query(None, ge=0, description="설정액 최대 (억원)"),
    sort_by: str | None = Query(None, description="정렬 기준 (total_amount/vintage_year/fund_name/company_name)"),
    sort_order: str = Query("desc", description="정렬 방향 (asc/desc)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: KOFIAService = Depends(get_kofia_service),
):
    """KOFIA 펀드 목록을 조회한다.

    운용사명, 펀드명, 펀드 유형, 법률 유형, 자산 클래스, 펀드 상태로 필터링할 수 있다.
    빈티지 연도 범위, 설정액 범위로 필터링할 수 있다.
    복수 선택 필터는 쉼표로 구분하여 전달한다 (OR 로직).
    회수 집중 구간(7~10년차) 펀드는 is_maturity_alert=true로 표시된다.
    """
    # 쉼표 구분 문자열을 리스트로 변환
    def _csv(val: str | None) -> list[str] | None:
        if not val:
            return None
        items = [v.strip() for v in val.split(",") if v.strip()]
        return items or None

    items, total = await service.search_funds(
        company_name=company_name,
        fund_name=fund_name,
        fund_types=_csv(fund_type),
        legal_types=_csv(legal_type),
        asset_classes=_csv(asset_class),
        fund_statuses=_csv(fund_status),
        vintage_from=vintage_from,
        vintage_to=vintage_to,
        amount_min=amount_min,
        amount_max=amount_max,
        sort_by=sort_by,
        sort_order=sort_order,
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
