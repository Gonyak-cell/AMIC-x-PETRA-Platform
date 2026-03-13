"""AWAITING_UPLOAD 상태 추가.

Revision ID: 010_add_awaiting_upload_status
Revises: 009_diagrams
Create Date: 2026-03-13
"""

from alembic import op

revision = "010_add_awaiting_upload_status"
down_revision = "009_diagrams"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """PostgreSQL enum에 AWAITING_UPLOAD 값을 추가한다."""
    op.execute("ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'AWAITING_UPLOAD'")


def downgrade() -> None:
    """PostgreSQL에서 enum 값 삭제는 직접 지원하지 않음 -- 무시."""
    pass
