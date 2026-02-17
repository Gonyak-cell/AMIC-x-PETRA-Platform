"""add fund_id to deals

Revision ID: 8c2f8cc1babc
Revises: df25553292c9
Create Date: 2026-02-17 11:46:38.864610

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8c2f8cc1babc'
down_revision: str | None = 'df25553292c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'deals',
        sa.Column(
            'fund_id',
            sa.Integer(),
            sa.ForeignKey('funds.id', ondelete='SET NULL'),
            nullable=True,
            comment='펀드 ID (펀드 단위 딜 추적)',
        ),
    )
    op.create_index(op.f('ix_deals_fund_id'), 'deals', ['fund_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_deals_fund_id'), table_name='deals')
    op.drop_column('deals', 'fund_id')
