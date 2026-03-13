"""기존 품질 실패 문서 상태 정합화.

status=COMPLETED + quality_status=FAIL인 기존 데이터를
status=QUALITY_FAILED로 변환한다.

Revision ID: 012_quality_failed_status
Revises: 011_add_quality_gate_columns
Create Date: 2026-03-13
"""

from alembic import op

revision = "012_quality_failed_status"
down_revision = "011_add_quality_gate_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE documents SET status = 'QUALITY_FAILED' "
        "WHERE status = 'COMPLETED' AND quality_status = 'FAIL'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE documents SET status = 'COMPLETED' WHERE status = 'QUALITY_FAILED'"
    )
