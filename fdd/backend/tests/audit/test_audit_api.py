"""Audit Log API 테스트 — FDD-1702."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog


def _seed_audit_logs(db: Session, count: int = 5):
    for i in range(count):
        db.add(
            AuditLog(
                entity_type="deal",
                entity_id=uuid.uuid4(),
                action=AuditAction.CREATE,
                actor=f"user{i}@fdd.dev",
            )
        )
    db.commit()


def test_search_audit_logs(client, db):
    _seed_audit_logs(db, 3)
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_search_audit_logs_filter(client, db):
    _seed_audit_logs(db, 4)
    resp = client.get("/api/v1/audit-logs", params={"entity_type": "deal"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 4


def test_search_audit_logs_pagination(client, db):
    _seed_audit_logs(db, 10)
    resp = client.get("/api/v1/audit-logs", params={"limit": 3, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert len(data["items"]) == 3
    assert data["limit"] == 3
    assert data["offset"] == 0


def test_get_audit_trail(client, db):
    entity_id = uuid.uuid4()
    for action in [AuditAction.CREATE, AuditAction.UPDATE]:
        db.add(
            AuditLog(
                entity_type="deal",
                entity_id=entity_id,
                action=action,
                actor="system",
            )
        )
    db.commit()

    resp = client.get(f"/api/v1/audit-logs/entity/deal/{entity_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
