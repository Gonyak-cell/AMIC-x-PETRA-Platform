"""PEF 펀드 레지스트리 pef_name 인덱스 추가.

pef_name 검색 성능 개선을 위한 인덱스.

Revision ID: 049
Revises: 048
"""

from __future__ import annotations

from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_pef_fund_registry_pef_name", "pef_fund_registry", ["pef_name"])


def downgrade() -> None:
    op.drop_index("ix_pef_fund_registry_pef_name", table_name="pef_fund_registry")
