"""Transcription jobs — audio upload + Clova STT + LLM meeting minutes.

Revision ID: 018
Revises: 017
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB as _JSONB

_JSON = sa.JSON().with_variant(_JSONB, "postgresql")

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

transcription_job_status = sa.Enum(
    "PENDING",
    "TRANSCRIBING",
    "ANALYZING",
    "COMPLETED",
    "APPROVED",
    "FAILED",
    name="transcriptionjobstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        transcription_job_status.create(bind, checkfirst=True)

    op.create_table(
        "transcription_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 입력 메타데이터
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("meeting_date", sa.String(10), nullable=False),
        sa.Column(
            "meeting_phase",
            sa.Enum(
                "MARKETING",
                "NEGOTIATION",
                name="meetingphase",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "buyer_id",
            sa.Uuid(),
            sa.ForeignKey("buyer_candidates.id"),
            nullable=True,
        ),
        # 참석자 (사용자 입력, JSON 배열)
        sa.Column("attendees_json", _JSON, nullable=True),
        # 오디오 파일
        sa.Column("audio_file_path", sa.String(500), nullable=False),
        sa.Column("audio_file_name", sa.String(300), nullable=False),
        sa.Column("audio_duration_seconds", sa.Integer, nullable=True),
        # 처리 상태
        sa.Column("status", transcription_job_status, nullable=False, server_default="PENDING"),
        # STT 결과
        sa.Column("transcript", sa.Text, nullable=True),
        # LLM 구조화 결과
        sa.Column("minutes_json", _JSON, nullable=True),
        # 확정된 미팅 로그
        sa.Column(
            "meeting_log_id",
            sa.Uuid(),
            sa.ForeignKey("meeting_logs.id"),
            nullable=True,
        ),
        # 비용 추적
        sa.Column("stt_cost_krw", sa.Float, nullable=False, server_default="0"),
        sa.Column("llm_cost_usd", sa.Float, nullable=False, server_default="0"),
        # 에러
        sa.Column("error_message", sa.Text, nullable=True),
        # 생성자
        sa.Column("created_by_email", sa.String(255), nullable=True),
        # 타임스탬프
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_transcription_jobs_transaction_id", "transcription_jobs", ["transaction_id"])
    op.create_index("ix_transcription_jobs_status", "transcription_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("transcription_jobs")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        transcription_job_status.drop(bind, checkfirst=True)
