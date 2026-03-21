"""MOU_SIGNED 단계를 파이프라인에서 제거 — 데이터를 MAIN_DUE_DILIGENCE로 이동.

- MOU_SIGNED 상태인 거래를 MAIN_DUE_DILIGENCE로 마이그레이션
- AttachmentEntityType에 MILESTONE 값 추가 (마일스톤 문서 업로드용)
- PostgreSQL enum에서 값 제거는 불가 → MOU_SIGNED enum은 잔존

Revision ID: 053
Revises: 052
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "053"
down_revision: str = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1) AttachmentEntityType에 MILESTONE 추가 (DDL 먼저 — R12-02)
    # PostgreSQL의 ALTER TYPE ... ADD VALUE는 트랜잭션 내부에서 실행 불가 →
    # autocommit_block()으로 현재 트랜잭션 밖에서 실행해야 함.
    # DDL을 DML보다 먼저 실행하여, DDL 실패 시 DML이 커밋되지 않도록 순서 보장.
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                sa.text(
                    """
                    DO $$ BEGIN
                        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attachmententitytype') THEN
                            ALTER TYPE attachmententitytype ADD VALUE IF NOT EXISTS 'MILESTONE';
                        END IF;
                    END $$;
                    """
                )
            )
    # SQLite: VARCHAR이므로 별도 ALTER 불필요

    # 2) MOU_SIGNED → MAIN_DUE_DILIGENCE 데이터 마이그레이션
    # NOTE: 배포 시 deploy.yml에서 마이그레이션이 코드 교체보다 먼저 실행되므로
    # race condition(마이그레이션 중 신규 MOU_SIGNED 삽입) 가능성은 낮음.
    op.execute(sa.text("UPDATE transactions SET phase = 'MAIN_DUE_DILIGENCE' WHERE phase = 'MOU_SIGNED'"))


def downgrade() -> None:
    # 비가역 마이그레이션 (R12-01: 표준 pass + 주석 패턴)
    # - MOU_SIGNED → MAIN_DUE_DILIGENCE 데이터 이동은 비가역적
    # - PostgreSQL enum에서 MILESTONE 값을 제거할 수 없음
    # - 롤백이 필요한 경우 데이터 복원 스크립트를 수동으로 실행하세요
    pass
