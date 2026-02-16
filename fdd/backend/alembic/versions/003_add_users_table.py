"""Add users table for RBAC v1.

Revision ID: 003_users
Revises: 002_nwc_debt
Create Date: 2026-02-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_users"
down_revision: str | None = "002_nwc_debt"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── UserRole enum ──────────────────────────────────────────
    userrole = postgresql.ENUM(
        "ADMIN",
        "MANAGER",
        "ANALYST",
        "VIEWER",
        name="userrole",
        create_type=False,
    )
    userrole.create(op.get_bind(), checkfirst=True)

    # ── users 테이블 ──────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "ADMIN",
                "MANAGER",
                "ANALYST",
                "VIEWER",
                name="userrole",
                create_type=False,
            ),
            nullable=False,
            server_default="ANALYST",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── audit_log에 user_id 컬럼 추가 ─────────────────────────
    op.add_column(
        "audit_log",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("audit_log", "user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
