"""Financial Models: 재무모델 + 체크리스트 + 체크리스트 항목 3개 테이블.

VDR 기반 자동 추출 → 사용자 리뷰 → Ralph Loop 최종 Excel 생성 워크플로우.

Revision ID: 020
Revises: 019
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB as _JSONB

_JSON = sa.JSON().with_variant(_JSONB, "postgresql")

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. financial_models 테이블 ─────────────────────────
    # Enum 타입은 sa.Enum()이 create_table 시 자동 생성
    op.create_table(
        "financial_models",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_type",
            sa.Enum("DCF", "LBO", "COMPS", "TRANSACTION_COMPS", "PROJECTION", "FULL", name="financialmodeltype"),
            nullable=False,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT", "GENERATING", "PENDING_REVIEW", "FINALIZING", "READY", "FAILED", name="financialmodelstatus"
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("parameters", _JSON, nullable=True),
        sa.Column("vdr_document_ids", _JSON, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column(
            "ralph_session_id",
            sa.Uuid(),
            sa.ForeignKey("ralph_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ralph_score", sa.Float, nullable=True),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fm_transaction_id", "financial_models", ["transaction_id"])
    op.create_index("ix_fm_txn_type_status", "financial_models", ["transaction_id", "model_type", "status"])

    # ── 3. fm_checklists 테이블 ────────────────────────────
    op.create_table(
        "fm_checklists",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "financial_model_id",
            sa.Uuid(),
            sa.ForeignKey("financial_models.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum("GENERATING", "PENDING_REVIEW", "REVIEWED", "FINALIZED", name="fmcheckliststatus"),
            nullable=False,
            server_default="GENERATING",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fm_checklist_model", "fm_checklists", ["financial_model_id"])
    op.create_index("ix_fm_checklist_status", "fm_checklists", ["status"])

    # ── 4. fm_checklist_items 테이블 ───────────────────────
    op.create_table(
        "fm_checklist_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "checklist_id",
            sa.Uuid(),
            sa.ForeignKey("fm_checklists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "REVENUE_FORECAST",
                "GROWTH_ASSUMPTIONS",
                "VOLUME_PRICE_MIX",
                "COGS_FORECAST",
                "SGA_FORECAST",
                "DEPRECIATION_AMORT",
                "CAPEX_FORECAST",
                "NWC_ASSUMPTIONS",
                "FCF_DERIVATION",
                "FM_DEBT_SCHEDULE",
                "WACC_COMPONENTS",
                "TAX_RATE",
                "DCF_PARAMETERS",
                "TRADING_MULTIPLES",
                "TRANSACTION_MULTIPLES",
                "BASE_SCENARIO",
                "UPSIDE_SCENARIO",
                "DOWNSIDE_SCENARIO",
                "SENSITIVITY_MATRIX",
                name="fmchecklistcategory",
            ),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        # 자동 추출
        sa.Column("auto_finding", sa.Text, nullable=True),
        sa.Column("auto_value", sa.String(200), nullable=True),
        # 사용자 수정
        sa.Column("user_correction", sa.Text, nullable=True),
        sa.Column("user_value", sa.String(200), nullable=True),
        # 메타
        sa.Column(
            "status",
            sa.Enum(
                "AUTO_GENERATED", "CONFIRMED", "CORRECTED", "FLAGGED", "NOT_APPLICABLE", name="fmchecklistitemstatus"
            ),
            nullable=False,
            server_default="AUTO_GENERATED",
        ),
        sa.Column("severity", sa.Enum("HIGH", "MEDIUM", "LOW", "INFO", name="fmchecklistseverity"), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("field_type", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        # VDR 소스
        sa.Column("source_vdr_doc_id", sa.Uuid(), nullable=True),
        sa.Column("source_vdr_doc_name", sa.String(300), nullable=True),
        sa.Column("source_location", sa.String(200), nullable=True),
        # 리뷰
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", _JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fm_cl_item_checklist", "fm_checklist_items", ["checklist_id"])
    op.create_index("ix_fm_cl_item_category", "fm_checklist_items", ["category"])


def downgrade() -> None:
    op.drop_table("fm_checklist_items")
    op.drop_table("fm_checklists")
    op.drop_table("financial_models")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS fmchecklistseverity")
        op.execute("DROP TYPE IF EXISTS fmchecklistcategory")
        op.execute("DROP TYPE IF EXISTS fmchecklistitemstatus")
        op.execute("DROP TYPE IF EXISTS fmcheckliststatus")
        op.execute("DROP TYPE IF EXISTS financialmodelstatus")
        op.execute("DROP TYPE IF EXISTS financialmodeltype")
