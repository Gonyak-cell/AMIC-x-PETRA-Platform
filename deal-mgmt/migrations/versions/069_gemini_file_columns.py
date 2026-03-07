"""069 — Gemini File API 캐시 컬럼 추가

VDR 문서의 Gemini File API 업로드 URI와 만료 시각을 캐싱하기 위한 컬럼.
- gemini_file_uri: Gemini에 업로드된 파일 URI (48h TTL)
- gemini_file_expires_at: 파일 만료 시각

Revision ID: 069
Revises: 068
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vdr_documents", sa.Column("gemini_file_uri", sa.String(500), nullable=True))
    op.add_column("vdr_documents", sa.Column("gemini_file_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("vdr_documents", "gemini_file_expires_at")
    op.drop_column("vdr_documents", "gemini_file_uri")
