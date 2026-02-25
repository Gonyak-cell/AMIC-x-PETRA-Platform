"""analysis_run에 교차검증 및 QA 결과 컬럼 추가.

Revision ID: 018_add_cross_verification
Revises: 017_fdd_ralph_sessions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018_add_cross_verification"
down_revision = "017_fdd_ralph_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_run",
        sa.Column("cross_verify_summary", postgresql.JSONB, nullable=True,
                   comment="교차검증 결과 요약 JSON"),
    )
    op.add_column(
        "analysis_run",
        sa.Column("qa_result", postgresql.JSONB, nullable=True,
                   comment="레포트 QA 결과 JSON"),
    )


def downgrade() -> None:
    op.drop_column("analysis_run", "qa_result")
    op.drop_column("analysis_run", "cross_verify_summary")
