"""085 — add ldd source control columns

Revision ID: 085
Revises: 18ec07933fb5
Create Date: 2026-03-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "085"
down_revision: str | None = "18ec07933fb5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ldd_reports" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("ldd_reports")}
    if "source_routing" not in existing_columns:
        op.add_column("ldd_reports", sa.Column("source_routing", sa.JSON(), nullable=True))
    if "evidence_ledger" not in existing_columns:
        op.add_column("ldd_reports", sa.Column("evidence_ledger", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ldd_reports" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("ldd_reports")}
    if "evidence_ledger" in existing_columns:
        op.drop_column("ldd_reports", "evidence_ledger")
    if "source_routing" in existing_columns:
        op.drop_column("ldd_reports", "source_routing")
