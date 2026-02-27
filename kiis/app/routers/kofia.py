import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.company import Company
from app.schemas.fund import (
    FundDetailResponse,
    FundListResponse,
    FundManagerListResponse,
    GPListResponse,
)
from app.services.kofia_service import KOFIAService
from app.services.pef_registry_service import PEFRegistryService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_kofia_service() -> KOFIAService:
    return KOFIAService()


async def _enrich_gp_logos(
    db: AsyncSession,
    items: list,
) -> None:
    """GP 목록 아이템에 logo_url을 매핑한다 (in-place)."""
    names = [item.company_name for item in items if item.company_name]
    if not names:
        return
    stmt = select(Company.corp_name, Company.logo_url).where(
        Company.corp_name.in_(names),
        Company.logo_url.isnot(None),
    )
    result = await db.execute(stmt)
    logo_map: dict[str, str] = {row.corp_name: row.logo_url for row in result}
    for item in items:
        item.logo_url = logo_map.get(item.company_name)


@router.get("/gp", response_model=GPListResponse, summary="운용사(GP) 목록 조회")
async def list_gps(
    company_name: str | None = Query(None, description="운용사명 검색"),
    asset_class: str | None = Query(None, description="자산 클래스 필터 — 쉼표 구분 복수 선택"),
    data_source: str | None = Query(None, description="데이터 소스 (kofia/pef_registry, 미지정=전체)"),
    sort_by: str = Query("total_aum", description="정렬 기준 (total_aum/fund_count/company_name)"),
    sort_order: str = Query("desc", description="정렬 방향 (asc/desc)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: KOFIAService = Depends(get_kofia_service),
    db: AsyncSession = Depends(get_db),
):
    """운용사(GP) 목록을 집계하여 조회한다.

    data_source 파라미터로 KOFIA / PEF 등록부 / 전체를 선택할 수 있다.
    """
    if data_source == "pef_registry":
        pef_svc = PEFRegistryService(db)
        items, total, ref_date = await pef_svc.get_gp_list(
            company_name=company_name,
            asset_class=asset_class,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size,
        )
        await _enrich_gp_logos(db, items)
        return GPListResponse(
            total=total,
            page=page,
            size=size,
            items=items,
            reference_date=ref_date,
        )

    # KOFIA (기본)
    items, total = await service.get_gp_list(
        company_name=company_name,
        asset_class=asset_class,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        size=size,
    )
    await service.close()

    # KOFIA 기준시점 가져오기
    ref_date = await service.get_reference_date()

    # DB에서 로고 URL 매핑
    await _enrich_gp_logos(db, items)

    return GPListResponse(
        total=total,
        page=page,
        size=size,
        items=items,
        reference_date=ref_date,
    )


@router.get("/funds", response_model=FundListResponse, summary="펀드 목록 조회")
async def list_funds(
    company_name: str | None = Query(None, description="운용사명 검색"),
    fund_name: str | None = Query(None, description="펀드명 검색"),
    fund_type: str | None = Query(None, description="펀드 유형 — 쉼표 구분 복수 선택 (blind,project)"),
    legal_type: str | None = Query(
        None, description="법률 유형 — 쉼표 구분 복수 선택 (professional_private,general_private,public)"
    ),
    asset_class: str | None = Query(
        None, description="자산 클래스 — 쉼표 구분 복수 선택 (vc,pef,real_estate,infra,mezzanine,fund_of_funds)"
    ),
    fund_status: str | None = Query(None, description="펀드 상태 — 쉼표 구분 복수 선택 (active,harvest,liquidated)"),
    data_source: str | None = Query(None, description="데이터 소스 (kofia/pef_registry, 미지정=전체)"),
    vintage_from: int | None = Query(None, description="빈티지 연도 시작"),
    vintage_to: int | None = Query(None, description="빈티지 연도 종료"),
    amount_min: int | None = Query(None, ge=0, description="설정액 최소 (억원)"),
    amount_max: int | None = Query(None, ge=0, description="설정액 최대 (억원)"),
    sort_by: str | None = Query(None, description="정렬 기준 (total_amount/vintage_year/fund_name/company_name)"),
    sort_order: str = Query("desc", description="정렬 방향 (asc/desc)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: KOFIAService = Depends(get_kofia_service),
    db: AsyncSession = Depends(get_db),
):
    """펀드 목록을 조회한다.

    data_source로 KOFIA / PEF 등록부 / 전체를 선택할 수 있다.
    복수 선택 필터는 쉼표로 구분하여 전달한다 (OR 로직).
    """

    def _csv(val: str | None) -> list[str] | None:
        if not val:
            return None
        items = [v.strip() for v in val.split(",") if v.strip()]
        return items or None

    filter_kwargs = dict(
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

    if data_source == "pef_registry":
        pef_svc = PEFRegistryService(db)
        items, total, ref_date = await pef_svc.search_funds(**filter_kwargs)
        return FundListResponse(
            total=total,
            page=page,
            size=size,
            items=items,
            reference_date=ref_date,
        )

    if data_source == "kofia" or data_source is None:
        # KOFIA 데이터 (기본)
        items, total = await service.search_funds(**filter_kwargs)
        await service.close()
        ref_date = await service.get_reference_date()
        return FundListResponse(
            total=total,
            page=page,
            size=size,
            items=items,
            reference_date=ref_date,
        )

    # 알 수 없는 data_source
    raise HTTPException(status_code=400, detail=f"Unknown data_source: {data_source}")


@router.get("/funds/{fund_code}", response_model=FundDetailResponse, summary="펀드 상세 정보")
async def get_fund(
    fund_code: str,
    service: KOFIAService = Depends(get_kofia_service),
    db: AsyncSession = Depends(get_db),
):
    """특정 펀드의 상세 정보를 조회한다.

    PEF-로 시작하는 코드는 PEF 등록부에서, 그 외는 KOFIA에서 조회한다.
    """
    if fund_code.startswith("PEF-"):
        pef_svc = PEFRegistryService(db)
        result = await pef_svc.get_fund_detail(fund_code)
        if result is None:
            raise HTTPException(status_code=404, detail=f"PEF fund not found: {fund_code}")
        return result

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
