"""Round 3 코드 리뷰 — 성능 인덱스 추가.

si_companies: revenue, has_investment_history 인덱스
buyer_marketing_logs: (buyer_id, transaction_id) 복합 인덱스 + log_date 인덱스

Revision ID: 050b
Revises: 050
"""

from __future__ import annotations

from alembic import op

revision = "050b"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_si_companies_revenue", "si_companies", ["revenue"])
    op.create_index(
        "ix_si_companies_has_investment_history",
        "si_companies",
        ["has_investment_history"],
    )
    op.create_index(
        "ix_buyer_marketing_logs_buyer_txn",
        "buyer_marketing_logs",
        ["buyer_id", "transaction_id"],
    )
    op.create_index(
        "ix_buyer_marketing_logs_log_date",
        "buyer_marketing_logs",
        ["log_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_buyer_marketing_logs_log_date", table_name="buyer_marketing_logs")
    op.drop_index("ix_buyer_marketing_logs_buyer_txn", table_name="buyer_marketing_logs")
    op.drop_index("ix_si_companies_has_investment_history", table_name="si_companies")
    op.drop_index("ix_si_companies_revenue", table_name="si_companies")
