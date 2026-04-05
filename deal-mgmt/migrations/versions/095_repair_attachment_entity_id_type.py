"""Re-assert attachments.entity_id string type for uploaded attachments.

Revision ID: 095
Revises: 094
Create Date: 2026-04-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "095"
down_revision: str | Sequence[str] | None = "094"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _load_attachment_entity_id_type(bind) -> str | None:
    if bind.dialect.name != "postgresql":
        return None
    result = bind.execute(
        sa.text(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute AS a
            JOIN pg_class AS c ON c.oid = a.attrelid
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = current_schema()
              AND c.relname = 'attachments'
              AND a.attname = 'entity_id'
              AND a.attnum > 0
              AND NOT a.attisdropped
            """
        )
    )
    return result.scalar_one_or_none()


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    entity_id_type = _load_attachment_entity_id_type(bind)
    if entity_id_type is None:
        raise RuntimeError("attachments.entity_id column was not found while validating its database type")

    normalized_type = entity_id_type.strip().lower()
    if normalized_type == "uuid":
        op.execute(sa.text("ALTER TABLE attachments ALTER COLUMN entity_id TYPE VARCHAR(50) USING entity_id::text"))
        return

    if normalized_type in {"character varying(50)", "character varying", "text"}:
        if normalized_type != "character varying(50)":
            op.execute(sa.text("ALTER TABLE attachments ALTER COLUMN entity_id TYPE VARCHAR(50) USING entity_id::text"))
        return

    raise RuntimeError(
        f"Unexpected attachments.entity_id database type {entity_id_type!r}. Expected uuid or a string-compatible type."
    )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM attachments "
            "WHERE entity_id IS NOT NULL "
            "AND entity_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'"
        )
    )
    non_uuid_count = result.scalar() or 0
    if non_uuid_count > 0:
        raise RuntimeError(
            "ROLLBACK BLOCKED: attachments.entity_id contains non-UUID strings. "
            "Remove or null those values before downgrading."
        )

    op.execute(sa.text("ALTER TABLE attachments ALTER COLUMN entity_id TYPE UUID USING entity_id::uuid"))
