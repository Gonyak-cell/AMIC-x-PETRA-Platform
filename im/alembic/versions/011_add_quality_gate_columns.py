"""IM 문서 품질 게이트 컬럼 추가.

quality_score, quality_status, quality_issues, slide_count,
generation_profile, supported_formats를 documents 테이블에 추가한다.
기존 COMPLETED 행은 LEGACY_UNVERIFIED로 마킹한다.

Revision ID: 011_add_quality_gate_columns
Revises: 010_add_awaiting_upload_status
Create Date: 2026-03-13
"""

import sqlalchemy as sa
from alembic import op

revision = "011_add_quality_gate_columns"
down_revision = "010_add_awaiting_upload_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column(
        "documents", sa.Column("quality_status", sa.String(20), nullable=True)
    )
    op.add_column("documents", sa.Column("quality_issues", sa.JSON(), nullable=True))
    op.add_column("documents", sa.Column("slide_count", sa.Integer(), nullable=True))
    op.add_column(
        "documents", sa.Column("generation_profile", sa.String(20), nullable=True)
    )
    op.add_column("documents", sa.Column("supported_formats", sa.JSON(), nullable=True))

    # 기존 COMPLETED 행에 LEGACY_UNVERIFIED 마킹
    op.execute(
        "UPDATE documents SET quality_status = 'LEGACY_UNVERIFIED' "
        "WHERE status = 'COMPLETED' AND quality_status IS NULL"
    )


def downgrade() -> None:
    op.drop_column("documents", "supported_formats")
    op.drop_column("documents", "generation_profile")
    op.drop_column("documents", "slide_count")
    op.drop_column("documents", "quality_issues")
    op.drop_column("documents", "quality_status")
    op.drop_column("documents", "quality_score")
