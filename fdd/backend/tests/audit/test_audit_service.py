"""Audit Log 서비스 테스트 — FDD-1702."""

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.services.audit.audit_service import (
    compute_changed_fields,
    create_enhanced_audit_log,
    get_entity_audit_trail,
    list_audit_logs,
)

# ── compute_changed_fields ─────────────────────────────


def test_changed_fields_both_none():
    assert compute_changed_fields(None, None) == []


def test_changed_fields_before_none():
    result = compute_changed_fields(None, {"a": 1, "b": 2})
    assert sorted(result) == ["a", "b"]


def test_changed_fields_after_none():
    result = compute_changed_fields({"x": 1}, None)
    assert result == ["x"]


def test_changed_fields_identical():
    assert compute_changed_fields({"a": 1}, {"a": 1}) == []


def test_changed_fields_mixed():
    before = {"a": 1, "b": 2, "c": 3}
    after = {"a": 1, "b": 99, "d": 4}
    result = compute_changed_fields(before, after)
    assert sorted(result) == ["b", "c", "d"]


# ── create_enhanced_audit_log ──────────────────────────


def test_create_enhanced_audit_log(db: Session):
    entity_id = uuid.uuid4()
    log = create_enhanced_audit_log(
        db,
        entity_type="deal",
        entity_id=entity_id,
        action=AuditAction.CREATE,
        actor="test@fdd.dev",
        user_email="test@fdd.dev",
        user_role="ADMIN",
        ip_address="127.0.0.1",
        before_state=None,
        after_state={"name": "Deal A"},
        changed_fields=["name"],
    )
    assert log.id is not None
    assert log.entity_type == "deal"
    assert log.user_email == "test@fdd.dev"
    assert log.ip_address == "127.0.0.1"
    assert log.after_state == {"name": "Deal A"}
    assert log.changed_fields == ["name"]


def test_create_audit_log_with_expiry(db: Session):
    expires = datetime.utcnow() + timedelta(days=90)
    log = create_enhanced_audit_log(
        db,
        entity_type="session",
        entity_id=uuid.uuid4(),
        action=AuditAction.LOGIN,
        expires_at=expires,
    )
    assert log.expires_at is not None


# ── list_audit_logs ────────────────────────────────────


def _seed_logs(db: Session, count: int = 5) -> list[AuditLog]:
    logs = []
    now = datetime.now()  # Explicit timestamp for SQLite compatibility
    for i in range(count):
        log = AuditLog(
            entity_type="deal" if i % 2 == 0 else "user",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE if i % 2 == 0 else AuditAction.UPDATE,
            actor=f"user{i}@fdd.dev",
            user_id=uuid.uuid4(),
            created_at=now,
        )
        db.add(log)
        logs.append(log)
    db.commit()
    return logs


def test_list_audit_logs_all(db: Session):
    _seed_logs(db, 5)
    items, total = list_audit_logs(db)
    assert total == 5
    assert len(items) == 5


def test_list_audit_logs_filter_entity_type(db: Session):
    _seed_logs(db, 6)
    items, total = list_audit_logs(db, entity_type="deal")
    assert total == 3
    assert all(item.entity_type == "deal" for item in items)


def test_list_audit_logs_filter_action(db: Session):
    _seed_logs(db, 4)
    items, total = list_audit_logs(db, action=AuditAction.CREATE)
    assert total == 2


def test_list_audit_logs_pagination(db: Session):
    _seed_logs(db, 10)
    items, total = list_audit_logs(db, limit=3, offset=0)
    assert total == 10
    assert len(items) == 3

    items2, _ = list_audit_logs(db, limit=3, offset=3)
    assert len(items2) == 3
    assert items[0].id != items2[0].id


def test_list_audit_logs_date_filter(db: Session):
    _seed_logs(db, 3)
    today = date.today()
    items, total = list_audit_logs(db, start_date=today, end_date=today)
    assert total == 3


# ── get_entity_audit_trail ─────────────────────────────


def test_entity_audit_trail(db: Session):
    entity_id = uuid.uuid4()
    for action in [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.APPROVE]:
        db.add(
            AuditLog(
                entity_type="deal_definition",
                entity_id=entity_id,
                action=action,
                actor="system",
            )
        )
    db.commit()

    trail = get_entity_audit_trail(db, "deal_definition", entity_id)
    assert len(trail) == 3
    assert trail[0].action == AuditAction.CREATE
    assert trail[2].action == AuditAction.APPROVE


def test_entity_audit_trail_empty(db: Session):
    trail = get_entity_audit_trail(db, "deal", uuid.uuid4())
    assert trail == []
