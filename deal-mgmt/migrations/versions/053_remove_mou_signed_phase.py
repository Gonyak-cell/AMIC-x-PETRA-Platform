"""MOU_SIGNED 단계를 파이프라인에서 제거 — 데이터를 MAIN_DUE_DILIGENCE로 이동.

- MOU_SIGNED 상태인 거래를 MAIN_DUE_DILIGENCE로 마이그레이션
- AttachmentEntityType에 MILESTONE 값 추가 (마일스톤 문서 업로드용)
- PostgreSQL enum에서 값 제거는 불가 → MOU_SIGNED enum은 잔존

Revision ID: 053
Revises: 052
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "053"
down_revision: str = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1) MOU_SIGNED → MAIN_DUE_DILIGENCE 데이터 마이그레이션
    op.execute(sa.text("UPDATE transactions SET phase = 'MAIN_DUE_DILIGENCE' WHERE phase = 'MOU_SIGNED'"))

    # 2) AttachmentEntityType에 MILESTONE 추가
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE attachmententitytype ADD VALUE IF NOT EXISTS 'MILESTONE'"))
    # SQLite: VARCHAR이므로 별도 ALTER 불필요


def downgrade() -> None:
    # MOU_SIGNED 단계 복원은 불필요 — 데이터가 이미 MAIN_DUE_DILIGENCE로 이동됨.
    # PostgreSQL enum에서 MILESTONE 제거 불가 → downgrade는 no-op.
    pass
