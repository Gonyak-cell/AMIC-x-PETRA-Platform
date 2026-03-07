"""070 — VcCompany 재무정보 컬럼 추가

금융위원회 기업재무정보 API(GetFinaStatInfoService_V2) 데이터를 저장하기 위한 컬럼.
- operating_profit: 영업이익(억원)
- net_income: 당기순이익(억원)
- total_assets: 자산총계(억원)
- total_debt: 부채총계(억원)
- total_equity: 자본총계(억원)
- capital: 자본금(억원)
- debt_ratio: 부채비율(%)

Revision ID: 070
Revises: 069
Create Date: 2026-03-07
"""

import sqlalchemy as sa
from alembic import op

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vc_companies", sa.Column("operating_profit", sa.Numeric(20, 2), nullable=True, comment="영업이익(억원)")
    )
    op.add_column("vc_companies", sa.Column("net_income", sa.Numeric(20, 2), nullable=True, comment="당기순이익(억원)"))
    op.add_column("vc_companies", sa.Column("total_assets", sa.Numeric(20, 2), nullable=True, comment="자산총계(억원)"))
    op.add_column("vc_companies", sa.Column("total_debt", sa.Numeric(20, 2), nullable=True, comment="부채총계(억원)"))
    op.add_column("vc_companies", sa.Column("total_equity", sa.Numeric(20, 2), nullable=True, comment="자본총계(억원)"))
    op.add_column("vc_companies", sa.Column("capital", sa.Numeric(20, 2), nullable=True, comment="자본금(억원)"))
    op.add_column("vc_companies", sa.Column("debt_ratio", sa.Numeric(10, 2), nullable=True, comment="부채비율(%)"))


def downgrade() -> None:
    op.drop_column("vc_companies", "debt_ratio")
    op.drop_column("vc_companies", "capital")
    op.drop_column("vc_companies", "total_equity")
    op.drop_column("vc_companies", "total_debt")
    op.drop_column("vc_companies", "total_assets")
    op.drop_column("vc_companies", "net_income")
    op.drop_column("vc_companies", "operating_profit")
