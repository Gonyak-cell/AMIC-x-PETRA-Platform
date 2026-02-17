"""Add deal classification fields and make dates optional.

Revision ID: 012_deal_classify
Revises: 011_token_blacklist
Create Date: 2026-02-17

New columns on `deal`:
  - deal_structure (VARCHAR 50, nullable)
  - investment_type (VARCHAR 50, nullable)
  - seller_type (VARCHAR 50, nullable)

Changed columns on `deal`:
  - reference_date: NOT NULL → nullable
  - period_start: NOT NULL → nullable
  - period_end: NOT NULL → nullable
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_deal_classify"
down_revision: str | None = "011_token_blacklist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Add deal classification columns ──
    op.add_column("deal", sa.Column("deal_structure", sa.String(50), nullable=True))
    op.add_column("deal", sa.Column("investment_type", sa.String(50), nullable=True))
    op.add_column("deal", sa.Column("seller_type", sa.String(50), nullable=True))

    # ── 2. Make date fields optional (nullable) ──
    op.alter_column("deal", "reference_date", existing_type=sa.Date(), nullable=True)
    op.alter_column("deal", "period_start", existing_type=sa.Date(), nullable=True)
    op.alter_column("deal", "period_end", existing_type=sa.Date(), nullable=True)


def downgrade() -> None:
    # Restore NOT NULL on date fields
    op.alter_column("deal", "period_end", existing_type=sa.Date(), nullable=False)
    op.alter_column("deal", "period_start", existing_type=sa.Date(), nullable=False)
    op.alter_column("deal", "reference_date", existing_type=sa.Date(), nullable=False)

    # Drop classification columns
    op.drop_column("deal", "seller_type")
    op.drop_column("deal", "investment_type")
    op.drop_column("deal", "deal_structure")
