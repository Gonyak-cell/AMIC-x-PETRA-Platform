"""Buyer tiering and marketing log schema updates.

Revision ID: 041
Revises: 040
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


BUYER_TIER_VALUES = ("TIER_1", "TIER_2", "TIER_3", "NOT_TARGET")
MARKETING_STAGE_VALUES = (
    "IDENTIFIED",
    "EMAIL_SENT",
    "PHONE_CALL",
    "ADVISOR_MEETING",
    "NDA_SIGNED",
    "TARGET_MEETING",
)


def _build_enum(name: str, values: tuple[str, ...], *, postgres: bool) -> sa.Enum:
    if postgres:
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    if is_postgresql:
        buyer_tier_values = ", ".join(f"'{value}'" for value in BUYER_TIER_VALUES)
        marketing_stage_values = ", ".join(f"'{value}'" for value in MARKETING_STAGE_VALUES)
        op.execute(
            f"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'buyertier') THEN
                    CREATE TYPE buyertier AS ENUM ({buyer_tier_values});
                END IF;
            END $$;
            """
        )
        op.execute(
            f"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'marketingstage') THEN
                    CREATE TYPE marketingstage AS ENUM ({marketing_stage_values});
                END IF;
            END $$;
            """
        )

    buyer_tier = _build_enum("buyertier", BUYER_TIER_VALUES, postgres=is_postgresql)
    marketing_stage = _build_enum(
        "marketingstage",
        MARKETING_STAGE_VALUES,
        postgres=is_postgresql,
    )

    op.add_column("buyer_candidates", sa.Column("tier", buyer_tier, nullable=True))
    op.add_column("buyer_candidates", sa.Column("corp_code", sa.String(8), nullable=True))

    op.create_table(
        "buyer_marketing_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "buyer_id",
            sa.Uuid(),
            sa.ForeignKey("buyer_candidates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("stage", marketing_stage, nullable=False),
        sa.Column("log_date", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    if is_postgresql:
        op.execute("ALTER TYPE vdrfoldercategory ADD VALUE IF NOT EXISTS 'MARKET_RESEARCH'")
        op.execute(
            """
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attachmententitytype') THEN
                    ALTER TYPE attachmententitytype ADD VALUE IF NOT EXISTS 'MARKETING_LOG';
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    op.drop_table("buyer_marketing_logs")
    op.drop_column("buyer_candidates", "corp_code")
    op.drop_column("buyer_candidates", "tier")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS marketingstage")
        op.execute("DROP TYPE IF EXISTS buyertier")
