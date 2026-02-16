"""심사역 추적 API 라우터"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.manager import (
    ManagerDealItem,
    ManagerMovementItem,
    ManagerMovementListResponse,
    ManagerProfileResponse,
    ManagerTrackResponse,
)
from app.services.manager_service import ManagerService

router = APIRouter()


def get_manager_service() -> ManagerService:
    """심사역 서비스 팩토리"""
    return ManagerService()


@router.get(
    "/movements",
    response_model=ManagerMovementListResponse,
    summary="심사역 이동 이력 조회",
)
async def get_movements(
    manager_name: str | None = Query(None, description="심사역 이름 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
    service: ManagerService = Depends(get_manager_service),
):
    """심사역 이동 이력을 조회한다. 이름 필터를 적용할 수 있다."""
    movements, total = await service.get_movements(
        db=db,
        manager_name=manager_name,
        page=page,
        size=size,
    )

    items = [
        ManagerMovementItem(
            id=m.id,
            manager_name=m.manager_name,
            from_company_id=m.from_company_id,
            from_company_name=m.from_company_name,
            from_fund_id=m.from_fund_id,
            to_company_id=m.to_company_id,
            to_company_name=m.to_company_name,
            to_fund_id=m.to_fund_id,
            movement_type=m.movement_type,
            detected_at=m.detected_at,
            source=m.source,
            notes=m.notes,
        )
        for m in movements
    ]

    return ManagerMovementListResponse(total=total, page=page, size=size, items=items)


@router.get(
    "/movements/by-company/{corp_code}",
    response_model=ManagerMovementListResponse,
    summary="기업별 심사역 이동 이력",
)
async def get_movements_by_company(
    corp_code: str,
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
    service: ManagerService = Depends(get_manager_service),
):
    """특정 기업과 관련된 심사역 이동 이력을 조회한다."""
    movements, total = await service.get_movements_by_company(
        db=db,
        corp_code=corp_code,
        page=page,
        size=size,
    )

    if total == 0:
        # 기업 자체가 없을 수도 있으므로 빈 결과 반환
        return ManagerMovementListResponse(total=0, page=page, size=size, items=[])

    items = [
        ManagerMovementItem(
            id=m.id,
            manager_name=m.manager_name,
            from_company_id=m.from_company_id,
            from_company_name=m.from_company_name,
            from_fund_id=m.from_fund_id,
            to_company_id=m.to_company_id,
            to_company_name=m.to_company_name,
            to_fund_id=m.to_fund_id,
            movement_type=m.movement_type,
            detected_at=m.detected_at,
            source=m.source,
            notes=m.notes,
        )
        for m in movements
    ]

    return ManagerMovementListResponse(total=total, page=page, size=size, items=items)


@router.get(
    "/{manager_name}/profile",
    response_model=ManagerProfileResponse,
    summary="심사역 프로필 조회",
)
async def get_manager_profile(
    manager_name: str,
    db: AsyncSession = Depends(get_db),
    service: ManagerService = Depends(get_manager_service),
):
    """심사역의 프로필 정보를 조회한다. 소속, 이동 이력, 관여 딜을 통합한다."""
    profile = await service.get_manager_profile(
        db=db,
        manager_name=manager_name,
    )

    # 이동 이력 변환
    movement_items = [
        ManagerMovementItem(
            id=m.id,
            manager_name=m.manager_name,
            from_company_id=m.from_company_id,
            from_company_name=m.from_company_name,
            from_fund_id=m.from_fund_id,
            to_company_id=m.to_company_id,
            to_company_name=m.to_company_name,
            to_fund_id=m.to_fund_id,
            movement_type=m.movement_type,
            detected_at=m.detected_at,
            source=m.source,
            notes=m.notes,
        )
        for m in profile["movements"]
    ]

    # 딜 목록 변환
    deal_items = [
        ManagerDealItem(
            id=d.id,
            target_company=d.target_company,
            amount_display=d.amount_display,
            round_stage=d.round_stage,
            sector=d.sector,
        )
        for d in profile["deals"]
    ]

    return ManagerProfileResponse(
        manager_name=profile["manager_name"],
        current_company=profile["current_company"],
        current_fund=profile["current_fund"],
        specialty_sectors=profile["specialty_sectors"],
        career_years=profile["career_years"],
        total_deals_involved=profile["total_deals_involved"],
        movements=movement_items,
        deals=deal_items,
    )


@router.post(
    "/track",
    response_model=ManagerTrackResponse,
    summary="심사역 이동 감지 실행",
    status_code=200,
)
async def track_manager_movements(
    db: AsyncSession = Depends(get_db),
    service: ManagerService = Depends(get_manager_service),
):
    """FundManager 데이터를 스캔하여 심사역 이동 이벤트를 감지한다."""
    from sqlalchemy import func, select

    from app.models.fund import FundManager

    # 스캔 대상 수 조회
    count_stmt = select(func.count()).select_from(FundManager)
    count_result = await db.execute(count_stmt)
    scanned_count = count_result.scalar() or 0

    # 이동 감지 실행
    new_movements = await service.detect_movements(db=db)

    items = [
        ManagerMovementItem(
            id=m.id,
            manager_name=m.manager_name,
            from_company_id=m.from_company_id,
            from_company_name=m.from_company_name,
            from_fund_id=m.from_fund_id,
            to_company_id=m.to_company_id,
            to_company_name=m.to_company_name,
            to_fund_id=m.to_fund_id,
            movement_type=m.movement_type,
            detected_at=m.detected_at,
            source=m.source,
            notes=m.notes,
        )
        for m in new_movements
    ]

    return ManagerTrackResponse(
        scanned_count=scanned_count,
        new_movements_count=len(new_movements),
        movements=items,
    )
