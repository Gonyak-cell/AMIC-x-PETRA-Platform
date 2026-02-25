"""Phase 8 — VDR (Virtual Data Room) 폴더 및 문서 관리

Revision ID: 014_vdr
Revises: 013
Create Date: 2026-02-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014_vdr"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ──
    vdr_folder_category = sa.Enum(
        "CORPORATE", "FINANCIAL", "LEGAL", "TAX", "HR", "TECHNICAL",
        "COMMERCIAL", "REAL_ESTATE", "ENVIRONMENT", "IP",
        "INSURANCE", "CUSTOM",
        name="vdrfoldercategory",
    )
    vdr_document_status = sa.Enum(
        "ACTIVE", "ARCHIVED", "DELETED",
        name="vdrdocumentstatus",
    )

    # ── vdr_folders 테이블 ──
    op.create_table(
        "vdr_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vdr_folders.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", vdr_folder_category, nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("description", sa.String(500), nullable=True),
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

    # ── vdr_documents 테이블 ──
    op.create_table(
        "vdr_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "folder_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vdr_folders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("original_name", sa.String(500), nullable=False),
        sa.Column("stored_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "mime_type",
            sa.String(100),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column(
            "status",
            vdr_document_status,
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("uploaded_by_email", sa.String(255), nullable=True),
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

    # ── 복합 인덱스 ──
    op.create_index(
        "ix_vdr_folders_txn_parent", "vdr_folders", ["transaction_id", "parent_id"]
    )
    op.create_index(
        "ix_vdr_documents_folder", "vdr_documents", ["folder_id", "status"]
    )
    op.create_index(
        "ix_vdr_documents_hash", "vdr_documents", ["transaction_id", "sha256_hash"]
    )

    # ── updated_at 자동 갱신 트리거 ──
    for table in ("vdr_folders", "vdr_documents"):
        op.execute(f"""
            CREATE OR REPLACE FUNCTION update_{table}_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
            $$ LANGUAGE plpgsql
        """)
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_{table}_updated_at()
        """)


def downgrade() -> None:
    for table in ("vdr_documents", "vdr_folders"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
        op.execute(f"DROP FUNCTION IF EXISTS update_{table}_updated_at()")
    op.drop_index("ix_vdr_documents_hash")
    op.drop_index("ix_vdr_documents_folder")
    op.drop_index("ix_vdr_folders_txn_parent")
    op.drop_table("vdr_documents")
    op.drop_table("vdr_folders")
    op.execute("DROP TYPE IF EXISTS vdrdocumentstatus")
    op.execute("DROP TYPE IF EXISTS vdrfoldercategory")
