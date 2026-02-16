"""Add NWC and Net Debt tables.

Revision ID: 002_nwc_debt
Revises: 001_initial
Create Date: 2026-02-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_nwc_debt"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── NWC enums ─────────────────────────────────────────────
    nwcstatus = postgresql.ENUM(
        "DRAFT", "REVIEW", "APPROVED", name="nwcstatus", create_type=False
    )
    nwcstatus.create(op.get_bind(), checkfirst=True)

    nwcclassification = postgresql.ENUM(
        "ABOVE_LINE",
        "BELOW_LINE",
        "EXCLUDED",
        name="nwcclassification",
        create_type=False,
    )
    nwcclassification.create(op.get_bind(), checkfirst=True)

    pegmethod = postgresql.ENUM(
        "LTM_AVERAGE",
        "TTM",
        "LAST_MONTH",
        "MAX",
        "MIN",
        "CUSTOM",
        name="pegmethod",
        create_type=False,
    )
    pegmethod.create(op.get_bind(), checkfirst=True)

    # ── Net Debt enums ────────────────────────────────────────
    debtstatus = postgresql.ENUM(
        "DRAFT", "REVIEW", "APPROVED", name="debtstatus", create_type=False
    )
    debtstatus.create(op.get_bind(), checkfirst=True)

    debtitemtype = postgresql.ENUM(
        "GROSS_DEBT",
        "CASH",
        "DEBT_LIKE",
        "CASH_LIKE",
        name="debtitemtype",
        create_type=False,
    )
    debtitemtype.create(op.get_bind(), checkfirst=True)

    debtitemstatus = postgresql.ENUM(
        "CANDIDATE",
        "PROPOSED",
        "APPROVED",
        "REJECTED",
        name="debtitemstatus",
        create_type=False,
    )
    debtitemstatus.create(op.get_bind(), checkfirst=True)

    # ── 14. nwc_calculation ───────────────────────────────────
    op.create_table(
        "nwc_calculation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal_snapshot.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # NWC Summary
        sa.Column("total_current_assets", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_current_liabilities", sa.Numeric(18, 4), nullable=False),
        sa.Column("net_working_capital", sa.Numeric(18, 4), nullable=False),
        # Peg
        sa.Column(
            "peg_method",
            postgresql.ENUM(
                "LTM_AVERAGE",
                "TTM",
                "LAST_MONTH",
                "MAX",
                "MIN",
                "CUSTOM",
                name="pegmethod",
                create_type=False,
            ),
            nullable=False,
            server_default="LTM_AVERAGE",
        ),
        sa.Column("peg_target", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("peg_delta", sa.Numeric(18, 4), nullable=False, server_default="0"),
        # Monthly Trend
        sa.Column("monthly_trend", postgresql.JSONB(), nullable=False),
        # Category Breakdown
        sa.Column("category_breakdown", postgresql.JSONB(), nullable=False),
        # Metadata
        sa.Column("engine_version", sa.String(20), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DRAFT", "REVIEW", "APPROVED", name="nwcstatus", create_type=False
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_nwc_calculation_deal", "nwc_calculation", ["deal_id"])
    op.create_index("ix_nwc_calculation_snapshot", "nwc_calculation", ["snapshot_id"])

    # ── 15. nwc_line_item ─────────────────────────────────────
    op.create_table(
        "nwc_line_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "nwc_calculation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nwc_calculation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Item Details
        sa.Column("account_code", sa.String(50), nullable=False),
        sa.Column("account_name", sa.String(500), nullable=False),
        sa.Column("line_item_category", sa.String(50), nullable=False),
        sa.Column(
            "classification",
            postgresql.ENUM(
                "ABOVE_LINE",
                "BELOW_LINE",
                "EXCLUDED",
                name="nwcclassification",
                create_type=False,
            ),
            nullable=False,
            server_default="ABOVE_LINE",
        ),
        # Amount
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        # Monthly Amounts
        sa.Column("monthly_amounts", postgresql.JSONB(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_nwc_line_item_calc", "nwc_line_item", ["nwc_calculation_id"])
    op.create_index("ix_nwc_line_item_deal", "nwc_line_item", ["deal_id"])

    # ── 16. net_debt_calculation ──────────────────────────────
    op.create_table(
        "net_debt_calculation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal_snapshot.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Net Debt Summary
        sa.Column("gross_debt", sa.Numeric(18, 4), nullable=False),
        sa.Column("cash_and_equivalents", sa.Numeric(18, 4), nullable=False),
        sa.Column("net_debt", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "debt_like_total", sa.Numeric(18, 4), nullable=False, server_default="0"
        ),
        sa.Column(
            "cash_like_total", sa.Numeric(18, 4), nullable=False, server_default="0"
        ),
        sa.Column("adjusted_net_debt", sa.Numeric(18, 4), nullable=False),
        # Options
        sa.Column(
            "include_lease_liabilities",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "include_deferred_revenue",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        # Balance Check
        sa.Column(
            "balance_check_error", sa.Numeric(18, 4), nullable=False, server_default="0"
        ),
        # Category Breakdown
        sa.Column("category_breakdown", postgresql.JSONB(), nullable=False),
        # Metadata
        sa.Column("engine_version", sa.String(20), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DRAFT", "REVIEW", "APPROVED", name="debtstatus", create_type=False
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_net_debt_calculation_deal", "net_debt_calculation", ["deal_id"])
    op.create_index(
        "ix_net_debt_calculation_snapshot", "net_debt_calculation", ["snapshot_id"]
    )

    # ── 17. debt_item ─────────────────────────────────────────
    op.create_table(
        "debt_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "net_debt_calculation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("net_debt_calculation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Item Details
        sa.Column(
            "item_type",
            postgresql.ENUM(
                "GROSS_DEBT",
                "CASH",
                "DEBT_LIKE",
                "CASH_LIKE",
                name="debtitemtype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        # Source Reference
        sa.Column("source_account_code", sa.String(50), nullable=True),
        sa.Column("source_account_name", sa.String(500), nullable=True),
        # Detection Metadata
        sa.Column(
            "detection_method", sa.String(50), nullable=False, server_default="manual"
        ),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        # Workflow
        sa.Column(
            "status",
            postgresql.ENUM(
                "CANDIDATE",
                "PROPOSED",
                "APPROVED",
                "REJECTED",
                name="debtitemstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="CANDIDATE",
        ),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_debt_item_calc", "debt_item", ["net_debt_calculation_id"])
    op.create_index("ix_debt_item_deal", "debt_item", ["deal_id"])
    op.create_index("ix_debt_item_status", "debt_item", ["status"])


def downgrade() -> None:
    op.drop_table("debt_item")
    op.drop_table("net_debt_calculation")
    op.drop_table("nwc_line_item")
    op.drop_table("nwc_calculation")

    for enum_name in [
        "debtitemstatus",
        "debtitemtype",
        "debtstatus",
        "nwcclassification",
        "pegmethod",
        "nwcstatus",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
