"""065 — transactions 테이블에 deal_type 컬럼 추가

거래 유형 분류 (MA/PE/RE/IB)를 명시적으로 관리하고
코드명 자동 생성 시 접두사로 사용한다.

Revision ID: 065
Revises: 064
"""

import sqlalchemy as sa
from alembic import op

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE dealtype AS ENUM ('MA', 'PE', 'RE', 'IB')")
    op.add_column(
        "transactions",
        sa.Column(
            "deal_type",
            sa.Enum("MA", "PE", "RE", "IB", name="dealtype", create_type=False),
            nullable=False,
            server_default="MA",
            comment="거래 유형 (코드명 접두사 기준)",
        ),
    )


def downgrade() -> None:
    op.drop_column("transactions", "deal_type")
    op.execute("DROP TYPE IF EXISTS dealtype")
