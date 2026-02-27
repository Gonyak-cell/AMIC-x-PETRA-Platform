"""SI 매핑 테이블 3종 생성 (si_companies, ksic_io_mappings, io_transactions).

Revision ID: 033
Revises: 032
"""

import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── si_companies ──────────────────────────────────────
    op.create_table(
        "si_companies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_name", sa.String(300), nullable=False),
        sa.Column("ksic_codes", sa.JSON(), nullable=True),
        sa.Column("revenue", sa.Numeric(20, 2), nullable=True),
        sa.Column("has_investment_history", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_si_companies_company_name", "si_companies", ["company_name"])

    # ── ksic_io_mappings ──────────────────────────────────
    op.create_table(
        "ksic_io_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("io_code", sa.String(20), nullable=False),
        sa.Column("io_name", sa.String(200), nullable=True),
        sa.Column("ksic_code", sa.String(20), nullable=False),
        sa.Column("ksic_name", sa.String(200), nullable=True),
    )
    op.create_index("ix_ksic_io_mappings_io_code", "ksic_io_mappings", ["io_code"])
    op.create_index("ix_ksic_io_mappings_ksic_code", "ksic_io_mappings", ["ksic_code"])

    # ── io_transactions ───────────────────────────────────
    op.create_table(
        "io_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_io_code", sa.String(20), nullable=False),
        sa.Column("source_io_name", sa.String(200), nullable=True),
        sa.Column("target_io_code", sa.String(20), nullable=False),
        sa.Column("target_io_name", sa.String(200), nullable=True),
        sa.Column("transaction_value", sa.Numeric(20, 2), nullable=False),
    )
    op.create_index("ix_io_transactions_source_io_code", "io_transactions", ["source_io_code"])
    op.create_index("ix_io_transactions_target_io_code", "io_transactions", ["target_io_code"])


def downgrade() -> None:
    op.drop_index("ix_io_transactions_target_io_code")
    op.drop_index("ix_io_transactions_source_io_code")
    op.drop_table("io_transactions")

    op.drop_index("ix_ksic_io_mappings_ksic_code")
    op.drop_index("ix_ksic_io_mappings_io_code")
    op.drop_table("ksic_io_mappings")

    op.drop_index("ix_si_companies_company_name")
    op.drop_table("si_companies")
