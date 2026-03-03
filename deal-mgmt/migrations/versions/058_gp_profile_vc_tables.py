"""058 — GP 프로필 + ValueChain 기업/계수 테이블 생성

MA_GP_v3.xlsx(358 GP)와 MA_ValueChain_v7.xlsx(114,964 기업, 1,574×1,574 계수표)
데이터를 수용하기 위한 3개 신규 테이블.

Revision ID: 058
Revises: 057
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "058"
down_revision: str = "057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- gp_profiles ---
    op.create_table(
        "gp_profiles",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("raw_name", sa.String(300), nullable=False),
        sa.Column("normalized_name", sa.String(300), nullable=False),
        sa.Column("min_committed_capital", sa.Numeric(20, 4), nullable=True),
        sa.Column("min_threshold", sa.Numeric(20, 4), nullable=True),
        sa.Column("max_committed_capital", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_pef_count", sa.Integer(), nullable=True),
        sa.Column("recent_pef_count", sa.Integer(), nullable=True),
        sa.Column("recent_committed_sum", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_committed_sum", sa.Numeric(20, 4), nullable=True),
        sa.Column("pef_count_2021", sa.Integer(), nullable=True),
        sa.Column("pef_count_2022", sa.Integer(), nullable=True),
        sa.Column("pef_count_2023", sa.Integer(), nullable=True),
        sa.Column("pef_count_2024", sa.Integer(), nullable=True),
        sa.Column("portfolio_sectors", sa.JSON(), nullable=True),
        sa.Column("portfolio_companies", sa.JSON(), nullable=True),
        sa.Column("portfolio_raw", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_name"),
    )
    op.create_index("ix_gp_profiles_normalized_name", "gp_profiles", ["normalized_name"])
    op.create_index("ix_gp_profiles_min_threshold", "gp_profiles", ["min_threshold"])

    # --- vc_industry_coefficients ---
    op.create_table(
        "vc_industry_coefficients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_industry", sa.String(300), nullable=False),
        sa.Column("target_industry", sa.String(300), nullable=False),
        sa.Column("coefficient", sa.Numeric(10, 6), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_industry", "target_industry", name="uq_vc_coeff_src_tgt"),
    )
    op.create_index("ix_vc_coeff_source", "vc_industry_coefficients", ["source_industry"])
    op.create_index("ix_vc_coeff_target", "vc_industry_coefficients", ["target_industry"])
    op.create_index("ix_vc_coeff_value", "vc_industry_coefficients", ["coefficient"])

    # --- vc_companies ---
    op.create_table(
        "vc_companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_name", sa.String(300), nullable=False),
        sa.Column("english_name", sa.String(300), nullable=True),
        sa.Column("disclosure_name", sa.String(300), nullable=True),
        sa.Column("listing_code", sa.String(20), nullable=True),
        sa.Column("ceo_name", sa.String(200), nullable=True),
        sa.Column("corp_type", sa.String(50), nullable=True),
        sa.Column("corp_reg_no", sa.String(20), nullable=True),
        sa.Column("biz_reg_no", sa.String(20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("homepage", sa.String(300), nullable=True),
        sa.Column("industry_name", sa.String(300), nullable=False),
        sa.Column("io_sector_code", sa.Integer(), nullable=True),
        sa.Column("io_sector_name", sa.String(200), nullable=True),
        sa.Column("founded_date", sa.String(10), nullable=True),
        sa.Column("fiscal_month", sa.String(5), nullable=True),
        sa.Column("corp_code", sa.String(10), nullable=True),
        sa.Column("revenue", sa.Numeric(20, 2), nullable=True),
        sa.Column("revenue_year", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vc_companies_industry", "vc_companies", ["industry_name"])
    op.create_index("ix_vc_companies_io_sector", "vc_companies", ["io_sector_code"])
    op.create_index("ix_vc_companies_revenue", "vc_companies", ["revenue"])
    op.create_index("ix_vc_companies_name", "vc_companies", ["company_name"])


def downgrade() -> None:
    op.drop_table("vc_companies")
    op.drop_table("vc_industry_coefficients")
    op.drop_table("gp_profiles")
