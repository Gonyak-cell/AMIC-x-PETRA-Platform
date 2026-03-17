"""add section classification columns to ib_articles

Revision ID: a1b2c3d4e5f6
Revises: f7a1b2c3d4e5
Create Date: 2026-03-18
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ib_articles", sa.Column("section_primary", sa.String(20), comment="대표 섹션 (ma, governance, fund)")
    )
    op.add_column("ib_articles", sa.Column("section_labels_json", sa.Text(), comment="통과 라벨 JSON"))
    op.add_column("ib_articles", sa.Column("section_scores_json", sa.Text(), comment="섹션별 점수 + 근거 JSON"))
    op.add_column(
        "ib_articles", sa.Column("section_classified_at", sa.DateTime(timezone=True), comment="섹션 분류 실행 시각")
    )
    op.add_column("ib_articles", sa.Column("section_version", sa.String(20), comment="분류 규칙 버전"))
    op.create_index("ix_ib_articles_section_primary", "ib_articles", ["section_primary"])


def downgrade() -> None:
    op.drop_index("ix_ib_articles_section_primary", table_name="ib_articles")
    op.drop_column("ib_articles", "section_version")
    op.drop_column("ib_articles", "section_classified_at")
    op.drop_column("ib_articles", "section_scores_json")
    op.drop_column("ib_articles", "section_labels_json")
    op.drop_column("ib_articles", "section_primary")
