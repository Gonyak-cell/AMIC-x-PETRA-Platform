"""092 backfill invalid attachment processing statuses

Revision ID: 092
Revises: 091
Create Date: 2026-04-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "092"
down_revision: str | Sequence[str] | None = "091"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE attachments
        SET processing_status = CASE
            WHEN vdr_document_id IS NOT NULL THEN 'SYNCED'
            WHEN entity_type = 'MARKETING_MATERIAL' THEN 'SKIPPED'
            ELSE 'PENDING'
        END
        WHERE processing_status IS NULL
           OR TRIM(processing_status) = ''
           OR UPPER(TRIM(processing_status)) NOT IN ('PENDING', 'RUNNING', 'SYNCED', 'FAILED', 'SKIPPED')
        """
    )


def downgrade() -> None:
    pass
