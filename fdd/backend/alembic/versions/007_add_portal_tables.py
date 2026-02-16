"""Phase 5: Add portal endpoint tables.

Revision ID: 007_portal_tables
Revises: 006_entity_fx
Create Date: 2026-02-11

New tables:
  - notification — 사용자 알림 (모듈별, 읽음 상태 추적)
  - export_record — 내보내기 이력 및 파일 관리
  - webhook_config — 시스템 전역 웹훅 설정
  - email_preference — 사용자별 이메일 알림 설정
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_portal_tables"
down_revision: str | None = "006_entity_fx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. notification ──────────────────────────────────────
    notificationmodule = postgresql.ENUM(
        "fdd", "kiis", "im", "portal", name="notificationmodule", create_type=False
    )
    notificationmodule.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notification",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module", notificationmodule, nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_notification_user", "notification", ["user_id"])
    op.create_index(
        "ix_notification_user_read", "notification", ["user_id", "is_read"]
    )
    op.create_index("ix_notification_created", "notification", ["created_at"])

    # ── 2. export_record ─────────────────────────────────────
    exportmodule = postgresql.ENUM(
        "fdd", "kiis", "im", name="exportmodule", create_type=False
    )
    exportmodule.create(op.get_bind(), checkfirst=True)

    exportstatus = postgresql.ENUM(
        "pending", "completed", "failed", "expired",
        name="exportstatus", create_type=False,
    )
    exportstatus.create(op.get_bind(), checkfirst=True)

    exportformat = postgresql.ENUM(
        "pdf", "pptx", "xlsx", "csv", "zip",
        name="exportformat", create_type=False,
    )
    exportformat.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "export_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("module", exportmodule, nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("format", exportformat, nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column(
            "status", exportstatus, nullable=False, server_default="pending"
        ),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("download_url", sa.String(500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by", sa.String(100), nullable=False, server_default="system"
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_export_record_user", "export_record", ["created_by_user_id"]
    )
    op.create_index("ix_export_record_module", "export_record", ["module"])
    op.create_index("ix_export_record_status", "export_record", ["status"])
    op.create_index("ix_export_record_created", "export_record", ["created_at"])

    # ── 3. webhook_config ────────────────────────────────────
    op.create_table(
        "webhook_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("events", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("secret", sa.String(255), nullable=True),
        sa.Column(
            "last_triggered_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── 4. email_preference ──────────────────────────────────
    op.create_table(
        "email_preference",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "deal_updates", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "watchlist_alerts", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "im_completion", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "weekly_digest", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("email_preference")
    op.drop_table("webhook_config")

    op.drop_index("ix_export_record_created", table_name="export_record")
    op.drop_index("ix_export_record_status", table_name="export_record")
    op.drop_index("ix_export_record_module", table_name="export_record")
    op.drop_index("ix_export_record_user", table_name="export_record")
    op.drop_table("export_record")

    op.drop_index("ix_notification_created", table_name="notification")
    op.drop_index("ix_notification_user_read", table_name="notification")
    op.drop_index("ix_notification_user", table_name="notification")
    op.drop_table("notification")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS exportformat")
    op.execute("DROP TYPE IF EXISTS exportstatus")
    op.execute("DROP TYPE IF EXISTS exportmodule")
    op.execute("DROP TYPE IF EXISTS notificationmodule")
