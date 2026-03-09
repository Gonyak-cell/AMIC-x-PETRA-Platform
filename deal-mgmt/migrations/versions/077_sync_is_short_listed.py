"""077 — Tier 1/2/3 기존 데이터의 is_short_listed 플래그 일괄 동기화

마이그레이션 045에서 is_short_listed가 server_default=false로 추가되었지만,
이전에 이미 tier가 설정된 레코드는 is_short_listed=false로 남아있음.
_sync_tier_short_list()는 POST/PATCH 시점에만 실행되므로 기존 데이터 보정 필요.

Revision ID: 077
Revises: 076
"""

import sqlalchemy as sa
from alembic import op

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE buyer_candidates
            SET is_short_listed = true
            WHERE tier IN ('TIER_1', 'TIER_2', 'TIER_3')
              AND is_short_listed = false
            """
        )
    )


def downgrade() -> None:
    # 데이터 정합성 수정이므로 롤백 불필요
    pass
