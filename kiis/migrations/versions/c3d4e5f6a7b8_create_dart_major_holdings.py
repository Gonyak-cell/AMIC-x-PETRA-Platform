"""create dart_major_holdings table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dart_major_holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rcept_no", sa.String(20), nullable=False, unique=True, index=True, comment="접수번호"),
        sa.Column("rcept_dt", sa.String(10), nullable=False, index=True, comment="접수일자 (YYYYMMDD)"),
        sa.Column("corp_code", sa.String(20), nullable=False, index=True, comment="피보유 기업 DART 고유번호"),
        sa.Column("corp_name", sa.String(300), nullable=False, comment="피보유 기업명"),
        sa.Column("report_tp", sa.String(20), nullable=True, comment="보고구분"),
        sa.Column("repror", sa.String(300), nullable=False, index=True, comment="대표보고자명"),
        sa.Column("stkqy", sa.String(50), nullable=True, comment="보유주식수"),
        sa.Column("stkrt", sa.String(20), nullable=True, comment="보유비율 (%)"),
        sa.Column("stkqy_irds", sa.String(50), nullable=True, comment="보유주식수 증감"),
        sa.Column("stkrt_irds", sa.String(20), nullable=True, comment="보유비율 증감"),
        sa.Column("ctr_stkqy", sa.String(50), nullable=True, comment="주요체결 주식수"),
        sa.Column("ctr_stkrt", sa.String(20), nullable=True, comment="주요체결 지분율"),
        sa.Column("report_resn", sa.String(200), nullable=True, comment="보고사유"),
        sa.Column(
            "company_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True, index=True, comment="피보유 기업 ID",
        ),
        sa.Column(
            "reporter_company_id", sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True, index=True, comment="보고자(GP) 기업 ID",
        ),
        sa.Column(
            "deal_id", sa.Integer(),
            sa.ForeignKey("deals.id", ondelete="SET NULL"),
            nullable=True, index=True, comment="생성된 딜 ID",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("dart_major_holdings")
