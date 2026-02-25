"""Phase 8 — ldd_reports 테이블 (법률실사 보고서 생성)

Revision ID: 010_ldd_reports
Revises: 009_marketing
Create Date: 2026-02-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010_ldd_reports"
down_revision: Union[str, None] = "009_marketing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum 타입 생성 (asyncpg 호환 — DO $$ 패턴) ──────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE lddreportstatus AS ENUM ('DRAFT', 'GENERATING', 'READY', 'FAILED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE lddreporttype AS ENUM ('FULL', 'REDFLAG');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ldditemstatus AS ENUM ('OK', 'ISSUE', 'NA', 'PENDING');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE lddissuelevel AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE lddsectiontype AS ENUM (
                'GOVERNANCE', 'CAPITAL', 'CONTRACTS', 'LITIGATION',
                'LABOR', 'IP', 'REAL_ESTATE', 'PERMITS', 'TAX', 'DATA_IT'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    # ── ldd_reports 테이블 ──
    op.create_table(
        "ldd_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_type",
                  postgresql.ENUM("FULL", "REDFLAG", name="lddreporttype", create_type=False),
                  nullable=False, server_default="FULL"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status",
                  postgresql.ENUM("DRAFT", "GENERATING", "READY", "FAILED", name="lddreportstatus", create_type=False),
                  nullable=False, server_default="DRAFT"),
        sa.Column("target_company", sa.String(200), nullable=True),
        sa.Column("dd_period", sa.String(100), nullable=True),
        sa.Column("law_firm", sa.String(200), nullable=True),
        sa.Column("prepared_by", sa.String(200), nullable=True),
        # 체크리스트 데이터
        sa.Column("sections", postgresql.JSONB, nullable=True),
        # 집계 카운트
        sa.Column("total_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("issue_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("red_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("amber_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("green_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ok_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("na_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pending_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rfi_count", sa.Integer, nullable=False, server_default="0"),
        # 파일 정보
        sa.Column("template_version", sa.String(20), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_by_email", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # ── 인덱스 ──
    op.create_index("ix_ldd_reports_transaction_status", "ldd_reports", ["transaction_id", "status"])
    op.create_index("ix_ldd_reports_report_type", "ldd_reports", ["report_type"])

    # ── updated_at 자동 갱신 트리거 (PostgreSQL) ──
    op.execute("""
        CREATE OR REPLACE FUNCTION update_ldd_reports_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_ldd_reports_updated_at
        BEFORE UPDATE ON ldd_reports
        FOR EACH ROW
        EXECUTE FUNCTION update_ldd_reports_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_ldd_reports_updated_at ON ldd_reports")
    op.execute("DROP FUNCTION IF EXISTS update_ldd_reports_updated_at()")
    op.drop_index("ix_ldd_reports_report_type", table_name="ldd_reports")
    op.drop_index("ix_ldd_reports_transaction_status", table_name="ldd_reports")
    op.drop_table("ldd_reports")
    op.execute("DROP TYPE IF EXISTS lddsectiontype")
    op.execute("DROP TYPE IF EXISTS lddissuelevel")
    op.execute("DROP TYPE IF EXISTS ldditemstatus")
    op.execute("DROP TYPE IF EXISTS lddreporttype")
    op.execute("DROP TYPE IF EXISTS lddreportstatus")
