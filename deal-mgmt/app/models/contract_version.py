import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ContractVersion(Base, TimestampMixin):
    """계약서 버전 이력 — Contract와 1:N 관계."""

    __tablename__ = "contract_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("contracts.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    changes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
