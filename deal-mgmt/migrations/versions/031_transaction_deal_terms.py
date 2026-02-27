"""Transaction 거래조건(Deal Terms) 필드 10개 추가.

Revision ID: 031
Revises: 030
"""

import sqlalchemy as sa
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("sale_process", sa.String(30), nullable=True))
    op.add_column("transactions", sa.Column("control_transfer", sa.String(20), nullable=True))
    op.add_column("transactions", sa.Column("target_stake", sa.Numeric(5, 2), nullable=True))
    op.add_column("transactions", sa.Column("new_share_ratio", sa.Numeric(5, 2), nullable=True))
    op.add_column("transactions", sa.Column("old_share_ratio", sa.Numeric(5, 2), nullable=True))
    op.add_column("transactions", sa.Column("valuation_basis", sa.String(30), nullable=True))
    op.add_column("transactions", sa.Column("cross_border", sa.String(20), nullable=True))
    op.add_column("transactions", sa.Column("target_buyer_types", sa.JSON(), nullable=True))
    op.add_column("transactions", sa.Column("exclusivity", sa.Boolean(), nullable=True))
    op.add_column("transactions", sa.Column("exclusivity_deadline", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "exclusivity_deadline")
    op.drop_column("transactions", "exclusivity")
    op.drop_column("transactions", "target_buyer_types")
    op.drop_column("transactions", "cross_border")
    op.drop_column("transactions", "valuation_basis")
    op.drop_column("transactions", "old_share_ratio")
    op.drop_column("transactions", "new_share_ratio")
    op.drop_column("transactions", "target_stake")
    op.drop_column("transactions", "control_transfer")
    op.drop_column("transactions", "sale_process")
