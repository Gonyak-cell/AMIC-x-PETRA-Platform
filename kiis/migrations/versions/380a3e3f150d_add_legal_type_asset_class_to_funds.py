"""add legal_type asset_class to funds

Revision ID: 380a3e3f150d
Revises: 8c2f8cc1babc
Create Date: 2026-02-17 15:29:32.559710

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '380a3e3f150d'
down_revision: str | None = '8c2f8cc1babc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 법률상 유형 컬럼 추가
    op.add_column(
        'funds',
        sa.Column(
            'legal_type',
            sa.String(length=30),
            nullable=True,
            comment='법률상 유형 (professional_private/general_private/public)',
        ),
    )
    op.create_index(op.f('ix_funds_legal_type'), 'funds', ['legal_type'], unique=False)

    # 자산 유형 컬럼 추가
    op.add_column(
        'funds',
        sa.Column(
            'asset_class',
            sa.String(length=30),
            nullable=True,
            comment='자산 유형 (vc/pef/real_estate/infra/mezzanine/fund_of_funds)',
        ),
    )
    op.create_index(op.f('ix_funds_asset_class'), 'funds', ['asset_class'], unique=False)

    # 기존 데이터에 기본값 설정
    op.execute("UPDATE funds SET legal_type = 'general_private' WHERE legal_type IS NULL")
    op.execute("UPDATE funds SET asset_class = 'vc' WHERE fund_category = 'VC' AND asset_class IS NULL")
    op.execute("UPDATE funds SET asset_class = 'pef' WHERE fund_category = 'PEF' AND asset_class IS NULL")
    op.execute("UPDATE funds SET asset_class = 'vc' WHERE asset_class IS NULL")


def downgrade() -> None:
    op.drop_index(op.f('ix_funds_asset_class'), table_name='funds')
    op.drop_column('funds', 'asset_class')
    op.drop_index(op.f('ix_funds_legal_type'), table_name='funds')
    op.drop_column('funds', 'legal_type')
