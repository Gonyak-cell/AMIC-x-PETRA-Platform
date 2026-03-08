"""074 — RFI V2 포털 (질의 원장 + 스레드 이력 + 첨부)

기존 round 기반 RFI 시스템을 질의 원장 + insert-only 스레드 이력 구조로 전면 교체.
- rfi_items: 질의 원장 (낙관적 락 + 소프트 삭제)
- rfi_threads: 답변/추가질의 이력 (insert-only)
- rfi_attachments: 증빙 자료 (퍼지 매칭 매핑)

Revision ID: 074
Revises: 073
Create Date: 2026-03-08
"""

import sqlalchemy as sa
from alembic import op

revision = "074"
down_revision = "073"


def upgrade() -> None:
    # ── 기존 테이블 삭제 ──
    op.drop_table("rfi_checklist_mappings")
    op.drop_table("rfi_items")
    op.drop_table("rfis")

    # ── rfi_items (질의 원장) ──
    op.create_table(
        "rfi_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_id", sa.Uuid(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_number", sa.String(50), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "FINANCIAL",
                "LEGAL",
                "OPERATIONAL",
                "COMMERCIAL",
                "HR",
                "IT",
                "ENVIRONMENTAL",
                "INSURANCE",
                "IP",
                "REAL_ESTATE",
                "VALUATION",
                "CORPORATE",
                "TAX",
                "OTHER",
                name="rficategoryv2",
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("HIGH", "MEDIUM", "LOW", name="rfipriority"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("target_doc", sa.String(100), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "current_status",
            sa.Enum("OPEN", "ANSWERED", "CLARIFICATION_NEEDED", "CLOSED", name="rfiitemstatusv2"),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column("internal_memo", sa.Text(), nullable=True),
        sa.Column("report_section_tag", sa.String(100), nullable=True),
        sa.Column("assignee_email", sa.String(255), nullable=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_rfi_items_transaction_id", "rfi_items", ["transaction_id"])

    # ── rfi_threads (답변/추가질의 이력) ──
    op.create_table(
        "rfi_threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("rfi_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_num", sa.Integer(), nullable=False),
        sa.Column("author_email", sa.String(255), nullable=False),
        sa.Column(
            "author_role",
            sa.Enum("ADVISOR", "TARGET", name="rfiauthorrole"),
            nullable=False,
        ),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rfi_threads_item_id", "rfi_threads", ["item_id"])

    # ── rfi_attachments (증빙 자료) ──
    op.create_table(
        "rfi_attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("rfi_threads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("rfi_items.id", ondelete="CASCADE"), nullable=True),
        sa.Column("transaction_id", sa.Uuid(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vdr_index", sa.String(50), nullable=True),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_url", sa.String(2000), nullable=False),
        sa.Column("is_mapped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rfi_attachments_thread_id", "rfi_attachments", ["thread_id"])
    op.create_index("ix_rfi_attachments_item_id", "rfi_attachments", ["item_id"])
    op.create_index("ix_rfi_attachments_transaction_id", "rfi_attachments", ["transaction_id"])


def downgrade() -> None:
    # ── 새 테이블 삭제 ──
    op.drop_table("rfi_attachments")
    op.drop_table("rfi_threads")
    op.drop_table("rfi_items")

    # ── Enum 타입 삭제 ──
    sa.Enum(name="rficategoryv2").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="rfipriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="rfiitemstatusv2").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="rfiauthorrole").drop(op.get_bind(), checkfirst=True)

    # ── 기존 테이블 복원 ──
    op.create_table(
        "rfis",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_id", sa.Uuid(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "SENT", "PARTIALLY_RESPONDED", "FULLY_RESPONDED", "CLOSED", "CANCELLED", name="rfistatus"),
            nullable=False,
            server_default="DRAFT",
        ),
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rfis_transaction_id", "rfis", ["transaction_id"])

    op.create_table(
        "rfi_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rfi_id", sa.Uuid(), sa.ForeignKey("rfis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "GENERAL",
                "FINANCIAL",
                "TAX",
                "LEGAL",
                "OPERATIONAL",
                "COMMERCIAL",
                "HR",
                "IT",
                "ENVIRONMENTAL",
                "INSURANCE",
                "IP",
                "REAL_ESTATE",
                "VALUATION",
                "OTHER",
                name="rficategory",
            ),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_detail", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", name="rfiitempriority"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("response_documents", sa.JSON(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_by", sa.String(255), nullable=True),
        sa.Column("reviewer_comment", sa.Text(), nullable=True),
        sa.Column("reviewer_email", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RESPONDED",
                "CLARIFICATION_NEEDED",
                "ACCEPTED",
                "NOT_APPLICABLE",
                name="rfiitemstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("assignee_email", sa.String(255), nullable=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column(
            "source_type",
            sa.Enum(
                "MANUAL",
                "IM_CHECKLIST",
                "FDD_CHECKLIST",
                "DD_CHECKLIST",
                "EXCEL_IMPORT",
                "AI_SUGGESTED",
                name="rfisourcetype",
            ),
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column("source_ref_id", sa.Uuid(), nullable=True),
        sa.Column("source_ref_key", sa.String(100), nullable=True),
        sa.Column("vdr_document_ids", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("follow_up_question", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rfi_items_rfi_id", "rfi_items", ["rfi_id"])
    op.create_index("ix_rfi_items_transaction_id", "rfi_items", ["transaction_id"])

    op.create_table(
        "rfi_checklist_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rfi_item_id", sa.Uuid(), sa.ForeignKey("rfi_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_module", sa.String(20), nullable=False),
        sa.Column("target_checklist_id", sa.Uuid(), nullable=True),
        sa.Column("target_item_id", sa.Uuid(), nullable=True),
        sa.Column("target_field_key", sa.String(100), nullable=True),
        sa.Column("synced", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rfi_checklist_mappings_rfi_item_id", "rfi_checklist_mappings", ["rfi_item_id"])
