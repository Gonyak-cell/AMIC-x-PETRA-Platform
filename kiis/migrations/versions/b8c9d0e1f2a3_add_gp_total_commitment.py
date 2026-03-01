"""Add gp_total_commitment column to companies.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "gp_total_commitment",
            sa.Numeric(20, 0),
            nullable=True,
            comment="FSS PEF 총약정액 합산 (억원, GP1+GP2+GP3 참여분)",
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "gp_total_commitment")
