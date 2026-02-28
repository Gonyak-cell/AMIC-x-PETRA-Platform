"""매수자 Tier 분류 + 마케팅 활동 로그 테이블 추가.

- buyer_candidates: tier (TIER_1/2/3/NOT_TARGET), corp_code 컬럼 추가
- buyer_marketing_logs: Short-List 6단계 마케팅 활동 로그 테이블 신규 생성
- VdrFolderCategory enum에 MARKET_RESEARCH 추가
- AttachmentEntityType enum에 MARKETING_LOG 추가

Revision ID: 041
Revises: 040
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. BuyerTier enum 생성
    buyer_tier = sa.Enum(
        "TIER_1", "TIER_2", "TIER_3", "NOT_TARGET",
        name="buyertier",
    )
    buyer_tier.create(op.get_bind(), checkfirst=True)

    # 2. MarketingStage enum 생성
    marketing_stage = sa.Enum(
        "IDENTIFIED", "EMAIL_SENT", "PHONE_CALL",
        "ADVISOR_MEETING", "NDA_SIGNED", "TARGET_MEETING",
        name="marketingstage",
    )
    marketing_stage.create(op.get_bind(), checkfirst=True)

    # 3. buyer_candidates 테이블에 컬럼 추가
    op.add_column(
        "buyer_candidates",
        sa.Column("tier", sa.Enum(
            "TIER_1", "TIER_2", "TIER_3", "NOT_TARGET",
            name="buyertier", create_type=False,
        ), nullable=True),
    )
    op.add_column(
        "buyer_candidates",
        sa.Column("corp_code", sa.String(8), nullable=True),
    )

    # 4. buyer_marketing_logs 테이블 생성
    op.create_table(
        "buyer_marketing_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "buyer_id", sa.Uuid(),
            sa.ForeignKey("buyer_candidates.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "transaction_id", sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("stage", sa.Enum(
            "IDENTIFIED", "EMAIL_SENT", "PHONE_CALL",
            "ADVISOR_MEETING", "NDA_SIGNED", "TARGET_MEETING",
            name="marketingstage", create_type=False,
        ), nullable=False),
        sa.Column("log_date", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 5. VdrFolderCategory enum에 MARKET_RESEARCH 추가
    op.execute("ALTER TYPE vdrfoldercategory ADD VALUE IF NOT EXISTS 'MARKET_RESEARCH'")

    # 6. AttachmentEntityType enum에 MARKETING_LOG 추가
    op.execute("ALTER TYPE attachmententitytype ADD VALUE IF NOT EXISTS 'MARKETING_LOG'")


def downgrade() -> None:
    # buyer_marketing_logs 테이블 삭제
    op.drop_table("buyer_marketing_logs")

    # buyer_candidates 컬럼 제거
    op.drop_column("buyer_candidates", "corp_code")
    op.drop_column("buyer_candidates", "tier")

    # enum 타입 삭제
    sa.Enum(name="marketingstage").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="buyertier").drop(op.get_bind(), checkfirst=True)

    # PostgreSQL enum에서 값 제거는 불가 — downgrade 시 무시
    # MARKET_RESEARCH, MARKETING_LOG 값은 enum에 남음
