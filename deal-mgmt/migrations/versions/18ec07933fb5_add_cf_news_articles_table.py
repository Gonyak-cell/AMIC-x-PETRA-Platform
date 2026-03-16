"""add_cf_news_articles_table

Revision ID: 18ec07933fb5
Revises: 084
Create Date: 2026-03-16 18:14:47.780558

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "18ec07933fb5"
down_revision: str | None = "084"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cf_news_articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("lead_text", sa.Text(), nullable=True),
        sa.Column("markdown_content", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.String(length=2000), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_paywalled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_url"),
        sa.UniqueConstraint("url_hash"),
    )
    op.create_index("ix_cf_news_articles_source", "cf_news_articles", ["source"])
    op.create_index("ix_cf_news_articles_url_hash", "cf_news_articles", ["url_hash"])
    op.create_index("ix_cf_news_source_published", "cf_news_articles", ["source", "published_at"])


def downgrade() -> None:
    op.drop_index("ix_cf_news_source_published", table_name="cf_news_articles")
    op.drop_index("ix_cf_news_articles_url_hash", table_name="cf_news_articles")
    op.drop_index("ix_cf_news_articles_source", table_name="cf_news_articles")
    op.drop_table("cf_news_articles")
