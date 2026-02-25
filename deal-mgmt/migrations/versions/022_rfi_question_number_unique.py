"""022: RFI 아이템 question_number 복합 유니크 제약 추가.

Revision ID: 022_rfi_uq
Revises: 021_rfi
Create Date: 2026-02-25
"""

from alembic import op

revision = "022_rfi_uq"
down_revision = "021_rfi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_rfi_items_rfi_id_question_number",
        "rfi_items",
        ["rfi_id", "question_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_rfi_items_rfi_id_question_number", "rfi_items", type_="unique")
