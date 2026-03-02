"""제재 분류 API 라우터"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_jwt_claims
from app.schemas.sanction import (
    ClassifiedSanctionItem,
    ClassifiedSanctionListItem,
    ClassifiedSanctionListResponse,
    SanctionClassifyResponse,
    SanctionSummaryResponse,
)
from app.services.sanction_service import SanctionService

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_jwt_claims)])


def get_sanction_service() -> SanctionService:
    """제재 서비스 팩토리"""
    return SanctionService()


@router.get(
    "/classified/{corp_code}",
    response_model=ClassifiedSanctionListResponse,
    summary="기업별 분류된 제재 목록",
)
async def get_classified_sanctions(
    corp_code: str,
    severity: str | None = Query(None, description="경중 필터 (caution/warning/critical)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
    service: SanctionService = Depends(get_sanction_service),
):
    """특정 기업의 분류된 제재 내역을 페이지네이션으로 조회한다."""
    sanctions, total = await service.get_sanctions_by_company(
        db=db,
        corp_code=corp_code,
        severity=severity,
        page=page,
        size=size,
    )

    items = [
        ClassifiedSanctionListItem(
            id=s.id,
            corp_code=s.corp_code,
            sanctions_type=s.sanctions_type,
            severity=s.severity,
            category=s.category,
            sanctions_date=s.sanctions_date,
        )
        for s in sanctions
    ]

    return ClassifiedSanctionListResponse(total=total, page=page, size=size, items=items)


@router.get(
    "/classified/{corp_code}/summary",
    response_model=SanctionSummaryResponse,
    summary="기업별 제재 요약",
)
async def get_sanction_summary(
    corp_code: str,
    db: AsyncSession = Depends(get_db),
    service: SanctionService = Depends(get_sanction_service),
):
    """특정 기업의 제재 경중별 건수를 요약한다."""
    summary = await service.get_sanction_summary(db=db, corp_code=corp_code)

    return SanctionSummaryResponse(
        total=summary["total"],
        caution_count=summary["caution_count"],
        warning_count=summary["warning_count"],
        critical_count=summary["critical_count"],
    )


@router.post(
    "/classify/{corp_code}",
    response_model=SanctionClassifyResponse,
    summary="제재 경중 분류 실행",
    status_code=201,
)
async def classify_sanctions(
    corp_code: str,
    db: AsyncSession = Depends(get_db),
    service: SanctionService = Depends(get_sanction_service),
):
    """DART에서 특정 기업의 제재 내역을 수집하고 경중을 분류한다."""
    try:
        records = await service.classify_for_company(db=db, corp_code=corp_code)
    except Exception:
        logger.exception("DART API 호출 실패: corp_code=%s", corp_code)
        raise HTTPException(
            status_code=502,
            detail="외부 API 호출에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        )

    items = [
        ClassifiedSanctionItem(
            id=r.id,
            company_id=r.company_id,
            corp_code=r.corp_code,
            sanctions_type=r.sanctions_type,
            sanctions_detail=r.sanctions_detail,
            sanctions_date=r.sanctions_date,
            sanctions_agency=r.sanctions_agency,
            severity=r.severity,
            severity_reason=r.severity_reason,
            category=r.category,
            classified_at=r.classified_at,
        )
        for r in records
    ]

    return SanctionClassifyResponse(
        corp_code=corp_code,
        classified_count=len(records),
        items=items,
    )
