"""SI 기업 테이블에 revenue_year 컬럼 추가.

매출액(revenue) 수집 시 기준 사업연도를 함께 저장하여
프론트엔드에서 "2024년 1,234억" 형태로 표시할 수 있도록 한다.

Revision ID: 039
Revises: 038
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "si_companies",
        sa.Column(
            "revenue_year",
            sa.Integer(),
            nullable=True,
            comment="매출액 기준 사업연도 (예: 2024)",
        ),
    )


def downgrade() -> None:
    op.drop_column("si_companies", "revenue_year")
