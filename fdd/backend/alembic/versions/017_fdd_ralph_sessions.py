"""FDD Ralph Loop 세션 테이블.

Revision ID: 017_fdd_ralph_sessions
Revises: 016
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "017_fdd_ralph_sessions"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fdd_ralph_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deal.id"), nullable=False),
        sa.Column("pass_type", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("checklist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prd", postgresql.JSONB, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("progress", postgresql.JSONB, nullable=True),
        sa.Column("total_iterations", sa.Integer, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, server_default="0.0"),
        sa.Column("final_score", sa.Float, server_default="0.0"),
        sa.Column("section_scores", postgresql.JSONB, nullable=True),
        sa.Column("refined_ir", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("critical_flags", postgresql.JSONB, nullable=True),
        sa.Column("learned_patterns", postgresql.JSONB, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fdd_ralph_sessions_deal_id", "fdd_ralph_sessions", ["deal_id"])
    op.create_index("ix_fdd_ralph_sessions_status", "fdd_ralph_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_fdd_ralph_sessions_status")
    op.drop_index("ix_fdd_ralph_sessions_deal_id")
    op.drop_table("fdd_ralph_sessions")
