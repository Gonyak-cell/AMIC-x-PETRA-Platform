"""LDD-VDR 통합: 텍스트 캐시, VDR 참조 링크, LDDReport 확장, 상태 확장.

Ralph Loop 2회 적용 워크플로우 지원:
- ANALYZING (Ralph Loop #1), REVIEW, FINALIZING (Ralph Loop #2) 상태 추가
- vdr_text_caches 테이블: VDR 문서 텍스트 추출 캐시
- ldd_vdr_references 테이블: LDD 항목 ↔ VDR 소스 문서 링크

Revision ID: 019
Revises: 018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. LDDReportStatus enum 확장 ──────────────────────
    op.execute("ALTER TYPE lddreportstatus ADD VALUE IF NOT EXISTS 'ANALYZING' BEFORE 'GENERATING'")
    op.execute("ALTER TYPE lddreportstatus ADD VALUE IF NOT EXISTS 'REVIEW' BEFORE 'GENERATING'")
    op.execute("ALTER TYPE lddreportstatus ADD VALUE IF NOT EXISTS 'FINALIZING' BEFORE 'GENERATING'")

    # ── 2. ldd_reports 테이블 컬럼 추가 ──────────────────
    op.add_column("ldd_reports", sa.Column("vdr_source", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column(
        "ldd_reports",
        sa.Column("draft_ralph_session_id", UUID(as_uuid=True), sa.ForeignKey("ralph_sessions.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "ldd_reports",
        sa.Column("final_ralph_session_id", UUID(as_uuid=True), sa.ForeignKey("ralph_sessions.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("ldd_reports", sa.Column("draft_score", sa.Float(), nullable=True))
    op.add_column("ldd_reports", sa.Column("final_score", sa.Float(), nullable=True))
    op.add_column("ldd_reports", sa.Column("analysis_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ldd_reports", sa.Column("analysis_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ldd_reports", sa.Column("review_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ldd_reports", sa.Column("review_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ldd_reports", sa.Column("finalize_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ldd_reports", sa.Column("finalize_completed_at", sa.DateTime(timezone=True), nullable=True))

    # ── 3. vdr_text_caches 테이블 ─────────────────────────
    op.create_table(
        "vdr_text_caches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("vdr_document_id", UUID(as_uuid=True), sa.ForeignKey("vdr_documents.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("tables_json", JSONB, nullable=True),
        sa.Column("ddrl_sections", JSONB, nullable=True),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("text_length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── 4. ldd_vdr_references 테이블 ──────────────────────
    op.create_table(
        "ldd_vdr_references",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ldd_report_id", UUID(as_uuid=True), sa.ForeignKey("ldd_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(30), nullable=False),
        sa.Column("vdr_document_id", UUID(as_uuid=True), sa.ForeignKey("vdr_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_type", sa.String(30), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence_snippet", sa.String(500), nullable=True),
        sa.Column("page_reference", sa.String(50), nullable=True),
        sa.Column("is_user_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ldd_report_id", "item_id", "vdr_document_id", name="uq_ldd_vdr_ref"),
    )

    # ── 5. 인덱스 ────────────────────────────────────────
    op.create_index("ix_ldd_vdr_references_report_item", "ldd_vdr_references", ["ldd_report_id", "item_id"])
    op.create_index("ix_ldd_vdr_references_document", "ldd_vdr_references", ["vdr_document_id"])
    op.create_index("ix_ldd_reports_draft_session", "ldd_reports", ["draft_ralph_session_id"])
    op.create_index("ix_ldd_reports_final_session", "ldd_reports", ["final_ralph_session_id"])

    # ── 6. updated_at 트리거 ─────────────────────────────
    for table in ("vdr_text_caches", "ldd_vdr_references"):
        op.execute(f"""
            CREATE OR REPLACE FUNCTION update_{table}_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_{table}_updated_at();
        """)


def downgrade() -> None:
    for table in ("ldd_vdr_references", "vdr_text_caches"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
        op.execute(f"DROP FUNCTION IF EXISTS update_{table}_updated_at()")

    op.drop_index("ix_ldd_reports_final_session", "ldd_reports")
    op.drop_index("ix_ldd_reports_draft_session", "ldd_reports")
    op.drop_index("ix_ldd_vdr_references_document", "ldd_vdr_references")
    op.drop_index("ix_ldd_vdr_references_report_item", "ldd_vdr_references")

    op.drop_table("ldd_vdr_references")
    op.drop_table("vdr_text_caches")

    for col in (
        "finalize_completed_at", "finalize_started_at",
        "review_completed_at", "review_started_at",
        "analysis_completed_at", "analysis_started_at",
        "final_score", "draft_score",
        "final_ralph_session_id", "draft_ralph_session_id",
        "vdr_source",
    ):
        op.drop_column("ldd_reports", col)

    # Note: PostgreSQL does not support removing values from enum types.
    # ANALYZING, REVIEW, FINALIZING values will remain but be unused.
