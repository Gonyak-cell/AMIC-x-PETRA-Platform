"""재무모델 품질 게이트 컬럼 추가 (quality_status, quality_report).

Revision ID: 084
Revises: 083
Create Date: 2026-03-13
"""

import sqlalchemy as sa
from alembic import op

revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("financial_models", sa.Column("quality_status", sa.String(20), nullable=True))
    op.add_column("financial_models", sa.Column("quality_report", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("financial_models", "quality_report")
    op.drop_column("financial_models", "quality_status")
