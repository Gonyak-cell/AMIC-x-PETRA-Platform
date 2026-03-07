"""072 — vdr_documents 테이블 복합 인덱스 추가

빈번한 쿼리 패턴에 대한 복합 인덱스:
- (transaction_id, classification_status): 분류 상태별 조회
- (folder_id, transaction_id, status): 폴더별 문서 목록

Revision ID: 072
Revises: 071
Create Date: 2026-03-07
"""

from alembic import op

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_vdr_documents_txn_classification",
        "vdr_documents",
        ["transaction_id", "classification_status"],
    )
    op.create_index(
        "ix_vdr_documents_folder_txn_status",
        "vdr_documents",
        ["folder_id", "transaction_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_vdr_documents_folder_txn_status", table_name="vdr_documents")
    op.drop_index("ix_vdr_documents_txn_classification", table_name="vdr_documents")
