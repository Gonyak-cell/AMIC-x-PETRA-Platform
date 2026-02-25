"""Phase 6 — legal_documents 테이블 (SPA/SHA/BTA/SSA/MOU 생성)

Revision ID: 007_phase6
Revises: 006_phase5b
Create Date: 2026-02-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_phase6"
down_revision: Union[str, None] = "006_phase5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ──
    legal_doc_type = sa.Enum(
        "SPA", "SHA", "BTA", "SSA", "MOU",
        name="legaldoctype",
    )
    legal_doc_status = sa.Enum(
        "DRAFT", "GENERATING", "READY", "FAILED",
        name="legaldocstatus",
    )

    # ── legal_documents 테이블 ──
    op.create_table(
        "legal_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("doc_type", legal_doc_type, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", legal_doc_status, nullable=False, server_default="DRAFT"),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("template_version", sa.String(20), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_by_email", sa.String(255), nullable=True),
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

    # updated_at 자동 갱신 트리거 (PostgreSQL) — asyncpg는 다중 명령 불가
    op.execute("""
        CREATE OR REPLACE FUNCTION update_legal_documents_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_legal_documents_updated_at
        BEFORE UPDATE ON legal_documents
        FOR EACH ROW
        EXECUTE FUNCTION update_legal_documents_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_legal_documents_updated_at ON legal_documents")
    op.execute("DROP FUNCTION IF EXISTS update_legal_documents_updated_at()")
    op.drop_table("legal_documents")
    op.execute("DROP TYPE IF EXISTS legaldocstatus")
    op.execute("DROP TYPE IF EXISTS legaldoctype")
