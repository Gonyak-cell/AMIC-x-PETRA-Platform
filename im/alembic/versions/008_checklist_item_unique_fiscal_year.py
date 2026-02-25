"""add fiscal_year to im_checklist_items unique constraint

Revision ID: 008_checklist_item_unique_fiscal_year
Revises: 007_im_ralph_sessions
Create Date: 2026-02-25
"""

from alembic import op

revision = "008_checklist_item_unique_fiscal_year"
down_revision = "007_im_ralph_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_im_checklist_items_checklist_field",
        "im_checklist_items",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_im_checklist_items_checklist_field_year",
        "im_checklist_items",
        ["checklist_id", "field_key", "fiscal_year"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_im_checklist_items_checklist_field_year",
        "im_checklist_items",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_im_checklist_items_checklist_field",
        "im_checklist_items",
        ["checklist_id", "field_key"],
    )
