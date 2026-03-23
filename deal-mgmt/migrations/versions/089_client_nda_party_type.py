"""089 add party type support for client NDAs

Revision ID: 089
Revises: 088
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "089"
down_revision: str | None = "088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    nda_party_type = sa.Enum("BUYER", "CLIENT", name="ndapartytype")
    bind = op.get_bind()
    nda_party_type.create(bind, checkfirst=True)

    op.add_column(
        "ndas",
        sa.Column(
            "party_type",
            nda_party_type,
            nullable=True,
            server_default="BUYER",
        ),
    )
    op.create_index(op.f("ix_ndas_party_type"), "ndas", ["party_type"], unique=False)
    op.alter_column("ndas", "buyer_candidate_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("ndas", "party_type", existing_type=nda_party_type, nullable=False)
    op.alter_column("ndas", "party_type", existing_type=nda_party_type, server_default=None)


def downgrade() -> None:
    nda_party_type = sa.Enum("BUYER", "CLIENT", name="ndapartytype")

    op.drop_index(op.f("ix_ndas_party_type"), table_name="ndas")
    op.drop_column("ndas", "party_type")
    op.alter_column("ndas", "buyer_candidate_id", existing_type=sa.Uuid(), nullable=False)

    bind = op.get_bind()
    nda_party_type.drop(bind, checkfirst=True)
