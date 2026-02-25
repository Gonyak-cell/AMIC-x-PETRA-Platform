"""Add title column to users table.

Revision ID: 013
Revises: 012_deal_classify
"""

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012_deal_classify"


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    columns = [c["name"] for c in inspect(conn).get_columns("users")]
    if "title" not in columns:
        op.add_column(
            "users",
            sa.Column("title", sa.String(100), nullable=False, server_default=""),
        )


def downgrade() -> None:
    op.drop_column("users", "title")
