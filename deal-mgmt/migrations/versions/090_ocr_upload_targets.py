"""090 add OCR upload target columns and categories

Revision ID: 090
Revises: 089
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "090"
down_revision: str | None = "089"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE docextractioncategory ADD VALUE IF NOT EXISTS 'ENGAGEMENT_CONTRACT'")

    op.add_column("engagements", sa.Column("counterparty_name", sa.String(length=200), nullable=True))
    op.add_column("engagements", sa.Column("service_scope_summary", sa.Text(), nullable=True))

    op.add_column(
        "marketing_materials",
        sa.Column(
            "source_mode",
            sa.String(length=20),
            nullable=False,
            server_default="GENERATED",
        ),
    )
    op.add_column("marketing_materials", sa.Column("attachment_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_marketing_materials_attachment_id_attachments",
        "marketing_materials",
        "attachments",
        ["attachment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_marketing_materials_attachment_id",
        "marketing_materials",
        ["attachment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_materials_attachment_id", table_name="marketing_materials")
    op.drop_constraint("fk_marketing_materials_attachment_id_attachments", "marketing_materials", type_="foreignkey")
    op.drop_column("marketing_materials", "attachment_id")
    op.drop_column("marketing_materials", "source_mode")

    op.drop_column("engagements", "service_scope_summary")
    op.drop_column("engagements", "counterparty_name")
