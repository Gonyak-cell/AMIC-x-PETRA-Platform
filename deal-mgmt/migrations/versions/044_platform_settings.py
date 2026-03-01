"""플랫폼 전역 설정 싱글턴 테이블.

- platform_settings 테이블 생성 (id=1 싱글턴)
- 초기 레코드 삽입 (table_style='DEFAULT')

Revision ID: 044
Revises: 043
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("site_name", sa.String(200), nullable=False, server_default="AMIC Platform"),
        sa.Column("contact_email", sa.String(200), nullable=True),
        sa.Column("legal_terms", sa.Text(), nullable=True),
        sa.Column("privacy_policy", sa.Text(), nullable=True),
        sa.Column("table_style", sa.String(50), nullable=False, server_default="DEFAULT"),
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
        sa.CheckConstraint("id = 1", name="ck_platform_settings_singleton"),
    )

    # 초기 싱글턴 레코드 삽입
    op.execute("INSERT INTO platform_settings (id, site_name, table_style) VALUES (1, 'AMIC Platform', 'DEFAULT')")


def downgrade() -> None:
    op.drop_table("platform_settings")
