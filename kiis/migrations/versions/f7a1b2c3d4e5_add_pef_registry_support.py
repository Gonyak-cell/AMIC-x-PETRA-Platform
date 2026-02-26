"""add PEF registry support: fund columns + fund_gps table

Revision ID: f7a1b2c3d4e5
Revises: c1a2b3d4e5f6
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "f7a1b2c3d4e5"
down_revision = "c1a2b3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add PEF registry columns to funds table
    op.add_column("funds", sa.Column("data_source", sa.String(30), server_default="kofia", nullable=False))
    op.add_column("funds", sa.Column("legal_basis", sa.String(200), nullable=True))
    op.add_column("funds", sa.Column("is_co_gp", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("funds", sa.Column("reference_date", sa.String(50), nullable=True))
    op.create_index("ix_funds_data_source", "funds", ["data_source"])

    # Create fund_gps table (Co-GP support)
    op.create_table(
        "fund_gps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), sa.ForeignKey("funds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gp_name", sa.String(200), nullable=False),
        sa.Column("gp_role", sa.String(10), server_default="gp1", nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fund_gps_fund_id", "fund_gps", ["fund_id"])
    op.create_index("ix_fund_gps_gp_name", "fund_gps", ["gp_name"])
    op.create_unique_constraint("uq_fund_gp", "fund_gps", ["fund_id", "gp_name"])


def downgrade() -> None:
    op.drop_table("fund_gps")
    op.drop_index("ix_funds_data_source", table_name="funds")
    op.drop_column("funds", "reference_date")
    op.drop_column("funds", "is_co_gp")
    op.drop_column("funds", "legal_basis")
    op.drop_column("funds", "data_source")
