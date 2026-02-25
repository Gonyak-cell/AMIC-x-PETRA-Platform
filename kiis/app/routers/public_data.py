from fastapi import APIRouter, Depends, Query

from app.schemas.public_data import GPRegistryItem, GPRegistryListResponse
from app.services.public_data_service import PublicDataService

router = APIRouter()


def get_public_data_service() -> PublicDataService:
    return PublicDataService()


@router.get("/gp", response_model=GPRegistryListResponse, summary="등록 자산운용사 목록 조회")
async def list_registered_gps(
    company_name: str | None = Query(None, description="운용사명 검색 (부분 일치)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    service: PublicDataService = Depends(get_public_data_service),
):
    """공공데이터포털 금융통계 기반 등록 자산운용사 목록을 조회한다.

    금융통계자산운용사정보 + 금융회사기본정보 API를 조합하여
    AUM, 펀드수, 재무현황, 설립일, 주소 등 통합 정보를 제공한다.
    KOFIA DIS에 미포함된 기관전용 사모펀드 운용사도 포함된다.
    """
    items, total = await service.search_gp_registry(
        company_name=company_name,
        page=page,
        size=size,
    )
    await service.close()
    return GPRegistryListResponse(total=total, page=page, size=size, items=items)


@router.get("/gp/{company_name}", response_model=GPRegistryItem | None, summary="운용사 상세 조회")
async def get_registered_gp(
    company_name: str,
    service: PublicDataService = Depends(get_public_data_service),
):
    """특정 운용사의 등록 정보를 조회한다."""
    result = await service.get_gp_by_name(company_name)
    await service.close()
    return result
