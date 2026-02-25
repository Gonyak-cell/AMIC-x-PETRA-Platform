"""Add title column to users table.

Revision ID: 004_add_user_title
Revises: 003_add_data_source
"""

from alembic import op
import sqlalchemy as sa

revision = "004_add_user_title"
down_revision = "003_add_data_source"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("title", sa.String(100), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("users", "title")
