"""Sprint 11 Phase 2-4: Audit enhancement, Job table, new enums.

Revision ID: 004_sprint11_p2_4
Revises: 003_users
Create Date: 2026-02-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_sprint11_p2_4"
down_revision: str | None = "003_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── AuditAction enum 확장 (LOGIN, LOGOUT, EXPORT, PURGE) ──
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'LOGIN'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'LOGOUT'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'EXPORT'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'PURGE'")

    # ── audit_log 확장 (FDD-1702) ─────────────────────────
    op.add_column("audit_log", sa.Column("user_email", sa.String(255), nullable=True))
    op.add_column("audit_log", sa.Column("user_role", sa.String(50), nullable=True))
    op.add_column("audit_log", sa.Column("ip_address", sa.String(45), nullable=True))
    op.add_column("audit_log", sa.Column("user_agent", sa.String(500), nullable=True))
    op.add_column(
        "audit_log",
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "audit_log",
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "audit_log",
        sa.Column("changed_fields", postgresql.JSONB(), nullable=True),
    )
    op.add_column("audit_log", sa.Column("session_id", sa.String(255), nullable=True))
    op.add_column("audit_log", sa.Column("request_id", sa.String(255), nullable=True))
    op.add_column(
        "audit_log",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # audit_log 인덱스
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_user", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_created", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_deal", "audit_log", ["deal_id"])
    op.create_index("ix_audit_log_expires", "audit_log", ["expires_at"])

    # ── JobStatus & JobType enum ───────────────────────────
    jobstatus = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        name="jobstatus",
        create_type=False,
    )
    jobstatus.create(op.get_bind(), checkfirst=True)

    jobtype = postgresql.ENUM(
        "REPORT_GENERATE",
        "DATA_INGEST",
        "ANOMALY_DETECT",
        "MASKING",
        "PURGE",
        name="jobtype",
        create_type=False,
    )
    jobtype.create(op.get_bind(), checkfirst=True)

    # ── job 테이블 (FDD-1801) ──────────────────────────────
    op.create_table(
        "job",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_type",
            postgresql.ENUM(
                "REPORT_GENERATE",
                "DATA_INGEST",
                "ANOMALY_DETECT",
                "MASKING",
                "PURGE",
                name="jobtype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="jobstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deal.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_params", postgresql.JSONB(), nullable=True),
        sa.Column("output_result", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_message", sa.String(500), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "timeout_seconds", sa.Integer(), nullable=False, server_default="600"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_job_status", "job", ["status"])
    op.create_index("ix_job_deal", "job", ["deal_id"])
    op.create_index("ix_job_type", "job", ["job_type"])
    op.create_index("ix_job_created", "job", ["created_at"])


def downgrade() -> None:
    # job
    op.drop_index("ix_job_created", table_name="job")
    op.drop_index("ix_job_type", table_name="job")
    op.drop_index("ix_job_deal", table_name="job")
    op.drop_index("ix_job_status", table_name="job")
    op.drop_table("job")
    op.execute("DROP TYPE IF EXISTS jobtype")
    op.execute("DROP TYPE IF EXISTS jobstatus")

    # audit_log extensions
    op.drop_index("ix_audit_log_expires", table_name="audit_log")
    op.drop_index("ix_audit_log_deal", table_name="audit_log")
    op.drop_index("ix_audit_log_created", table_name="audit_log")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_user", table_name="audit_log")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_column("audit_log", "expires_at")
    op.drop_column("audit_log", "request_id")
    op.drop_column("audit_log", "session_id")
    op.drop_column("audit_log", "changed_fields")
    op.drop_column("audit_log", "after_state")
    op.drop_column("audit_log", "before_state")
    op.drop_column("audit_log", "user_agent")
    op.drop_column("audit_log", "ip_address")
    op.drop_column("audit_log", "user_role")
    op.drop_column("audit_log", "user_email")
