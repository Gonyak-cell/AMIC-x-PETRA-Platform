"""Sprint 16: Add entity (multi-entity) and exchange_rate (multi-currency) tables.

Revision ID: 006_entity_fx
Revises: 005_workflow_vdr_rv
Create Date: 2026-02-10

New tables:
  - entity — 딜 하위 법인 (TARGET/SUBSIDIARY/SPV/CONSOLIDATED)
  - exchange_rate — 딜별 환율 (CLOSING/AVERAGE/HISTORICAL)

New columns (all nullable for backward compatibility):
  - journal_entry.entity_id (FK entity.id SET NULL)
  - upload_file.entity_id (FK entity.id SET NULL)
  - account_mapping.entity_id (FK entity.id SET NULL)
  - nwc_calculation.entity_id (FK entity.id SET NULL)
  - qoe_calculation.entity_id (FK entity.id SET NULL)
  - net_debt_calculation.entity_id (FK entity.id SET NULL)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_entity_fx"
down_revision: str | None = "005_workflow_vdr_rv"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Entity table ──────────────────────────────────────
    op.create_table(
        "entity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entity.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "entity_type",
            sa.String(20),
            nullable=False,
            server_default="TARGET",
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column(
            "functional_currency",
            sa.String(10),
            nullable=False,
            server_default="KRW",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ownership_pct", sa.Numeric(7, 4), nullable=True),
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
    )
    op.create_index("ix_entity_deal", "entity", ["deal_id"])
    op.create_unique_constraint("uq_entity_deal_code", "entity", ["deal_id", "code"])

    # ── 2. Exchange rate table ───────────────────────────────
    op.create_table(
        "exchange_rate",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_currency", sa.String(10), nullable=False),
        sa.Column("to_currency", sa.String(10), nullable=False),
        sa.Column("rate_type", sa.String(20), nullable=False),
        sa.Column("rate", sa.Numeric(18, 4), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("period_key", sa.String(7), nullable=True),
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column(
            "created_by", sa.String(100), nullable=False, server_default="system"
        ),
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
    )
    op.create_index("ix_exchange_rate_deal", "exchange_rate", ["deal_id"])
    op.create_unique_constraint(
        "uq_exchange_rate",
        "exchange_rate",
        ["deal_id", "from_currency", "to_currency", "rate_type", "effective_date"],
    )

    # ── 3. Add entity_id FK to existing tables ───────────────
    for table in [
        "journal_entry",
        "upload_file",
        "account_mapping",
        "nwc_calculation",
        "qoe_calculation",
        "net_debt_calculation",
    ]:
        op.add_column(
            table,
            sa.Column(
                "entity_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            f"fk_{table}_entity_id",
            table,
            "entity",
            ["entity_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Index on journal_entry.entity_id (high-volume table)
    op.create_index("ix_journal_entry_entity", "journal_entry", ["entity_id"])


def downgrade() -> None:
    # Drop entity_id FK + column from all tables
    for table in [
        "net_debt_calculation",
        "qoe_calculation",
        "nwc_calculation",
        "account_mapping",
        "upload_file",
        "journal_entry",
    ]:
        op.drop_constraint(f"fk_{table}_entity_id", table, type_="foreignkey")
        op.drop_column(table, "entity_id")

    op.drop_index("ix_journal_entry_entity", table_name="journal_entry")
    op.drop_table("exchange_rate")
    op.drop_table("entity")
