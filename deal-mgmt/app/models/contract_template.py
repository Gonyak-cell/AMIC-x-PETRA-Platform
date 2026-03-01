"""계약서 템플릿 모델 — SPA/SHA/BTA/SSA/MOU 5종 모듈러 템플릿."""

import uuid

from sqlalchemy import JSON, Enum, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ContractTemplateStatus, LegalDocType


class ContractTemplate(Base, TimestampMixin):
    """계약서 템플릿 — 조항 + 변수의 루트 엔티티."""

    __tablename__ = "contract_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    doc_type: Mapped[LegalDocType] = mapped_column(Enum(LegalDocType), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    status: Mapped[ContractTemplateStatus] = mapped_column(
        Enum(ContractTemplateStatus), nullable=False, default=ContractTemplateStatus.ACTIVE
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    clauses: Mapped[list["ContractClause"]] = relationship(  # noqa: F821
        "ContractClause",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ContractClause.clause_order",
    )
    variables: Mapped[list["TemplateVariable"]] = relationship(  # noqa: F821
        "TemplateVariable",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateVariable.display_order",
    )
