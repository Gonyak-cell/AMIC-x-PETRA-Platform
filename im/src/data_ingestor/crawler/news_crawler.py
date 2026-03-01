"""뉴스 크롤러.

네이버 뉴스, 구글 뉴스 등에서 기업 관련 뉴스를 수집합니다.

사용 예시:
    crawler = NewsCrawler()

    # 키워드로 뉴스 검색
    articles = await crawler.search("삼성전자", days=30)

    # 특정 소스에서 검색
    naver_articles = await crawler.search_naver("현대자동차", count=10)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

from src.data_ingestor.crawler.playwright_engine import CrawlerConfig, PlaywrightEngine
from src.data_ingestor.exceptions import ContentExtractionError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """뉴스 기사 정보."""

    title: str
    """기사 제목."""

    url: str
    """기사 URL."""

    source: str
    """뉴스 소스 (예: 조선일보, 한국경제)."""

    published_at: datetime | None = None
    """게시 일시."""

    summary: str = ""
    """기사 요약."""

    content: str = ""
    """기사 본문 (크롤링된 경우)."""

    thumbnail_url: str = ""
    """썸네일 이미지 URL."""

    author: str = ""
    """기자/저자."""

    category: str = ""
    """카테고리 (경제, IT 등)."""

    keywords: list[str] = field(default_factory=list)
    """관련 키워드."""

    sentiment: float | None = None
    """감성 점수 (-1.0 ~ 1.0). None이면 분석되지 않음."""

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "summary": self.summary,
            "content": self.content,
            "thumbnail_url": self.thumbnail_url,
            "author": self.author,
            "category": self.category,
            "keywords": self.keywords,
            "sentiment": self.sentiment,
        }


class NewsCrawler:
    """뉴스 크롤러.

    네이버 뉴스, 구글 뉴스에서 키워드 기반 뉴스 검색 및
    기사 본문 추출을 제공합니다.

    Attributes:
        engine: Playwright 엔진 인스턴스.

    Example:
        >>> crawler = NewsCrawler()
        >>> articles = await crawler.search("삼성전자", days=7)
        >>> for article in articles[:5]:
        ...     print(f"[{article.source}] {article.title}")
    """

    # 네이버 뉴스 검색 URL
    NAVER_SEARCH_URL = "https://search.naver.com/search.naver"

    # 구글 뉴스 검색 URL
    GOOGLE_NEWS_URL = "https://news.google.com/search"

    def __init__(
        self,
        *,
        headless: bool = True,
        timeout: float = 30.0,
        engine: PlaywrightEngine | None = None,
    ) -> None:
        """NewsCrawler 초기화.

        Args:
            headless: 헤드리스 모드 여부.
            timeout: 크롤링 타임아웃 (초).
            engine: 기존 PlaywrightEngine 인스턴스. None이면 새로 생성.
        """
        self._engine = engine
        self._own_engine = engine is None
        self._config = CrawlerConfig(
            headless=headless,
            timeout=timeout,
            block_images=True,  # 속도 향상
        )
        self._initialized = False

    async def _ensure_engine(self) -> PlaywrightEngine:
        """엔진이 초기화되었는지 확인."""
        if self._engine is None:
            self._engine = PlaywrightEngine(self._config)
            await self._engine._ensure_browser()
            self._initialized = True
        return self._engine

    async def close(self) -> None:
        """리소스 정리."""
        if self._own_engine and self._engine is not None:
            await self._engine.close()
            self._engine = None

    async def search(
        self,
        keyword: str,
        *,
        days: int = 30,
        count: int = 20,
        sources: list[str] | None = None,
    ) -> list[NewsArticle]:
        """여러 소스에서 뉴스를 검색합니다.

        Args:
            keyword: 검색 키워드.
            days: 검색 기간 (일).
            count: 가져올 기사 수.
            sources: 검색할 소스 리스트. None이면 ["naver"].

        Returns:
            뉴스 기사 리스트.
        """
        sources = sources or ["naver"]
        all_articles: list[NewsArticle] = []

        for source in sources:
            if source.lower() == "naver":
                articles = await self.search_naver(keyword, days=days, count=count)
                all_articles.extend(articles)
            elif source.lower() == "google":
                articles = await self.search_google(keyword, days=days, count=count)
                all_articles.extend(articles)

        # 날짜순 정렬
        all_articles.sort(
            key=lambda a: a.published_at or datetime.min,
            reverse=True,
        )

        return all_articles[:count]

    async def search_naver(
        self,
        keyword: str,
        *,
        days: int = 30,
        count: int = 20,
    ) -> list[NewsArticle]:
        """네이버 뉴스에서 검색합니다.

        Args:
            keyword: 검색 키워드.
            days: 검색 기간 (일).
            count: 가져올 기사 수.

        Returns:
            뉴스 기사 리스트.
        """
        engine = await self._ensure_engine()

        # 검색 URL 구성
        params = {
            "where": "news",
            "query": keyword,
            "sm": "tab_opt",
            "sort": "1",  # 최신순
            "photo": "0",
            "field": "0",
            "pd": "4",  # 직접 입력
        }

        # 날짜 범위 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        params["ds"] = start_date.strftime("%Y.%m.%d")
        params["de"] = end_date.strftime("%Y.%m.%d")

        url = f"{self.NAVER_SEARCH_URL}?{urlencode(params)}"
        articles: list[NewsArticle] = []

        try:
            await engine.get_page(url)

            # JavaScript로 기사 추출
            script = """
            Array.from(document.querySelectorAll('.news_wrap')).map(item => {
                const titleEl = item.querySelector('.news_tit');
                const sourceEl = item.querySelector('.info.press');
                const descEl = item.querySelector('.dsc_txt_wrap');
                const dateEl = item.querySelector('.info_group span.info');
                const thumbEl = item.querySelector('.dsc_thumb img');

                return {
                    title: titleEl ? titleEl.innerText.trim() : '',
                    url: titleEl ? titleEl.href : '',
                    source: sourceEl ? sourceEl.innerText.trim() : '',
                    summary: descEl ? descEl.innerText.trim() : '',
                    date: dateEl ? dateEl.innerText.trim() : '',
                    thumbnail: thumbEl ? thumbEl.src : ''
                };
            }).filter(item => item.title && item.url);
            """

            raw_articles = await engine.evaluate_script(url, script)

            for raw in raw_articles[:count]:
                published_at = self._parse_naver_date(raw.get("date", ""))
                articles.append(
                    NewsArticle(
                        title=raw.get("title", ""),
                        url=raw.get("url", ""),
                        source=raw.get("source", "네이버 뉴스"),
                        published_at=published_at,
                        summary=raw.get("summary", ""),
                        thumbnail_url=raw.get("thumbnail", ""),
                    )
                )

        except Exception as e:
            logger.warning("네이버 뉴스 검색 실패: %s", e)

        return articles

    async def search_google(
        self,
        keyword: str,
        *,
        days: int = 30,
        count: int = 20,
        language: str = "ko",
    ) -> list[NewsArticle]:
        """구글 뉴스에서 검색합니다.

        Args:
            keyword: 검색 키워드.
            days: 검색 기간 (일).
            count: 가져올 기사 수.
            language: 언어 코드.

        Returns:
            뉴스 기사 리스트.
        """
        engine = await self._ensure_engine()

        # 구글 뉴스 URL
        encoded_keyword = quote(keyword)
        url = f"{self.GOOGLE_NEWS_URL}?q={encoded_keyword}&hl={language}&gl=KR&ceid=KR:{language}"

        articles: list[NewsArticle] = []

        try:
            await engine.get_page(url)

            # JavaScript로 기사 추출
            script = """
            Array.from(document.querySelectorAll('article')).map(item => {
                const titleEl = item.querySelector('h3, h4');
                const linkEl = item.querySelector('a');
                const sourceEl = item.querySelector('[data-n-tid]');
                const timeEl = item.querySelector('time');

                return {
                    title: titleEl ? titleEl.innerText.trim() : '',
                    url: linkEl ? linkEl.href : '',
                    source: sourceEl ? sourceEl.innerText.trim() : '구글 뉴스',
                    date: timeEl ? timeEl.getAttribute('datetime') : ''
                };
            }).filter(item => item.title && item.url);
            """

            raw_articles = await engine.evaluate_script(url, script)

            for raw in raw_articles[:count]:
                published_at = None
                date_str = raw.get("date", "")
                if date_str:
                    try:
                        published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                articles.append(
                    NewsArticle(
                        title=raw.get("title", ""),
                        url=raw.get("url", ""),
                        source=raw.get("source", "구글 뉴스"),
                        published_at=published_at,
                    )
                )

        except Exception as e:
            logger.warning("구글 뉴스 검색 실패: %s", e)

        return articles

    async def get_article_content(
        self,
        url: str,
        *,
        timeout: float | None = None,
    ) -> str:
        """기사 본문을 가져옵니다.

        Args:
            url: 기사 URL.
            timeout: 타임아웃 (초).

        Returns:
            기사 본문 텍스트.

        Raises:
            ContentExtractionError: 본문 추출 실패.
        """
        engine = await self._ensure_engine()

        try:
            await engine.get_page(url, timeout=timeout)

            # 일반적인 기사 본문 선택자들
            selectors = [
                "article",
                ".article-body",
                ".article_body",
                "#articleBody",
                "#article-body",
                ".news_end",
                "#newsct_article",
                ".story-body",
                "#content",
            ]

            for selector in selectors:
                try:
                    text = await engine.extract_text(url, selector, timeout=timeout)
                    if text and len(text) > 100:
                        return self._clean_article_text(text)
                except Exception:
                    continue

            # 폴백: body에서 추출
            text = await engine.extract_text(url, "body", timeout=timeout)
            return self._clean_article_text(text)

        except Exception as e:
            raise ContentExtractionError(
                message=f"기사 본문 추출 실패: {e}",
                details={"url": url},
            ) from e

    def _parse_naver_date(self, date_str: str) -> datetime | None:
        """네이버 날짜 문자열을 파싱합니다."""
        if not date_str:
            return None

        try:
            # "2024.01.15." 형식
            if re.match(r"\d{4}\.\d{2}\.\d{2}\.", date_str):
                return datetime.strptime(date_str, "%Y.%m.%d.")

            # "1시간 전", "3일 전" 등
            match = re.search(r"(\d+)(분|시간|일|주|개월) 전", date_str)
            if match:
                value = int(match.group(1))
                unit = match.group(2)

                now = datetime.now()
                if unit == "분":
                    return now - timedelta(minutes=value)
                if unit == "시간":
                    return now - timedelta(hours=value)
                if unit == "일":
                    return now - timedelta(days=value)
                if unit == "주":
                    return now - timedelta(weeks=value)
                if unit == "개월":
                    return now - timedelta(days=value * 30)

            # "어제", "그제"
            if "어제" in date_str:
                return datetime.now() - timedelta(days=1)
            if "그제" in date_str:
                return datetime.now() - timedelta(days=2)

        except Exception:
            pass

        return None

    def _clean_article_text(self, text: str) -> str:
        """기사 본문을 정리합니다."""
        # 불필요한 공백 제거
        text = re.sub(r"\s+", " ", text)

        # 광고/관련기사 문구 제거
        patterns = [
            r"\[.*기자\]",
            r"관련기사.*$",
            r"무단.*금지",
            r"저작권.*보호",
            r"ⓒ.*$",
            r"Copyright.*$",
        ]
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text.strip()

    async def analyze_sentiment(
        self,
        articles: list[NewsArticle],
    ) -> list[NewsArticle]:
        """기사들의 감성을 분석합니다.

        Note:
            현재는 간단한 키워드 기반 분석을 수행합니다.
            향후 ML 기반 분석으로 확장 가능.

        Args:
            articles: 분석할 기사 리스트.

        Returns:
            감성 점수가 추가된 기사 리스트.
        """
        positive_keywords = [
            "상승", "호재", "성장", "증가", "돌파", "최고",
            "긍정", "기대", "확대", "개선", "흑자",
        ]
        negative_keywords = [
            "하락", "악재", "감소", "축소", "위기", "최저",
            "우려", "적자", "손실", "하향", "부진",
        ]

        for article in articles:
            text = f"{article.title} {article.summary}"

            positive_count = sum(1 for kw in positive_keywords if kw in text)
            negative_count = sum(1 for kw in negative_keywords if kw in text)

            total = positive_count + negative_count
            if total > 0:
                article.sentiment = (positive_count - negative_count) / total
            else:
                article.sentiment = 0.0

        return articles
