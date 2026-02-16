import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VdrFolderType(str, enum.Enum):
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"
    ACCOUNTS_RECEIVABLE = "ACCOUNTS_RECEIVABLE"
    ACCOUNTS_PAYABLE = "ACCOUNTS_PAYABLE"
    BANK_DEBT = "BANK_DEBT"
    LEASE = "LEASE"
    OTHERS = "OTHERS"
    CUSTOM = "CUSTOM"


class VdrFolder(Base):
    __tablename__ = "vdr_folder"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vdr_folder.id", ondelete="CASCADE"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_type: Mapped[VdrFolderType] = mapped_column(
        Enum(VdrFolderType), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    deal: Mapped["Deal"] = relationship(back_populates="vdr_folders")  # noqa: F821
    parent: Mapped["VdrFolder | None"] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list["VdrFolder"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    uploads: Mapped[list["UploadFile"]] = relationship(  # noqa: F821
        back_populates="vdr_folder"
    )
