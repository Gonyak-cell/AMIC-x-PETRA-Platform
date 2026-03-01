"""TransactionPhase 7→9단계 재구성.

- BIDDING_DD → BIDDING 변경
- MOU_SIGNED, MAIN_DUE_DILIGENCE 신규 추가
- 기존 BIDDING_DD 데이터를 BIDDING으로 마이그레이션

Revision ID: 046
Revises: 045
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # PostgreSQL: ALTER TYPE ADD VALUE는 트랜잭션 내에서 새 값을 즉시 사용 불가.
        # autocommit_block()으로 DDL을 독립 트랜잭션에서 실행한 뒤,
        # 후속 DML(UPDATE)은 Alembic 트랜잭션에서 안전하게 실행한다.
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE transactionphase ADD VALUE IF NOT EXISTS 'BIDDING'"))
            op.execute(sa.text("ALTER TYPE transactionphase ADD VALUE IF NOT EXISTS 'MOU_SIGNED'"))
            op.execute(sa.text("ALTER TYPE transactionphase ADD VALUE IF NOT EXISTS 'MAIN_DUE_DILIGENCE'"))

        # 데이터 마이그레이션: BIDDING_DD → BIDDING (멱등 — 재실행 안전)
        op.execute(sa.text("UPDATE transactions SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'"))
    else:
        # SQLite: VARCHAR이므로 직접 UPDATE
        op.execute(sa.text("UPDATE transactions SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'"))


def downgrade() -> None:
    # ⚠️ 데이터 유실 경고: MOU_SIGNED/MAIN_DUE_DILIGENCE 상태의 거래는
    # NEGOTIATION으로 폴백되며, 원래 단계 정보가 소실됩니다.
    #
    # PostgreSQL enum 참고: ALTER TYPE ADD VALUE로 추가된 값은 제거 불가하므로,
    # BIDDING_DD, BIDDING, MOU_SIGNED, MAIN_DUE_DILIGENCE 모두 enum에 잔존합니다.
    # 따라서 아래 UPDATE 문은 PostgreSQL/SQLite 모두에서 안전하게 실행됩니다.
    bind = op.get_bind()
    count = bind.execute(
        sa.text("SELECT COUNT(*) FROM transactions WHERE phase IN ('MOU_SIGNED', 'MAIN_DUE_DILIGENCE')")
    ).scalar()
    if count and count > 0:
        raise RuntimeError(
            f"ROLLBACK BLOCKED: {count}건의 거래가 MOU_SIGNED/MAIN_DUE_DILIGENCE 상태입니다. "
            "수동 데이터 처리 후 재실행하십시오. "
            "확인: SELECT phase, COUNT(*) FROM transactions "
            "WHERE phase IN ('MOU_SIGNED','MAIN_DUE_DILIGENCE') GROUP BY phase;"
        )
    op.execute(
        sa.text("UPDATE transactions SET phase = 'NEGOTIATION' WHERE phase IN ('MOU_SIGNED', 'MAIN_DUE_DILIGENCE')")
    )
    # BIDDING → BIDDING_DD 복원
    op.execute(sa.text("UPDATE transactions SET phase = 'BIDDING_DD' WHERE phase = 'BIDDING'"))
