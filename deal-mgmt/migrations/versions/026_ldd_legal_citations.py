"""LDD 법률 인용 검증 결과 — legal_citations JSONB 컬럼 추가.

Revision ID: 026
Revises: 025
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ldd_reports",
        sa.Column("legal_citations", JSONB, nullable=True, comment="법률 인용 검증 결과 (section_type → citation_verification)"),
    )


def downgrade() -> None:
    op.drop_column("ldd_reports", "legal_citations")
