"""008 — legal_documents status·created_at 인덱스 추가

조회 성능 향상:
  - status 컬럼: 상태별 필터링 (GENERATING, READY, FAILED) 쿼리 최적화
  - created_at 컬럼: 최신 문서 정렬 쿼리 최적화
  - (transaction_id, status) 복합 인덱스: 특정 거래의 GENERATING 문서 감시 폴링 최적화

Revision ID: 008_indexes
Revises: 007_phase6
Create Date: 2026-02-23

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_indexes"
down_revision: Union[str, None] = "007_phase6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 상태 필터링 인덱스 (단일)
    op.create_index(
        "ix_legal_documents_status",
        "legal_documents",
        ["status"],
    )

    # 생성일 정렬 인덱스 (내림차순 — ORDER BY created_at DESC)
    op.create_index(
        "ix_legal_documents_created_at",
        "legal_documents",
        ["created_at"],
        postgresql_using="btree",
        postgresql_ops={"created_at": "DESC"},
    )

    # 거래별 상태 복합 인덱스 — 폴링 쿼리 최적화
    # SELECT * FROM legal_documents WHERE transaction_id=? AND status='GENERATING'
    op.create_index(
        "ix_legal_documents_txn_status",
        "legal_documents",
        ["transaction_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_legal_documents_txn_status", table_name="legal_documents")
    op.drop_index("ix_legal_documents_created_at", table_name="legal_documents")
    op.drop_index("ix_legal_documents_status", table_name="legal_documents")
