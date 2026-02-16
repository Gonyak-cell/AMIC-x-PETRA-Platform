"""Webhooks API — Phase 5 Portal endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.schemas.webhook import (
    WebhookConfigRead,
    WebhookCreate,
    WebhookTestResult,
    WebhookUpdate,
)
from app.services.webhook.webhook_service import (
    create_webhook,
    delete_webhook,
    list_webhooks,
    test_webhook,
    update_webhook,
)

router = APIRouter(tags=["webhooks"])


@router.get("/webhooks", response_model=list[WebhookConfigRead])
def list_webhook_configs(
    current_user: CurrentUser = require_permission(Permission.WEBHOOK_MANAGE),
    db: Session = Depends(get_db),
):
    """웹훅 목록을 조회한다. Admin 전용."""
    return list_webhooks(db)


@router.post("/webhooks", response_model=WebhookConfigRead, status_code=201)
def create_webhook_config(
    body: WebhookCreate,
    current_user: CurrentUser = require_permission(Permission.WEBHOOK_MANAGE),
    db: Session = Depends(get_db),
):
    """웹훅을 생성한다. Admin 전용."""
    return create_webhook(
        db, url=body.url, events=body.events, secret=body.secret
    )


@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResult)
def test_webhook_config(
    webhook_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.WEBHOOK_MANAGE),
    db: Session = Depends(get_db),
):
    """웹훅 테스트 호출을 발송한다. Admin 전용."""
    return test_webhook(db, webhook_id)


@router.put("/webhooks/{webhook_id}", response_model=WebhookConfigRead)
def update_webhook_config(
    webhook_id: uuid.UUID,
    body: WebhookUpdate,
    current_user: CurrentUser = require_permission(Permission.WEBHOOK_MANAGE),
    db: Session = Depends(get_db),
):
    """웹훅 설정을 수정한다. Admin 전용."""
    update_data = body.model_dump(exclude_unset=True)
    webhook = update_webhook(db, webhook_id=webhook_id, **update_data)
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook_config(
    webhook_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.WEBHOOK_MANAGE),
    db: Session = Depends(get_db),
):
    """웹훅을 삭제한다. Admin 전용."""
    deleted = delete_webhook(db, webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return None
