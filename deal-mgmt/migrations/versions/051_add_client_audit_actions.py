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
down_revision = "050b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'CLIENT_ASSIGNED'"))
            op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'CLIENT_REMOVED'"))


def downgrade() -> None:
    # PostgreSQL은 ALTER TYPE ... DROP VALUE를 지원하지 않으므로
    # CLIENT_ASSIGNED, CLIENT_REMOVED 값은 enum에 잔존한다.
    # 이 값들은 애플리케이션에서 미사용 시 무해하며,
    # 완전 롤백이 필요한 경우 enum 재생성이 필요하다:
    #   1. 임시 VARCHAR 컬럼으로 데이터 이관
    #   2. 기존 enum 타입 DROP
    #   3. 새 enum 타입 CREATE (제거 대상 값 제외)
    #   4. VARCHAR → 새 enum으로 CAST 후 원래 컬럼 복원
    pass
