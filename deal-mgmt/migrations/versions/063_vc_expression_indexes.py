"""063 — vc_companies 표현식 인덱스 (PostgreSQL 전용)

func.replace(func.replace(col, '-', ''), ' ', '') 쿼리 패턴에 맞는
표현식 인덱스로 교체하여 114,964건 full-scan 방지.

SQLite(CI)에서는 표현식 인덱스를 지원하지 않으므로 skip.

Revision ID: 063
Revises: 062
"""

from alembic import op

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_vc_companies_corp_reg_no", table_name="vc_companies")
    op.drop_index("ix_vc_companies_biz_reg_no", table_name="vc_companies")
    op.execute(
        "CREATE INDEX ix_vc_companies_corp_reg_no_expr "
        "ON vc_companies (REPLACE(REPLACE(corp_reg_no, '-', ''), ' ', ''))"
    )
    op.execute(
        "CREATE INDEX ix_vc_companies_biz_reg_no_expr ON vc_companies (REPLACE(REPLACE(biz_reg_no, '-', ''), ' ', ''))"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_vc_companies_biz_reg_no_expr", table_name="vc_companies")
    op.drop_index("ix_vc_companies_corp_reg_no_expr", table_name="vc_companies")
    op.create_index("ix_vc_companies_corp_reg_no", "vc_companies", ["corp_reg_no"])
    op.create_index("ix_vc_companies_biz_reg_no", "vc_companies", ["biz_reg_no"])
