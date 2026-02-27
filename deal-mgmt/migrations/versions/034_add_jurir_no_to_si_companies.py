"""si_companies에 jurir_no(법인등록번호), corp_code(사업자등록번호) 컬럼 추가.

Revision ID: 034
Revises: 033
"""

import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("si_companies", sa.Column("jurir_no", sa.String(13), nullable=True))
    op.add_column("si_companies", sa.Column("corp_code", sa.String(10), nullable=True))
    op.create_unique_constraint("uq_si_companies_jurir_no", "si_companies", ["jurir_no"])
    op.create_index("ix_si_companies_jurir_no", "si_companies", ["jurir_no"])


def downgrade() -> None:
    op.drop_index("ix_si_companies_jurir_no", table_name="si_companies")
    op.drop_constraint("uq_si_companies_jurir_no", "si_companies", type_="unique")
    op.drop_column("si_companies", "corp_code")
    op.drop_column("si_companies", "jurir_no")
