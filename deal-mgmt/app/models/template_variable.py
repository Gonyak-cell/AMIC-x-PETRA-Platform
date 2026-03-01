"""템플릿 변수 모델 — 사용자가 입력하는 계약서 파라미터 정의."""

import uuid

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import TemplateVariableInputType


class TemplateVariable(Base, TimestampMixin):
    """템플릿 변수 — 체크리스트 UI를 동적으로 생성하는 메타데이터."""

    __tablename__ = "template_variables"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("contract_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variable_key: Mapped[str] = mapped_column(String(100), nullable=False)
    input_type: Mapped[TemplateVariableInputType] = mapped_column(
        Enum(TemplateVariableInputType), nullable=False, default=TemplateVariableInputType.TEXT
    )
    question_label: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    select_options: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    visible_condition: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    template: Mapped["ContractTemplate"] = relationship(  # noqa: F821
        "ContractTemplate", back_populates="variables"
    )

    __table_args__ = (UniqueConstraint("template_id", "variable_key", name="uq_variable_template_key"),)
