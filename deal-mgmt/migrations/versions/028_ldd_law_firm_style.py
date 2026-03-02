"""LDD 법무법인 스타일 — LAW_FIRM enum + 3개 JSONB 컬럼 추가.

Revision ID: 028
Revises: 027
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB

_JSON = sa.JSON().with_variant(_PG_JSONB(), "postgresql")

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # LDDReportType enum에 LAW_FIRM 값 추가 (PostgreSQL 전용)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE lddreporttype ADD VALUE IF NOT EXISTS 'LAW_FIRM'")

    # 법무법인 목차 구조
    op.add_column(
        "ldd_reports",
        sa.Column(
            "law_firm_toc",
            _JSON,
            nullable=True,
            comment="법무법인 8개 목차 구조 (I~VIII 매핑 결과)",
        ),
    )
    # 법무법인 3단 서술 결과
    op.add_column(
        "ldd_reports",
        sa.Column(
            "law_firm_sections",
            _JSON,
            nullable=True,
            comment="법무법인 3단 서술 결과 (section → {현황/검토/Recommendation})",
        ),
    )
    # D 라벨 수집: IRL 항목
    op.add_column(
        "ldd_reports",
        sa.Column(
            "irl_items",
            _JSON,
            nullable=True,
            comment="D 라벨 수집: Information Request List 항목",
        ),
    )


def downgrade() -> None:
    op.drop_column("ldd_reports", "irl_items")
    op.drop_column("ldd_reports", "law_firm_sections")
    op.drop_column("ldd_reports", "law_firm_toc")
    # PostgreSQL에서는 enum 값 제거가 직접 불가 — 별도 처리 필요
