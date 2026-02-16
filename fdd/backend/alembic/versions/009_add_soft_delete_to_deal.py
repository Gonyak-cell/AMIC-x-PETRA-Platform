"""Add soft delete columns to deal table.

Revision ID: 009_soft_delete
Revises: 008_add_industry
Create Date: 2026-02-13

Changes:
  - deal.is_deleted BOOLEAN NOT NULL DEFAULT false
  - deal.deleted_at TIMESTAMP WITH TIME ZONE NULL
  - ix_deal_is_deleted 인덱스 추가
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_soft_delete"
down_revision: str | None = "008_add_industry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "deal",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "deal",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index("ix_deal_is_deleted", "deal", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_deal_is_deleted", table_name="deal")
    op.drop_column("deal", "deleted_at")
    op.drop_column("deal", "is_deleted")
