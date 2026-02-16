"""Add partial unique index on documents.corp_code for active documents.

Prevents concurrent generation for the same corp_code (TOCTOU fix).

Revision ID: 002_active_corpcode
Revises: 001_initial
Create Date: 2026-02-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_active_corpcode"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_documents_corp_code_active
        ON documents (corp_code)
        WHERE status IN ('PENDING', 'COLLECTING', 'ANALYZING', 'GENERATING', 'RENDERING')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_documents_corp_code_active")
