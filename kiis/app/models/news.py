import hashlib
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class NewsArticle(TimestampMixin, Base):
    """뉴스 기사 모델"""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), index=True, comment="기사 제목")
    content: Mapped[str | None] = mapped_column(Text, comment="기사 본문")
    summary: Mapped[str | None] = mapped_column(Text, comment="기사 요약")
    source: Mapped[str] = mapped_column(String(50), index=True, comment="출처 (platum, dealsite 등)")
    author: Mapped[str | None] = mapped_column(String(100), comment="저자")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, comment="발행일시")
    url: Mapped[str] = mapped_column(String(1000), unique=True, comment="기사 URL")
    url_hash: Mapped[str] = mapped_column(String(64), index=True, comment="URL SHA256 해시 (중복 감지)")
    sentiment_score: Mapped[float | None] = mapped_column(Float, comment="감성 점수 (-1.0 ~ 1.0)")
    keywords: Mapped[str | None] = mapped_column(Text, comment="키워드 (JSON)")
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True, comment="관련 기업 ID"
    )

    company: Mapped["Company | None"] = relationship(back_populates="news_articles")  # noqa: F821

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """URL의 SHA256 해시를 생성한다."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()
