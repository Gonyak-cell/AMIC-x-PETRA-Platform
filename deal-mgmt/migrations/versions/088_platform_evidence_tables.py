"""088 add platform-wide evidence records and document chunks

Revision ID: 088
Revises: 087
Create Date: 2026-03-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "088"
down_revision: str | None = "087"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "document_chunks" not in table_names:
        op.create_table(
            "document_chunks",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("transaction_id", sa.Uuid(), nullable=False),
            sa.Column("vdr_document_id", sa.Uuid(), nullable=False),
            sa.Column("vdr_text_cache_id", sa.Uuid(), nullable=True),
            sa.Column("chunk_id", sa.String(length=120), nullable=False),
            sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locator_type", sa.String(length=30), nullable=True),
            sa.Column("page", sa.Integer(), nullable=True),
            sa.Column("paragraph", sa.Integer(), nullable=True),
            sa.Column("sheet", sa.String(length=120), nullable=True),
            sa.Column("row", sa.Integer(), nullable=True),
            sa.Column("page_reference", sa.String(length=100), nullable=True),
            sa.Column("chunk_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vdr_document_id"], ["vdr_documents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vdr_text_cache_id"], ["vdr_text_caches.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("vdr_document_id", "chunk_id", name="uq_document_chunks_document_chunk"),
        )
        op.create_index(op.f("ix_document_chunks_transaction_id"), "document_chunks", ["transaction_id"])
        op.create_index(op.f("ix_document_chunks_vdr_document_id"), "document_chunks", ["vdr_document_id"])
        op.create_index(op.f("ix_document_chunks_vdr_text_cache_id"), "document_chunks", ["vdr_text_cache_id"])

    if "evidence_records" not in table_names:
        op.create_table(
            "evidence_records",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("transaction_id", sa.Uuid(), nullable=False),
            sa.Column("artifact_type", sa.String(length=40), nullable=False),
            sa.Column("artifact_id", sa.Uuid(), nullable=False),
            sa.Column("workstream", sa.String(length=30), nullable=False),
            sa.Column("section_type", sa.String(length=30), nullable=True),
            sa.Column("item_id", sa.String(length=30), nullable=True),
            sa.Column("vdr_document_id", sa.Uuid(), nullable=True),
            sa.Column("document_chunk_id", sa.Uuid(), nullable=True),
            sa.Column("reference_label", sa.String(length=500), nullable=False),
            sa.Column("original_name", sa.String(length=500), nullable=True),
            sa.Column("primary_workstream", sa.String(length=30), nullable=True),
            sa.Column("workstream_tags", _JSON, nullable=True),
            sa.Column("evidence_kind", sa.String(length=50), nullable=True),
            sa.Column("directness", sa.String(length=20), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("source_page", sa.String(length=100), nullable=True),
            sa.Column("source_snippet", sa.Text(), nullable=True),
            sa.Column("evidence_locator", _JSON, nullable=True),
            sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_foreign_workstream", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_unresolved_reference", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("used_in_draft", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("used_in_final", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("analysis_phase", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vdr_document_id"], ["vdr_documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["document_chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_evidence_records_transaction_id"), "evidence_records", ["transaction_id"])
        op.create_index(
            op.f("ix_evidence_records_artifact_type"),
            "evidence_records",
            ["artifact_type"],
        )
        op.create_index(
            op.f("ix_evidence_records_artifact_id"),
            "evidence_records",
            ["artifact_id"],
        )
        op.create_index(op.f("ix_evidence_records_workstream"), "evidence_records", ["workstream"])
        op.create_index(op.f("ix_evidence_records_section_type"), "evidence_records", ["section_type"])
        op.create_index(op.f("ix_evidence_records_item_id"), "evidence_records", ["item_id"])
        op.create_index(op.f("ix_evidence_records_vdr_document_id"), "evidence_records", ["vdr_document_id"])
        op.create_index(op.f("ix_evidence_records_document_chunk_id"), "evidence_records", ["document_chunk_id"])

    if "ldd_evidence_records" in table_names and "evidence_records" in inspector.get_table_names():
        evidence_count = bind.execute(sa.text("SELECT COUNT(*) FROM evidence_records")).scalar() or 0
        if evidence_count == 0:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO evidence_records (
                        id,
                        transaction_id,
                        artifact_type,
                        artifact_id,
                        workstream,
                        section_type,
                        item_id,
                        vdr_document_id,
                        document_chunk_id,
                        reference_label,
                        original_name,
                        primary_workstream,
                        workstream_tags,
                        evidence_kind,
                        directness,
                        confidence,
                        relevance_score,
                        source_page,
                        source_snippet,
                        evidence_locator,
                        requires_manual_review,
                        is_foreign_workstream,
                        is_unresolved_reference,
                        used_in_draft,
                        used_in_final,
                        analysis_phase,
                        ordinal,
                        created_at,
                        updated_at
                    )
                    SELECT
                        id,
                        transaction_id,
                        'LDD_REPORT',
                        ldd_report_id,
                        'LDD',
                        section_type,
                        item_id,
                        vdr_document_id,
                        NULL,
                        reference_label,
                        original_name,
                        primary_workstream,
                        workstream_tags,
                        evidence_kind,
                        directness,
                        confidence,
                        relevance_score,
                        source_page,
                        source_snippet,
                        evidence_locator,
                        requires_manual_review,
                        is_foreign_workstream,
                        is_unresolved_reference,
                        used_in_draft,
                        used_in_final,
                        analysis_phase,
                        ordinal,
                        created_at,
                        updated_at
                    FROM ldd_evidence_records
                    """
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "evidence_records" in table_names:
        for index_name in (
            op.f("ix_evidence_records_document_chunk_id"),
            op.f("ix_evidence_records_vdr_document_id"),
            op.f("ix_evidence_records_item_id"),
            op.f("ix_evidence_records_section_type"),
            op.f("ix_evidence_records_workstream"),
            op.f("ix_evidence_records_artifact_id"),
            op.f("ix_evidence_records_artifact_type"),
            op.f("ix_evidence_records_transaction_id"),
        ):
            op.drop_index(index_name, table_name="evidence_records")
        op.drop_table("evidence_records")

    if "document_chunks" in table_names:
        for index_name in (
            op.f("ix_document_chunks_vdr_text_cache_id"),
            op.f("ix_document_chunks_vdr_document_id"),
            op.f("ix_document_chunks_transaction_id"),
        ):
            op.drop_index(index_name, table_name="document_chunks")
        op.drop_table("document_chunks")
