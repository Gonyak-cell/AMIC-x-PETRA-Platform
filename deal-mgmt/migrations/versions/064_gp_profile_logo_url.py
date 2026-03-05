"""064 — gp_profiles 테이블에 logo_url 컬럼 추가

CI 로고 URL(thevc.kr 기준)을 GP 프로필에 저장한다.
Excel MA_GP_v3.xlsx O열에 수동 입력된 URL을 시딩 스크립트가 읽어 채운다.

Revision ID: 064
Revises: 063
"""

import sqlalchemy as sa
from alembic import op

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gp_profiles",
        sa.Column("logo_url", sa.String(2048), nullable=True, comment="O열 CI 로고 URL"),
    )


def downgrade() -> None:
    op.drop_column("gp_profiles", "logo_url")
