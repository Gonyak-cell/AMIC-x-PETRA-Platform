"""LDD 별첨(Appendix) — appendices JSONB 컬럼 추가.

Revision ID: 027
Revises: 026
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ldd_reports",
        sa.Column("appendices", JSONB, nullable=True, comment="별첨 테이블 데이터 (6종: 소송/IP/부동산/계약/보험/인허가)"),
    )


def downgrade() -> None:
    op.drop_column("ldd_reports", "appendices")
