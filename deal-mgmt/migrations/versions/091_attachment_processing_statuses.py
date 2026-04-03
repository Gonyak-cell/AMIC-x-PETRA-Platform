"""091 add attachment processing state and nda markup attachment link

Revision ID: 091
Revises: 090
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "091"
down_revision: str | None = "090"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    attachment_columns = {column["name"] for column in inspector.get_columns("attachments")}
    if "processing_status" not in attachment_columns:
        op.add_column(
            "attachments",
            sa.Column(
                "processing_status",
                sa.String(length=20),
                nullable=False,
                server_default="PENDING",
            ),
        )
    if "processing_error" not in attachment_columns:
        op.add_column("attachments", sa.Column("processing_error", sa.Text(), nullable=True))

    update_where_clause = ""
    if "processing_status" in attachment_columns:
        update_where_clause = """
        WHERE processing_status IS NULL
           OR TRIM(processing_status) = ''
           OR UPPER(TRIM(processing_status)) NOT IN ('PENDING', 'RUNNING', 'SYNCED', 'FAILED', 'SKIPPED')
        """

    op.execute(
        f"""
        UPDATE attachments
        SET processing_status = CASE
            WHEN vdr_document_id IS NOT NULL THEN 'SYNCED'
            WHEN entity_type = 'MARKETING_MATERIAL' THEN 'SKIPPED'
            ELSE 'PENDING'
        END
        {update_where_clause}
        """
    )

    nda_markup_columns = {column["name"] for column in inspector.get_columns("nda_markups")}
    if "attachment_id" not in nda_markup_columns:
        op.add_column("nda_markups", sa.Column("attachment_id", sa.Uuid(), nullable=True))

    existing_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("nda_markups")}
    if "fk_nda_markups_attachment_id_attachments" not in existing_foreign_keys:
        op.create_foreign_key(
            "fk_nda_markups_attachment_id_attachments",
            "nda_markups",
            "attachments",
            ["attachment_id"],
            ["id"],
            ondelete="SET NULL",
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("nda_markups")}
    if "ix_nda_markups_attachment_id" not in existing_indexes:
        op.create_index(
            "ix_nda_markups_attachment_id",
            "nda_markups",
            ["attachment_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_nda_markups_attachment_id", table_name="nda_markups")
    op.drop_constraint("fk_nda_markups_attachment_id_attachments", "nda_markups", type_="foreignkey")
    op.drop_column("nda_markups", "attachment_id")

    op.drop_column("attachments", "processing_error")
    op.drop_column("attachments", "processing_status")
