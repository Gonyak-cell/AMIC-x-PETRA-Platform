"""071 — attachments 테이블에 vdr_document_id FK 추가

마케팅 자료 첨부 파일 → VDR 자동 연동을 위한 참조 컬럼.
ondelete=SET NULL: VDR 문서 삭제 시 attachment 참조만 해제.

Revision ID: 071
Revises: 070
Create Date: 2026-03-07
"""

import sqlalchemy as sa
from alembic import op

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attachments",
        sa.Column("vdr_document_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_attachments_vdr_document_id",
        "attachments",
        "vdr_documents",
        ["vdr_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_attachments_vdr_document_id", "attachments", ["vdr_document_id"])


def downgrade() -> None:
    op.drop_index("ix_attachments_vdr_document_id", table_name="attachments")
    op.drop_constraint("fk_attachments_vdr_document_id", "attachments", type_="foreignkey")
    op.drop_column("attachments", "vdr_document_id")
