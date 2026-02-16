"""알림 및 워치리스트 Pydantic 스키마"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistCreate(BaseModel):
    """워치리스트 추가 요청"""

    company_id: int
    alert_types: list[str] = Field(default_factory=lambda: ["new_disclosure", "reputation_change"])


class WatchlistItem(BaseModel):
    """워치리스트 항목 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company_id: int
    company_name: str | None = None
    alert_types: list[str] = []
    is_active: bool
    created_at: datetime


class WatchlistListResponse(BaseModel):
    """워치리스트 목록 응답"""

    total: int
    items: list[WatchlistItem]


class AlertHistoryItem(BaseModel):
    """알림 이력 항목 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: str
    title: str
    message: str | None = None
    is_read: bool
    company_id: int
    company_name: str | None = None
    reference_id: int | None = None
    reference_type: str | None = None
    created_at: datetime


class AlertListResponse(BaseModel):
    """알림 목록 응답 (페이지네이션)"""

    total: int
    page: int
    size: int
    items: list[AlertHistoryItem]


class UnreadCountResponse(BaseModel):
    """미읽음 알림 수 응답"""

    count: int
