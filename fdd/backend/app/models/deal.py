import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
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
from app.utils.db_types import JsonbColumn


class DealType(str, enum.Enum):
    COMPLETION_ACCOUNTS = "COMPLETION_ACCOUNTS"
    LOCKED_BOX = "LOCKED_BOX"


class DealStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class DefinitionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"


class SnapshotStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class IndustryType(str, enum.Enum):
    GENERAL = "general"
    TECH_SAAS = "tech"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    FINANCIAL_SERVICES = "financial_services"
    LOGISTICS = "logistics"


class DealStructure(str, enum.Enum):
    """거래구조"""

    SHARE_ACQUISITION = "SHARE_ACQUISITION"
    ASSET_ACQUISITION = "ASSET_ACQUISITION"
    MERGER = "MERGER"
    CORPORATE_SPLIT = "CORPORATE_SPLIT"
    MBO = "MBO"
    OTHER = "OTHER"


class InvestmentType(str, enum.Enum):
    """투자 유형"""

    EQUITY = "EQUITY"
    DEBT = "DEBT"
    MEZZANINE = "MEZZANINE"
    CONVERTIBLE = "CONVERTIBLE"
    OTHER = "OTHER"


class SellerType(str, enum.Enum):
    """매도인 유형"""

    INDIVIDUAL = "INDIVIDUAL"
    CORPORATE = "CORPORATE"
    INSTITUTIONAL = "INSTITUTIONAL"
    PE_FUND = "PE_FUND"
    MANAGEMENT = "MANAGEMENT"
    OTHER = "OTHER"


class DealPhase(str, enum.Enum):
    MOU = "MOU"
    VDR_SETUP = "VDR_SETUP"
    DATA_UPLOAD = "DATA_UPLOAD"
    ANALYSIS = "ANALYSIS"
    CHECKLIST_REVIEW = "CHECKLIST_REVIEW"
    REPORTING = "REPORTING"


class Deal(Base):
    __tablename__ = "deal"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_type: Mapped[DealType] = mapped_column(Enum(DealType), nullable=False)
    base_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="KRW"
    )
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[DealStatus] = mapped_column(
        Enum(DealStatus), nullable=False, default=DealStatus.DRAFT
    )
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Workflow: client/target information
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Workflow: industry classification
    industry: Mapped[IndustryType] = mapped_column(
        Enum(
            IndustryType,
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
        default=IndustryType.GENERAL,
    )

    # Workflow: deal classification
    deal_structure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    investment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    seller_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Workflow: team composition
    team_partner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Workflow: FDD scope flags
    scope_qoe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scope_nwc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scope_debt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Workflow: current phase
    current_phase: Mapped[DealPhase] = mapped_column(
        Enum(DealPhase), nullable=False, default=DealPhase.MOU
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    definitions: Mapped[list["DealDefinition"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        order_by="DealDefinition.version",
    )
    snapshots: Mapped[list["DealSnapshot"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(  # noqa: F821
        back_populates="deal", cascade="all, delete-orphan"
    )
    vdr_folders: Mapped[list["VdrFolder"]] = relationship(  # noqa: F821
        back_populates="deal", cascade="all, delete-orphan"
    )
    report_versions: Mapped[list["ReportVersion"]] = relationship(  # noqa: F821
        back_populates="deal", cascade="all, delete-orphan"
    )


class DealDefinition(Base):
    __tablename__ = "deal_definition"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deal.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    definition_data: Mapped[dict] = mapped_column(JsonbColumn, nullable=False)
    status: Mapped[DefinitionStatus] = mapped_column(
        Enum(DefinitionStatus), nullable=False, default=DefinitionStatus.DRAFT
    )
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    deal: Mapped["Deal"] = relationship(back_populates="definitions")


class DealSnapshot(Base):
    __tablename__ = "deal_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deal.id", ondelete="CASCADE"), nullable=False
    )
    definition_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal_definition.id", ondelete="CASCADE"),
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[SnapshotStatus] = mapped_column(
        Enum(SnapshotStatus), nullable=False, default=SnapshotStatus.RUNNING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    deal: Mapped["Deal"] = relationship(back_populates="snapshots")
    definition: Mapped["DealDefinition"] = relationship()
