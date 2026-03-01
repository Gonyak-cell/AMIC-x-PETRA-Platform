"""AuditAction enum에 CLIENT_ASSIGNED, CLIENT_REMOVED 값 추가.

deal_clients 라우터에서 사용하는 감사 액션이 PostgreSQL enum에 미등록 상태였음.
SQLite(CI)에서는 VARCHAR이므로 무관하나, PostgreSQL 프로덕션에서 런타임 크래시 발생.

Revision ID: 051
Revises: 050
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'CLIENT_ASSIGNED'"))
        op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'CLIENT_REMOVED'"))


def downgrade() -> None:
    # PostgreSQL enum 값 제거 불가 — 애플리케이션에서 미사용으로 무해
    pass
