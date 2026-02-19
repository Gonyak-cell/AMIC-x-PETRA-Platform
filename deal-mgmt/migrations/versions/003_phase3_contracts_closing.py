"""Phase 3 — contracts, contract_versions, closing_checklists tables

Revision ID: 003_phase3
Revises: 002_phase2
Create Date: 2026-02-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_phase3"
down_revision: Union[str, None] = "002_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ──
    contract_type = sa.Enum(
        "SPA", "AMENDMENT", "SIDE_LETTER", "SHAREHOLDERS_AGREEMENT", "ESCROW_AGREEMENT", "OTHER",
        name="contracttype",
    )
    contract_status = sa.Enum(
        "DRAFT", "UNDER_REVIEW", "PENDING_SIGNATURE", "PARTIALLY_SIGNED", "FULLY_EXECUTED", "TERMINATED",
        name="contractstatus",
    )
    signature_status = sa.Enum(
        "NOT_REQUIRED", "PENDING", "SIGNED", "DECLINED",
        name="signaturestatus",
    )
    closing_category = sa.Enum(
        "REGULATORY", "LEGAL", "FINANCIAL", "CORPORATE", "CONDITION_PRECEDENT", "FUND_FLOW", "OTHER",
        name="closingcategory",
    )
    closing_condition_status = sa.Enum(
        "PENDING", "IN_PROGRESS", "COMPLETED", "WAIVED", "NOT_APPLICABLE",
        name="closingconditionstatus",
    )

    # ── contracts ──
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("contract_type", contract_type, nullable=False, server_default="SPA"),
        sa.Column("status", contract_status, nullable=False, server_default="DRAFT"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("counterparty_name", sa.String(200), nullable=True),
        sa.Column("effective_date", sa.String(10), nullable=True),
        sa.Column("expiry_date", sa.String(10), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("seller_signature", signature_status, nullable=False, server_default="PENDING"),
        sa.Column("buyer_signature", signature_status, nullable=False, server_default="PENDING"),
        sa.Column("ai_analysis_summary", sa.Text(), nullable=True),
        sa.Column("ai_risk_flags", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── contract_versions ──
    op.create_table(
        "contract_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("changes_summary", sa.Text(), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=False),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── closing_checklists ──
    op.create_table(
        "closing_checklists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("category", closing_category, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", closing_condition_status, nullable=False, server_default="PENDING"),
        sa.Column("responsible_party", sa.String(200), nullable=True),
        sa.Column("responsible_email", sa.String(255), nullable=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("completed_date", sa.String(10), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("closing_checklists")
    op.drop_table("contract_versions")
    op.drop_table("contracts")

    for name in [
        "closingconditionstatus", "closingcategory", "signaturestatus",
        "contractstatus", "contracttype",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
