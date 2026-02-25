"""add im_checklists and im_checklist_items tables

Revision ID: 006_im_checklists
Revises: 005_audit_logs
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "006_im_checklists"
down_revision = "005_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- im_checklists ---
    op.create_table(
        "im_checklists",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id", UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            unique=True, nullable=False,
        ),
        sa.Column("transaction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("vdr_document_ids", JSONB, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="EXTRACTING"),
        sa.Column("total_items", sa.Integer, server_default="0"),
        sa.Column("confirmed_items", sa.Integer, server_default="0"),
        sa.Column("missing_items", sa.Integer, server_default="0"),
        sa.Column("raw_extraction", JSONB, server_default="{}"),
        sa.Column("extraction_task_id", sa.String(255), nullable=True),
        sa.Column("generation_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_im_checklists_document_id", "im_checklists", ["document_id"])
    op.create_index("ix_im_checklists_status", "im_checklists", ["status"])
    op.create_index("ix_im_checklists_transaction_id", "im_checklists", ["transaction_id"])

    # --- im_checklist_items ---
    op.create_table(
        "im_checklist_items",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "checklist_id", UUID(as_uuid=True),
            sa.ForeignKey("im_checklists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("field_label", sa.String(200), nullable=False),
        sa.Column("field_type", sa.String(20), server_default="text"),
        sa.Column("extracted_value", sa.Text, nullable=True),
        sa.Column("confirmed_value", sa.Text, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("source_vdr_doc_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_vdr_doc_name", sa.String(500), nullable=True),
        sa.Column("source_location", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), server_default="EXTRACTED"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_required", sa.Boolean, server_default="true"),
        sa.Column("fiscal_year", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_im_checklist_items_status", "im_checklist_items", ["status"])
    op.create_index("ix_im_checklist_items_category", "im_checklist_items", ["category"])
    op.create_index(
        "ix_im_checklist_items_checklist_category",
        "im_checklist_items",
        ["checklist_id", "category"],
    )
    op.create_unique_constraint(
        "uq_im_checklist_items_checklist_field",
        "im_checklist_items",
        ["checklist_id", "field_key"],
    )


def downgrade() -> None:
    op.drop_table("im_checklist_items")
    op.drop_table("im_checklists")
