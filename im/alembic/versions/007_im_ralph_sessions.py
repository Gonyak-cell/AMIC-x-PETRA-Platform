"""add im_ralph_sessions table

Revision ID: 007_im_ralph_sessions
Revises: 006_im_checklists
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB as _JSONB

revision = "007_im_ralph_sessions"
down_revision = "006_im_checklists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "im_ralph_sessions",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pass_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("doc_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNING"),
        sa.Column(
            "prd",
            sa.JSON().with_variant(_JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "progress",
            sa.JSON().with_variant(_JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "config",
            sa.JSON().with_variant(_JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("total_iterations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("final_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "section_scores",
            sa.JSON().with_variant(_JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("output_path", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "critical_flags",
            sa.JSON().with_variant(_JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "learned_patterns",
            sa.JSON().with_variant(_JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("ix_im_ralph_document", "im_ralph_sessions", ["document_id"])
    op.create_index("ix_im_ralph_status", "im_ralph_sessions", ["status"])
    op.create_index(
        "ix_im_ralph_doc_pass", "im_ralph_sessions", ["document_id", "pass_number"]
    )


def downgrade() -> None:
    op.drop_index("ix_im_ralph_doc_pass", table_name="im_ralph_sessions")
    op.drop_index("ix_im_ralph_status", table_name="im_ralph_sessions")
    op.drop_index("ix_im_ralph_document", table_name="im_ralph_sessions")
    op.drop_table("im_ralph_sessions")
