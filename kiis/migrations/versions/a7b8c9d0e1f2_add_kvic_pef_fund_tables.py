"""Add kvic_funds and pef_funds tables for GP fund linking.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # KVIC 자조합 테이블
    op.create_table(
        "kvic_funds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="GP 운용사 (companies FK)",
        ),
        sa.Column("fund_name", sa.String(500), nullable=False, comment="자조합명"),
        sa.Column(
            "fund_size",
            sa.Numeric(20, 0),
            nullable=True,
            comment="자조합 규모 (백만원)",
        ),
        sa.Column(
            "operator_type",
            sa.String(100),
            nullable=True,
            comment="운영사구분 (벤처투자회사, 신기술사, LLC 등)",
        ),
        sa.Column("representative", sa.String(100), nullable=True, comment="대표자"),
        sa.Column("phone", sa.String(50), nullable=True, comment="연락처"),
        sa.Column("established_date", sa.String(20), nullable=True, comment="결성일"),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="동기화 시각",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 금감원 PEF 현황 테이블
    op.create_table(
        "pef_funds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pef_name", sa.String(500), nullable=False, index=True, comment="PEF 명칭"
        ),
        sa.Column(
            "legal_basis",
            sa.String(200),
            nullable=True,
            comment="설립근거법률 (자본시장법 등)",
        ),
        sa.Column(
            "registration_date",
            sa.String(20),
            nullable=True,
            comment="등록일(설립일)",
        ),
        sa.Column(
            "total_commitment",
            sa.Numeric(20, 0),
            nullable=True,
            comment="총약정액 (억원)",
        ),
        sa.Column(
            "gp1_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="GP1 (주 업무집행사원)",
        ),
        sa.Column(
            "gp2_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            comment="GP2 (공동 업무집행사원)",
        ),
        sa.Column(
            "gp3_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            comment="GP3 (공동 업무집행사원)",
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="동기화 시각",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("pef_funds")
    op.drop_table("kvic_funds")
