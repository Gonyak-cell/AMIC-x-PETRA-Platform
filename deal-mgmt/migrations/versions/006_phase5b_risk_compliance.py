"""Phase 5B — risk_items, compliance_items tables

Revision ID: 006_phase5b
Revises: 005_phase5a
Create Date: 2026-02-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_phase5b"
down_revision: Union[str, None] = "005_phase5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types via raw SQL (idempotent) ──
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE riskcategory AS ENUM ('REGULATORY', 'FINANCIAL', 'LEGAL', 'OPERATIONAL', 'REPUTATIONAL', 'TAX', 'ENVIRONMENTAL', 'MARKET', 'OTHER');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE riskseverity AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE risklikelihood AS ENUM ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW', 'VERY_LOW');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE riskstatus AS ENUM ('IDENTIFIED', 'ASSESSING', 'MITIGATING', 'MITIGATED', 'ACCEPTED', 'CLOSED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE compliancecategory AS ENUM ('ANTITRUST', 'FOREIGN_INVESTMENT', 'SECURITIES', 'DATA_PRIVACY', 'ANTI_CORRUPTION', 'SANCTIONS', 'ENVIRONMENTAL', 'LABOR', 'TAX', 'OTHER');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE compliancestatus AS ENUM ('NOT_STARTED', 'IN_REVIEW', 'PENDING_APPROVAL', 'APPROVED', 'FLAGGED', 'NON_COMPLIANT', 'WAIVED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # ── risk_items ──
    op.create_table(
        "risk_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column("category", postgresql.ENUM("REGULATORY", "FINANCIAL", "LEGAL", "OPERATIONAL", "REPUTATIONAL", "TAX", "ENVIRONMENTAL", "MARKET", "OTHER", name="riskcategory", create_type=False), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", postgresql.ENUM("CRITICAL", "HIGH", "MEDIUM", "LOW", name="riskseverity", create_type=False), nullable=False, server_default="MEDIUM"),
        sa.Column("likelihood", postgresql.ENUM("VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW", name="risklikelihood", create_type=False), nullable=False, server_default="MEDIUM"),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("mitigation_strategy", sa.Text, nullable=True),
        sa.Column("owner_email", sa.String(255), nullable=True),
        sa.Column("status", postgresql.ENUM("IDENTIFIED", "ASSESSING", "MITIGATING", "MITIGATED", "ACCEPTED", "CLOSED", name="riskstatus", create_type=False), nullable=False, server_default="IDENTIFIED"),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── compliance_items ──
    op.create_table(
        "compliance_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column("category", postgresql.ENUM("ANTITRUST", "FOREIGN_INVESTMENT", "SECURITIES", "DATA_PRIVACY", "ANTI_CORRUPTION", "SANCTIONS", "ENVIRONMENTAL", "LABOR", "TAX", "OTHER", name="compliancecategory", create_type=False), nullable=False),
        sa.Column("requirement", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("jurisdiction", sa.String(100), nullable=True),
        sa.Column("regulatory_body", sa.String(200), nullable=True),
        sa.Column("assignee_email", sa.String(255), nullable=True),
        sa.Column("status", postgresql.ENUM("NOT_STARTED", "IN_REVIEW", "PENDING_APPROVAL", "APPROVED", "FLAGGED", "NON_COMPLIANT", "WAIVED", name="compliancestatus", create_type=False), nullable=False, server_default="NOT_STARTED"),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("filing_reference", sa.String(200), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("compliance_items")
    op.drop_table("risk_items")
    op.execute("DROP TYPE IF EXISTS compliancestatus")
    op.execute("DROP TYPE IF EXISTS compliancecategory")
    op.execute("DROP TYPE IF EXISTS riskstatus")
    op.execute("DROP TYPE IF EXISTS risklikelihood")
    op.execute("DROP TYPE IF EXISTS riskseverity")
    op.execute("DROP TYPE IF EXISTS riskcategory")
