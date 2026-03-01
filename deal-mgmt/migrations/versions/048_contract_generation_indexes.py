"""계약서 생성 성능 인덱스 추가.

- legal_documents.template_id FK 인덱스
- contract_templates.status 필터 인덱스
"""

from __future__ import annotations

from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_legal_documents_template_id",
        "legal_documents",
        ["template_id"],
    )
    op.create_index(
        "ix_contract_templates_status",
        "contract_templates",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_contract_templates_status", table_name="contract_templates")
    op.drop_index("ix_legal_documents_template_id", table_name="legal_documents")
