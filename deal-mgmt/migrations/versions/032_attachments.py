"""범용 첨부파일(attachments) 테이블 생성.

Revision ID: 032
Revises: 031
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(300), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False, server_default="application/octet-stream"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_attachments_transaction_id", "attachments", ["transaction_id"])
    op.create_index("ix_attachments_entity_type", "attachments", ["entity_type"])
    op.create_index("ix_attachments_entity_id", "attachments", ["entity_id"])
    op.create_index(
        "ix_attachments_txn_entity",
        "attachments",
        ["transaction_id", "entity_type", "entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_attachments_txn_entity")
    op.drop_index("ix_attachments_entity_id")
    op.drop_index("ix_attachments_entity_type")
    op.drop_index("ix_attachments_transaction_id")
    op.drop_table("attachments")
