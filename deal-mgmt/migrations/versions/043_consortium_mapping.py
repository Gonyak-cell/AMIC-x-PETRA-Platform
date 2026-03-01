"""컨소시엄/공동투자 매핑 테이블 + deal_role + created_by_email.

- DealRole enum 생성 (SOLE_BUYER / CONSORTIUM_LEAD / CO_INVESTOR / FINANCING_PROVIDER)
- ConsortiumStatus enum 생성 (TAPPING / CONFIRMED / DROPPED)
- buyer_candidates.deal_role 컬럼 추가
- buyer_marketing_logs.created_by_email 컬럼 추가
- consortium_mappings 테이블 신규 생성

Revision ID: 043
Revises: 042
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. DealRole enum 생성
    deal_role_enum = sa.Enum(
        "SOLE_BUYER",
        "CONSORTIUM_LEAD",
        "CO_INVESTOR",
        "FINANCING_PROVIDER",
        name="dealrole",
    )
    deal_role_enum.create(op.get_bind(), checkfirst=True)

    # 2. ConsortiumStatus enum 생성
    consortium_status_enum = sa.Enum(
        "TAPPING",
        "CONFIRMED",
        "DROPPED",
        name="consortiumstatus",
    )
    consortium_status_enum.create(op.get_bind(), checkfirst=True)

    # 3. buyer_candidates.deal_role 컬럼 추가
    op.add_column(
        "buyer_candidates",
        sa.Column(
            "deal_role",
            sa.Enum(
                "SOLE_BUYER",
                "CONSORTIUM_LEAD",
                "CO_INVESTOR",
                "FINANCING_PROVIDER",
                name="dealrole",
                create_type=False,
            ),
            nullable=True,
        ),
    )

    # 4. buyer_marketing_logs.created_by_email 컬럼 추가
    op.add_column(
        "buyer_marketing_logs",
        sa.Column("created_by_email", sa.String(255), nullable=True),
    )

    # 5. consortium_mappings 테이블 생성
    op.create_table(
        "consortium_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "lead_buyer_id",
            sa.Uuid(),
            sa.ForeignKey("buyer_candidates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "co_investor_buyer_id",
            sa.Uuid(),
            sa.ForeignKey("buyer_candidates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "TAPPING",
                "CONFIRMED",
                "DROPPED",
                name="consortiumstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="TAPPING",
        ),
        sa.Column("equity_share_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "lead_buyer_id != co_investor_buyer_id",
            name="ck_no_self_consortium",
        ),
        sa.CheckConstraint(
            "equity_share_pct >= 0 AND equity_share_pct <= 100",
            name="ck_equity_share_range",
        ),
        sa.UniqueConstraint(
            "transaction_id",
            "lead_buyer_id",
            "co_investor_buyer_id",
            name="uq_consortium_pair_per_txn",
        ),
    )


def downgrade() -> None:
    # consortium_mappings 테이블 삭제
    op.drop_table("consortium_mappings")

    # buyer_marketing_logs.created_by_email 제거
    op.drop_column("buyer_marketing_logs", "created_by_email")

    # buyer_candidates.deal_role 제거
    op.drop_column("buyer_candidates", "deal_role")

    # enum 타입 삭제 (생성 역순: dealrole → consortiumstatus)
    sa.Enum(name="dealrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="consortiumstatus").drop(op.get_bind(), checkfirst=True)
