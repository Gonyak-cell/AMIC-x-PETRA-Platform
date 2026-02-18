"""initial schema — transactions, engagements, working_group, buyers, timeline, audit

Revision ID: 001_initial
Revises:
Create Date: 2026-02-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── transactions ──
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code_name", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "side",
            sa.Enum("SELL", "BUY", "DUAL", name="transactionside"),
            nullable=False,
        ),
        sa.Column(
            "phase",
            sa.Enum(
                "ENGAGEMENT", "PREPARATION", "MARKETING", "BIDDING_DD",
                "NEGOTIATION", "CLOSING", "POST_CLOSING",
                name="transactionphase",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ACTIVE", "ON_HOLD", "COMPLETED", "TERMINATED", name="transactionstatus"),
            nullable=False,
        ),
        sa.Column("target_company_name", sa.String(200), nullable=False),
        sa.Column("target_corp_code", sa.String(20), nullable=True),
        sa.Column("client_name", sa.String(200), nullable=False),
        sa.Column("estimated_deal_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KRW"),
        sa.Column("deal_structure", sa.String(50), nullable=True),
        sa.Column("investment_type", sa.String(50), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("lead_advisor_email", sa.String(255), nullable=False),
        sa.Column("deal_captain_email", sa.String(255), nullable=True),
        sa.Column("target_close_date", sa.String(10), nullable=True),
        sa.Column("fdd_deal_id", sa.String(36), nullable=True),
        sa.Column("im_document_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── engagements ──
    op.create_table(
        "engagements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column(
            "type",
            sa.Enum("EXCLUSIVE", "NON_EXCLUSIVE", "CO_ADVISORY", name="engagementtype"),
            nullable=False,
        ),
        sa.Column("fee_structure", postgresql.JSONB(), nullable=True),
        sa.Column("signed_at", sa.String(10), nullable=True),
        sa.Column("expires_at", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── working_group_members ──
    op.create_table(
        "working_group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("organization", sa.String(200), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "LEAD_ADVISOR", "LEGAL_COUNSEL", "ACCOUNTING_ADVISOR", "TAX_ADVISOR",
                "INDUSTRY_EXPERT", "VALUATION_ADVISOR", "OTHER",
                name="workinggrouprole",
            ),
            nullable=False,
        ),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("transaction_id", "email", name="uq_wg_transaction_email"),
    )

    # ── buyer_candidates ──
    op.create_table(
        "buyer_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(20), nullable=True),
        sa.Column(
            "buyer_type",
            sa.Enum("STRATEGIC", "FINANCIAL_SPONSOR", "FAMILY_OFFICE", "INDIVIDUAL", "OTHER", name="buyertype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "IDENTIFIED", "CONTACTED", "NDA_SENT", "NDA_SIGNED", "CIM_SENT",
                "INTEREST_CONFIRMED", "IOI_RECEIVED", "IOI_ACCEPTED", "DD_GRANTED",
                "DD_IN_PROGRESS", "LOI_RECEIVED", "LOI_ACCEPTED", "SELECTED", "REJECTED",
                name="buyercandidatestatus",
            ),
            nullable=False,
        ),
        sa.Column("ioi_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("ioi_date", sa.String(10), nullable=True),
        sa.Column("loi_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("loi_date", sa.String(10), nullable=True),
        sa.Column("final_offer_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── deal_timeline ──
    op.create_table(
        "deal_timeline",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_date", sa.String(10), nullable=False),
        sa.Column("is_auto_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── audit_logs ──
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE", "UPDATE", "DELETE", "PHASE_TRANSITION", "STATUS_CHANGE",
                "MEMBER_ADDED", "MEMBER_REMOVED", "SERVICE_LINKED",
                name="auditaction",
            ),
            nullable=False,
        ),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("deal_timeline")
    op.drop_table("buyer_candidates")
    op.drop_table("working_group_members")
    op.drop_table("engagements")
    op.drop_table("transactions")

    # Drop enums
    for name in [
        "auditaction", "buyercandidatestatus", "buyertype", "workinggrouprole",
        "engagementtype", "transactionstatus", "transactionphase", "transactionside",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
