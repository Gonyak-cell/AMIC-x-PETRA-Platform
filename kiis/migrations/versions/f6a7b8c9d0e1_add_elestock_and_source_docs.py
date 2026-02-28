"""add elestock table and disclosure_id FK

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. dart_executive_holdings 테이블 생성
    op.create_table(
        "dart_executive_holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "rcept_no",
            sa.String(20),
            nullable=False,
            unique=True,
            index=True,
            comment="접수번호 (중복 방지 키)",
        ),
        sa.Column("rcept_dt", sa.String(10), nullable=False, index=True, comment="접수일자 (YYYYMMDD)"),
        sa.Column("corp_code", sa.String(20), nullable=False, index=True, comment="대상 기업 DART 고유번호"),
        sa.Column("corp_name", sa.String(300), nullable=False, comment="법인명"),
        sa.Column("repror", sa.String(300), nullable=False, index=True, comment="보고자명"),
        # 임원/주요주주 구분
        sa.Column("isu_exctv_rgist_at", sa.String(5), nullable=True, comment="임원 등록 여부 (Y/N)"),
        sa.Column("isu_exctv_ofcps", sa.String(100), nullable=True, comment="직책"),
        sa.Column("isu_main_shrholdr", sa.String(5), nullable=True, comment="주요주주 여부 (Y/N)"),
        # 주식 보유 현황
        sa.Column("sp_stock_lmp_cnt", sa.String(50), nullable=True, comment="소유 주식수"),
        sa.Column("sp_stock_lmp_irds_cnt", sa.String(50), nullable=True, comment="소유 주식수 증감"),
        sa.Column("sp_stock_lmp_rate", sa.String(20), nullable=True, comment="소유 비율 (%)"),
        sa.Column("sp_stock_lmp_irds_rate", sa.String(20), nullable=True, comment="소유 비율 증감"),
        sa.Column("ctr_stkqy", sa.String(50), nullable=True, comment="특정증권등 소유 주식수"),
        sa.Column("ctr_stkrt", sa.String(20), nullable=True, comment="특정증권등 소유 비율"),
        sa.Column("report_resn", sa.String(200), nullable=True, comment="변동사유"),
        # FK
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="대상 기업 ID",
        ),
        sa.Column(
            "reporter_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="보고자 소속 기업 ID",
        ),
        sa.Column(
            "deal_id",
            sa.Integer(),
            sa.ForeignKey("deals.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="생성된 딜 ID",
        ),
        sa.Column(
            "disclosure_id",
            sa.Integer(),
            sa.ForeignKey("disclosures.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="원문 공시 ID (감사추적)",
        ),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. deals 테이블에 disclosure_id 추가
    with op.batch_alter_table("deals") as batch_op:
        batch_op.add_column(
            sa.Column(
                "disclosure_id",
                sa.Integer(),
                sa.ForeignKey("disclosures.id", ondelete="SET NULL"),
                nullable=True,
                comment="원문 공시 ID (감사추적)",
            )
        )
        batch_op.create_index("ix_deals_disclosure_id", ["disclosure_id"])

    # 3. dart_major_holdings 테이블에 disclosure_id 추가
    with op.batch_alter_table("dart_major_holdings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "disclosure_id",
                sa.Integer(),
                sa.ForeignKey("disclosures.id", ondelete="SET NULL"),
                nullable=True,
                comment="원문 공시 ID (감사추적)",
            )
        )
        batch_op.create_index("ix_dart_major_holdings_disclosure_id", ["disclosure_id"])


def downgrade() -> None:
    # ⚠️ 경고: dart_executive_holdings 테이블 DROP 시 모든 임원소유보고 데이터가 삭제됩니다.
    # deals/dart_major_holdings의 disclosure_id 컬럼 DROP 시 원문 공시 연결 정보가 손실됩니다.
    # 프로덕션에서 실행 전 반드시 데이터 백업을 수행하세요.
    with op.batch_alter_table("dart_major_holdings") as batch_op:
        batch_op.drop_index("ix_dart_major_holdings_disclosure_id")
        batch_op.drop_column("disclosure_id")

    with op.batch_alter_table("deals") as batch_op:
        batch_op.drop_index("ix_deals_disclosure_id")
        batch_op.drop_column("disclosure_id")

    op.drop_table("dart_executive_holdings")
