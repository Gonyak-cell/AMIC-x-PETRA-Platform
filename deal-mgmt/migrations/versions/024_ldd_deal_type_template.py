"""LDD 거래유형별 템플릿 시스템 — deal_type, template_type 컬럼 추가.

Revision ID: 024
Revises: 023_ldd_multi_llm
"""

from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023_ldd_multi_llm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ldd_reports",
        sa.Column("deal_type", sa.String(50), nullable=True, comment="거래유형 (STOCK_ACQUISITION 등)"),
    )
    op.add_column(
        "ldd_reports",
        sa.Column("template_type", sa.String(50), nullable=True, comment="적용된 템플릿 식별자"),
    )
    op.create_index("ix_ldd_reports_deal_type", "ldd_reports", ["deal_type"])


def downgrade() -> None:
    op.drop_index("ix_ldd_reports_deal_type", table_name="ldd_reports")
    op.drop_column("ldd_reports", "template_type")
    op.drop_column("ldd_reports", "deal_type")
