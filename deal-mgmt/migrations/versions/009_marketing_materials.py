"""009 — marketing_materials 테이블 생성 (TM / DM / IM PPTX 관리)

memo_generator.py 기반 PPTX 생성 자료를 거래별로 관리한다.
- MarketingDocType: TM / DM / IM
- MarketingDocStatus: DRAFT / GENERATING / READY / FAILED
- distributed_to JSONB: 배포 대상 추적

Revision ID: 009_marketing
Revises: 008_indexes
Create Date: 2026-02-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_marketing"
down_revision: Union[str, None] = "008_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum 타입 생성 (asyncpg 호환 — DO $$ 패턴) ──────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE marketingdoctype AS ENUM ('TM', 'DM', 'IM');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE marketingdocstatus AS ENUM ('DRAFT', 'GENERATING', 'READY', 'FAILED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    # ── 테이블 생성 ────────────────────────────────────────────
    op.create_table(
        "marketing_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("transactions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("doc_type",
                  postgresql.ENUM("TM", "DM", "IM", name="marketingdoctype", create_type=False),
                  nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("project_code", sa.String(100), nullable=True),
        sa.Column("status",
                  postgresql.ENUM("DRAFT", "GENERATING", "READY", "FAILED", name="marketingdocstatus", create_type=False),
                  nullable=False, server_default="DRAFT"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("distributed_to", postgresql.JSONB, nullable=True),
        sa.Column("distributed_at", sa.String(50), nullable=True),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )

    # ── 인덱스 ─────────────────────────────────────────────────
    op.create_index("ix_marketing_materials_transaction_id",
                    "marketing_materials", ["transaction_id"])
    op.create_index("ix_marketing_materials_doc_type_status",
                    "marketing_materials", ["doc_type", "status"])
    op.create_index("ix_marketing_materials_created_at",
                    "marketing_materials", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_marketing_materials_created_at", table_name="marketing_materials")
    op.drop_index("ix_marketing_materials_doc_type_status", table_name="marketing_materials")
    op.drop_index("ix_marketing_materials_transaction_id", table_name="marketing_materials")
    op.drop_table("marketing_materials")

    op.execute("DROP TYPE IF EXISTS marketingdocstatus")
    op.execute("DROP TYPE IF EXISTS marketingdoctype")
