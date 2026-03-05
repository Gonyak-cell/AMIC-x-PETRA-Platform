"""066 — docextractioncategory에 REGISTRY_DOCS, BIZ_REG_DOCS 추가

법인등기부와 사업자등록증을 별도 카테고리로 분리하여
업로드 분류 및 추출 대상을 명확히 구분한다.

Revision ID: 066
Revises: 065
"""

from alembic import op

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE docextractioncategory ADD VALUE IF NOT EXISTS 'REGISTRY_DOCS'")
        op.execute("ALTER TYPE docextractioncategory ADD VALUE IF NOT EXISTS 'BIZ_REG_DOCS'")


def downgrade() -> None:
    # PostgreSQL ENUM 값은 삭제 불가 — 롤백 시 애플리케이션 레이어에서 값을 사용하지 않도록 관리
    pass
