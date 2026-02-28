"""add ib_articles table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ib_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False, index=True, comment="기사 제목"),
        sa.Column("lead_text", sa.Text(), nullable=True, comment="첫 문단 (저작권 보호, 전문 저장 금지)"),
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            index=True,
            comment="출처 (investchosun, dealsite, ibtomato, bloter)",
        ),
        sa.Column("author", sa.String(100), nullable=True, comment="저자"),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
            index=True,
            comment="발행일시",
        ),
        sa.Column("canonical_url", sa.String(1000), nullable=False, unique=True, comment="원문 아웃링크 (필수)"),
        sa.Column("url_hash", sa.String(64), nullable=False, index=True, comment="URL SHA256 해시 (중복 감지)"),
        sa.Column(
            "is_paywalled", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Paywall 감지 여부"
        ),
        # NLP 분류 결과
        sa.Column(
            "category",
            sa.String(30),
            nullable=True,
            index=True,
            comment="카테고리 (deal_progress, sourcing_history, investment_style, reputation, personnel_evaluation)",
        ),
        sa.Column("domain", sa.String(10), nullable=True, comment="도메인 (fact, opinion)"),
        sa.Column("sentiment_score", sa.Float(), nullable=True, comment="감성 점수 (-1.0 ~ 1.0)"),
        sa.Column("keywords", sa.Text(), nullable=True, comment="키워드 (JSON 문자열)"),
        # GP 매칭
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="매칭된 GP 기업 ID",
        ),
        sa.Column("match_confidence", sa.Float(), nullable=True, comment="GP 매칭 신뢰도 (0.0 ~ 1.0)"),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # 복합 인덱스: GP별 시간순 조회
    op.create_index("ix_ib_articles_company_published", "ib_articles", ["company_id", "published_at"])


def downgrade() -> None:
    op.drop_index("ix_ib_articles_company_published", table_name="ib_articles")
    op.drop_table("ib_articles")
