"""Phase 2 — ndas, bids, dd_checklists tables

Revision ID: 002_phase2
Revises: 001_initial
Create Date: 2026-02-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_phase2"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ──
    nda_type = sa.Enum("ONE_WAY", "MUTUAL", name="ndatype")
    nda_status = sa.Enum("DRAFT", "SENT", "SIGNED", "EXPIRED", "REJECTED", name="ndastatus")
    bid_type = sa.Enum("IOI", "LOI", "FINAL_OFFER", name="bidtype")
    bid_status = sa.Enum(
        "SUBMITTED", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN", "EXPIRED",
        name="bidstatus",
    )
    valuation_method = sa.Enum(
        "EV_EBITDA", "EV_REVENUE", "PRICE_BOOK", "DCF", "COMPARABLE", "OTHER",
        name="valuationmethod",
    )
    dd_workstream = sa.Enum(
        "FINANCIAL", "LEGAL", "TAX", "COMMERCIAL", "IT", "HR",
        "ENVIRONMENTAL", "INSURANCE", "OTHER",
        name="ddworkstream",
    )
    dd_checklist_status = sa.Enum(
        "NOT_STARTED", "IN_PROGRESS", "COMPLETED", "NOT_APPLICABLE",
        name="ddcheckliststatus",
    )

    # ── ndas ──
    op.create_table(
        "ndas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "buyer_candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buyer_candidates.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("nda_type", nda_type, nullable=False, server_default="MUTUAL"),
        sa.Column("status", nda_status, nullable=False, server_default="DRAFT"),
        sa.Column("sent_at", sa.String(10), nullable=True),
        sa.Column("signed_at", sa.String(10), nullable=True),
        sa.Column("expires_at", sa.String(10), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── bids ──
    op.create_table(
        "bids",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "buyer_candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buyer_candidates.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("bid_type", bid_type, nullable=False),
        sa.Column("status", bid_status, nullable=False, server_default="SUBMITTED"),
        sa.Column("amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KRW"),
        sa.Column("valuation_method", valuation_method, nullable=True),
        sa.Column("multiple", sa.Numeric(10, 2), nullable=True),
        sa.Column("submitted_at", sa.String(10), nullable=True),
        sa.Column("valid_until", sa.String(10), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── dd_checklists ──
    op.create_table(
        "dd_checklists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("workstream", dd_workstream, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assignee_email", sa.String(255), nullable=True),
        sa.Column("status", dd_checklist_status, nullable=False, server_default="NOT_STARTED"),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("dd_checklists")
    op.drop_table("bids")
    op.drop_table("ndas")

    for name in [
        "ddcheckliststatus", "ddworkstream", "valuationmethod",
        "bidstatus", "bidtype", "ndastatus", "ndatype",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
