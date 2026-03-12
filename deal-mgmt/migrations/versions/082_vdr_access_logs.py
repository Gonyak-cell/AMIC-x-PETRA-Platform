"""VDR 접근 추적 로그 테이블 추가.

Revision ID: 082
Revises: 081
Create Date: 2026-03-12
"""

import sqlalchemy as sa
from alembic import op

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vdr_access_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("folder_id", sa.Uuid(), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column(
            "action",
            sa.Enum("VIEW", "DOWNLOAD", "UPLOAD", name="vdraccessaction"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("buyer_id", sa.Uuid(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["vdr_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["folder_id"], ["vdr_folders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyer_candidates.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_vdr_access_logs_transaction_id",
        "vdr_access_logs",
        ["transaction_id"],
    )
    op.create_index("ix_vdr_access_logs_document_id", "vdr_access_logs", ["document_id"])
    op.create_index("ix_vdr_access_logs_user_email", "vdr_access_logs", ["user_email"])
    op.create_index("ix_vdr_access_logs_buyer_id", "vdr_access_logs", ["buyer_id"])
    op.create_index(
        "ix_vdr_access_logs_txn_email",
        "vdr_access_logs",
        ["transaction_id", "user_email"],
    )
    op.create_index(
        "ix_vdr_access_logs_txn_buyer",
        "vdr_access_logs",
        ["transaction_id", "buyer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_vdr_access_logs_txn_buyer", "vdr_access_logs")
    op.drop_index("ix_vdr_access_logs_txn_email", "vdr_access_logs")
    op.drop_index("ix_vdr_access_logs_buyer_id", "vdr_access_logs")
    op.drop_index("ix_vdr_access_logs_user_email", "vdr_access_logs")
    op.drop_index("ix_vdr_access_logs_document_id", "vdr_access_logs")
    op.drop_index("ix_vdr_access_logs_transaction_id", "vdr_access_logs")
    op.drop_table("vdr_access_logs")
    op.execute("DROP TYPE IF EXISTS vdraccessaction")
