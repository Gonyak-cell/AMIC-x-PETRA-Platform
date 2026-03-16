"""Cloudflare /crawl API로 수집한 IB 뉴스 기사 모델.

Phase B에서 활성화. Phase A에서는 테이블만 생성하여 스키마를 선점한다.
"""

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CFNewsArticle(Base, TimestampMixin):
    """Cloudflare /crawl로 수집한 IB 뉴스 기사."""

    __tablename__ = "cf_news_articles"
    __table_args__ = (Index("ix_cf_news_source_published", "source", "published_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500))
    lead_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str] = mapped_column(String(2000), unique=True)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_paywalled: Mapped[bool] = mapped_column(Boolean, default=False)

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """URL의 SHA256 해시를 생성한다."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()
