"""Phase 4 — pmi_tasks, earnout_milestones tables

Revision ID: 004_phase4
Revises: 003_phase3
Create Date: 2026-02-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_phase4"
down_revision: Union[str, None] = "003_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ──
    pmi_category = sa.Enum(
        "INTEGRATION_PLAN", "DAY_ONE", "FIRST_100_DAYS", "SYNERGY", "CULTURE",
        "IT_SYSTEMS", "HR", "COMMUNICATION", "OTHER",
        name="pmicategory",
    )
    pmi_task_status = sa.Enum(
        "NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED", "DEFERRED",
        name="pmitaskstatus",
    )
    pmi_priority = sa.Enum(
        "CRITICAL", "HIGH", "MEDIUM", "LOW",
        name="pmipriority",
    )
    earnout_status = sa.Enum(
        "PENDING", "MEASUREMENT_PERIOD", "ACHIEVED", "PARTIALLY_ACHIEVED", "MISSED", "DISPUTED",
        name="earnoutstatus",
    )
    earnout_metric = sa.Enum(
        "REVENUE", "EBITDA", "NET_INCOME", "CUSTOMER_COUNT", "CONTRACT_VALUE",
        "WORKING_CAPITAL", "OTHER",
        name="earnoutmetric",
    )

    # ── pmi_tasks ──
    op.create_table(
        "pmi_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("category", pmi_category, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", pmi_task_status, nullable=False, server_default="NOT_STARTED"),
        sa.Column("priority", pmi_priority, nullable=False, server_default="MEDIUM"),
        sa.Column("assignee_name", sa.String(200), nullable=True),
        sa.Column("assignee_email", sa.String(255), nullable=True),
        sa.Column("start_date", sa.String(10), nullable=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("completed_date", sa.String(10), nullable=True),
        sa.Column("dependency_ids", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── earnout_milestones ──
    op.create_table(
        "earnout_milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metric", earnout_metric, nullable=False),
        sa.Column("target_value", sa.Numeric(20, 2), nullable=False),
        sa.Column("actual_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="KRW"),
        sa.Column("measurement_start", sa.String(10), nullable=True),
        sa.Column("measurement_end", sa.String(10), nullable=True),
        sa.Column("payment_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("payment_date", sa.String(10), nullable=True),
        sa.Column("status", earnout_status, nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("earnout_milestones")
    op.drop_table("pmi_tasks")

    for name in [
        "earnoutmetric", "earnoutstatus", "pmipriority",
        "pmitaskstatus", "pmicategory",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
