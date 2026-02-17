"""Add data_source column, make corp_code nullable.

Session 25에서 IM 모듈 corp_code 필수 → 선택사항 전환 시 모델만 변경하고
마이그레이션을 누락한 것을 보완.

Revision ID: 003_add_data_source
Revises: 002_active_corpcode
Create Date: 2026-02-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_data_source"
down_revision: str | None = "002_active_corpcode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add data_source column with default "DART" for existing rows
    op.add_column(
        "documents",
        sa.Column("data_source", sa.String(20), server_default="DART", nullable=False),
    )

    # 2. Make corp_code nullable (was NOT NULL in 001_initial)
    op.alter_column(
        "documents",
        "corp_code",
        existing_type=sa.String(8),
        nullable=True,
    )

    # 3. Update partial unique index to exclude NULL corp_code
    op.execute("DROP INDEX IF EXISTS uq_documents_corp_code_active")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_documents_corp_code_active
        ON documents (corp_code)
        WHERE corp_code IS NOT NULL
          AND status IN ('PENDING', 'COLLECTING', 'ANALYZING', 'GENERATING', 'RENDERING')
        """
    )


def downgrade() -> None:
    # Restore original partial unique index
    op.execute("DROP INDEX IF EXISTS uq_documents_corp_code_active")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_documents_corp_code_active
        ON documents (corp_code)
        WHERE status IN ('PENDING', 'COLLECTING', 'ANALYZING', 'GENERATING', 'RENDERING')
        """
    )

    # Make corp_code NOT NULL again
    op.alter_column(
        "documents",
        "corp_code",
        existing_type=sa.String(8),
        nullable=False,
    )

    # Remove data_source column
    op.drop_column("documents", "data_source")
