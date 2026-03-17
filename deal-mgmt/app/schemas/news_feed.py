"""뉴스 피드 Pydantic 스키마 — 대시보드 M&A 뉴스 섹션 응답 모델."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# ── 소스/카테고리 매핑 ──────────────────────────────────────

SOURCE_DISPLAY: dict[str, str] = {
    # KIIS 소스 (기존 4개 IB 매체)
    "investchosun": "인베스트조선",
    "dealsite": "딜사이트",
    "ibtomato": "IB토마토",
    "bizwatch": "비즈워치",
    "kmnanews": "한국M&A신문",
    # Cloudflare 소스 (Phase B 추가 예정)
    "hankyung_ib": "한경IB",
    "mk_ib": "매경IB",
    "chosunbiz_ma": "조선비즈 M&A",
    "thebell": "더벨",
}

CATEGORY_DISPLAY: dict[str, str] = {
    "ma": "M&A",
    "governance": "거버넌스",
    "fund": "펀드",
}

KIIS_SOURCES = {"investchosun", "dealsite", "ibtomato", "bizwatch", "kmnanews"}
CF_SOURCES = {"hankyung_ib", "mk_ib", "chosunbiz_ma", "thebell"}

SourceType = Literal["kiis", "cloudflare"]


def get_source_display(source: str) -> str:
    """소스 코드를 한글 표시명으로 변환한다."""
    return SOURCE_DISPLAY.get(source, source)


def get_category_display(category: str | None) -> str:
    """카테고리 코드를 한글 표시명으로 변환한다."""
    if not category:
        return "미분류"
    return CATEGORY_DISPLAY.get(category, "미분류")


def get_source_type(source: str) -> SourceType:
    """소스가 KIIS인지 Cloudflare인지 판별한다."""
    if source in KIIS_SOURCES:
        return "kiis"
    return "cloudflare"


# ── 응답 스키마 ──────────────────────────────────────────────


class NewsFeedItem(BaseModel):
    """뉴스 피드 개별 아이템."""

    id: str  # "kiis-123" 또는 "cf-<uuid>"
    title: str
    lead_text: str | None = None
    canonical_url: str
    source: str
    source_display: str
    source_type: SourceType
    published_at: datetime | None = None
    category: str | None = None
    category_display: str = "미분류"
    is_paywalled: bool = False
    markdown_available: bool = False


class NewsFeedResponse(BaseModel):
    """뉴스 피드 API 응답."""

    items: list[NewsFeedItem]
    total: int
    cached: bool = False
    error: str | None = None
