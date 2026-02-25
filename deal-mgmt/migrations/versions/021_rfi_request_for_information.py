"""021: RFI (Request for Information) 테이블 추가.

Revision ID: 021_rfi
Revises: 020_financial_models
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021_rfi"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RFI 라운드 테이블
    op.create_table(
        "rfis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("recipient_name", sa.String(200), nullable=True),
        sa.Column("recipient_email", sa.String(255), nullable=True),
        sa.Column("recipient_company", sa.String(200), nullable=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("responded_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # RFI 아이템 테이블
    op.create_table(
        "rfi_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rfi_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rfis.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_detail", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("response_documents", postgresql.JSONB(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_by", sa.String(255), nullable=True),
        sa.Column("reviewer_comment", sa.Text(), nullable=True),
        sa.Column("reviewer_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("assignee_email", sa.String(255), nullable=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="MANUAL"),
        sa.Column("source_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ref_key", sa.String(100), nullable=True),
        sa.Column("vdr_document_ids", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("follow_up_question", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # RFI 체크리스트 매핑 테이블
    op.create_table(
        "rfi_checklist_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rfi_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rfi_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("target_module", sa.String(20), nullable=False),
        sa.Column("target_checklist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_field_key", sa.String(100), nullable=True),
        sa.Column("synced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("rfi_checklist_mappings")
    op.drop_table("rfi_items")
    op.drop_table("rfis")
