"""012: Ralph Loop Phase 2 — final_artifact, learned_patterns 컬럼 추가.

Revision ID: 012_ralph_phase2
Revises: 011_ralph_sessions
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "012_ralph_phase2"
down_revision = "011_ralph_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ralph_sessions", sa.Column("final_artifact", JSONB, nullable=True))
    op.add_column("ralph_sessions", sa.Column("learned_patterns", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("ralph_sessions", "learned_patterns")
    op.drop_column("ralph_sessions", "final_artifact")
