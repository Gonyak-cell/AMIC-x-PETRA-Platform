"""Set ON DELETE SET NULL for deal team FK columns.

Revision ID: 015
Revises: 014

Allows user deletion without FK constraint errors — deal team
assignments (team_partner_id, team_manager_id) are set to NULL.
"""

from alembic import op
from sqlalchemy import text

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None

# (table, column, constraint_name)
_FK_COLS = [
    ("deals", "team_partner_id", "deals_team_partner_id_fkey"),
    ("deals", "team_manager_id", "deals_team_manager_id_fkey"),
]


def upgrade() -> None:
    for table, col, constraint in _FK_COLS:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, "users", [col], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    for table, col, constraint in _FK_COLS:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, "users", [col], ["id"])
