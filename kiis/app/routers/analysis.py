"""평판 분석 API 라우터"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.company import Company
from app.models.reputation import ReputationScore
from app.schemas.analysis import (
    ReputationCalculateRequest,
    ReputationHistoryItem,
    ReputationHistoryResponse,
    ReputationListItem,
    ReputationListResponse,
    ReputationScoreResponse,
)
from app.services.reputation_service import ReputationService

router = APIRouter()


def get_reputation_service() -> ReputationService:
    """평판 서비스 팩토리"""
    return ReputationService()


@router.get(
    "/reputation",
    response_model=ReputationListResponse,
    summary="평판 목록 조회",
)
async def list_reputations(
    status_tag: str | None = Query(None, description="상태 태그 필터 (rising/stable/risk)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
):
    """기업 평판 목록을 조회한다."""
    query = select(
        ReputationScore.company_id,
        Company.corp_code,
        Company.corp_name,
        ReputationScore.total_score,
        ReputationScore.status_tag,
        ReputationScore.scored_at,
    ).join(Company, ReputationScore.company_id == Company.id)

    if status_tag:
        query = query.where(ReputationScore.status_tag == status_tag)

    # 총 건수
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션
    query = query.order_by(ReputationScore.total_score.desc()).offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    rows = result.all()

    items = [
        ReputationListItem(
            company_id=row.company_id,
            corp_code=row.corp_code,
            corp_name=row.corp_name,
            total_score=row.total_score,
            status_tag=row.status_tag,
            scored_at=row.scored_at,
        )
        for row in rows
    ]

    return ReputationListResponse(total=total, page=page, size=size, items=items)


@router.get(
    "/reputation/{corp_code}",
    response_model=ReputationScoreResponse,
    summary="기업 평판 조회",
)
async def get_reputation(
    corp_code: str,
    db: AsyncSession = Depends(get_db),
    service: ReputationService = Depends(get_reputation_service),
):
    """특정 기업의 현재 평판 지수를 조회한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    reputation = await service.get_reputation(db, corp_code)

    if not reputation:
        raise HTTPException(
            status_code=404,
            detail=f"평판 정보가 없습니다. POST /reputation/{corp_code}/calculate로 계산하세요.",
        )

    return ReputationScoreResponse(
        company_id=reputation.company_id,
        corp_code=company.corp_code,
        corp_name=company.corp_name,
        trend_score=reputation.trend_score,
        news_score=reputation.news_score,
        performance_score=reputation.performance_score,
        total_score=reputation.total_score,
        status_tag=reputation.status_tag,
        scored_at=reputation.scored_at,
        news_count=reputation.news_count,
        exit_count=reputation.exit_count,
    )


@router.get(
    "/reputation/{corp_code}/history",
    response_model=ReputationHistoryResponse,
    summary="기업 평판 이력 조회",
)
async def get_reputation_history(
    corp_code: str,
    limit: int = Query(30, ge=1, le=365, description="조회 건수"),
    db: AsyncSession = Depends(get_db),
    service: ReputationService = Depends(get_reputation_service),
):
    """특정 기업의 평판 지수 시계열 이력을 조회한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    history = await service.get_reputation_history(db, corp_code, limit)

    items = [
        ReputationHistoryItem(
            total_score=h.total_score,
            status_tag=h.status_tag,
            trend_score=h.trend_score,
            news_score=h.news_score,
            performance_score=h.performance_score,
            recorded_at=h.recorded_at,
        )
        for h in history
    ]

    return ReputationHistoryResponse(
        corp_code=company.corp_code,
        corp_name=company.corp_name,
        total=len(items),
        items=items,
    )


@router.post(
    "/reputation/{corp_code}/calculate",
    response_model=ReputationScoreResponse,
    summary="기업 평판 계산",
)
async def calculate_reputation(
    corp_code: str,
    request: ReputationCalculateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    service: ReputationService = Depends(get_reputation_service),
):
    """특정 기업의 평판 지수를 (재)계산한다."""
    if request is None:
        request = ReputationCalculateRequest()

    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    reputation = await service.calculate_reputation(
        db=db,
        corp_code=corp_code,
        months=request.months,
        save_history=request.save_history,
    )

    if not reputation:
        raise HTTPException(status_code=500, detail="평판 계산에 실패했습니다.")

    return ReputationScoreResponse(
        company_id=reputation.company_id,
        corp_code=company.corp_code,
        corp_name=company.corp_name,
        trend_score=reputation.trend_score,
        news_score=reputation.news_score,
        performance_score=reputation.performance_score,
        total_score=reputation.total_score,
        status_tag=reputation.status_tag,
        scored_at=reputation.scored_at,
        news_count=reputation.news_count,
        exit_count=reputation.exit_count,
    )
