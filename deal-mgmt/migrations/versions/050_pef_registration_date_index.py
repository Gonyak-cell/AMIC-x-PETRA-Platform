"""PEF 펀드 레지스트리 registration_date 인덱스 추가.

FI 자동 매핑 알고리즘에서 registration_date >= '2021-01-01' 필터링 성능 개선.

Revision ID: 050
Revises: 049
"""

from __future__ import annotations

from alembic import op

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_pef_fund_registry_reg_date",
        "pef_fund_registry",
        ["registration_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_pef_fund_registry_reg_date", table_name="pef_fund_registry")
