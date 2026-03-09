"""075 — 범용 문서 버전 관리 시스템 (VCS Phase 1)

Document_Master + Revision(SHA-256 중복 차단) + Block(Phase 2 스텁) 테이블 생성.
기존 ContractMarkup/NdaMarkup 테이블은 유지하고 병행 운영.

Revision ID: 075
Revises: 074
Create Date: 2026-03-08
"""

import sqlalchemy as sa
from alembic import op

revision = "075"
down_revision = "074"


def upgrade() -> None:
    # ── document_masters (문서 원장) ──
    op.create_table(
        "document_masters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_type", sa.String(30), nullable=False),
        sa.Column("doc_name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_revision_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "contract_id",
            sa.Uuid(),
            sa.ForeignKey("contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "nda_id",
            sa.Uuid(),
            sa.ForeignKey("ndas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_masters_transaction_id", "document_masters", ["transaction_id"])
    op.create_index("ix_document_masters_doc_type", "document_masters", ["doc_type"])

    # ── document_revisions (리비전) ──
    op.create_table(
        "document_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("document_masters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("uploaded_by_email", sa.String(255), nullable=True),
        sa.Column("upload_source", sa.String(20), nullable=False, server_default="MANUAL"),
        sa.Column("changes_summary", sa.Text(), nullable=True),
        sa.Column(
            "prev_revision_id",
            sa.Uuid(),
            sa.ForeignKey("document_revisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_entity_type", sa.String(50), nullable=True),
        sa.Column("source_entity_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_revisions_document_id", "document_revisions", ["document_id"])
    op.create_index("ix_document_revisions_sha256_hash", "document_revisions", ["sha256_hash"])

    # ── document_blocks (Phase 2 스텁) ──
    op.create_table(
        "document_blocks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("document_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_key", sa.String(100), nullable=False),
        sa.Column("block_type", sa.String(20), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_blocks_revision_id", "document_blocks", ["revision_id"])


def downgrade() -> None:
    op.drop_table("document_blocks")
    op.drop_table("document_revisions")
    op.drop_table("document_masters")
