"""VDR 접근 추적 로그 — 매수자 실사 활동 기록."""

import uuid

from sqlalchemy import Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import VdrAccessAction


class VdrAccessLog(Base, TimestampMixin):
    """VDR 문서 접근 기록.

    매수자별 실사 진행 현황(조회·다운로드·업로드)을 추적한다.
    AuditLog(CRUD 감사)와 목적이 다르므로 별도 테이블로 관리.
    """

    __tablename__ = "vdr_access_logs"
    __table_args__ = (
        Index("ix_vdr_access_logs_txn_email", "transaction_id", "user_email"),
        Index("ix_vdr_access_logs_txn_buyer", "transaction_id", "buyer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("vdr_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("vdr_folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── 접근자 정보 ────────────────────────────────────
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[VdrAccessAction] = mapped_column(Enum(VdrAccessAction), nullable=False)

    # ── 메타데이터 ─────────────────────────────────────
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── 매수자 연결 (nullable — ADVISOR 접근 시 null) ──
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("buyer_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
