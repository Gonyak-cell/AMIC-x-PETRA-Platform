import asyncio
import hashlib
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.news import NewsArticle
from app.schemas.news import NewsCollectResponse
from app.utils.http_client import AsyncHTTPClient

logger = logging.getLogger(__name__)

# RSS 피드 소스 목록
RSS_SOURCES: dict[str, str] = {
    "platum": "https://platum.kr/feed",
    "dealsite": "https://dealsite.co.kr/rss",
    "venturesquare": "https://www.venturesquare.net/feed",
}

# HTML 태그 제거 정규식
HTML_TAG_RE = re.compile(r"<[^>]+>")
# 연속 공백 제거
MULTI_SPACE_RE = re.compile(r"\s+")


class NewsService:
    """뉴스 수집 서비스

    RSS 피드에서 뉴스 기사를 수집하고 DB에 저장한다.
    - 중복 감지: URL 해시 기반
    - 본문 전처리: HTML 태그 제거, 텍스트 정규화
    - robots.txt 준수: 요청 간격 2-3초
    """

    def __init__(self) -> None:
        self.client = AsyncHTTPClient(
            timeout=30.0,
            headers={
                "User-Agent": "KIIS/0.1.0 (Investment Intelligence Bot)",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """URL의 SHA256 해시를 생성한다."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def clean_html(html: str) -> str:
        """HTML 태그를 제거하고 텍스트를 정규화한다."""
        if not html:
            return ""
        text = HTML_TAG_RE.sub("", html)
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&nbsp;", " ").replace("&quot;", '"')
        text = MULTI_SPACE_RE.sub(" ", text)
        return text.strip()

    @staticmethod
    def _parse_published_date(entry: dict) -> datetime | None:
        """RSS 엔트리에서 발행일을 파싱한다."""
        published = entry.get("published") or entry.get("updated")
        if not published:
            return None
        try:
            return parsedate_to_datetime(published)
        except (ValueError, TypeError):
            pass
        # feedparser의 parsed struct 사용
        for key in ("published_parsed", "updated_parsed"):
            parsed = entry.get(key)
            if parsed:
                try:
                    return datetime(*parsed[:6])
                except (ValueError, TypeError):
                    pass
        return None

    async def _fetch_rss(self, source: str, url: str) -> list[dict]:
        """RSS 피드를 가져와 파싱한다."""
        try:
            response = await self.client.get(url)
            feed = feedparser.parse(response.text)

            articles = []
            for entry in feed.entries:
                article_url = entry.get("link", "")
                if not article_url:
                    continue

                title = entry.get("title", "")
                content = ""
                if entry.get("content"):
                    content = entry.content[0].get("value", "")
                elif entry.get("summary"):
                    content = entry.get("summary", "")

                articles.append(
                    {
                        "title": self.clean_html(title),
                        "content": self.clean_html(content),
                        "summary": self.clean_html(entry.get("summary", ""))[:500] if entry.get("summary") else None,
                        "source": source,
                        "author": entry.get("author"),
                        "published_at": self._parse_published_date(entry),
                        "url": article_url,
                        "url_hash": self.generate_url_hash(article_url),
                    }
                )

            return articles
        except Exception as e:
            logger.error("RSS fetch failed (source=%s, url=%s): %s", source, url, e)
            return []

    async def _check_duplicates(self, db: AsyncSession, url_hashes: list[str]) -> set[str]:
        """DB에서 이미 존재하는 URL 해시를 조회한다."""
        if not url_hashes:
            return set()
        result = await db.execute(select(NewsArticle.url_hash).where(NewsArticle.url_hash.in_(url_hashes)))
        return set(result.scalars().all())

    async def collect_from_source(self, db: AsyncSession, source: str, url: str) -> NewsCollectResponse:
        """특정 소스에서 뉴스를 수집하고 DB에 저장한다."""
        articles = await self._fetch_rss(source, url)
        collected = len(articles)

        if not articles:
            return NewsCollectResponse(source=source, collected=0, duplicates=0, new_articles=0)

        # 배치 내 중복 제거 (같은 URL이 RSS 피드에 여러 번 등장할 수 있음)
        seen_hashes: set[str] = set()
        unique_articles = []
        for article_data in articles:
            if article_data["url_hash"] not in seen_hashes:
                seen_hashes.add(article_data["url_hash"])
                unique_articles.append(article_data)

        # DB 중복 체크
        url_hashes = [a["url_hash"] for a in unique_articles]
        existing_hashes = await self._check_duplicates(db, url_hashes)
        duplicates = len(existing_hashes)

        # 신규 기사만 저장
        new_count = 0
        for article_data in unique_articles:
            if article_data["url_hash"] in existing_hashes:
                continue

            news_article = NewsArticle(
                title=article_data["title"],
                content=article_data["content"],
                summary=article_data["summary"],
                source=article_data["source"],
                author=article_data["author"],
                published_at=article_data["published_at"],
                url=article_data["url"],
                url_hash=article_data["url_hash"],
            )
            db.add(news_article)
            new_count += 1

        if new_count > 0:
            await db.flush()
            await db.commit()

        return NewsCollectResponse(source=source, collected=collected, duplicates=duplicates, new_articles=new_count)

    async def collect_all(
        self,
        db: AsyncSession,
        source_filter: str | None = None,
    ) -> list[NewsCollectResponse]:
        """전체 또는 특정 소스에서 뉴스를 수집한다."""
        sources = RSS_SOURCES
        if source_filter:
            if source_filter not in RSS_SOURCES:
                return [NewsCollectResponse(source=source_filter, collected=0, duplicates=0, new_articles=0)]
            sources = {source_filter: RSS_SOURCES[source_filter]}

        results = []
        for source, url in sources.items():
            result = await self.collect_from_source(db, source, url)
            results.append(result)
            # robots.txt 준수: 소스 간 간격
            await asyncio.sleep(settings.REITS_REQUEST_DELAY)

        return results

    async def close(self) -> None:
        """HTTP 클라이언트를 종료한다."""
        await self.client.close()
