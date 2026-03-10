"""078 — MarketingStage enum에 CIM_SENT, DD_STARTED 값 추가.

마케팅 그리드에 IM 발송 / DD 진행 컬럼을 추가하여
전체 딜 파이프라인과 유기적으로 동기화한다.

Revision ID: 078
Revises: 077
"""

from alembic import op

revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE marketingstage ADD VALUE IF NOT EXISTS 'CIM_SENT'")
        op.execute("ALTER TYPE marketingstage ADD VALUE IF NOT EXISTS 'DD_STARTED'")


def downgrade() -> None:
    # PostgreSQL enum에서 값 제거는 불가 — 값이 남아도 무해
    pass
