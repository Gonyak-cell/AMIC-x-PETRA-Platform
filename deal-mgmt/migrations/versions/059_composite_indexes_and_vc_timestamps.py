"""059 — 복합 인덱스 추가 + vc_companies 타임스탬프 컬럼

vc_companies에 created_at/updated_at 추가 (TimestampMixin 반영).
vc_industry_coefficients에 복합 인덱스 2개 추가 (source+coefficient, target+coefficient).
vc_companies에 복합 인덱스 3개 추가 (industry_name+revenue, io_sector_name+revenue, io_sector_name).

Revision ID: 059
Revises: 058
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "059"
down_revision: str = "058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- vc_companies: 타임스탬프 컬럼 추가 ---
    op.add_column(
        "vc_companies",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column(
        "vc_companies",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # PostgreSQL: 트랜잭션 종료 후 CONCURRENTLY 인덱스 생성 (non-blocking)
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    if is_pg:
        bind.execute(sa.text("COMMIT"))

    # --- vc_companies: 복합 인덱스 ---
    op.create_index(
        "ix_vc_companies_industry_revenue",
        "vc_companies",
        ["industry_name", "revenue"],
        postgresql_concurrently=is_pg,
    )
    op.create_index(
        "ix_vc_companies_io_sector_name_revenue",
        "vc_companies",
        ["io_sector_name", "revenue"],
        postgresql_concurrently=is_pg,
    )
    op.create_index(
        "ix_vc_companies_io_sector_name",
        "vc_companies",
        ["io_sector_name"],
        postgresql_concurrently=is_pg,
    )

    # --- vc_industry_coefficients: 복합 인덱스 ---
    op.create_index(
        "ix_vc_coeff_source_value",
        "vc_industry_coefficients",
        ["source_industry", "coefficient"],
        postgresql_concurrently=is_pg,
    )
    op.create_index(
        "ix_vc_coeff_target_value",
        "vc_industry_coefficients",
        ["target_industry", "coefficient"],
        postgresql_concurrently=is_pg,
    )


def downgrade() -> None:
    # --- vc_industry_coefficients: 복합 인덱스 제거 ---
    op.drop_index("ix_vc_coeff_target_value", table_name="vc_industry_coefficients")
    op.drop_index("ix_vc_coeff_source_value", table_name="vc_industry_coefficients")

    # --- vc_companies: 복합 인덱스 제거 ---
    op.drop_index("ix_vc_companies_io_sector_name", table_name="vc_companies")
    op.drop_index("ix_vc_companies_io_sector_name_revenue", table_name="vc_companies")
    op.drop_index("ix_vc_companies_industry_revenue", table_name="vc_companies")

    # --- vc_companies: 타임스탬프 컬럼 제거 ---
    op.drop_column("vc_companies", "updated_at")
    op.drop_column("vc_companies", "created_at")
