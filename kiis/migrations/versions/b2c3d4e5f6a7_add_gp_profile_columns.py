"""add GP profile columns to companies

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # corp_code: NOT NULL → nullable (비공시 GP 수용)
    with op.batch_alter_table("companies") as batch_op:
        batch_op.alter_column("corp_code", existing_type=sa.String(20), nullable=True)

    # GP 프로파일 컬럼 추가
    op.add_column(
        "companies",
        sa.Column("is_gp", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="GP(사모펀드 운용사) 여부"),
    )
    op.add_column(
        "companies",
        sa.Column("finance_company_code", sa.String(50), nullable=True, comment="금융회사코드 (공공데이터포털)"),
    )
    op.add_column(
        "companies",
        sa.Column("gp_authorization_date", sa.String(10), nullable=True, comment="인가일자"),
    )
    op.add_column(
        "companies",
        sa.Column("gp_aum", sa.Numeric(20, 0), nullable=True, comment="운용자산 AUM (백만원)"),
    )
    op.add_column(
        "companies",
        sa.Column("gp_fund_count", sa.Integer(), nullable=True, comment="운용 펀드수"),
    )
    op.add_column(
        "companies",
        sa.Column("gp_employee_count", sa.Integer(), nullable=True, comment="임직원수"),
    )
    op.add_column(
        "companies",
        sa.Column("gp_strategy_tags", sa.JSON(), nullable=True, comment="전략 태그"),
    )
    op.add_column(
        "companies",
        sa.Column("gp_profile_synced_at", sa.DateTime(timezone=True), nullable=True, comment="GP 프로파일 마지막 동기화 시각"),
    )

    # 인덱스
    op.create_index("ix_companies_is_gp", "companies", ["is_gp"])
    op.create_unique_constraint("uq_companies_finance_company_code", "companies", ["finance_company_code"])


def downgrade() -> None:
    op.drop_constraint("uq_companies_finance_company_code", "companies", type_="unique")
    op.drop_index("ix_companies_is_gp", table_name="companies")

    op.drop_column("companies", "gp_profile_synced_at")
    op.drop_column("companies", "gp_strategy_tags")
    op.drop_column("companies", "gp_employee_count")
    op.drop_column("companies", "gp_fund_count")
    op.drop_column("companies", "gp_aum")
    op.drop_column("companies", "gp_authorization_date")
    op.drop_column("companies", "finance_company_code")
    op.drop_column("companies", "is_gp")

    # corp_code: nullable → NOT NULL 복원
    with op.batch_alter_table("companies") as batch_op:
        batch_op.alter_column("corp_code", existing_type=sa.String(20), nullable=False)
