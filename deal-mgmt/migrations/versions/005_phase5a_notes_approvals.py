"""Phase 5A — deal_notes, approval_requests tables

Revision ID: 005_phase5a
Revises: 004_phase4
Create Date: 2026-02-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB

_JSON = sa.JSON().with_variant(_PG_JSONB(), "postgresql")

# revision identifiers, used by Alembic.
revision: str = "005_phase5a"
down_revision: str | None = "004_phase4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enum types (cross-DB compatible) ──
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE notetype AS ENUM ('COMMENT', 'DECISION', 'QUESTION', 'ACTION_ITEM');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE approvaltype AS ENUM ('PHASE_ADVANCE', 'STATUS_CHANGE', 'CONTRACT_SIGN', 'DEAL_TERMS');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE approvalstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

    # ── deal_notes ──
    op.create_table(
        "deal_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("author_email", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "note_type",
            sa.Enum("COMMENT", "DECISION", "QUESTION", "ACTION_ITEM", name="notetype", create_type=False),
            nullable=False,
            server_default="COMMENT",
        ),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("deal_notes.id"), nullable=True),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("mentions", _JSON, nullable=True),
        sa.Column("attachments", _JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── approval_requests ──
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("requester_email", sa.String(255), nullable=False),
        sa.Column(
            "approval_type",
            sa.Enum(
                "PHASE_ADVANCE", "STATUS_CHANGE", "CONTRACT_SIGN", "DEAL_TERMS", name="approvaltype", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "CANCELLED", name="approvalstatus", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("approvers", _JSON, nullable=False),
        sa.Column("deadline", sa.String(10), nullable=True),
        sa.Column("related_entity_type", sa.String(50), nullable=True),
        sa.Column("related_entity_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 새 AuditAction 값 추가 (PostgreSQL 전용) ──
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'APPROVAL_REQUESTED'")
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'APPROVAL_DECIDED'")
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'NOTE_CREATED'")


def downgrade() -> None:
    op.drop_table("approval_requests")
    op.drop_table("deal_notes")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS approvalstatus")
        op.execute("DROP TYPE IF EXISTS approvaltype")
        op.execute("DROP TYPE IF EXISTS notetype")
