"""알림 및 워치리스트 API 라우터"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.alert import (
    AlertHistoryItem,
    AlertListResponse,
    UnreadCountResponse,
    WatchlistCreate,
    WatchlistItem,
    WatchlistListResponse,
)
from app.services.alert_service import AlertService

watchlist_router = APIRouter()
alerts_router = APIRouter()


def get_alert_service() -> AlertService:
    """알림 서비스 팩토리"""
    return AlertService()


# ─────────────────────────────── Watchlist ───────────────────────────────


@watchlist_router.get(
    "",
    response_model=WatchlistListResponse,
    summary="워치리스트 조회",
)
async def get_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AlertService = Depends(get_alert_service),
):
    """현재 사용자의 활성 워치리스트를 조회한다."""
    items = await service.get_watchlist(db, current_user.id)
    return WatchlistListResponse(
        total=len(items),
        items=[WatchlistItem(**item) for item in items],
    )


@watchlist_router.post(
    "",
    response_model=WatchlistItem,
    summary="워치리스트 추가",
    status_code=201,
)
async def add_to_watchlist(
    request: WatchlistCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AlertService = Depends(get_alert_service),
):
    """워치리스트에 기업을 추가한다. 이미 존재하면 알림 유형을 업데이트한다."""
    import json

    watchlist = await service.add_to_watchlist(
        db=db,
        user_id=current_user.id,
        company_id=request.company_id,
        alert_types=request.alert_types,
    )

    alert_types = json.loads(watchlist.alert_types) if watchlist.alert_types else []

    return WatchlistItem(
        id=watchlist.id,
        user_id=watchlist.user_id,
        company_id=watchlist.company_id,
        company_name=None,
        alert_types=alert_types,
        is_active=watchlist.is_active,
        created_at=watchlist.created_at,
    )


@watchlist_router.delete(
    "/{company_id}",
    summary="워치리스트 제거",
)
async def remove_from_watchlist(
    company_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AlertService = Depends(get_alert_service),
):
    """워치리스트에서 기업을 비활성화한다."""
    removed = await service.remove_from_watchlist(
        db=db,
        user_id=current_user.id,
        company_id=company_id,
    )
    if not removed:
        raise HTTPException(
            status_code=404,
            detail="워치리스트에 등록되지 않은 기업입니다",
        )
    return {"message": "삭제 완료"}


# ────────────────────────────── Alerts ──────────────────────────────


@alerts_router.get(
    "",
    response_model=AlertListResponse,
    summary="알림 목록 조회",
)
async def get_alerts(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AlertService = Depends(get_alert_service),
):
    """현재 사용자의 알림 이력을 조회한다."""
    items, total = await service.get_alerts(
        db=db,
        user_id=current_user.id,
        page=page,
        size=size,
    )
    return AlertListResponse(
        total=total,
        page=page,
        size=size,
        items=[AlertHistoryItem(**item) for item in items],
    )


@alerts_router.post(
    "/{alert_id}/read",
    summary="알림 읽음 처리",
)
async def mark_alert_as_read(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AlertService = Depends(get_alert_service),
):
    """알림을 읽음 상태로 변경한다."""
    success = await service.mark_as_read(
        db=db,
        alert_id=alert_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail="알림을 찾을 수 없습니다",
        )
    return {"message": "읽음 처리 완료"}


@alerts_router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="미읽음 알림 수 조회",
)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: AlertService = Depends(get_alert_service),
):
    """현재 사용자의 미읽음 알림 수를 반환한다."""
    count = await service.get_unread_count(db=db, user_id=current_user.id)
    return UnreadCountResponse(count=count)
