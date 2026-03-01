"""대시보드 API 라우터"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter()


def get_dashboard_service() -> DashboardService:
    """대시보드 서비스 팩토리"""
    return DashboardService()


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="대시보드 요약",
)
async def get_dashboard_summary(
    _claims: JWTClaims = Depends(get_jwt_claims),
    db: AsyncSession = Depends(get_db),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    """전체 시스템 대시보드 요약 데이터를 반환한다.

    수집 기업 수, 펀드 수, 리츠 수, 뉴스 수, 딜 수,
    최근 7일 뉴스 수, 최근 딜 5건, Risk 기업 목록,
    데이터 신선도를 포함한다.
    """
    summary = await service.get_summary(db)
    return DashboardSummary(**summary)
