"""061 — AuditAction enum에 READ 값 추가

pef_registry, si_mapping 라우터에서 AuditAction.READ를 사용하지만,
PostgreSQL auditaction enum 타입에 등록되어 있지 않아 INSERT 시 에러 발생.
SQLite는 enum을 VARCHAR로 처리하므로 CI 테스트에서는 발견되지 않음.

Revision ID: 061
Revises: 060
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "061"
down_revision: str = "060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'READ'"))


def downgrade() -> None:
    # PostgreSQL enum에서 값을 제거하는 것은 지원되지 않음
    # READ 값이 남아 있어도 무해함
    pass
