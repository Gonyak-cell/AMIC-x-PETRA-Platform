"""Data Retention 테스트 — FDD-1703."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.services.retention.policy import RETENTION_PERIODS, DataType, RetentionPolicy


def test_retention_periods_defined():
    """모든 데이터 유형에 보존 기간이 정의되어 있다."""
    for dt in DataType:
        assert dt in RETENTION_PERIODS


def test_get_expiry_date():
    """만료일이 올바르게 계산된다."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as OrmSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    policy = RetentionPolicy(db)
    now = datetime(2026, 1, 1)
    expiry = policy.get_expiry_date(DataType.DEAL_DRAFT, from_date=now)
    assert expiry == now + timedelta(days=90)

    expiry7 = policy.get_expiry_date(DataType.DEAL_COMPLETE, from_date=now)
    assert expiry7 == now + timedelta(days=365 * 7)

    db.close()


def test_count_expired_audit_logs(db: Session):
    """만료된 로그 수를 올바르게 센다."""
    past = datetime.utcnow() - timedelta(days=1)
    future = datetime.utcnow() + timedelta(days=30)

    db.add(AuditLog(
        entity_type="test", entity_id=uuid.uuid4(),
        action=AuditAction.CREATE, actor="system", expires_at=past,
    ))
    db.add(AuditLog(
        entity_type="test", entity_id=uuid.uuid4(),
        action=AuditAction.CREATE, actor="system", expires_at=future,
    ))
    db.add(AuditLog(
        entity_type="test", entity_id=uuid.uuid4(),
        action=AuditAction.CREATE, actor="system", expires_at=None,
    ))
    db.commit()

    policy = RetentionPolicy(db)
    assert policy.count_expired_audit_logs() == 1


def test_purge_dry_run(db: Session):
    """dry_run=True이면 실제 삭제하지 않는다."""
    past = datetime.utcnow() - timedelta(days=1)
    db.add(AuditLog(
        entity_type="test", entity_id=uuid.uuid4(),
        action=AuditAction.CREATE, actor="system", expires_at=past,
    ))
    db.commit()

    policy = RetentionPolicy(db)
    result = policy.purge_expired_audit_logs(dry_run=True)
    assert result.purged_count == 1
    assert result.dry_run is True
    # 실제로 삭제되지 않았는지 확인
    assert policy.count_expired_audit_logs() == 1


def test_purge_actual(db: Session):
    """dry_run=False이면 실제로 삭제한다."""
    past = datetime.utcnow() - timedelta(days=1)
    for _ in range(3):
        db.add(AuditLog(
            entity_type="test", entity_id=uuid.uuid4(),
            action=AuditAction.CREATE, actor="system", expires_at=past,
        ))
    db.commit()

    policy = RetentionPolicy(db)
    result = policy.purge_expired_audit_logs(dry_run=False)
    assert result.purged_count == 3
    assert result.dry_run is False
    assert policy.count_expired_audit_logs() == 0


def test_retention_summary(db: Session):
    """보존 정책 요약 정보를 반환한다."""
    db.add(AuditLog(
        entity_type="test", entity_id=uuid.uuid4(),
        action=AuditAction.CREATE, actor="system",
    ))
    db.commit()

    policy = RetentionPolicy(db)
    summary = policy.get_retention_summary()
    assert "policies" in summary
    assert "audit_logs" in summary
    assert summary["audit_logs"]["total"] == 1
    assert "deal_complete" in summary["policies"]


def test_retention_api_summary(client, db):
    """보존 정책 요약 API."""
    resp = client.get("/api/v1/retention/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "policies" in data


def test_retention_api_purge_dry_run(client, db):
    """파기 API (dry_run)."""
    past = datetime.utcnow() - timedelta(days=1)
    db.add(AuditLog(
        entity_type="test", entity_id=uuid.uuid4(),
        action=AuditAction.CREATE, actor="system", expires_at=past,
    ))
    db.commit()

    resp = client.post("/api/v1/retention/purge/audit-logs", params={"dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["purged_count"] == 1
