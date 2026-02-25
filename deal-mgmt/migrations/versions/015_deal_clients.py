"""deal_clients junction table for CLIENT role access control.

Revision ID: 015
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "015"
down_revision = "014_vdr"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("organization", sa.String(200), nullable=True),
        sa.Column("added_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("transaction_id", "email", name="uq_deal_client_txn_email"),
    )
    op.create_index("ix_deal_clients_transaction_id", "deal_clients", ["transaction_id"])
    op.create_index("ix_deal_clients_email", "deal_clients", ["email"])


def downgrade() -> None:
    op.drop_table("deal_clients")
