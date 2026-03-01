"""TransactionPhase 7→9단계 재구성.

- BIDDING_DD → BIDDING 변경
- MOU_SIGNED, MAIN_DUE_DILIGENCE 신규 추가
- 기존 BIDDING_DD 데이터를 BIDDING으로 마이그레이션

Revision ID: 046
Revises: 045
"""

from __future__ import annotations

from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # PostgreSQL: enum 값 추가 후 데이터 마이그레이션
        op.execute("ALTER TYPE transactionphase ADD VALUE IF NOT EXISTS 'BIDDING'")
        op.execute("ALTER TYPE transactionphase ADD VALUE IF NOT EXISTS 'MOU_SIGNED'")
        op.execute("ALTER TYPE transactionphase ADD VALUE IF NOT EXISTS 'MAIN_DUE_DILIGENCE'")

        # COMMIT 필요 — ALTER TYPE ADD VALUE는 트랜잭션 내에서 즉시 사용 불가
        op.execute("COMMIT")

        # 데이터 마이그레이션: BIDDING_DD → BIDDING
        op.execute(
            "UPDATE transactions SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'"
        )
        op.execute(
            "UPDATE deal_timelines SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'"
        )
    else:
        # SQLite: VARCHAR이므로 직접 UPDATE
        op.execute(
            "UPDATE transactions SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'"
        )
        op.execute(
            "UPDATE deal_timelines SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'"
        )


def downgrade() -> None:
    # BIDDING → BIDDING_DD 복원
    op.execute(
        "UPDATE transactions SET phase = 'BIDDING_DD' WHERE phase = 'BIDDING'"
    )
    op.execute(
        "UPDATE deal_timelines SET phase = 'BIDDING_DD' WHERE phase = 'BIDDING'"
    )
    # MOU_SIGNED, MAIN_DUE_DILIGENCE 데이터가 있으면 NEGOTIATION으로 폴백
    op.execute(
        "UPDATE transactions SET phase = 'NEGOTIATION' "
        "WHERE phase IN ('MOU_SIGNED', 'MAIN_DUE_DILIGENCE')"
    )
    op.execute(
        "UPDATE deal_timelines SET phase = 'NEGOTIATION' "
        "WHERE phase IN ('MOU_SIGNED', 'MAIN_DUE_DILIGENCE')"
    )
