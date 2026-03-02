"""AuditLog.entity_id를 Uuid → String(100)으로 변경.

Milestone 첨부파일 CRUD 시 entity_id에 문자열(milestoneKey 등)이
감사 로그에 기록될 수 있으므로, UUID 전용 타입에서 범용 문자열로 전환한다.
기존 UUID entity_id는 VARCHAR(100) 캐스팅으로 무손실 보존된다.

Revision ID: 055
Revises: 054
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "055"
down_revision: str = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TABLE audit_logs ALTER COLUMN entity_id TYPE VARCHAR(100) USING entity_id::text"))
    else:
        # SQLite: 타입 강제 없으므로 별도 작업 불필요
        pass


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # UUID가 아닌 값이 있으면 롤백 차단
        result = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM audit_logs "
                "WHERE entity_id IS NOT NULL "
                "AND entity_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'"
            )
        )
        non_uuid_count = result.scalar() or 0
        if non_uuid_count > 0:
            raise RuntimeError(
                f"ROLLBACK BLOCKED: audit_logs.entity_id에 UUID가 아닌 값이 {non_uuid_count}건 존재합니다. "
                "문자열 entity_id를 삭제하거나 NULL로 변경한 뒤 롤백하세요."
            )
        op.execute(sa.text("ALTER TABLE audit_logs ALTER COLUMN entity_id TYPE UUID USING entity_id::uuid"))
    else:
        # SQLite: 별도 작업 불필요
        pass
