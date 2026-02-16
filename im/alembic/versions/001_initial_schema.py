"""Initial schema — users, api_keys, documents, companies

Revision ID: 001_initial
Revises:
Create Date: 2026-02-10 22:15:00

> 마지막 수정: 2026-02-10 22:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === users ===
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="USER"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # === api_keys ===
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_api_keys_user_id_users")
        ),
        sa.UniqueConstraint("key_hash", name=op.f("uq_api_keys_key_hash")),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # === companies ===
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("corp_code", sa.String(8), nullable=False),
        sa.Column("corp_name", sa.String(200), nullable=False),
        sa.Column("corp_name_en", sa.String(200), nullable=True),
        sa.Column("stock_code", sa.String(10), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("homepage_url", sa.String(500), nullable=True),
        sa.Column("dart_data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"),
        sa.Column(
            "financial_summary", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"
        ),
        sa.Column("brand_assets", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"),
        sa.Column("fetch_task_id", sa.String(255), nullable=True),
        sa.Column("fetch_status", sa.String(20), server_default="PENDING"),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cache_expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("corp_code", name=op.f("uq_companies_corp_code")),
    )
    op.create_index("ix_companies_corp_code", "companies", ["corp_code"])
    op.create_index("ix_companies_stock_code", "companies", ["stock_code"])

    # === documents ===
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("corp_code", sa.String(8), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("project_name", sa.String(200), nullable=True),
        sa.Column("im_style", sa.String(20), server_default="FULL"),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), server_default="[]"),
        sa.Column(
            "generation_config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"
        ),
        sa.Column("status", sa.String(20), server_default="PENDING"),
        sa.Column("progress_pct", sa.Integer(), server_default="0"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "stage_details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}"
        ),
        sa.Column("pptx_path", sa.String(500), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_documents_owner_id_users")
        ),
    )
    op.create_index("ix_documents_corp_code", "documents", ["corp_code"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_celery_task_id", "documents", ["celery_task_id"])
    op.create_index("ix_documents_owner_status", "documents", ["owner_id", "status"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("companies")
    op.drop_table("api_keys")
    op.drop_table("users")
