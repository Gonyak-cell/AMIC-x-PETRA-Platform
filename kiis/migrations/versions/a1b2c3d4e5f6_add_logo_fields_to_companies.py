"""add logo fields to companies

Revision ID: a1b2c3d4e5f6
Revises: f7a1b2c3d4e5
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "f7a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("logo_url", sa.String(1000), nullable=True, comment="로고 이미지 URL"))
    op.add_column("companies", sa.Column("logo_source", sa.String(30), nullable=True, comment="로고 소스 (og_image/meta_icon/favicon)"))
    op.add_column("companies", sa.Column("logo_fetched_at", sa.DateTime(timezone=True), nullable=True, comment="로고 수집 시각"))


def downgrade() -> None:
    op.drop_column("companies", "logo_fetched_at")
    op.drop_column("companies", "logo_source")
    op.drop_column("companies", "logo_url")
