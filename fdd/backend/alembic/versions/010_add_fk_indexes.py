"""Add missing FK column indexes.

Revision ID: 010_fk_indexes
Revises: 009_soft_delete
Create Date: 2026-02-13

Changes:
  - ix_deal_definition_deal_id on deal_definition(deal_id)
  - ix_deal_snapshot_deal_id on deal_snapshot(deal_id)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_fk_indexes"
down_revision: str | None = "009_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_deal_definition_deal_id", "deal_definition", ["deal_id"]
    )
    op.create_index(
        "ix_deal_snapshot_deal_id", "deal_snapshot", ["deal_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_deal_snapshot_deal_id", table_name="deal_snapshot")
    op.drop_index("ix_deal_definition_deal_id", table_name="deal_definition")
