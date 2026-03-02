"""PEF 총약정액 컬럼 정밀도 확장: NUMERIC(20,2) → NUMERIC(20,4).

소수점 이하 4자리까지 보존하여 FI 추천 비교 정밀도를 개선한다.

Revision ID: 052
Revises: 051
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "052"
down_revision: str = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.alter_column(
            "pef_fund_registry",
            "total_committed_capital",
            type_=sa.Numeric(20, 4),
        )
    # SQLite: NUMERIC은 type affinity → 변경 불필요


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.alter_column(
            "pef_fund_registry",
            "total_committed_capital",
            type_=sa.Numeric(20, 2),
        )
