"""Phase 5A — deal_notes, approval_requests tables

Revision ID: 005_phase5a
Revises: 004_phase4
Create Date: 2026-02-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_phase5a"
down_revision: Union[str, None] = "004_phase4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ──
    note_type = sa.Enum("COMMENT", "DECISION", "QUESTION", "ACTION_ITEM", name="notetype")
    approval_type = sa.Enum("PHASE_ADVANCE", "STATUS_CHANGE", "CONTRACT_SIGN", "DEAL_TERMS", name="approvaltype")
    approval_status = sa.Enum("PENDING", "APPROVED", "REJECTED", "CANCELLED", name="approvalstatus")

    note_type.create(op.get_bind(), checkfirst=True)
    approval_type.create(op.get_bind(), checkfirst=True)
    approval_status.create(op.get_bind(), checkfirst=True)

    # ── deal_notes ──
    op.create_table(
        "deal_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column("author_email", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("note_type", note_type, nullable=False, server_default="COMMENT"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deal_notes.id"), nullable=True),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("mentions", postgresql.JSONB, nullable=True),
        sa.Column("attachments", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── approval_requests ──
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False, index=True),
        sa.Column("requester_email", sa.String(255), nullable=False),
        sa.Column("approval_type", approval_type, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", approval_status, nullable=False, server_default="PENDING"),
        sa.Column("approvers", postgresql.JSONB, nullable=False),
        sa.Column("deadline", sa.String(10), nullable=True),
        sa.Column("related_entity_type", sa.String(50), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 새 AuditAction 값 추가 ──
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'APPROVAL_REQUESTED'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'APPROVAL_DECIDED'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'NOTE_CREATED'")


def downgrade() -> None:
    op.drop_table("approval_requests")
    op.drop_table("deal_notes")
    op.execute("DROP TYPE IF EXISTS approvalstatus")
    op.execute("DROP TYPE IF EXISTS approvaltype")
    op.execute("DROP TYPE IF EXISTS notetype")
