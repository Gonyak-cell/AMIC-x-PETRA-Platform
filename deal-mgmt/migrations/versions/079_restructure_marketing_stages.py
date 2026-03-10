"""079 — MarketingStage enum 재구성: 8단계를 실무 M&A 프로세스에 맞춰 재정의.

기존 단계(EMAIL_SENT, PHONE_CALL, ADVISOR_MEETING, TARGET_MEETING, CIM_SENT, DD_STARTED)를
신규 단계(TEASER_SENT, IM_DISTRIBUTED, QNA_COMPLETED, MGMT_PRESENTATION, LOI_RECEIVED, DD_IN_PROGRESS)로 교체.

Revision ID: 079
Revises: 078
"""

import sqlalchemy as sa
from alembic import op

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None

# 신규 추가 enum 값
_NEW_VALUES = [
    "TEASER_SENT",
    "IM_DISTRIBUTED",
    "QNA_COMPLETED",
    "MGMT_PRESENTATION",
    "LOI_RECEIVED",
    "DD_IN_PROGRESS",
]

# 구 → 신 데이터 매핑 (upgrade)
_UPGRADE_MAP: dict[str, str] = {
    "EMAIL_SENT": "TEASER_SENT",
    "PHONE_CALL": "TEASER_SENT",
    "ADVISOR_MEETING": "TEASER_SENT",
    "TARGET_MEETING": "NDA_SIGNED",
    "CIM_SENT": "IM_DISTRIBUTED",
    "DD_STARTED": "DD_IN_PROGRESS",
}

# 삭제 대상 구 enum 값
_OLD_VALUES = [
    "EMAIL_SENT",
    "PHONE_CALL",
    "ADVISOR_MEETING",
    "TARGET_MEETING",
    "CIM_SENT",
    "DD_STARTED",
]

# 신 → 구 데이터 매핑 (downgrade)
# ⚠️ QNA_COMPLETED, MGMT_PRESENTATION, LOI_RECEIVED는 구 enum에 1:1 대응이 없음
# → 가장 가까운 구 단계로 매핑하므로 downgrade 시 세부 단계 정보가 유실됨
_DOWNGRADE_MAP: dict[str, str] = {
    "TEASER_SENT": "EMAIL_SENT",
    "IM_DISTRIBUTED": "CIM_SENT",
    "DD_IN_PROGRESS": "DD_STARTED",
    "QNA_COMPLETED": "CIM_SENT",  # ⚠️ 데이터 유실: Q&A 세부 정보 소실
    "MGMT_PRESENTATION": "CIM_SENT",  # ⚠️ 데이터 유실: MP 세부 정보 소실
    "LOI_RECEIVED": "DD_STARTED",  # ⚠️ 데이터 유실: LOI 세부 정보 소실
}

# 최종 enum에 포함될 모든 값 (upgrade 후)
_FINAL_VALUES = [
    "IDENTIFIED",
    "TEASER_SENT",
    "NDA_SIGNED",
    "IM_DISTRIBUTED",
    "QNA_COMPLETED",
    "MGMT_PRESENTATION",
    "LOI_RECEIVED",
    "DD_IN_PROGRESS",
]

# 롤백 후 enum에 포함될 모든 값 (downgrade 후)
_ROLLBACK_VALUES = [
    "IDENTIFIED",
    "EMAIL_SENT",
    "PHONE_CALL",
    "ADVISOR_MEETING",
    "NDA_SIGNED",
    "TARGET_MEETING",
    "CIM_SENT",
    "DD_STARTED",
]


def _get_marketing_stage_columns() -> list[tuple[str, str]]:
    """marketing_stage 타입을 사용하는 (테이블, 컬럼) 목록."""
    return [
        ("buyer_marketing_logs", "stage"),
    ]


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        # 1) 신규 enum 값 추가
        for val in _NEW_VALUES:
            op.execute(f"ALTER TYPE marketingstage ADD VALUE IF NOT EXISTS '{val}'")

        # 커밋하여 새 enum 값 사용 가능하게 함
        op.execute("COMMIT")

        # 2) 데이터 마이그레이션: 구 값 → 신 값
        #    asyncpg는 bind param을 VARCHAR로 전송하므로 enum 캐스팅 필수
        for old_val, new_val in _UPGRADE_MAP.items():
            op.execute(
                sa.text(
                    "UPDATE buyer_marketing_logs"
                    " SET stage = CAST(:new_val AS marketingstage)"
                    " WHERE stage = CAST(:old_val AS marketingstage)"
                ).bindparams(new_val=new_val, old_val=old_val)
            )

        # 3) 구 enum 값 제거 — 타입 교체 방식
        #    PostgreSQL은 ALTER TYPE ... DROP VALUE를 지원하지 않으므로
        #    새 타입 생성 → 컬럼 변환 → 구 타입 삭제 → 이름 변경
        columns = _get_marketing_stage_columns()

        # 새 타입 생성
        values_str = ", ".join(f"'{v}'" for v in _FINAL_VALUES)
        op.execute(f"CREATE TYPE marketingstage_new AS ENUM ({values_str})")

        # 컬럼 타입 변환
        for table, col in columns:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {col} TYPE marketingstage_new USING {col}::text::marketingstage_new"
            )

        # 구 타입 삭제 및 이름 변경
        op.execute("DROP TYPE marketingstage")
        op.execute("ALTER TYPE marketingstage_new RENAME TO marketingstage")

    else:
        # SQLite: VARCHAR로 저장되므로 UPDATE만 수행
        for old_val, new_val in _UPGRADE_MAP.items():
            op.execute(
                sa.text("UPDATE buyer_marketing_logs SET stage = :new WHERE stage = :old").bindparams(
                    new=new_val, old=old_val
                )
            )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        # 1) 구 enum 값 추가
        for val in _OLD_VALUES:
            op.execute(f"ALTER TYPE marketingstage ADD VALUE IF NOT EXISTS '{val}'")

        op.execute("COMMIT")

        # 2) 데이터 롤백: 신 값 → 구 값
        for new_val, old_val in _DOWNGRADE_MAP.items():
            op.execute(
                sa.text(
                    "UPDATE buyer_marketing_logs"
                    " SET stage = CAST(:old_val AS marketingstage)"
                    " WHERE stage = CAST(:new_val AS marketingstage)"
                ).bindparams(old_val=old_val, new_val=new_val)
            )

        # 3) 신규 enum 값 제거 — 타입 교체 방식
        columns = _get_marketing_stage_columns()

        values_str = ", ".join(f"'{v}'" for v in _ROLLBACK_VALUES)
        op.execute(f"CREATE TYPE marketingstage_old AS ENUM ({values_str})")

        for table, col in columns:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {col} TYPE marketingstage_old USING {col}::text::marketingstage_old"
            )

        op.execute("DROP TYPE marketingstage")
        op.execute("ALTER TYPE marketingstage_old RENAME TO marketingstage")

    else:
        # SQLite: UPDATE만 수행
        for new_val, old_val in _DOWNGRADE_MAP.items():
            op.execute(
                sa.text("UPDATE buyer_marketing_logs SET stage = :old WHERE stage = :new").bindparams(
                    old=old_val, new=new_val
                )
            )
