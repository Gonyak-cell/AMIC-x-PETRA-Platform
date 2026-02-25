"""Add title column to users table.

Revision ID: add_user_title
Revises: a3b7c9d1e4f2
"""

from alembic import op
import sqlalchemy as sa

revision = "add_user_title"
down_revision = "a3b7c9d1e4f2"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("title", sa.String(100), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("users", "title")
