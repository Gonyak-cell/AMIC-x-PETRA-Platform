"""087 add VDR routing override table

Revision ID: 087
Revises: 086
Create Date: 2026-03-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "087"
down_revision: str | None = "086"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "vdr_document_routing_overrides" not in table_names:
        op.create_table(
            "vdr_document_routing_overrides",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("transaction_id", sa.Uuid(), nullable=False),
            sa.Column("vdr_document_id", sa.Uuid(), nullable=False),
            sa.Column("primary_workstream", sa.String(length=30), nullable=False),
            sa.Column("workstream_tags", _JSON, nullable=False),
            sa.Column("override_note", sa.Text(), nullable=True),
            sa.Column("reviewed_by_email", sa.String(length=255), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vdr_document_id"], ["vdr_documents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_vdr_document_routing_overrides_transaction_id"),
            "vdr_document_routing_overrides",
            ["transaction_id"],
        )
        op.create_index(
            op.f("ix_vdr_document_routing_overrides_primary_workstream"),
            "vdr_document_routing_overrides",
            ["primary_workstream"],
        )
        op.create_index(
            op.f("ix_vdr_document_routing_overrides_vdr_document_id"),
            "vdr_document_routing_overrides",
            ["vdr_document_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "vdr_document_routing_overrides" in table_names:
        op.drop_index(
            op.f("ix_vdr_document_routing_overrides_vdr_document_id"),
            table_name="vdr_document_routing_overrides",
        )
        op.drop_index(
            op.f("ix_vdr_document_routing_overrides_primary_workstream"),
            table_name="vdr_document_routing_overrides",
        )
        op.drop_index(
            op.f("ix_vdr_document_routing_overrides_transaction_id"),
            table_name="vdr_document_routing_overrides",
        )
        op.drop_table("vdr_document_routing_overrides")
