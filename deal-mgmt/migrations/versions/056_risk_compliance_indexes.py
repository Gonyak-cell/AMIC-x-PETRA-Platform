"""Add composite indexes on risk_items and compliance_items.

Revision ID: 056
Revises: 055
"""

from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_risk_items_txn_sev_status",
        "risk_items",
        ["transaction_id", "severity", "status"],
    )
    op.create_index(
        "ix_compliance_items_txn_status",
        "compliance_items",
        ["transaction_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_items_txn_status", table_name="compliance_items")
    op.drop_index("ix_risk_items_txn_sev_status", table_name="risk_items")
