"""add kofia_last_synced to funds

Revision ID: bd86aed05da0
Revises: 21461a9d3037
Create Date: 2026-02-17 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd86aed05da0'
down_revision: Union[str, None] = '21461a9d3037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('funds', sa.Column(
        'kofia_last_synced',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='KOFIA 마지막 동기화 시각',
    ))


def downgrade() -> None:
    op.drop_column('funds', 'kofia_last_synced')
