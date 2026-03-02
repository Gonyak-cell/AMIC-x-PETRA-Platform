"""MA 6대 지시사항 Phase 1 — 스키마 추가.

- pef_fund_registry 테이블 생성 (PEF 펀드 레지스트리)
- buyer_candidates.is_short_listed Boolean 컬럼 추가
- BuyerCandidateStatus enum에 BID_SUBMITTED/BID_NOT_SUBMITTED/BID_DROPPED 추가

Revision ID: 045
Revises: 044
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. pef_fund_registry 테이블
    op.create_table(
        "pef_fund_registry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("pef_name", sa.String(300), nullable=False),
        sa.Column("legal_basis", sa.String(100), nullable=True),
        sa.Column("registration_date", sa.String(10), nullable=True),
        sa.Column("gp1", sa.String(200), nullable=True),
        sa.Column("gp2", sa.String(200), nullable=True),
        sa.Column("gp3", sa.String(200), nullable=True),
        sa.Column("total_committed_capital", sa.Numeric(20, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_pef_fund_registry_capital",
        "pef_fund_registry",
        ["total_committed_capital"],
    )

    # 2. buyer_candidates.is_short_listed
    op.add_column(
        "buyer_candidates",
        sa.Column(
            "is_short_listed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 3. BuyerCandidateStatus enum 확장 (PostgreSQL만)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE buyercandidatestatus ADD VALUE IF NOT EXISTS 'BID_SUBMITTED'"))
            op.execute(sa.text("ALTER TYPE buyercandidatestatus ADD VALUE IF NOT EXISTS 'BID_NOT_SUBMITTED'"))
            op.execute(sa.text("ALTER TYPE buyercandidatestatus ADD VALUE IF NOT EXISTS 'BID_DROPPED'"))


def downgrade() -> None:
    op.drop_column("buyer_candidates", "is_short_listed")
    op.drop_index("ix_pef_fund_registry_capital", table_name="pef_fund_registry")
    op.drop_table("pef_fund_registry")
    # PostgreSQL enum 값 제거 불가 (ALTER TYPE DROP VALUE 미지원).
    # BID_SUBMITTED, BID_NOT_SUBMITTED, BID_DROPPED는 enum에 잔존하지만
    # 애플리케이션에서 사용하지 않으면 무해하다. 완전 제거가 필요하면
    # 새 enum 타입을 생성하고 교체하는 마이그레이션을 작성해야 한다.
