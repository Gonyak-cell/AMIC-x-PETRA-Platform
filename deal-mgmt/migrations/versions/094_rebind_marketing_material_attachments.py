"""094 rebind marketing material attachments

Revision ID: 094
Revises: 093
Create Date: 2026-04-02
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "094"
down_revision: str | Sequence[str] | None = "093"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    attachments = sa.Table(
        "attachments",
        metadata,
        sa.Column("id", sa.Uuid()),
        sa.Column("transaction_id", sa.Uuid()),
        sa.Column("entity_type", sa.String()),
        sa.Column("entity_id", sa.String()),
        sa.Column("file_path", sa.String()),
        sa.Column("file_name", sa.String()),
        sa.Column("file_size_bytes", sa.Integer()),
        sa.Column("uploaded_by_email", sa.String()),
    )
    marketing_materials = sa.Table(
        "marketing_materials",
        metadata,
        sa.Column("id", sa.Uuid()),
        sa.Column("transaction_id", sa.Uuid()),
        sa.Column("doc_type", sa.String()),
        sa.Column("title", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("source_mode", sa.String()),
        sa.Column("attachment_id", sa.Uuid()),
        sa.Column("file_path", sa.String()),
        sa.Column("file_name", sa.String()),
        sa.Column("file_size_bytes", sa.Integer()),
        sa.Column("quality_status", sa.String()),
        sa.Column("created_by_email", sa.String()),
    )

    candidate_rows = list(
        bind.execute(
            sa.select(
                attachments.c.id,
                attachments.c.transaction_id,
                attachments.c.entity_id,
                attachments.c.file_path,
                attachments.c.file_name,
                attachments.c.file_size_bytes,
                attachments.c.uploaded_by_email,
            ).where(
                attachments.c.entity_type == "MARKETING_MATERIAL",
                sa.or_(
                    attachments.c.entity_id == "TM",
                    attachments.c.entity_id.is_(None),
                ),
            )
        ).mappings()
    )

    if not candidate_rows:
        return

    attachment_ids = [row["id"] for row in candidate_rows]
    existing_material_rows = list(
        bind.execute(
            sa.select(marketing_materials.c.id, marketing_materials.c.attachment_id).where(
                marketing_materials.c.attachment_id.in_(attachment_ids)
            )
        ).mappings()
    )
    existing_material_by_attachment = {
        row["attachment_id"]: row["id"] for row in existing_material_rows
    }

    rows_to_insert: list[dict[str, object | None]] = []
    attachment_rebinds: list[tuple[uuid.UUID, str]] = []

    for attachment in candidate_rows:
        attachment_id = attachment["id"]
        linked_material_id = existing_material_by_attachment.get(attachment_id)
        if linked_material_id is not None:
            attachment_rebinds.append((attachment_id, str(linked_material_id)))
            continue

        file_name = str(attachment["file_name"] or "uploaded-tm")
        title = Path(file_name).stem or file_name
        new_material_id = uuid.uuid4()
        rows_to_insert.append(
            {
                "id": new_material_id,
                "transaction_id": attachment["transaction_id"],
                "doc_type": "TM",
                "title": title,
                "status": "READY",
                "source_mode": "UPLOADED",
                "attachment_id": attachment_id,
                "file_path": attachment["file_path"],
                "file_name": file_name,
                "file_size_bytes": attachment["file_size_bytes"],
                "quality_status": "SKIPPED",
                "created_by_email": attachment["uploaded_by_email"],
            }
        )
        attachment_rebinds.append((attachment_id, str(new_material_id)))

    if rows_to_insert:
        bind.execute(sa.insert(marketing_materials), rows_to_insert)

    for attachment_id, material_id in attachment_rebinds:
        bind.execute(
            sa.update(attachments)
            .where(attachments.c.id == attachment_id)
            .values(entity_id=material_id)
        )


def downgrade() -> None:
    # This migration repairs legacy/orphan attachment bindings in place.
    # Reverting it would risk detaching valid uploaded marketing materials.
    pass
