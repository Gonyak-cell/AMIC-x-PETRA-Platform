"""057 — legal_documents에 generated_html, template_id 컬럼 추가

모델에 추가된 컬럼이 마이그레이션 없이 누락되어 프로덕션에서
'column legal_documents.generated_html does not exist' 500 에러 발생.

Revision ID: 057
Revises: 056
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "057"
down_revision: str | None = "056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("legal_documents", sa.Column("generated_html", sa.Text, nullable=True))
    op.add_column(
        "legal_documents",
        sa.Column("template_id", sa.Uuid, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("legal_documents", "template_id")
    op.drop_column("legal_documents", "generated_html")
