"""Add token_blacklist table for JWT revocation.

Revision ID: 011_token_blacklist
Revises: 010_fk_indexes
Create Date: 2026-02-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_token_blacklist"
down_revision: str | None = "010_fk_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "token_blacklist",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("jti", sa.String(36), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_type", sa.String(10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_token_blacklist_jti", "token_blacklist", ["jti"], unique=True
    )
    op.create_index(
        "ix_token_blacklist_expires", "token_blacklist", ["expires_at"]
    )
    op.create_index(
        "ix_token_blacklist_user", "token_blacklist", ["user_id"]
    )


def downgrade() -> None:
    op.drop_table("token_blacklist")
