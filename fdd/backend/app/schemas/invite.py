"""초대 요청/응답 스키마."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class InviteCreateRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    title: str = Field(default="", max_length=100)
    transaction_ids: list[uuid.UUID] = Field(..., min_length=1)
    transaction_names: list[str] = Field(default_factory=list)


class InviteCreateResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    is_new_user: bool
    assigned_deal_count: int
    invite_sent: bool
    invite_error: str | None = None


class InviteAcceptRequest(BaseModel):
    token: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6, max_length=128)


class InviteAcceptResponse(BaseModel):
    message: str
    email: str


class InviteVerifyRequest(BaseModel):
    token: str = Field(..., min_length=1)


class InviteTokenInfo(BaseModel):
    valid: bool
    email: str | None = None
    display_name: str | None = None
    expired: bool = False
    already_used: bool = False
