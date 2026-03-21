"""086 add ldd evidence records and vdr trace chunks

Revision ID: 086
Revises: 085
Create Date: 2026-03-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "086"
down_revision: str | None = "085"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "vdr_text_caches" in table_names:
        cache_columns = {column["name"] for column in inspector.get_columns("vdr_text_caches")}
        if "chunks_json" not in cache_columns:
            op.add_column("vdr_text_caches", sa.Column("chunks_json", sa.JSON(), nullable=True))

    if "ldd_evidence_records" not in table_names:
        op.create_table(
            "ldd_evidence_records",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("ldd_report_id", sa.Uuid(), nullable=False),
            sa.Column("transaction_id", sa.Uuid(), nullable=True),
            sa.Column("item_id", sa.String(length=30), nullable=False),
            sa.Column("section_type", sa.String(length=30), nullable=False),
            sa.Column("vdr_document_id", sa.Uuid(), nullable=True),
            sa.Column("reference_label", sa.String(length=500), nullable=False),
            sa.Column("original_name", sa.String(length=500), nullable=True),
            sa.Column("primary_workstream", sa.String(length=30), nullable=True),
            sa.Column("workstream_tags", sa.JSON(), nullable=True),
            sa.Column("evidence_kind", sa.String(length=50), nullable=True),
            sa.Column("directness", sa.String(length=20), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("source_page", sa.String(length=100), nullable=True),
            sa.Column("chunk_id", sa.String(length=120), nullable=True),
            sa.Column("source_snippet", sa.Text(), nullable=True),
            sa.Column("evidence_locator", sa.JSON(), nullable=True),
            sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_foreign_workstream", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_unresolved_reference", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("used_in_draft", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("used_in_final", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("analysis_phase", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["ldd_report_id"], ["ldd_reports.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vdr_document_id"], ["vdr_documents.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ldd_evidence_records_ldd_report_id"), "ldd_evidence_records", ["ldd_report_id"])
        op.create_index(op.f("ix_ldd_evidence_records_transaction_id"), "ldd_evidence_records", ["transaction_id"])
        op.create_index(op.f("ix_ldd_evidence_records_item_id"), "ldd_evidence_records", ["item_id"])
        op.create_index(op.f("ix_ldd_evidence_records_section_type"), "ldd_evidence_records", ["section_type"])
        op.create_index(op.f("ix_ldd_evidence_records_vdr_document_id"), "ldd_evidence_records", ["vdr_document_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "ldd_evidence_records" in table_names:
        for index_name in (
            op.f("ix_ldd_evidence_records_vdr_document_id"),
            op.f("ix_ldd_evidence_records_section_type"),
            op.f("ix_ldd_evidence_records_item_id"),
            op.f("ix_ldd_evidence_records_transaction_id"),
            op.f("ix_ldd_evidence_records_ldd_report_id"),
        ):
            op.drop_index(index_name, table_name="ldd_evidence_records")
        op.drop_table("ldd_evidence_records")

    if "vdr_text_caches" in table_names:
        cache_columns = {column["name"] for column in inspector.get_columns("vdr_text_caches")}
        if "chunks_json" in cache_columns:
            op.drop_column("vdr_text_caches", "chunks_json")
