"""Consortium mapping schema updates.

Revision ID: 043
Revises: 042
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


DEAL_ROLE_VALUES = (
    "SOLE_BUYER",
    "CONSORTIUM_LEAD",
    "CO_INVESTOR",
    "FINANCING_PROVIDER",
)
CONSORTIUM_STATUS_VALUES = ("TAPPING", "CONFIRMED", "DROPPED")


def _build_enum(name: str, values: tuple[str, ...], *, postgres: bool) -> sa.Enum:
    if postgres:
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _ensure_postgres_enum(name: str, values: tuple[str, ...]) -> None:
    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                CREATE TYPE {name} AS ENUM ({values_sql});
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    if is_postgresql:
        _ensure_postgres_enum("dealrole", DEAL_ROLE_VALUES)
        _ensure_postgres_enum("consortiumstatus", CONSORTIUM_STATUS_VALUES)

    deal_role_enum = _build_enum("dealrole", DEAL_ROLE_VALUES, postgres=is_postgresql)
    consortium_status_enum = _build_enum(
        "consortiumstatus",
        CONSORTIUM_STATUS_VALUES,
        postgres=is_postgresql,
    )

    op.add_column("buyer_candidates", sa.Column("deal_role", deal_role_enum, nullable=True))
    op.add_column(
        "buyer_marketing_logs",
        sa.Column("created_by_email", sa.String(255), nullable=True),
    )

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
            consortium_status_enum,
            nullable=False,
            server_default="TAPPING",
        ),
        sa.Column("equity_share_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
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
    op.drop_table("consortium_mappings")
    op.drop_column("buyer_marketing_logs", "created_by_email")
    op.drop_column("buyer_candidates", "deal_role")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS consortiumstatus")
        op.execute("DROP TYPE IF EXISTS dealrole")
