"""SQLAlchemy 선언적 Base 및 메타데이터 설정 (T-I03).

> 마지막 수정: 2026-02-10 16:29:08

Alembic autogenerate와 호환되는 naming convention을 적용한다.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Alembic 친화적 naming convention
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """모든 ORM 모델의 기본 클래스."""

    metadata = MetaData(naming_convention=convention)
