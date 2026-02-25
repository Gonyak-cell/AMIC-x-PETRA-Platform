"""Permit analysis and requirements tables.

Revision ID: 017
Revises: 016
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PgENUM

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None

# Enum types
permit_filing_type = PgENUM(
    "CHANGE_NOTIFICATION", "CHANGE_APPROVAL", "NEW_REGISTRATION", "RENEWAL",
    name="permitfilingtype", create_type=False,
)
permit_timing_type = PgENUM(
    "PRE_FILING", "POST_FILING", "BOTH",
    name="permittimingtype", create_type=False,
)
permit_analysis_status = PgENUM(
    "PENDING", "ANALYZING", "COMPLETED", "FAILED", "MANUALLY_REVIEWED",
    name="permitanalysisstatus", create_type=False,
)
permit_requirement_status = PgENUM(
    "IDENTIFIED", "DOCUMENTS_PREPARING", "FILED", "APPROVED", "NOT_APPLICABLE",
    name="permitrequirementstatus", create_type=False,
)


def upgrade() -> None:
    # Create enum types
    permit_filing_type.create(op.get_bind(), checkfirst=True)
    permit_timing_type.create(op.get_bind(), checkfirst=True)
    permit_analysis_status.create(op.get_bind(), checkfirst=True)
    permit_requirement_status.create(op.get_bind(), checkfirst=True)

    # Add PERMITS to existing compliancecategory enum
    op.execute("ALTER TYPE compliancecategory ADD VALUE IF NOT EXISTS 'PERMITS'")

    # permit_analyses table
    op.create_table(
        "permit_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", permit_analysis_status, nullable=False, server_default="PENDING"),
        sa.Column("business_types", JSONB, nullable=True),
        sa.Column("existing_permits", JSONB, nullable=True),
        sa.Column("analysis_method", sa.String(50), nullable=True),
        sa.Column("llm_cost_usd", sa.Numeric(8, 4), nullable=True),
        sa.Column("analysis_notes", sa.Text, nullable=True),
        sa.Column("analyzed_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_permit_analyses_transaction_id", "permit_analyses", ["transaction_id"])

    # permit_requirements table
    op.create_table(
        "permit_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", UUID(as_uuid=True), sa.ForeignKey("permit_analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("permit_name", sa.String(300), nullable=False),
        sa.Column("regulatory_body", sa.String(200), nullable=False),
        sa.Column("legal_basis", sa.String(500), nullable=True),
        sa.Column("filing_type", permit_filing_type, nullable=False),
        sa.Column("timing_type", permit_timing_type, nullable=False),
        sa.Column("pre_filing_deadline_days", sa.Integer, nullable=True),
        sa.Column("post_filing_deadline_days", sa.Integer, nullable=True),
        sa.Column("calculated_deadline", sa.String(10), nullable=True),
        sa.Column("required_documents", JSONB, nullable=True),
        sa.Column("status", permit_requirement_status, nullable=False, server_default="IDENTIFIED"),
        sa.Column("source", sa.String(20), nullable=False, server_default="KB"),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("compliance_item_id", UUID(as_uuid=True), sa.ForeignKey("compliance_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_permit_requirements_analysis_id", "permit_requirements", ["analysis_id"])
    op.create_index("ix_permit_requirements_transaction_id", "permit_requirements", ["transaction_id"])

    # Add permit_requirement_id FK to compliance_items
    op.add_column(
        "compliance_items",
        sa.Column("permit_requirement_id", UUID(as_uuid=True), sa.ForeignKey("permit_requirements.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("compliance_items", "permit_requirement_id")
    op.drop_table("permit_requirements")
    op.drop_table("permit_analyses")
    permit_requirement_status.drop(op.get_bind(), checkfirst=True)
    permit_analysis_status.drop(op.get_bind(), checkfirst=True)
    permit_timing_type.drop(op.get_bind(), checkfirst=True)
    permit_filing_type.drop(op.get_bind(), checkfirst=True)
