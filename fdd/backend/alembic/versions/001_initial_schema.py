"""Initial schema with 12 models.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. deal ──────────────────────────────────────────────
    op.create_table(
        "deal",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "deal_type",
            sa.Enum("COMPLETION_ACCOUNTS", "LOCKED_BOX", name="dealtype"),
            nullable=False,
        ),
        sa.Column("base_currency", sa.String(10), nullable=False, server_default="KRW"),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ACTIVE", "ARCHIVED", name="dealstatus"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "created_by", sa.String(100), nullable=False, server_default="system"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 2. deal_definition ───────────────────────────────────
    op.create_table(
        "deal_definition",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("definition_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "APPROVED", "LOCKED", name="definitionstatus"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 3. deal_snapshot ─────────────────────────────────────
    op.create_table(
        "deal_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "definition_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal_definition.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(20), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=True),
        sa.Column(
            "status",
            sa.Enum("RUNNING", "SUCCESS", "FAILED", name="snapshotstatus"),
            nullable=False,
            server_default="RUNNING",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 4. audit_log ─────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE", "UPDATE", "DELETE", "APPROVE", "LOCK", name="auditaction"
            ),
            nullable=False,
        ),
        sa.Column("actor", sa.String(100), nullable=False, server_default="system"),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 5. upload_file ───────────────────────────────────────
    op.create_table(
        "upload_file",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("stored_path", sa.String(1000), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "detected_type",
            sa.Enum("TB", "GL", "AR", "AP", "BANK", "DEBT", "LEASE", name="uploadtype"),
            nullable=True,
        ),
        sa.Column(
            "confirmed_type",
            sa.Enum("TB", "GL", "AR", "AP", "BANK", "DEBT", "LEASE", name="uploadtype"),
            nullable=True,
        ),
        sa.Column("detection_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "DETECTING",
                "VALIDATING",
                "INGESTING",
                "COMPLETED",
                "FAILED",
                name="ingestionstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("rows_processed", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("validation_summary", postgresql.JSONB(), nullable=True),
        sa.Column(
            "uploaded_by", sa.String(100), nullable=False, server_default="system"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 6. upload_validation_error ───────────────────────────
    op.create_table(
        "upload_validation_error",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "upload_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("upload_file.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("ERROR", "WARNING", name="validationseverity"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(20), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 7. journal_entry ─────────────────────────────────────
    op.create_table(
        "journal_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "upload_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("upload_file.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("account_code", sa.String(50), nullable=True),
        sa.Column("account_name", sa.String(500), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("debit", sa.Numeric(18, 4), nullable=True),
        sa.Column("credit", sa.Numeric(18, 4), nullable=True),
        sa.Column("balance", sa.Numeric(18, 4), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("entry_id", sa.String(100), nullable=True),
        sa.Column("line_id", sa.String(100), nullable=True),
        sa.Column("counterparty", sa.String(500), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_journal_entry_deal", "journal_entry", ["deal_id"])
    op.create_index("ix_journal_entry_upload", "journal_entry", ["upload_file_id"])
    op.create_index("ix_journal_entry_account", "journal_entry", ["account_code"])
    op.create_index("ix_journal_entry_date", "journal_entry", ["entry_date"])
    op.create_index("ix_journal_entry_entry_id", "journal_entry", ["entry_id"])

    # ── 8. standard_line_item ────────────────────────────────
    op.create_table(
        "standard_line_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name_en", sa.String(255), nullable=False),
        sa.Column("name_ko", sa.String(255), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "REVENUE",
                "COGS",
                "SGA",
                "OTHER_OPERATING_INCOME",
                "DEPRECIATION_AMORTIZATION",
                "NON_OPERATING",
                "INTEREST_EXPENSE",
                "INTEREST_INCOME",
                "TAX_EXPENSE",
                "CASH",
                "AR",
                "INVENTORY",
                "OTHER_CURRENT_ASSETS",
                "PPE",
                "INTANGIBLES",
                "OTHER_NONCURRENT_ASSETS",
                "AP",
                "ACCRUALS",
                "OTHER_CURRENT_LIABILITIES",
                "DEBT",
                "LEASE_LIABILITIES",
                "OTHER_NONCURRENT_LIABILITIES",
                "EQUITY",
                name="lineitemcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "statement_type",
            sa.Enum("IS", "BS", name="financialstatement"),
            nullable=False,
        ),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("parent_code", sa.String(50), nullable=True),
        sa.Column("is_subtotal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("keywords", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 9. account_mapping ───────────────────────────────────
    op.create_table(
        "account_mapping",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_account_code", sa.String(50), nullable=False),
        sa.Column("source_account_name", sa.String(500), nullable=False),
        sa.Column(
            "target_line_item_code",
            sa.String(50),
            sa.ForeignKey("standard_line_item.code"),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Enum("HIGH", "MEDIUM", "LOW", "UNMAPPED", name="mappingconfidence"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("PROPOSED", "APPROVED", "REJECTED", "MANUAL", name="mappingstatus"),
            nullable=False,
            server_default="PROPOSED",
        ),
        sa.Column("match_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("algorithm", sa.String(50), nullable=True),
        sa.Column("affected_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_account_mapping_deal", "account_mapping", ["deal_id"])
    op.create_index(
        "ix_account_mapping_source", "account_mapping", ["source_account_code"]
    )
    op.create_index("ix_account_mapping_status", "account_mapping", ["status"])
    op.create_index(
        "uq_account_mapping_deal_source",
        "account_mapping",
        ["deal_id", "source_account_code"],
        unique=True,
    )

    # ── 10. tie_out_result ───────────────────────────────────
    op.create_table(
        "tie_out_result",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal_snapshot.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "statement_type",
            sa.Enum("IS", "BS", name="financialstatement"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("PASS", "FAIL", "WARNING", name="tieoutstatus"),
            nullable=False,
        ),
        sa.Column("tb_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("reconstructed_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("variance", sa.Numeric(18, 4), nullable=False),
        sa.Column("variance_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "unmapped_account_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "unmapped_total", sa.Numeric(18, 4), nullable=False, server_default="0"
        ),
        sa.Column("top_discrepancies", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tie_out_result_deal", "tie_out_result", ["deal_id"])
    op.create_index("ix_tie_out_result_snapshot", "tie_out_result", ["snapshot_id"])
    op.create_index("ix_tie_out_result_status", "tie_out_result", ["status"])

    # ── 11. evidence_link ────────────────────────────────────
    op.create_table(
        "evidence_link",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("FILE", "TB", "GL", "PDF", name="sourcetype"),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("source_detail", postgresql.JSONB(), nullable=True),
        sa.Column("transaction_id", sa.String(255), nullable=True),
        sa.Column("filter_hash", sa.String(64), nullable=True),
        sa.Column("engine_version", sa.String(20), nullable=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal_snapshot.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_evidence_link_target", "evidence_link", ["target_type", "target_id"]
    )
    op.create_index(
        "ix_evidence_link_source", "evidence_link", ["source_type", "source_id"]
    )
    op.create_index("ix_evidence_link_deal", "evidence_link", ["deal_id"])
    op.create_index("ix_evidence_link_snapshot", "evidence_link", ["snapshot_id"])

    # ── 12. qoe_calculation ──────────────────────────────────
    op.create_table(
        "qoe_calculation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal_snapshot.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=False),
        sa.Column("cogs", sa.Numeric(18, 4), nullable=False),
        sa.Column("gross_profit", sa.Numeric(18, 4), nullable=False),
        sa.Column("sga", sa.Numeric(18, 4), nullable=False),
        sa.Column("depreciation_amortization", sa.Numeric(18, 4), nullable=False),
        sa.Column("other_operating", sa.Numeric(18, 4), nullable=False),
        sa.Column("operating_income", sa.Numeric(18, 4), nullable=False),
        sa.Column("reported_ebitda", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "total_adjustments", sa.Numeric(18, 4), nullable=False, server_default="0"
        ),
        sa.Column("adjusted_ebitda", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "balance_check_error", sa.Numeric(18, 4), nullable=False, server_default="0"
        ),
        sa.Column("category_breakdown", postgresql.JSONB(), nullable=False),
        sa.Column("engine_version", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "REVIEW", "APPROVED", name="qoestatus"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_qoe_calculation_deal", "qoe_calculation", ["deal_id"])
    op.create_index("ix_qoe_calculation_snapshot", "qoe_calculation", ["snapshot_id"])

    # ── 13. adjustment_item ──────────────────────────────────
    op.create_table(
        "adjustment_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "qoe_calculation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qoe_calculation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "NON_RECURRING",
                "NON_OPERATING",
                "NORMALIZATION",
                "OWNER_RELATED",
                "PRO_FORMA",
                name="adjustmentcategory",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "detection_method", sa.String(50), nullable=False, server_default="manual"
        ),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("source_account_code", sa.String(50), nullable=True),
        sa.Column("source_account_name", sa.String(500), nullable=True),
        sa.Column("source_entry_ids", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "CANDIDATE",
                "PROPOSED",
                "APPROVED",
                "REJECTED",
                name="adjustmentstatus",
            ),
            nullable=False,
            server_default="CANDIDATE",
        ),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_adjustment_item_qoe", "adjustment_item", ["qoe_calculation_id"])
    op.create_index("ix_adjustment_item_deal", "adjustment_item", ["deal_id"])
    op.create_index("ix_adjustment_item_status", "adjustment_item", ["status"])


def downgrade() -> None:
    op.drop_table("adjustment_item")
    op.drop_table("qoe_calculation")
    op.drop_table("evidence_link")
    op.drop_table("tie_out_result")
    op.drop_table("account_mapping")
    op.drop_table("standard_line_item")
    op.drop_table("journal_entry")
    op.drop_table("upload_validation_error")
    op.drop_table("upload_file")
    op.drop_table("audit_log")
    op.drop_table("deal_snapshot")
    op.drop_table("deal_definition")
    op.drop_table("deal")

    # Drop all enum types
    for enum_name in [
        "adjustmentstatus",
        "adjustmentcategory",
        "qoestatus",
        "sourcetype",
        "tieoutstatus",
        "financialstatement",
        "lineitemcategory",
        "mappingstatus",
        "mappingconfidence",
        "ingestionstatus",
        "uploadtype",
        "validationseverity",
        "auditaction",
        "snapshotstatus",
        "definitionstatus",
        "dealstatus",
        "dealtype",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
