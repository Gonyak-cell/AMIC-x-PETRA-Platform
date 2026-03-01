"""add deal_type and rcept_no columns to deals

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deals",
        sa.Column(
            "deal_type", sa.String(30), nullable=True,
            comment="딜 유형 (investment/acquisition/exit/holding_change)",
        ),
    )
    op.add_column(
        "deals",
        sa.Column(
            "rcept_no", sa.String(20), nullable=True,
            comment="DART 접수번호 (공시 원문 연결)",
        ),
    )
    op.create_index("ix_deals_deal_type", "deals", ["deal_type"])
    op.create_index("ix_deals_rcept_no", "deals", ["rcept_no"])


def downgrade() -> None:
    op.drop_index("ix_deals_rcept_no", table_name="deals")
    op.drop_index("ix_deals_deal_type", table_name="deals")
    op.drop_column("deals", "rcept_no")
    op.drop_column("deals", "deal_type")
