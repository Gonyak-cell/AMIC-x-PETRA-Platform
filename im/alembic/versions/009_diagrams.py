"""create diagrams table

Revision ID: 009_diagrams
Revises: 008_checklist_uq_fiscal_yr
Create Date: 2026-03-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009_diagrams"
down_revision = "008_checklist_uq_fiscal_yr"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagrams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("diagram_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "excalidraw_data",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
        sa.Column("png_path", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diagrams_document_type",
        "diagrams",
        ["document_id", "diagram_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_diagrams_document_type", table_name="diagrams")
    op.drop_table("diagrams")
