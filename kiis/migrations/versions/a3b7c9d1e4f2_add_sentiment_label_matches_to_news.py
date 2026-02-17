"""add sentiment_label and sentiment_matches to news_articles

Revision ID: a3b7c9d1e4f2
Revises: bd86aed05da0
Create Date: 2026-02-17 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b7c9d1e4f2'
down_revision: Union[str, None] = 'bd86aed05da0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'news_articles',
        sa.Column(
            'sentiment_label',
            sa.String(20),
            nullable=True,
            comment='감성 레이블 (positive/negative/neutral)',
        ),
    )
    op.add_column(
        'news_articles',
        sa.Column(
            'sentiment_matches',
            sa.Text(),
            nullable=True,
            comment='감성 매칭 결과 (JSON: {positive_matches, negative_matches})',
        ),
    )


def downgrade() -> None:
    op.drop_column('news_articles', 'sentiment_matches')
    op.drop_column('news_articles', 'sentiment_label')
