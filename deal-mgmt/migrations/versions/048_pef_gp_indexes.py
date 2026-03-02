"""PEF 펀드 레지스트리 GP 인덱스 추가.

모델에 선언된 gp1/gp2/gp3 인덱스가 045 마이그레이션에서 누락되었으므로 추가.

Revision ID: 048b
Revises: 048
"""

from __future__ import annotations

from alembic import op

revision = "048b"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_pef_fund_registry_gp1", "pef_fund_registry", ["gp1"])
    op.create_index("ix_pef_fund_registry_gp2", "pef_fund_registry", ["gp2"])
    op.create_index("ix_pef_fund_registry_gp3", "pef_fund_registry", ["gp3"])


def downgrade() -> None:
    op.drop_index("ix_pef_fund_registry_gp3", table_name="pef_fund_registry")
    op.drop_index("ix_pef_fund_registry_gp2", table_name="pef_fund_registry")
    op.drop_index("ix_pef_fund_registry_gp1", table_name="pef_fund_registry")
