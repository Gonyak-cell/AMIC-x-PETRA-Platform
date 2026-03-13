"""마케팅 자료 품질 검증 컬럼 추가 (quality_score, quality_status, quality_issues, slide_count).

Revision ID: 083
Revises: 082
Create Date: 2026-03-13
"""

import sqlalchemy as sa
from alembic import op

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("marketing_materials", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("marketing_materials", sa.Column("quality_status", sa.String(20), nullable=True))
    op.add_column("marketing_materials", sa.Column("quality_issues", sa.JSON(), nullable=True))
    op.add_column("marketing_materials", sa.Column("slide_count", sa.Integer(), nullable=True))

    # 기존 READY 행에 LEGACY_UNVERIFIED 마킹
    op.execute(
        "UPDATE marketing_materials SET quality_status = 'LEGACY_UNVERIFIED' "
        "WHERE status = 'READY' AND quality_status IS NULL"
    )


def downgrade() -> None:
    op.drop_column("marketing_materials", "slide_count")
    op.drop_column("marketing_materials", "quality_issues")
    op.drop_column("marketing_materials", "quality_status")
    op.drop_column("marketing_materials", "quality_score")
