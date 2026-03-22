"""Unify buyer marketing logs into meeting logs.

Revision ID: 080
Revises: 079
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None

MARKETING_STAGE_VALUES = (
    "IDENTIFIED",
    "TEASER_SENT",
    "NDA_SIGNED",
    "IM_DISTRIBUTED",
    "QNA_COMPLETED",
    "MGMT_PRESENTATION",
    "LOI_RECEIVED",
    "DD_IN_PROGRESS",
)

STAGE_LABELS: dict[str, str] = {
    "IDENTIFIED": "Buyer identified",
    "TEASER_SENT": "Teaser sent",
    "NDA_SIGNED": "NDA signed",
    "IM_DISTRIBUTED": "IM distributed",
    "QNA_COMPLETED": "Q&A completed",
    "MGMT_PRESENTATION": "Management presentation",
    "LOI_RECEIVED": "LOI received",
    "DD_IN_PROGRESS": "DD in progress",
}


def _meeting_log_stage_column(postgres: bool) -> sa.TypeEngine:
    if postgres:
        return postgresql.ENUM(
            *MARKETING_STAGE_VALUES,
            name="marketingstage",
            create_type=False,
        )
    return sa.String(30)


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_postgresql = bind.dialect.name == "postgresql"

    existing_columns = {column["name"] for column in inspector.get_columns("meeting_logs")}
    if "marketing_stage" not in existing_columns:
        op.add_column(
            "meeting_logs",
            sa.Column("marketing_stage", _meeting_log_stage_column(is_postgresql), nullable=True),
        )

    if not _index_exists(inspector, "meeting_logs", "ix_meeting_logs_buyer_stage"):
        op.create_index(
            "ix_meeting_logs_buyer_stage",
            "meeting_logs",
            ["buyer_id", "marketing_stage"],
        )
    if not _index_exists(inspector, "meeting_logs", "ix_meeting_logs_txn_phase"):
        op.create_index(
            "ix_meeting_logs_txn_phase",
            "meeting_logs",
            ["transaction_id", "meeting_phase"],
        )

    if is_postgresql:
        bind.execute(
            sa.text(
                """
                INSERT INTO meeting_logs (
                    id,
                    transaction_id,
                    meeting_phase,
                    title,
                    meeting_date,
                    channel,
                    status,
                    summary,
                    buyer_id,
                    marketing_stage,
                    created_by_email,
                    created_at,
                    updated_at,
                    attendee_count
                )
                SELECT
                    gen_random_uuid(),
                    transaction_id,
                    'MARKETING',
                    LEFT(
                        CASE stage::text
                            WHEN 'IDENTIFIED' THEN 'Buyer identified'
                            WHEN 'TEASER_SENT' THEN 'Teaser sent'
                            WHEN 'NDA_SIGNED' THEN 'NDA signed'
                            WHEN 'IM_DISTRIBUTED' THEN 'IM distributed'
                            WHEN 'QNA_COMPLETED' THEN 'Q&A completed'
                            WHEN 'MGMT_PRESENTATION' THEN 'Management presentation'
                            WHEN 'LOI_RECEIVED' THEN 'LOI received'
                            WHEN 'DD_IN_PROGRESS' THEN 'DD in progress'
                            ELSE stage::text
                        END
                        || CASE
                            WHEN content IS NOT NULL AND content != '' THEN ' - ' || LEFT(content, 50)
                            ELSE ''
                        END,
                        300
                    ),
                    log_date,
                    'EMAIL',
                    'COMPLETED',
                    content,
                    buyer_id,
                    stage::text::marketingstage,
                    created_by_email,
                    created_at,
                    updated_at,
                    0
                FROM buyer_marketing_logs
                """
            )
        )
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT
                buyer_id,
                transaction_id,
                stage,
                log_date,
                content,
                created_by_email,
                created_at,
                updated_at
            FROM buyer_marketing_logs
            """
        )
    ).fetchall()

    for row in rows:
        stage_value = row[2]
        content_value = row[4]
        label = STAGE_LABELS.get(stage_value, stage_value)
        title = f"{label} - {content_value[:50]}" if content_value else label

        bind.execute(
            sa.text(
                """
                INSERT INTO meeting_logs (
                    id,
                    transaction_id,
                    meeting_phase,
                    title,
                    meeting_date,
                    channel,
                    status,
                    summary,
                    buyer_id,
                    marketing_stage,
                    created_by_email,
                    created_at,
                    updated_at,
                    attendee_count
                )
                VALUES (
                    :id,
                    :transaction_id,
                    'MARKETING',
                    :title,
                    :meeting_date,
                    'EMAIL',
                    'COMPLETED',
                    :summary,
                    :buyer_id,
                    :marketing_stage,
                    :created_by_email,
                    :created_at,
                    :updated_at,
                    0
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "transaction_id": str(row[1]),
                "title": title[:300],
                "meeting_date": row[3],
                "summary": content_value,
                "buyer_id": str(row[0]) if row[0] is not None else None,
                "marketing_stage": stage_value,
                "created_by_email": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {column["name"] for column in inspector.get_columns("meeting_logs")}
    if "marketing_stage" not in existing_columns:
        return

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS _backup_080_marketing_meeting_logs AS
                SELECT * FROM meeting_logs WHERE marketing_stage IS NOT NULL
                """
            )
        )

    op.execute(sa.text("DELETE FROM meeting_logs WHERE marketing_stage IS NOT NULL"))

    if _index_exists(inspector, "meeting_logs", "ix_meeting_logs_txn_phase"):
        op.drop_index("ix_meeting_logs_txn_phase", table_name="meeting_logs")
    if _index_exists(inspector, "meeting_logs", "ix_meeting_logs_buyer_stage"):
        op.drop_index("ix_meeting_logs_buyer_stage", table_name="meeting_logs")

    op.drop_column("meeting_logs", "marketing_stage")
