"""SI 기업 ksic_codes JSON 이중 직렬화 버그 수정.

036 마이그레이션의 _seed_dummy_companies()에서 json.dumps(codes)를
sa.JSON 컬럼에 전달하여 이중 직렬화 발생.
이 마이그레이션은 기존 더미 기업의 ksic_codes를 올바른 JSON 배열로 정정한다.

Revision ID: 038
Revises: 037
"""

from __future__ import annotations

import json
import logging

import sqlalchemy as sa
from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)

# ORM 없이 sa.JSON 타입 바인딩을 위한 테이블 참조
_si_companies = sa.table(
    "si_companies",
    sa.column("id", sa.Uuid),
    sa.column("ksic_codes", sa.JSON),
)


def upgrade() -> None:
    conn = op.get_bind()

    # 더미 기업 = jurir_no IS NULL (실제 기업은 jurir_no가 있음)
    result = conn.execute(sa.text("SELECT id, ksic_codes FROM si_companies WHERE jurir_no IS NULL"))
    rows = result.fetchall()
    fixed = 0

    for row_id, ksic_codes_raw in rows:
        if ksic_codes_raw is None:
            continue

        # 원본 데이터 보존 로그 (복원 추적용)
        logger.info("BACKUP: id=%s, ksic_codes=%r", row_id, ksic_codes_raw)

        # 이중 직렬화 감지: 값이 str이면 json.loads로 한 번 더 파싱.
        # NOTE: PostgreSQL은 JSON 컬럼을 자동 역직렬화(list 반환)하지만,
        # SQLite는 TEXT로 저장하므로 항상 str을 반환한다.
        # CI(SQLite)에서는 모든 행이 str → 수정 대상이 되고,
        # 프로덕션(PostgreSQL)에서는 이중 직렬화된 행만 str → 수정 대상이 된다.
        if isinstance(ksic_codes_raw, str):
            try:
                parsed = json.loads(ksic_codes_raw)
                if isinstance(parsed, list):
                    # sa.JSON 타입 바인딩으로 UPDATE — 크로스 DB 호환
                    conn.execute(
                        _si_companies.update().where(_si_companies.c.id == row_id).values(ksic_codes=parsed),
                    )
                    fixed += 1
                else:
                    logger.warning("ksic_codes가 list가 아님: id=%s, parsed=%r", row_id, parsed)
            except (json.JSONDecodeError, TypeError):
                logger.warning("ksic_codes 파싱 실패: id=%s, raw=%r", row_id, ksic_codes_raw)

    logger.info("si_companies ksic_codes 수정: %d/%d건", fixed, len(rows))


def downgrade() -> None:
    # 데이터 수정 롤백은 불필요 (이전 상태가 이미 잘못된 데이터)
    pass
