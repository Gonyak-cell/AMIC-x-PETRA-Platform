"""FDD Checklist and Analysis Run tables.

Revision ID: 016
Revises: 015
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── fdd_checklist ────────────────────────────────────────────────
    op.create_table(
        "fdd_checklist",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum(
                "GENERATING",
                "PENDING_REVIEW",
                "REVIEWED",
                "FINALIZED",
                name="checkliststatus",
            ),
            nullable=False,
            server_default="GENERATING",
        ),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_fdd_checklist_deal", "fdd_checklist", ["deal_id"])
    op.create_index("ix_fdd_checklist_status", "fdd_checklist", ["status"])

    # ── fdd_checklist_item ───────────────────────────────────────────
    op.create_table(
        "fdd_checklist_item",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "checklist_id",
            UUID(as_uuid=True),
            sa.ForeignKey("fdd_checklist.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "REVENUE_RECOGNITION",
                "COGS_CLASSIFICATION",
                "SGA_ANALYSIS",
                "NON_RECURRING_ITEMS",
                "RELATED_PARTY_TRANSACTIONS",
                "EBITDA_ADJUSTMENTS",
                "NWC_CLASSIFICATION",
                "AR_AGING",
                "AP_AGING",
                "INVENTORY_ANALYSIS",
                "NWC_SEASONALITY",
                "DEBT_SCHEDULE",
                "DEBT_LIKE_ITEMS",
                "CASH_LIKE_ITEMS",
                "LEASE_OBLIGATIONS",
                "TAX_REVIEW",
                "CONTINGENT_LIABILITIES",
                "OFF_BALANCE_SHEET",
                name="checklistcategory",
            ),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("auto_finding", sa.Text, nullable=True),
        sa.Column("auto_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("user_correction", sa.Text, nullable=True),
        sa.Column("user_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "AUTO_GENERATED",
                "CONFIRMED",
                "CORRECTED",
                "FLAGGED",
                "NOT_APPLICABLE",
                name="checklistitemstatus",
            ),
            nullable=False,
            server_default="AUTO_GENERATED",
        ),
        sa.Column(
            "severity",
            sa.Enum("HIGH", "MEDIUM", "LOW", "INFO", name="checklistseverity"),
            nullable=True,
        ),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_fdd_checklist_item_checklist", "fdd_checklist_item", ["checklist_id"]
    )
    op.create_index(
        "ix_fdd_checklist_item_category", "fdd_checklist_item", ["category"]
    )

    # ── checklist_item_vdr_link ──────────────────────────────────────
    op.create_table(
        "checklist_item_vdr_link",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "checklist_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("fdd_checklist_item.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "upload_file_id",
            UUID(as_uuid=True),
            sa.ForeignKey("upload_file.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "vdr_folder_id",
            UUID(as_uuid=True),
            sa.ForeignKey("vdr_folder.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "evidence_link_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evidence_link.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_detail", sa.JSON, nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_checklist_vdr_item", "checklist_item_vdr_link", ["checklist_item_id"]
    )
    op.create_index(
        "ix_checklist_vdr_upload", "checklist_item_vdr_link", ["upload_file_id"]
    )

    # ── analysis_run ─────────────────────────────────────────────────
    op.create_table(
        "analysis_run",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("job.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger", sa.String(50), nullable=False, server_default="manual"),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                name="analysisrunstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("input_file_ids", sa.JSON, nullable=True),
        sa.Column(
            "output_checklist_id",
            UUID(as_uuid=True),
            sa.ForeignKey("fdd_checklist.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("progress_percent", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_analysis_run_deal", "analysis_run", ["deal_id"])
    op.create_index("ix_analysis_run_status", "analysis_run", ["status"])

    # ── DealPhase에 CHECKLIST_REVIEW 추가 ────────────────────────────
    op.execute("ALTER TYPE dealphase ADD VALUE IF NOT EXISTS 'CHECKLIST_REVIEW'")

    # ── JobType에 AUTO_ANALYSIS 추가 ─────────────────────────────────
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'AUTO_ANALYSIS'")


def downgrade() -> None:
    op.drop_table("analysis_run")
    op.drop_table("checklist_item_vdr_link")
    op.drop_table("fdd_checklist_item")
    op.drop_table("fdd_checklist")

    op.execute("DROP TYPE IF EXISTS analysisrunstatus")
    op.execute("DROP TYPE IF EXISTS checklistseverity")
    op.execute("DROP TYPE IF EXISTS checklistitemstatus")
    op.execute("DROP TYPE IF EXISTS checklistcategory")
    op.execute("DROP TYPE IF EXISTS checkliststatus")
