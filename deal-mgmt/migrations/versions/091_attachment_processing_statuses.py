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
    op.add_column(
        "attachments",
        sa.Column(
            "processing_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column("attachments", sa.Column("processing_error", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE attachments
        SET processing_status = CASE
            WHEN vdr_document_id IS NOT NULL THEN 'SYNCED'
            ELSE 'SKIPPED'
        END
        """
    )

    op.add_column("nda_markups", sa.Column("attachment_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_nda_markups_attachment_id_attachments",
        "nda_markups",
        "attachments",
        ["attachment_id"],
        ["id"],
        ondelete="SET NULL",
    )
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
