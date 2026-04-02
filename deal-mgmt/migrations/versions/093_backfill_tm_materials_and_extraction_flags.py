"""093 backfill tm materials and extraction flags

Revision ID: 093
Revises: 092
Create Date: 2026-04-01
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "093"
down_revision: str | Sequence[str] | None = "092"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_extractions",
        sa.Column(
            "auto_apply_signed_at",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        "document_extractions",
        "auto_apply_signed_at",
        server_default=None,
    )

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

    existing_attachment_ids = {
        attachment_id
        for attachment_id in bind.execute(
            sa.select(marketing_materials.c.attachment_id).where(
                marketing_materials.c.attachment_id.is_not(None)
            )
        ).scalars()
    }

    legacy_tm_attachments = bind.execute(
        sa.select(
            attachments.c.id,
            attachments.c.transaction_id,
            attachments.c.file_path,
            attachments.c.file_name,
            attachments.c.file_size_bytes,
            attachments.c.uploaded_by_email,
        ).where(
            attachments.c.entity_type == "MARKETING_MATERIAL",
            attachments.c.entity_id == "TM",
        )
    ).mappings()

    rows_to_insert: list[dict[str, object | None]] = []
    for attachment in legacy_tm_attachments:
        attachment_id = attachment["id"]
        if attachment_id in existing_attachment_ids:
            continue

        file_name = str(attachment["file_name"] or "uploaded-tm")
        title = Path(file_name).stem or file_name
        rows_to_insert.append(
            {
                "id": uuid.uuid4(),
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

    if rows_to_insert:
        bind.execute(sa.insert(marketing_materials), rows_to_insert)


def downgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    attachments = sa.Table(
        "attachments",
        metadata,
        sa.Column("id", sa.Uuid()),
        sa.Column("entity_type", sa.String()),
        sa.Column("entity_id", sa.String()),
    )
    marketing_materials = sa.Table(
        "marketing_materials",
        metadata,
        sa.Column("attachment_id", sa.Uuid()),
        sa.Column("doc_type", sa.String()),
        sa.Column("source_mode", sa.String()),
    )

    legacy_attachment_ids = bind.execute(
        sa.select(attachments.c.id).where(
            attachments.c.entity_type == "MARKETING_MATERIAL",
            attachments.c.entity_id == "TM",
        )
    ).scalars()
    legacy_attachment_ids = list(legacy_attachment_ids)

    if legacy_attachment_ids:
        bind.execute(
            sa.delete(marketing_materials).where(
                marketing_materials.c.attachment_id.in_(legacy_attachment_ids),
                marketing_materials.c.doc_type == "TM",
                marketing_materials.c.source_mode == "UPLOADED",
            )
        )

    op.drop_column("document_extractions", "auto_apply_signed_at")
