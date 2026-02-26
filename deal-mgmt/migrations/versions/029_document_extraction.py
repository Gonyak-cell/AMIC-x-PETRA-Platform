"""document_extractions 테이블 + NDA/Bid/Transaction AI 추출 필드.

Revision ID: 029
Revises: 028
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. document_extractions 테이블 ──────────────────────
    op.create_table(
        "document_extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vdr_document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("vdr_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 분류
        sa.Column(
            "doc_category",
            sa.Enum(
                "NDA", "LOI_MOU", "SPA_BTA", "CORPORATE_DOCS", "TAX_FILING",
                "TEASER_IM", "DD_REPORT", "RFI_RESPONSE", "REFERENCE_ONLY",
                name="docextractioncategory",
            ),
            nullable=True,
        ),
        sa.Column("classification_confidence", sa.Float, nullable=True),
        # 상태
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "CLASSIFYING", "EXTRACTING",
                "COMPLETED", "FAILED", "CONFIRMED",
                name="extractionstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        # 추출 결과
        sa.Column("extracted_data", JSONB, nullable=True),
        # 매핑 대상
        sa.Column("target_model", sa.String(50), nullable=True),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        # 비용
        sa.Column("llm_cost_usd", sa.Float, nullable=False, server_default="0"),
        # 사용자 검토
        sa.Column("reviewed_by_email", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.String(50), nullable=True),
        # 타임스탬프
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_document_extractions_txn_id",
        "document_extractions",
        ["transaction_id"],
    )
    op.create_index(
        "ix_document_extractions_vdr_doc_id",
        "document_extractions",
        ["vdr_document_id"],
    )

    # ── 2. ndas 테이블 컬럼 추가 ────────────────────────────
    op.add_column("ndas", sa.Column("counterparty_name", sa.String(200), nullable=True))
    op.add_column("ndas", sa.Column("jurisdiction", sa.String(200), nullable=True))
    op.add_column("ndas", sa.Column("confidentiality_period_months", sa.Integer, nullable=True))

    # ── 3. bids 테이블 컬럼 추가 ────────────────────────────
    op.add_column("bids", sa.Column("exclusivity_period_days", sa.Integer, nullable=True))
    op.add_column("bids", sa.Column("conditions_precedent", JSONB, nullable=True))

    # ── 4. transactions 테이블 JSONB 컬럼 추가 ──────────────
    op.add_column("transactions", sa.Column("corporate_info", JSONB, nullable=True))
    op.add_column("transactions", sa.Column("financial_summary", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "financial_summary")
    op.drop_column("transactions", "corporate_info")
    op.drop_column("bids", "conditions_precedent")
    op.drop_column("bids", "exclusivity_period_days")
    op.drop_column("ndas", "confidentiality_period_months")
    op.drop_column("ndas", "jurisdiction")
    op.drop_column("ndas", "counterparty_name")
    op.drop_index("ix_document_extractions_vdr_doc_id", table_name="document_extractions")
    op.drop_index("ix_document_extractions_txn_id", table_name="document_extractions")
    op.drop_table("document_extractions")
    op.execute("DROP TYPE IF EXISTS extractionstatus")
    op.execute("DROP TYPE IF EXISTS docextractioncategory")
