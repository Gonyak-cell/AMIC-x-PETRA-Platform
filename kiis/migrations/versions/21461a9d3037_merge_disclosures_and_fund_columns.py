"""merge disclosures and fund_columns

Revision ID: 21461a9d3037
Revises: 380a3e3f150d, 9181478c6ec0
Create Date: 2026-02-17 08:54:22.922220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21461a9d3037'
down_revision: Union[str, None] = ('380a3e3f150d', '9181478c6ec0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
