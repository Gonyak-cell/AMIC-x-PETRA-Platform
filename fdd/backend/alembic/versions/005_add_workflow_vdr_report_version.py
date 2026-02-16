"""Sprint 13: Add workflow columns, VDR folders, report versions.

Revision ID: 005_workflow_vdr_rv
Revises: 004_sprint11_p2_4
Create Date: 2026-02-09

New columns on `deal`:
  - client_name, client_contact_name, client_contact_email, target_company_name
  - team_partner_id (FK user.id), team_manager_id (FK user.id)
  - scope_qoe, scope_nwc, scope_debt (boolean defaults true)
  - current_phase (varchar default 'MOU')

New tables:
  - vdr_folder  — Virtual Data Room folder hierarchy
  - report_version — versioned report snapshots

New column on `upload_file`:
  - vdr_folder_id (FK vdr_folder.id SET NULL)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_workflow_vdr_rv"
down_revision: str | None = "004_sprint11_p2_4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Deal table: workflow columns ──────────────────────
    op.add_column("deal", sa.Column("client_name", sa.String(255), nullable=True))
    op.add_column(
        "deal", sa.Column("client_contact_name", sa.String(255), nullable=True)
    )
    op.add_column(
        "deal", sa.Column("client_contact_email", sa.String(255), nullable=True)
    )
    op.add_column(
        "deal", sa.Column("target_company_name", sa.String(255), nullable=True)
    )

    op.add_column(
        "deal",
        sa.Column(
            "team_partner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "deal",
        sa.Column(
            "team_manager_id",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )

    op.add_column(
        "deal",
        sa.Column(
            "scope_qoe", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    op.add_column(
        "deal",
        sa.Column(
            "scope_nwc", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    op.add_column(
        "deal",
        sa.Column(
            "scope_debt", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )

    # Use VARCHAR instead of PostgreSQL ENUM for SQLite test compatibility
    op.add_column(
        "deal",
        sa.Column(
            "current_phase",
            sa.String(50),
            nullable=False,
            server_default="MOU",
        ),
    )

    # ── 2. vdr_folder table ──────────────────────────────────
    op.create_table(
        "vdr_folder",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "deal_id",
            sa.Uuid(),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("vdr_folder.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("folder_type", sa.String(50), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")
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
    op.create_index("ix_vdr_folder_deal_id", "vdr_folder", ["deal_id"])

    # ── 3. report_version table ──────────────────────────────
    op.create_table(
        "report_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "deal_id",
            sa.Uuid(),
            sa.ForeignKey("deal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="DRAFT"),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("file_format", sa.String(10), nullable=False, server_default="pptx"),
        sa.Column("options", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_report_version_deal_id", "report_version", ["deal_id"])

    # ── 4. upload_file: add vdr_folder_id ────────────────────
    op.add_column(
        "upload_file",
        sa.Column(
            "vdr_folder_id",
            sa.Uuid(),
            sa.ForeignKey("vdr_folder.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # upload_file
    op.drop_column("upload_file", "vdr_folder_id")

    # report_version
    op.drop_index("ix_report_version_deal_id", table_name="report_version")
    op.drop_table("report_version")

    # vdr_folder
    op.drop_index("ix_vdr_folder_deal_id", table_name="vdr_folder")
    op.drop_table("vdr_folder")

    # deal workflow columns
    op.drop_column("deal", "current_phase")
    op.drop_column("deal", "scope_debt")
    op.drop_column("deal", "scope_nwc")
    op.drop_column("deal", "scope_qoe")
    op.drop_column("deal", "team_manager_id")
    op.drop_column("deal", "team_partner_id")
    op.drop_column("deal", "target_company_name")
    op.drop_column("deal", "client_contact_email")
    op.drop_column("deal", "client_contact_name")
    op.drop_column("deal", "client_name")
