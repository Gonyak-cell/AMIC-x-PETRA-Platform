"""060 — gp_profiles에 yearly_pef_counts JSON 컬럼 추가

Sheet 3 '연도별 활동 매트릭스' 데이터 (2010~2024)를 저장하기 위한 JSON 컬럼.
기존 pef_count_2021~2024 개별 컬럼 외에, 전체 연도 이력을 {연도: 건수} 형태로 저장.

Revision ID: 060
Revises: 059
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "060"
down_revision: str = "059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gp_profiles",
        sa.Column("yearly_pef_counts", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gp_profiles", "yearly_pef_counts")
