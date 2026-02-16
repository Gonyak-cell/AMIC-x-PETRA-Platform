"""Phase 6: Add industry column to deals table.

Revision ID: 008_add_industry
Revises: 007_portal_tables
Create Date: 2026-02-12

Changes:
  - industrytype ENUM 추가 (general, tech, healthcare, manufacturing,
    financial_services, logistics)
  - deals.industry 컬럼 추가 (NOT NULL, default='general')
  - ix_deal_industry 인덱스 추가
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_add_industry"
down_revision: str | None = "007_portal_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create industrytype ENUM ──
    industrytype = postgresql.ENUM(
        "general",
        "tech",
        "healthcare",
        "manufacturing",
        "financial_services",
        "logistics",
        name="industrytype",
        create_type=False,
    )
    industrytype.create(op.get_bind(), checkfirst=True)

    # ── 2. Add industry column to deals ──
    op.add_column(
        "deal",
        sa.Column(
            "industry",
            industrytype,
            nullable=False,
            server_default="general",
        ),
    )

    # ── 3. Create index ──
    op.create_index("ix_deal_industry", "deal", ["industry"])


def downgrade() -> None:
    op.drop_index("ix_deal_industry", table_name="deal")
    op.drop_column("deal", "industry")
    op.execute("DROP TYPE IF EXISTS industrytype")
