"""전자공시 Deep Link API 라우터"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_jwt_claims
from app.schemas.disclosure import (
    DeepLinkResponse,
    DisclosureListItem,
    DisclosureListResponse,
    DisclosureSyncResponse,
)
from app.services.disclosure_service import DisclosureService

router = APIRouter(dependencies=[Depends(get_jwt_claims)])


def get_disclosure_service() -> DisclosureService:
    """공시 서비스 팩토리"""
    return DisclosureService()


@router.get(
    "/{corp_code}",
    response_model=DisclosureListResponse,
    summary="공시 목록 조회",
)
async def get_disclosures(
    corp_code: str,
    disclosure_type: str | None = Query(None, description="공시 유형 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
    service: DisclosureService = Depends(get_disclosure_service),
):
    """특정 기업의 공시 목록을 페이지네이션으로 조회한다."""
    disclosures, total = await service.get_disclosures(
        db=db,
        corp_code=corp_code,
        disclosure_type=disclosure_type,
        page=page,
        size=size,
    )

    items = [
        DisclosureListItem(
            id=d.id,
            report_nm=d.report_nm,
            rcept_no=d.rcept_no,
            rcept_dt=d.rcept_dt,
            disclosure_type=d.disclosure_type,
            dart_viewer_url=d.dart_viewer_url,
            kofia_url=d.kofia_url,
            source=d.source,
        )
        for d in disclosures
    ]

    return DisclosureListResponse(total=total, page=page, size=size, items=items)


@router.get(
    "/link/{rcept_no}",
    response_model=DeepLinkResponse,
    summary="공시 Deep Link 조회",
)
async def get_deep_link(
    rcept_no: str,
    db: AsyncSession = Depends(get_db),
    service: DisclosureService = Depends(get_disclosure_service),
):
    """접수번호로 공시 원문 Deep Link를 조회한다."""
    disclosure = await service.get_deep_link(db=db, rcept_no=rcept_no)

    if not disclosure:
        raise HTTPException(status_code=404, detail=f"공시를 찾을 수 없습니다: {rcept_no}")

    return DeepLinkResponse(
        rcept_no=disclosure.rcept_no,
        dart_viewer_url=disclosure.dart_viewer_url,
        dart_pdf_url=disclosure.dart_pdf_url,
        kofia_url=disclosure.kofia_url,
        report_nm=disclosure.report_nm,
        source=disclosure.source,
    )


@router.post(
    "/{corp_code}/sync",
    response_model=DisclosureSyncResponse,
    summary="DART 공시 동기화",
    status_code=201,
)
async def sync_disclosures(
    corp_code: str,
    bgn_de: str | None = Query(None, description="시작일 (YYYYMMDD)"),
    end_de: str | None = Query(None, description="종료일 (YYYYMMDD)"),
    db: AsyncSession = Depends(get_db),
    service: DisclosureService = Depends(get_disclosure_service),
):
    """DART에서 공시 데이터를 동기화하고 Deep Link를 생성한다."""
    synced_count, skipped_count = await service.sync_disclosures(
        db=db,
        corp_code=corp_code,
        bgn_de=bgn_de,
        end_de=end_de,
    )

    return DisclosureSyncResponse(
        corp_code=corp_code,
        source="dart",
        synced_count=synced_count,
        skipped_count=skipped_count,
    )


@router.post(
    "/kofia/{fund_code}/sync",
    response_model=DisclosureSyncResponse,
    summary="KOFIA 펀드 공시 동기화",
    status_code=201,
)
async def sync_kofia_disclosures(
    fund_code: str,
    db: AsyncSession = Depends(get_db),
    service: DisclosureService = Depends(get_disclosure_service),
):
    """KOFIA DIS에서 펀드 공시 데이터를 동기화하고 Deep Link를 생성한다."""
    synced_count, skipped_count = await service.sync_kofia_disclosures(
        db=db,
        fund_code=fund_code,
    )

    return DisclosureSyncResponse(
        fund_code=fund_code,
        source="kofia",
        synced_count=synced_count,
        skipped_count=skipped_count,
    )
