"""add audit_logs table

Revision ID: c1a2b3d4e5f6
Revises: add_user_title
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "c1a2b3d4e5f6"
down_revision = "add_user_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("action", sa.Enum("CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "EXPORT", name="auditaction"), nullable=False),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_kiis_audit_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_kiis_audit_action", "audit_logs", ["action"])
    op.create_index("ix_kiis_audit_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_kiis_audit_created")
    op.drop_index("ix_kiis_audit_action")
    op.drop_index("ix_kiis_audit_entity")
    op.drop_table("audit_logs")
    op.execute("DROP TYPE IF EXISTS auditaction")
