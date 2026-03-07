"""073 — nda_markups 테이블 생성

NDA 문서 버전 관리 (트랙 체인지) 지원.
일자별 버전 추적 + Redline 메타데이터 저장.

Revision ID: 073
Revises: 072
Create Date: 2026-03-07
"""

import sqlalchemy as sa
from alembic import op

revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nda_markups",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("nda_id", sa.Uuid(), sa.ForeignKey("ndas.id", ondelete="CASCADE"), nullable=False),
        # 버전 관리
        sa.Column("version_label", sa.String(100), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_date", sa.String(10), nullable=False),
        sa.Column("source_party", sa.String(200), nullable=True),
        sa.Column("markup_type", sa.String(20), nullable=True),
        # 파일
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        # 변경 요약
        sa.Column("changes_summary", sa.Text(), nullable=True),
        sa.Column("key_changes", sa.JSON(), nullable=True),
        # Redline 메타데이터
        sa.Column("redline_file_path", sa.String(500), nullable=True),
        sa.Column("redline_issues_count", sa.Integer(), nullable=True),
        sa.Column(
            "base_version_id",
            sa.Uuid(),
            sa.ForeignKey("nda_markups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        # 타임스탬프
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_nda_markups_nda_id", "nda_markups", ["nda_id"])
    op.create_index("ix_nda_markups_version_date", "nda_markups", ["version_date"])


def downgrade() -> None:
    op.drop_index("ix_nda_markups_version_date", table_name="nda_markups")
    op.drop_index("ix_nda_markups_nda_id", table_name="nda_markups")
    op.drop_table("nda_markups")
