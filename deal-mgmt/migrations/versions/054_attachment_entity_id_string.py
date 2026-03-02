"""Attachment.entity_id를 Uuid → String(50)으로 변경.

마일스톤 문서 업로드 시 entity_id에 milestoneKey 문자열("MOU_SIGNED", "SIGNING")을
저장해야 하므로, UUID 전용 타입에서 범용 문자열로 전환한다.
기존 UUID entity_id는 VARCHAR(50) 캐스팅으로 무손실 보존된다.

Revision ID: 054
Revises: 053
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "054"
down_revision: str = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # PostgreSQL: UUID → VARCHAR(50) 명시적 캐스팅
        op.execute(sa.text("ALTER TABLE attachments ALTER COLUMN entity_id TYPE VARCHAR(50) USING entity_id::text"))
    else:
        # SQLite: 타입 강제 없으므로 별도 작업 불필요
        pass


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # milestoneKey 문자열이 존재하면 UUID 캐스팅 실패 → 차단 (R12-04)
        result = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM attachments "
                "WHERE entity_id IS NOT NULL "
                "AND entity_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'"
            )
        )
        non_uuid_count = result.scalar() or 0
        if non_uuid_count > 0:
            raise RuntimeError(
                f"ROLLBACK BLOCKED: entity_id에 UUID가 아닌 값이 {non_uuid_count}건 존재합니다. "
                "milestoneKey 문자열을 삭제하거나 NULL로 변경한 뒤 롤백하세요."
            )
        op.execute(sa.text("ALTER TABLE attachments ALTER COLUMN entity_id TYPE UUID USING entity_id::uuid"))
