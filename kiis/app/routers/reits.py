from fastapi import APIRouter, Depends, Query

from app.schemas.reits import REITsAssetListResponse, REITsDetailResponse, REITsListResponse
from app.services.reits_service import REITsService

router = APIRouter()


def get_reits_service() -> REITsService:
    return REITsService()


@router.get("/", response_model=REITsListResponse, summary="리츠 목록 조회")
async def list_reits(
    reits_type: str | None = Query(None, description="리츠 유형 (self_managed/entrusted)"),
    status: str | None = Query(None, description="상태 (authorized/operating/dissolved)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: REITsService = Depends(get_reits_service),
):
    """리츠 목록을 조회한다.

    리츠 유형(자기관리/위탁관리), 상태(인가/영업/해산)로 필터링할 수 있다.
    부동산 자산 비율 70% 미달 리츠는 has_asset_ratio_warning=true로 표시된다.
    """
    items, total = await service.search_reits(
        reits_type=reits_type,
        status=status,
        page=page,
        size=size,
    )
    await service.close()
    return REITsListResponse(total=total, page=page, size=size, items=items)


@router.get("/{reits_code}", response_model=REITsDetailResponse, summary="리츠 상세 정보")
async def get_reits(
    reits_code: str,
    service: REITsService = Depends(get_reits_service),
):
    """특정 리츠의 상세 정보를 조회한다. 보유 자산 목록을 포함한다."""
    result = await service.get_reits_detail(reits_code)
    await service.close()
    return result


@router.get("/{reits_code}/assets", response_model=REITsAssetListResponse, summary="리츠 자산 내역")
async def list_reits_assets(
    reits_code: str,
    service: REITsService = Depends(get_reits_service),
):
    """특정 리츠의 보유 자산 내역을 조회한다."""
    assets = await service.get_reits_assets(reits_code)
    await service.close()
    return REITsAssetListResponse(total=len(assets), items=assets)
