"""068 — VDR 문서 자동 분류 컬럼 추가

Direct Upload 기능의 다단계 자동 라우팅을 위한 분류 상태 컬럼 추가.
- classification_status: 1차/2차 심사 결과 상태
- classification_score: 메타데이터 스코어링 점수
- manual_review_needed: 수동 확인 필요 여부

Revision ID: 068
Revises: 067
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None

_ENUM_NAME = "vdrclassificationstatus"
_ENUM_VALUES = ("DIRECT", "PENDING_REVIEW", "CLASSIFIED", "MANUAL_REVIEW", "MANUAL")


def upgrade() -> None:
    # SQLite (테스트 환경): enum 타입 대신 VARCHAR 사용
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        col_type = sa.String(20)
    else:
        enum_type = sa.Enum(*_ENUM_VALUES, name=_ENUM_NAME)
        enum_type.create(bind, checkfirst=True)
        col_type = enum_type

    op.add_column("vdr_documents", sa.Column("classification_status", col_type, nullable=True))
    op.add_column("vdr_documents", sa.Column("classification_score", sa.Integer(), nullable=True))
    op.add_column("vdr_documents", sa.Column("manual_review_needed", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    # ⚠️ 주의: classification_status, classification_score 데이터가 유실됩니다.
    # 이미 분류된 문서의 이력은 복구할 수 없습니다.
    op.drop_column("vdr_documents", "manual_review_needed")
    op.drop_column("vdr_documents", "classification_score")
    op.drop_column("vdr_documents", "classification_status")

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        sa.Enum(name=_ENUM_NAME).drop(bind, checkfirst=True)
