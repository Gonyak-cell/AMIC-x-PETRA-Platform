"""add audit_logs table

Revision ID: 005_audit_logs
Revises: 004_add_user_title
Create Date: 2026-02-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB as _JSONB

_JSON = sa.JSON().with_variant(_JSONB, "postgresql")

revision = "005_audit_logs"
down_revision = "004_add_user_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE",
                "UPDATE",
                "DELETE",
                "LOGIN",
                "LOGOUT",
                "EXPORT",
                name="im_auditaction",
            ),
            nullable=False,
        ),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("old_value", _JSON, nullable=True),
        sa.Column("new_value", _JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("ix_im_audit_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_im_audit_action", "audit_logs", ["action"])
    op.create_index("ix_im_audit_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_im_audit_created")
    op.drop_index("ix_im_audit_action")
    op.drop_index("ix_im_audit_entity")
    op.drop_table("audit_logs")
    op.execute("DROP TYPE IF EXISTS im_auditaction")
