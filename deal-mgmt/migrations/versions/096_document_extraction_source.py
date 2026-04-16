"""Add extraction source metadata.

Revision ID: 096
Revises: 095
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "096"
down_revision = "095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_extractions",
        sa.Column(
            "extraction_source",
            sa.String(length=30),
            nullable=False,
            server_default="LLM",
        ),
    )
    op.add_column("document_extractions", sa.Column("processing_note", sa.Text(), nullable=True))
    op.alter_column("document_extractions", "extraction_source", server_default=None)


def downgrade() -> None:
    op.drop_column("document_extractions", "processing_note")
    op.drop_column("document_extractions", "extraction_source")
