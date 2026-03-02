"""Meeting logs, attendees, action items, negotiation issues, contract markups.

Revision ID: 016
Revises: 015
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB as _JSONB

_JSON = sa.JSON().with_variant(_JSONB, "postgresql")

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── Enum 타입 생성 (PostgreSQL 전용 raw SQL) ──────────
    if bind.dialect.name == "postgresql":
        enums = [
            ("meetingphase", ["MARKETING", "NEGOTIATION"]),
            ("meetingchannel", ["IN_PERSON", "EMAIL", "PHONE", "VIDEO", "HYBRID"]),
            ("meetingstatus", ["SCHEDULED", "COMPLETED", "CANCELLED", "POSTPONED"]),
            (
                "attendeerole",
                [
                    "SELLER_ADVISOR",
                    "BUYER_ADVISOR",
                    "LEGAL_COUNSEL",
                    "CLIENT_REPRESENTATIVE",
                    "COUNTERPARTY",
                    "OBSERVER",
                    "OTHER",
                ],
            ),
            ("actionitemstatus", ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"]),
            (
                "buyerreaction",
                ["VERY_POSITIVE", "POSITIVE", "NEUTRAL", "NEGATIVE", "VERY_NEGATIVE"],
            ),
            (
                "conditionmatchlevel",
                ["FULL_MATCH", "PARTIAL_MATCH", "MISMATCH", "NOT_ASSESSED"],
            ),
            (
                "negotiationissuestatus",
                ["OPEN", "IN_PROGRESS", "AGREED", "DEFERRED", "DEADLOCKED"],
            ),
            (
                "negotiationissuepriority",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            ),
        ]
        for name, values in enums:
            vals = ", ".join(f"'{v}'" for v in values)
            op.execute(
                f"DO $$ BEGIN "
                f"IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN "
                f"CREATE TYPE {name} AS ENUM ({vals}); "
                f"END IF; END $$;"
            )

    # ── Cross-DB Enum 참조 ──
    meetingphase = sa.Enum("MARKETING", "NEGOTIATION", name="meetingphase", create_type=False)
    meetingchannel = sa.Enum("IN_PERSON", "EMAIL", "PHONE", "VIDEO", "HYBRID", name="meetingchannel", create_type=False)
    meetingstatus = sa.Enum("SCHEDULED", "COMPLETED", "CANCELLED", "POSTPONED", name="meetingstatus", create_type=False)
    attendeerole = sa.Enum(
        "SELLER_ADVISOR",
        "BUYER_ADVISOR",
        "LEGAL_COUNSEL",
        "CLIENT_REPRESENTATIVE",
        "COUNTERPARTY",
        "OBSERVER",
        "OTHER",
        name="attendeerole",
        create_type=False,
    )
    actionitemstatus = sa.Enum(
        "PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="actionitemstatus", create_type=False
    )
    buyerreaction = sa.Enum(
        "VERY_POSITIVE", "POSITIVE", "NEUTRAL", "NEGATIVE", "VERY_NEGATIVE", name="buyerreaction", create_type=False
    )
    conditionmatchlevel = sa.Enum(
        "FULL_MATCH", "PARTIAL_MATCH", "MISMATCH", "NOT_ASSESSED", name="conditionmatchlevel", create_type=False
    )
    negotiationissuestatus = sa.Enum(
        "OPEN", "IN_PROGRESS", "AGREED", "DEFERRED", "DEADLOCKED", name="negotiationissuestatus", create_type=False
    )
    negotiationissuepriority = sa.Enum(
        "CRITICAL", "HIGH", "MEDIUM", "LOW", name="negotiationissuepriority", create_type=False
    )

    # ── meeting_logs ──────────────────────────────────────
    op.create_table(
        "meeting_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_id", sa.Uuid(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meeting_phase", meetingphase, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("meeting_date", sa.String(10), nullable=False),
        sa.Column("meeting_time", sa.String(5), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("channel", meetingchannel, nullable=False, server_default="IN_PERSON"),
        sa.Column("status", meetingstatus, nullable=False, server_default="COMPLETED"),
        sa.Column("minutes", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("provided_materials", _JSON, nullable=True),
        sa.Column("attachments", _JSON, nullable=True),
        sa.Column("buyer_id", sa.Uuid(), sa.ForeignKey("buyer_candidates.id"), nullable=True),
        sa.Column("condition_match", conditionmatchlevel, nullable=True),
        sa.Column("condition_notes", sa.Text, nullable=True),
        sa.Column("contract_id", sa.Uuid(), sa.ForeignKey("contracts.id"), nullable=True),
        sa.Column("attendee_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_meeting_logs_transaction_id", "meeting_logs", ["transaction_id"])
    op.create_index("ix_meeting_logs_buyer_id", "meeting_logs", ["buyer_id"])
    op.create_index("ix_meeting_logs_contract_id", "meeting_logs", ["contract_id"])

    # ── meeting_attendees ─────────────────────────────────
    op.create_table(
        "meeting_attendees",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meeting_logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("organization", sa.String(200), nullable=True),
        sa.Column("role", attendeerole, nullable=False, server_default="OTHER"),
        sa.Column("reaction", buyerreaction, nullable=True),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_meeting_attendees_meeting_id", "meeting_attendees", ["meeting_id"])

    # ── meeting_action_items ──────────────────────────────
    op.create_table(
        "meeting_action_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meeting_logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("assignee_email", sa.String(255), nullable=True),
        sa.Column("assignee_name", sa.String(200), nullable=True),
        sa.Column("due_date", sa.String(10), nullable=True),
        sa.Column("status", actionitemstatus, nullable=False, server_default="PENDING"),
        sa.Column("priority", negotiationissuepriority, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_meeting_action_items_meeting_id", "meeting_action_items", ["meeting_id"])

    # ── negotiation_issues ────────────────────────────────
    op.create_table(
        "negotiation_issues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_id", sa.Uuid(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meeting_logs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("clause_reference", sa.String(200), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("our_position", sa.Text, nullable=True),
        sa.Column("counterpart_position", sa.Text, nullable=True),
        sa.Column("legal_review", sa.Text, nullable=True),
        sa.Column("ai_suggestion", sa.Text, nullable=True),
        sa.Column("ai_suggestion_rationale", sa.Text, nullable=True),
        sa.Column("status", negotiationissuestatus, nullable=False, server_default="OPEN"),
        sa.Column("priority", negotiationissuepriority, nullable=False, server_default="MEDIUM"),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.String(30), nullable=True),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_negotiation_issues_transaction_id", "negotiation_issues", ["transaction_id"])
    op.create_index("ix_negotiation_issues_meeting_id", "negotiation_issues", ["meeting_id"])

    # ── contract_markups ──────────────────────────────────
    op.create_table(
        "contract_markups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contract_id", sa.Uuid(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meeting_logs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version_label", sa.String(100), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("source_party", sa.String(200), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("changes_summary", sa.Text, nullable=True),
        sa.Column("key_changes", _JSON, nullable=True),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_contract_markups_contract_id", "contract_markups", ["contract_id"])


def downgrade() -> None:
    op.drop_index("ix_contract_markups_contract_id")
    op.drop_table("contract_markups")
    op.drop_index("ix_negotiation_issues_meeting_id")
    op.drop_index("ix_negotiation_issues_transaction_id")
    op.drop_table("negotiation_issues")
    op.drop_index("ix_meeting_action_items_meeting_id")
    op.drop_table("meeting_action_items")
    op.drop_index("ix_meeting_attendees_meeting_id")
    op.drop_table("meeting_attendees")
    op.drop_index("ix_meeting_logs_contract_id")
    op.drop_index("ix_meeting_logs_buyer_id")
    op.drop_index("ix_meeting_logs_transaction_id")
    op.drop_table("meeting_logs")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS negotiationissuepriority")
        op.execute("DROP TYPE IF EXISTS negotiationissuestatus")
        op.execute("DROP TYPE IF EXISTS conditionmatchlevel")
        op.execute("DROP TYPE IF EXISTS buyerreaction")
        op.execute("DROP TYPE IF EXISTS actionitemstatus")
        op.execute("DROP TYPE IF EXISTS attendeerole")
        op.execute("DROP TYPE IF EXISTS meetingstatus")
        op.execute("DROP TYPE IF EXISTS meetingchannel")
        op.execute("DROP TYPE IF EXISTS meetingphase")
