"""계약서 조항 모델 — 특정 템플릿에 소속된 개별 조항."""

import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ContractClause(Base, TimestampMixin):
    """계약서 조항 — Jinja2 템플릿 콘텐츠와 조건식을 포함."""

    __tablename__ = "contract_clauses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("contract_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_boilerplate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    condition_expression: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    template: Mapped["ContractTemplate"] = relationship(  # noqa: F821
        "ContractTemplate", back_populates="clauses"
    )

    __table_args__ = (UniqueConstraint("template_id", "clause_order", name="uq_clause_template_order"),)
