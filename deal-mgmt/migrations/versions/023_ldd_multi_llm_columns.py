"""023: LDD 멀티 LLM 파이프라인 결과 저장용 JSONB 컬럼 추가.

Revision ID: 023_ldd_multi_llm
Revises: 022_rfi_uq
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "023_ldd_multi_llm"
down_revision = "022_rfi_uq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ldd_reports", sa.Column("dual_risk_summary", JSONB, nullable=True))
    op.add_column("ldd_reports", sa.Column("gap_detection", JSONB, nullable=True))
    op.add_column("ldd_reports", sa.Column("jurisdiction_analysis", JSONB, nullable=True))
    op.add_column("ldd_reports", sa.Column("qa_result", JSONB, nullable=True))
    op.add_column("ldd_reports", sa.Column("pipeline_stages", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("ldd_reports", "pipeline_stages")
    op.drop_column("ldd_reports", "qa_result")
    op.drop_column("ldd_reports", "jurisdiction_analysis")
    op.drop_column("ldd_reports", "gap_detection")
    op.drop_column("ldd_reports", "dual_risk_summary")
