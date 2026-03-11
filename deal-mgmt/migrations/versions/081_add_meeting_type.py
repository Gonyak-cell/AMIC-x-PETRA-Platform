"""081 — meeting_logs에 meeting_type 컬럼 추가.

미팅/식사/티타임 등 접촉 유형을 구분하기 위한 새 필드.
기존 데이터는 NULL (nullable=True).

Revision ID: 081
Revises: 080
"""

import sqlalchemy as sa
from alembic import op

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meeting_logs",
        sa.Column("meeting_type", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meeting_logs", "meeting_type")
