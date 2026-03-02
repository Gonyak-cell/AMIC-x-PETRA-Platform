"""011: Ralph Loop 세션 테이블 추가.

Revision ID: 011_ralph_sessions
Revises: 010_ldd_reports
Create Date: 2026-02-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB as _JSONB

_JSON = sa.JSON().with_variant(_JSONB, "postgresql")

revision = "011_ralph_sessions"
down_revision = "010_ldd_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ralph_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        # 문서 유형 및 상태
        sa.Column("doc_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNING"),
        # JSONB 상태
        sa.Column("prd", _JSON, nullable=True),
        sa.Column("progress", _JSON, nullable=True),
        sa.Column("config", _JSON, nullable=True),
        # 결과 집계
        sa.Column("total_iterations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("final_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("section_scores", _JSON, nullable=True),
        # 출력 파일
        sa.Column("output_path", sa.String(500), nullable=True),
        sa.Column("output_file_name", sa.String(300), nullable=True),
        sa.Column("output_file_size", sa.Integer, nullable=True),
        # 에러/플래그
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("critical_flags", _JSON, nullable=True),
        # 요청자
        sa.Column("created_by_email", sa.String(255), nullable=True),
        # 타임스탬프
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("ralph_sessions")
