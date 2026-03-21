"""080 — 마케팅 로그 + 미팅 로그 통합.

meeting_logs 테이블에 marketing_stage 컬럼 추가 후,
buyer_marketing_logs 데이터를 meeting_logs로 복사.

원본 buyer_marketing_logs 테이블은 삭제하지 않음 (롤백 안전성).

Revision ID: 080
Revises: 079
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None

# 마케팅 단계 라벨 (SQLite title 자동 생성용 — PostgreSQL은 CASE 표현식 사용)
_STAGE_LABELS: dict[str, str] = {
    "IDENTIFIED": "매수자 식별",
    "TEASER_SENT": "Teaser 배포",
    "NDA_SIGNED": "NDA 체결",
    "IM_DISTRIBUTED": "IM 배포",
    "QNA_COMPLETED": "Q&A 완료",
    "MGMT_PRESENTATION": "경영진 프레젠테이션",
    "LOI_RECEIVED": "LOI 접수",
    "DD_IN_PROGRESS": "DD 진행",
}


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        # 1) meeting_logs 테이블에 marketing_stage 컬럼 추가
        #    marketingstage enum은 이미 존재 (buyer_marketing_logs에서 사용 중)
        op.add_column(
            "meeting_logs",
            sa.Column(
                "marketing_stage",
                sa.Enum(
                    "IDENTIFIED",
                    "TEASER_SENT",
                    "NDA_SIGNED",
                    "IM_DISTRIBUTED",
                    "QNA_COMPLETED",
                    "MGMT_PRESENTATION",
                    "LOI_RECEIVED",
                    "DD_IN_PROGRESS",
                    name="marketingstage",
                    create_type=False,  # 이미 존재하는 enum 재사용
                ),
                nullable=True,
            ),
        )
        # 인덱스
        op.create_index(
            "ix_meeting_logs_buyer_stage",
            "meeting_logs",
            ["buyer_id", "marketing_stage"],
        )
        op.create_index(
            "ix_meeting_logs_txn_phase",
            "meeting_logs",
            ["transaction_id", "meeting_phase"],
        )

        # 2) buyer_marketing_logs → meeting_logs 배치 데이터 복사 (INSERT...SELECT)
        #    gen_random_uuid() + CASE 표현식으로 단일 문 처리 — row-by-row 대비 대량 성능 향상
        conn = op.get_bind()
        conn.execute(
            sa.text(
                "INSERT INTO meeting_logs "
                "(id, transaction_id, meeting_phase, title, meeting_date, "
                "channel, status, summary, buyer_id, marketing_stage, "
                "created_by_email, created_at, updated_at, attendee_count) "
                "SELECT "
                "  gen_random_uuid()::text, "
                "  transaction_id::text, "
                "  'MARKETING', "
                "  LEFT(CASE stage "
                "    WHEN 'IDENTIFIED' THEN '매수자 식별' "
                "    WHEN 'TEASER_SENT' THEN 'Teaser 배포' "
                "    WHEN 'NDA_SIGNED' THEN 'NDA 체결' "
                "    WHEN 'IM_DISTRIBUTED' THEN 'IM 배포' "
                "    WHEN 'QNA_COMPLETED' THEN 'Q&A 완료' "
                "    WHEN 'MGMT_PRESENTATION' THEN '경영진 프레젠테이션' "
                "    WHEN 'LOI_RECEIVED' THEN 'LOI 접수' "
                "    WHEN 'DD_IN_PROGRESS' THEN 'DD 진행' "
                "    ELSE stage "
                "  END || CASE WHEN content IS NOT NULL AND content != '' "
                "    THEN ' — ' || LEFT(content, 50) ELSE '' END, 300), "
                "  log_date, "
                "  'EMAIL', "
                "  'COMPLETED', "
                "  content, "
                "  buyer_id::text, "
                "  stage::marketingstage, "
                "  created_by_email, "
                "  created_at, "
                "  updated_at, "
                "  0 "
                "FROM buyer_marketing_logs"
            )
        )

    else:
        # SQLite: VARCHAR 컬럼 추가 + row-by-row 데이터 복사
        # (SQLite에는 gen_random_uuid()가 없으므로 Python uuid 생성 필요)
        op.add_column(
            "meeting_logs",
            sa.Column("marketing_stage", sa.String(30), nullable=True),
        )
        op.create_index(
            "ix_meeting_logs_buyer_stage",
            "meeting_logs",
            ["buyer_id", "marketing_stage"],
        )
        op.create_index(
            "ix_meeting_logs_txn_phase",
            "meeting_logs",
            ["transaction_id", "meeting_phase"],
        )

        conn = op.get_bind()
        rows = conn.execute(
            sa.text(
                "SELECT id, buyer_id, transaction_id, stage, log_date, content, "
                "created_by_email, created_at, updated_at "
                "FROM buyer_marketing_logs"
            )
        ).fetchall()

        for row in rows:
            stage_val = row[3]
            content_val = row[5]
            label = _STAGE_LABELS.get(stage_val, stage_val)
            title = f"{label} — {content_val[:50]}" if content_val else label

            conn.execute(
                sa.text(
                    "INSERT INTO meeting_logs "
                    "(id, transaction_id, meeting_phase, title, meeting_date, "
                    "channel, status, summary, buyer_id, marketing_stage, "
                    "created_by_email, created_at, updated_at, attendee_count) "
                    "VALUES ("
                    ":id, :txn_id, 'MARKETING', :title, :log_date, "
                    "'EMAIL', 'COMPLETED', :summary, :buyer_id, :stage, "
                    ":created_by, :created_at, :updated_at, 0)"
                ).bindparams(
                    id=str(uuid.uuid4()),
                    txn_id=str(row[2]),
                    title=title[:300],
                    log_date=row[4],
                    summary=content_val,
                    buyer_id=str(row[1]),
                    stage=stage_val,
                    created_by=row[6],
                    created_at=row[7],
                    updated_at=row[8],
                )
            )


def downgrade() -> None:
    # ⚠️ 데이터 복원 불가 (R12-02):
    #    downgrade 시 marketing_stage 컬럼과 복사된 데이터가 삭제됩니다.
    #    buyer_marketing_logs → meeting_logs 로 복사된 데이터의 역방향 복원은
    #    구현하지 않습니다. 이유:
    #    - 통합 후 meeting_logs에서 직접 수정된 데이터는 원본과 다를 수 있음
    #    - 통합 후 신규 생성된 marketing_stage 미팅 로그는 원본 테이블에 대응 없음
    #    PostgreSQL에서는 _backup_080_marketing_meeting_logs 백업 테이블을 생성하여
    #    수동 복구 가능하도록 합니다.
    #
    # 📋 배포 순서 주의 (S-09):
    #    1) 새 코드 배포 (meeting_logs API 활성화)
    #    2) alembic upgrade head (이 마이그레이션 실행)
    #    코드가 먼저 배포되어야 meeting_logs 라우터가 marketing_stage 컬럼을 인식함.
    #
    # 📋 원본 ID 추적성 (S-06):
    #    데이터 복사 시 새 UUID를 생성하므로 원본 buyer_marketing_logs.id와
    #    meeting_logs.id 간 직접 매핑이 없음. 추적 필요 시 원본 테이블의
    #    buyer_id + log_date + content 조합으로 대조 가능 (원본 테이블 보존됨).

    dialect = op.get_bind().dialect.name

    # PostgreSQL: 삭제 전 백업 테이블 생성 (신규 데이터 보존)
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS _backup_080_marketing_meeting_logs AS "
                "SELECT * FROM meeting_logs WHERE marketing_stage IS NOT NULL"
            )
        )

    op.execute(sa.text("DELETE FROM meeting_logs WHERE marketing_stage IS NOT NULL"))
    op.drop_index("ix_meeting_logs_txn_phase", table_name="meeting_logs")
    op.drop_index("ix_meeting_logs_buyer_stage", table_name="meeting_logs")
    op.drop_column("meeting_logs", "marketing_stage")
