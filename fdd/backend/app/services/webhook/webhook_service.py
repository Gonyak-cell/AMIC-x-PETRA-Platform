"""Webhook service — Phase 5."""

from __future__ import annotations

import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.webhook import WebhookConfig


def list_webhooks(db: Session) -> list[WebhookConfig]:
    """Return all webhook configs, newest first."""
    stmt = select(WebhookConfig).order_by(WebhookConfig.created_at.desc())
    return list(db.scalars(stmt).all())


def create_webhook(
    db: Session,
    *,
    url: str,
    events: list[str],
    secret: str | None = None,
) -> WebhookConfig:
    """Create a new webhook config."""
    webhook = WebhookConfig(url=url, events=events, secret=secret)
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


def update_webhook(
    db: Session,
    *,
    webhook_id: uuid.UUID,
    **kwargs: object,
) -> WebhookConfig | None:
    """Update a webhook config. Returns None if not found."""
    webhook = db.get(WebhookConfig, webhook_id)
    if webhook is None:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(webhook, key, value)
    db.commit()
    db.refresh(webhook)
    return webhook


def delete_webhook(db: Session, webhook_id: uuid.UUID) -> bool:
    """Delete a webhook config. Returns True if deleted."""
    webhook = db.get(WebhookConfig, webhook_id)
    if webhook is None:
        return False
    db.delete(webhook)
    db.commit()
    return True


def test_webhook(db: Session, webhook_id: uuid.UUID) -> dict[str, str | None]:
    """Send a test POST to the webhook URL. Returns status and message."""
    webhook = db.get(WebhookConfig, webhook_id)
    if webhook is None:
        return {"status": "failed", "message": "Webhook not found"}

    payload = {
        "event": "test",
        "data": {"message": "This is a test webhook delivery from AMIC x PETRA."},
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if webhook.secret:
        headers["X-Webhook-Secret"] = webhook.secret

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook.url, json=payload, headers=headers)
        if 200 <= response.status_code < 300:
            return {"status": "ok", "message": f"HTTP {response.status_code}"}
        return {
            "status": "failed",
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }
    except httpx.RequestError as exc:
        return {"status": "failed", "message": str(exc)[:200]}
