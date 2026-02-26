"""LDD 6블록 서술(Narrative) 데이터 — narrative_sections JSONB 컬럼 추가.

Revision ID: 025
Revises: 024
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ldd_reports",
        sa.Column("narrative_sections", JSONB, nullable=True, comment="6블록 서술 결과 (section_type → [NarrativeResult])"),
    )


def downgrade() -> None:
    op.drop_column("ldd_reports", "narrative_sections")
