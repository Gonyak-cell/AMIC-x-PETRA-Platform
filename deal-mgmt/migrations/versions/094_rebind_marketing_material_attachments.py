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

LEGACY_TM_TITLE_MAX_LEN = 300
LEGACY_TM_FILE_NAME_MAX_LEN = 300
LEGACY_TM_FILE_PATH_MAX_LEN = 500
LEGACY_TM_EMAIL_MAX_LEN = 255

revision: str = "094"
down_revision: str | Sequence[str] | None = "093"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_legacy_text(value: object | None, max_len: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized[:max_len]


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    transactions = sa.Table(
        "transactions",
        metadata,
        sa.Column("id", sa.Uuid()),
    )
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

    valid_transaction_ids = {transaction_id for transaction_id in bind.execute(sa.select(transactions.c.id)).scalars()}
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
    existing_material_by_attachment = {row["attachment_id"]: row["id"] for row in existing_material_rows}

    rows_to_insert: list[dict[str, object | None]] = []
    attachment_rebinds: list[tuple[uuid.UUID, str]] = []

    for attachment in candidate_rows:
        attachment_id = attachment["id"]
        linked_material_id = existing_material_by_attachment.get(attachment_id)
        if linked_material_id is not None:
            attachment_rebinds.append((attachment_id, str(linked_material_id)))
            continue
        transaction_id = attachment["transaction_id"]
        if transaction_id is None or transaction_id not in valid_transaction_ids:
            continue

        file_name = _normalize_legacy_text(attachment["file_name"], LEGACY_TM_FILE_NAME_MAX_LEN) or "uploaded-tm"
        title = _normalize_legacy_text(Path(file_name).stem or file_name, LEGACY_TM_TITLE_MAX_LEN) or "uploaded-tm"
        new_material_id = uuid.uuid4()
        rows_to_insert.append(
            {
                "id": new_material_id,
                "transaction_id": transaction_id,
                "doc_type": "TM",
                "title": title,
                "status": "READY",
                "source_mode": "UPLOADED",
                "attachment_id": attachment_id,
                "file_path": _normalize_legacy_text(attachment["file_path"], LEGACY_TM_FILE_PATH_MAX_LEN),
                "file_name": file_name,
                "file_size_bytes": attachment["file_size_bytes"],
                "quality_status": "SKIPPED",
                "created_by_email": _normalize_legacy_text(attachment["uploaded_by_email"], LEGACY_TM_EMAIL_MAX_LEN),
            }
        )
        attachment_rebinds.append((attachment_id, str(new_material_id)))

    if rows_to_insert:
        bind.execute(sa.insert(marketing_materials), rows_to_insert)

    for attachment_id, material_id in attachment_rebinds:
        bind.execute(sa.update(attachments).where(attachments.c.id == attachment_id).values(entity_id=material_id))


def downgrade() -> None:
    # This migration repairs legacy/orphan attachment bindings in place.
    # Reverting it would risk detaching valid uploaded marketing materials.
    pass
