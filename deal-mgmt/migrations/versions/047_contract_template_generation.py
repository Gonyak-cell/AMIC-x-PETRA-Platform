"""계약서 템플릿 자동 생성 시스템.

- contract_templates, contract_clauses, template_variables 테이블 생성
- legal_documents 테이블에 generated_html, template_id 컬럼 추가
"""

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    # ── contract_templates ──────────────────────────────────────────────
    op.create_table(
        "contract_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "doc_type",
            sa.Enum("SPA", "SHA", "BTA", "SSA", "MOU", name="legaldoctype", create_type=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ACTIVE", "ARCHIVED", name="contracttemplatestatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "metadata_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── contract_clauses ────────────────────────────────────────────────
    op.create_table(
        "contract_clauses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("contract_templates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("clause_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_boilerplate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("condition_expression", sa.String(500), nullable=True),
        sa.Column(
            "metadata_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "clause_order", name="uq_clause_template_order"),
    )

    # ── template_variables ──────────────────────────────────────────────
    op.create_table(
        "template_variables",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("contract_templates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("variable_key", sa.String(100), nullable=False),
        sa.Column(
            "input_type",
            sa.Enum(
                "TEXT",
                "TEXTAREA",
                "NUMBER",
                "DATE",
                "SELECT",
                "BOOLEAN",
                "CURRENCY",
                "PERCENTAGE",
                name="templatevariableinputtype",
            ),
            nullable=False,
            server_default="TEXT",
        ),
        sa.Column("question_label", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_value", sa.String(500), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "select_options",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("group_name", sa.String(100), nullable=True),
        sa.Column("visible_condition", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "variable_key", name="uq_variable_template_key"),
    )

    # ── legal_documents 확장 ────────────────────────────────────────────
    op.add_column("legal_documents", sa.Column("generated_html", sa.Text(), nullable=True))
    op.add_column(
        "legal_documents",
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("contract_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # ⚠️ template_id FK 참조 + generated_html 데이터가 삭제됩니다.
    # 기존 LegalDocument에 저장된 생성 HTML은 복구 불가.
    op.drop_column("legal_documents", "template_id")
    op.drop_column("legal_documents", "generated_html")
    op.drop_table("template_variables")
    op.drop_table("contract_clauses")
    op.drop_table("contract_templates")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS contracttemplatestatus")
        op.execute("DROP TYPE IF EXISTS templatevariableinputtype")
