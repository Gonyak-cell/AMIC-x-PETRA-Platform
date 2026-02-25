"""Add CLIENT role to userrole enum.

Revision ID: 014
"""

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'CLIENT'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum values; safe to leave in place.
    pass
