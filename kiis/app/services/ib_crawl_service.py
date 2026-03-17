"""IB 매체 크롤링 서비스

4개 IB 전문 매체(인베스트조선, 딜사이트, IB토마토, 블로터)에서
무료 공개 기사를 수집하는 어댑터 패턴 기반 크롤러.

제한사항:
- 로그인/유료 결제 없이 접근 가능한 무료 기사만 수집
- Paywall 탐지 시 is_paywalled=True, og:description만 저장
- robots.txt 준수 (요청 간 딜레이)
"""

import asyncio
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ib_article import MAX_LEAD_TEXT_LENGTH, MIN_PARAGRAPH_LENGTH, IBArticle
from app.utils.http_client import AsyncHTTPClient

logger = logging.getLogger(__name__)

# 섹션 분류기 lazy init (모듈 레벨 싱글턴)
_section_classifier = None


def _get_section_classifier():
    """MASectionClassifier 싱글턴을 반환한다 (순환 import 방지를 위해 lazy)."""
    global _section_classifier
    if _section_classifier is None:
        from app.services.ma_section_classifier import MASectionClassifier

        _section_classifier = MASectionClassifier()
    return _section_classifier


def _apply_section_inline(article: IBArticle, body_text: str | None = None) -> None:
    """수집 시점에 3섹션 분류를 즉시 적용한다 (본문 → lead_text 폴백)."""
    import json
    from datetime import UTC, datetime

    clf = _get_section_classifier()
    classify_body = body_text or article.lead_text
    result = clf.classify(article.title, classify_body)
    article.section_primary = result.primary
    article.section_labels_json = json.dumps(result.labels, ensure_ascii=False) if result.labels else None
    article.section_scores_json = json.dumps(result.detail, ensure_ascii=False, default=str)
    article.section_classified_at = datetime.now(UTC)
    article.section_version = clf.version


# HTML 태그 제거 정규식
HTML_TAG_RE = re.compile(r"<[^>]+>")
MULTI_SPACE_RE = re.compile(r"\s+")

# 공통 Paywall 감지 패턴
PAYWALL_PATTERNS = [
    re.compile(r"(구독자\s*전용|회원\s*전용|유료\s*회원|프리미엄\s*기사)", re.IGNORECASE),
    re.compile(r"(로그인\s*후\s*열람|결제\s*후\s*이용)", re.IGNORECASE),
    re.compile(r"유료\s*사이트에\s*노출된\s*기사", re.IGNORECASE),
    re.compile(r"(premium\s*content|subscribers?\s*only)", re.IGNORECASE),
]


def clean_html(html: str) -> str:
    """HTML 태그를 제거하고 텍스트를 정규화한다."""
    if not html:
        return ""
    text = HTML_TAG_RE.sub("", html)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"')
    text = MULTI_SPACE_RE.sub(" ", text)
    return text.strip()


def generate_url_hash(url: str) -> str:
    """URL의 SHA256 해시를 생성한다.

    IBArticle.generate_url_hash 와 동일 로직. 모듈 레벨 편의 함수.
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _parse_rss_date(entry: dict) -> datetime | None:
    """RSS 엔트리에서 발행일시를 추출한다 (feedparser 호환)."""
    published = entry.get("published") or entry.get("updated")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published)
    except (ValueError, TypeError):
        pass
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6])
            except (ValueError, TypeError):
                pass
    return None


def detect_paywall_common(html: str) -> bool:
    """공통 Paywall 패턴을 감지한다."""
    return any(p.search(html) for p in PAYWALL_PATTERNS)


def _extract_og_description(soup: BeautifulSoup) -> str:
    """og:description 또는 meta description을 추출한다."""
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return clean_html(str(og["content"]))
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return clean_html(str(meta["content"]))
    return ""


def _extract_lead_paragraph(soup: BeautifulSoup, selectors: list[str]) -> str:
    """지정된 CSS 선택자에서 첫 문단을 추출한다."""
    for selector in selectors:
        container = soup.select_one(selector)
        if container:
            first_p = container.find("p")
            if first_p:
                text = clean_html(first_p.get_text(strip=True))
                if len(text) > MIN_PARAGRAPH_LENGTH:
                    return text[:MAX_LEAD_TEXT_LENGTH]
    return ""


# ─────────── 추상 어댑터 ───────────


class IBSourceAdapter(ABC):
    """IB 매체 크롤러 추상 베이스 클래스

    서브클래스는 fetch_article_list를 구현하고,
    content_selectors / author_selectors를 오버라이드하여 상세 파싱을 커스터마이즈한다.
    """

    source_name: str
    base_url: str
    content_selectors: list[str] = [".article-body", "#article-body", "article"]
    author_selectors: str = ".byline, .reporter"

    def __init__(self, client: AsyncHTTPClient) -> None:
        self.client = client

    @abstractmethod
    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        """기사 목록(제목, URL, 발행일 등 메타데이터)을 수집한다."""
        ...

    async def fetch_article_detail(self, url: str) -> dict | None:
        """기사 상세 페이지에서 lead_text, author, body_text를 추출한다.

        body_text: 기사 본문 전체 평문 (분류에만 사용, DB 미저장).
        공통 로직을 제공한다. 서브클래스는 content_selectors, author_selectors로 커스터마이즈.
        """
        try:
            resp = await self.client.get(url)
            html = resp.text
            soup = BeautifulSoup(html, "lxml")
            is_paywalled = self.detect_paywall(html, soup=soup)

            body_text = ""
            if is_paywalled:
                lead_text = _extract_og_description(soup)
            else:
                lead_text = _extract_lead_paragraph(soup, self.content_selectors)
                if not lead_text:
                    lead_text = _extract_og_description(soup)
                # 본문 전체 평문 추출 (분류용, 저장 안 함)
                for selector in self.content_selectors:
                    container = soup.select_one(selector)
                    if container:
                        body_text = clean_html(container.get_text(" ", strip=True))
                        break

            author_tag = soup.select_one(self.author_selectors)
            author = clean_html(author_tag.get_text(strip=True)) if author_tag else None

            return {
                "lead_text": lead_text[:MAX_LEAD_TEXT_LENGTH] if lead_text else None,
                "author": author,
                "is_paywalled": is_paywalled,
                "body_text": body_text or None,
            }
        except Exception:
            logger.warning("%s 상세 수집 실패: %s", self.source_name, url, exc_info=True)
            return None

    def detect_paywall(self, html: str, *, soup: BeautifulSoup | None = None) -> bool:
        """Paywall을 감지한다. 서브클래스에서 오버라이드 가능."""
        return detect_paywall_common(html)


# ─────────── 인베스트조선 ───────────


class InvestChosunAdapter(IBSourceAdapter):
    """인베스트조선 어댑터 (investchosun.com) — RSS 활용"""

    source_name = "investchosun"
    base_url = "https://www.investchosun.com"
    rss_url = "https://www.investchosun.com/rss/rss.xml"
    content_selectors = [".article-body", "#article-body", ".news-content", "article"]
    author_selectors = ".byline, .reporter, .article-info .name"

    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        articles: list[dict] = []
        try:
            resp = await self.client.get(self.rss_url)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[: max_pages * 20]:
                try:
                    article_url = entry.get("link", "")
                    if not article_url:
                        continue
                    title = clean_html(entry.get("title", ""))
                    published_at = _parse_rss_date(entry)
                    summary = clean_html(entry.get("summary", entry.get("description", "")))
                    articles.append(
                        {
                            "title": title,
                            "url": article_url,
                            "published_at": published_at,
                            "lead_text": summary[:MAX_LEAD_TEXT_LENGTH] if summary else None,
                        }
                    )
                except Exception:
                    logger.debug("인베스트조선 RSS entry 파싱 스킵: %s", entry.get("link", "unknown"))
                    continue
        except Exception:
            logger.warning("인베스트조선 RSS 수집 실패", exc_info=True)
        return articles

    def detect_paywall(self, html: str, *, soup: BeautifulSoup | None = None) -> bool:
        if detect_paywall_common(html):
            return True
        if soup is None:
            soup = BeautifulSoup(html, "lxml")
        premium = soup.select_one(".premium, .subscriber-only, .paywall")
        return premium is not None


# ─────────── 딜사이트 ───────────


class DealsiteAdapter(IBSourceAdapter):
    """딜사이트 어댑터 (dealsite.co.kr) — 메인페이지 HTML 스크래핑"""

    source_name = "dealsite"
    base_url = "https://dealsite.co.kr"
    content_selectors = [".article-body", ".article-content", "#article-body", "article"]

    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        articles: list[dict] = []
        seen_urls: set[str] = set()
        try:
            resp = await self.client.get(self.base_url)
            soup = BeautifulSoup(resp.text, "lxml")
            for link_tag in soup.select("a[href^='/articles/'][title]"):
                href = link_tag.get("href", "")
                title = link_tag.get("title", "").strip()
                if not href or not title:
                    continue
                full_url = f"{self.base_url}{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                articles.append({"title": clean_html(title), "url": full_url})
        except Exception:
            logger.warning("딜사이트 목록 수집 실패", exc_info=True)
        return articles


# ─────────── IB토마토 ───────────


class IBTomatoAdapter(IBSourceAdapter):
    """IB토마토 어댑터 (ibtomato.com) — ASP.NET 구조 HTML 스크래핑"""

    source_name = "ibtomato"
    base_url = "https://www.ibtomato.com"
    # IB금융 카테고리 (cate=1100, subCate=1101=투자은행, 1102=PE·M&A)
    list_urls = [
        "https://www.ibtomato.com/CateSub.aspx?cate=1100&subCate=1101&type=1",
        "https://www.ibtomato.com/CateSub.aspx?cate=1100&subCate=1102&type=1",
    ]
    content_selectors = [".article-body", "#article-body", ".article-content", ".viewBox", "article"]

    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        articles: list[dict] = []
        seen_urls: set[str] = set()
        for list_url in self.list_urls:
            try:
                resp = await self.client.get(list_url)
                soup = BeautifulSoup(resp.text, "lxml")
                for link_tag in soup.select("a[href*='View.aspx?no=']"):
                    href = link_tag.get("href", "")
                    if not href:
                        continue
                    # &amp; → & 변환
                    href = href.replace("&amp;", "&")
                    if not href.startswith("http"):
                        if not href.startswith("/"):
                            href = f"/{href}"
                        href = f"{self.base_url}{href}"
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    # 제목 추출: .s_tit6 span 내부 또는 직접 텍스트
                    title_el = link_tag.select_one(".s_tit6 span, .s_tit6")
                    if title_el:
                        # 카테고리 태그(.l_con) 제거 후 텍스트 추출
                        for cat_tag in title_el.select(".l_con"):
                            cat_tag.decompose()
                        title = title_el.get_text(strip=True)
                    else:
                        title = link_tag.get_text(strip=True)
                    if title:
                        articles.append({"title": clean_html(title), "url": href})
            except Exception:
                logger.warning("IB토마토 목록 수집 실패: %s", list_url, exc_info=True)
            await asyncio.sleep(settings.IB_CRAWL_REQUEST_DELAY)
        return articles


# ─────────── 블로터 ───────────


class BizwatchAdapter(IBSourceAdapter):
    """비즈워치 어댑터 (news.bizwatch.co.kr) — 거버넌스 섹션 HTML 스크래핑"""

    source_name = "bizwatch"
    base_url = "https://news.bizwatch.co.kr"
    list_url = "https://news.bizwatch.co.kr/category/governance"
    content_selectors = [".article_content", ".article_body", ".view_cont", "article"]
    author_selectors = ".byline, .reporter, .writer"

    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        articles: list[dict] = []
        seen_urls: set[str] = set()
        try:
            resp = await self.client.get(self.list_url)
            soup = BeautifulSoup(resp.text, "lxml")
            for dt_tag in soup.select("dt.title a"):
                href = dt_tag.get("href", "")
                if not href:
                    continue
                # //news.bizwatch.co.kr/... → https://news.bizwatch.co.kr/...
                if href.startswith("//"):
                    href = f"https:{href}"
                elif not href.startswith("http"):
                    href = f"{self.base_url}{href}"
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                title = dt_tag.get_text(strip=True)
                if not title:
                    continue
                # 같은 <dl> 내 dd.body에서 lead_text 추출
                dl = dt_tag.find_parent("dl")
                lead_text = None
                if dl:
                    body_tag = dl.select_one("dd.body a")
                    if body_tag:
                        lead_text = clean_html(body_tag.get_text(strip=True))
                articles.append(
                    {
                        "title": clean_html(title),
                        "url": href,
                        "lead_text": lead_text[:MAX_LEAD_TEXT_LENGTH] if lead_text else None,
                        "category": "governance",
                    }
                )
        except Exception:
            logger.warning("비즈워치 목록 수집 실패", exc_info=True)
        return articles


# ─────────── 한국M&A신문 ───────────


class KmnaAdapter(IBSourceAdapter):
    """한국M&A경제신문 어댑터 (kmnanews.com) — HTML 스크래핑"""

    source_name = "kmnanews"
    base_url = "https://www.kmnanews.com"
    list_url = "https://www.kmnanews.com/news/articleList.html?sc_section_code=S1N1&view_type=sm"
    content_selectors = [".article-body", "#article-view-content-div", ".view-content", "article"]
    author_selectors = ".byline, .reporter"

    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        articles: list[dict] = []
        seen_urls: set[str] = set()
        for page in range(1, max_pages + 1):
            try:
                url = f"{self.list_url}&page={page}"
                resp = await self.client.get(url)
                soup = BeautifulSoup(resp.text, "lxml")
                for item in soup.select(".list-titles a"):
                    href = item.get("href", "")
                    if not href or "articleView" not in href:
                        continue
                    if not href.startswith("http"):
                        href = f"{self.base_url}{href}"
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    title = item.get_text(strip=True)
                    if not title:
                        continue
                    # 같은 부모에서 lead_text 추출
                    parent = item.find_parent("div", class_="list-block") or item.find_parent("li")
                    lead_text = None
                    if parent:
                        summary = parent.select_one(".list-summary a")
                        if summary:
                            lead_text = clean_html(summary.get_text(strip=True))
                    articles.append(
                        {
                            "title": clean_html(title),
                            "url": href,
                            "lead_text": lead_text[:MAX_LEAD_TEXT_LENGTH] if lead_text else None,
                            "category": "ma",
                        }
                    )
            except Exception:
                logger.warning("한국M&A신문 목록 수집 실패 (page=%d)", page, exc_info=True)
            await asyncio.sleep(settings.IB_CRAWL_REQUEST_DELAY)
        return articles


# ─────────── 통합 크롤링 서비스 ───────────


class IBCrawlService:
    """IB 매체 통합 크롤링 서비스"""

    def __init__(self) -> None:
        self.client = AsyncHTTPClient(
            timeout=30.0,
            headers={
                "User-Agent": "KIIS/0.1.0 (Investment Intelligence Bot; +https://ap-platform.kr)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        self.adapters: list[IBSourceAdapter] = [
            InvestChosunAdapter(self.client),
            DealsiteAdapter(self.client),
            IBTomatoAdapter(self.client),
            BizwatchAdapter(self.client),
            KmnaAdapter(self.client),
        ]

    async def collect_all(
        self,
        db: AsyncSession,
        source_filter: str | None = None,
    ) -> dict[str, dict]:
        """전체 또는 특정 소스에서 IB 기사를 수집한다.

        Returns:
            {"investchosun": {"collected": 10, "new": 5, "duplicates": 5}, ...}
        """
        adapters = self.adapters
        if source_filter:
            adapters = [a for a in self.adapters if a.source_name == source_filter]

        results: dict[str, dict] = {}
        for adapter in adapters:
            try:
                result = await self._collect_from_adapter(db, adapter)
            except Exception:
                logger.exception("IB 수집 어댑터 실패: %s", adapter.source_name)
                result = {"collected": 0, "new": 0, "duplicates": 0}
            results[adapter.source_name] = result
            await asyncio.sleep(settings.IB_CRAWL_REQUEST_DELAY)

        return results

    async def _collect_from_adapter(self, db: AsyncSession, adapter: IBSourceAdapter) -> dict:
        """단일 어댑터에서 기사를 수집한다."""
        logger.info("IB 수집 시작: %s", adapter.source_name)

        article_list = await adapter.fetch_article_list(max_pages=settings.IB_CRAWL_MAX_PAGES)
        collected = len(article_list)

        if not article_list:
            return {"collected": 0, "new": 0, "duplicates": 0}

        # URL 해시 기반 중복 제거 (배치 내)
        seen_hashes: set[str] = set()
        unique_articles: list[dict] = []
        for article in article_list:
            url_hash = generate_url_hash(article["url"])
            if url_hash not in seen_hashes:
                seen_hashes.add(url_hash)
                article["url_hash"] = url_hash
                unique_articles.append(article)

        # DB 중복 체크
        url_hashes = [a["url_hash"] for a in unique_articles]
        existing = await self._check_duplicates(db, url_hashes)
        duplicates = len(existing)

        # 신규 기사 상세 수집 + 저장
        new_count = 0
        for article in unique_articles:
            if article["url_hash"] in existing:
                continue

            # 상세 페이지에서 lead_text + body_text 보강
            if not article.get("lead_text"):
                detail = await adapter.fetch_article_detail(article["url"])
                if detail:
                    article["lead_text"] = detail.get("lead_text")
                    article["author"] = detail.get("author")
                    article["is_paywalled"] = detail.get("is_paywalled", False)
                    article["_body_text"] = detail.get("body_text")  # 분류용 임시
                await asyncio.sleep(settings.IB_CRAWL_REQUEST_DELAY)
            else:
                article.setdefault("is_paywalled", False)
                article.setdefault("author", None)
                # lead_text가 이미 있어도 본문 추출 시도 (분류 정확도 향상)
                detail = await adapter.fetch_article_detail(article["url"])
                if detail:
                    article["_body_text"] = detail.get("body_text")
                await asyncio.sleep(settings.IB_CRAWL_REQUEST_DELAY)

            # IB_PAYWALL_SKIP=True이면 paywall 기사 완전 스킵
            if settings.IB_PAYWALL_SKIP and article.get("is_paywalled"):
                continue

            ib_article = IBArticle(
                title=article["title"],
                lead_text=article.get("lead_text"),
                source=adapter.source_name,
                author=article.get("author"),
                published_at=article.get("published_at"),
                canonical_url=article["url"],
                url_hash=article["url_hash"],
                is_paywalled=article.get("is_paywalled", False),
            )
            # 3섹션 분류 즉시 적용 (본문 있으면 본문 사용, 없으면 lead_text 폴백)
            body_text = article.get("_body_text")
            _apply_section_inline(ib_article, body_text)

            db.add(ib_article)
            try:
                await db.flush()
                new_count += 1
            except IntegrityError:
                await db.rollback()
                logger.debug("중복 기사 스킵: %s", article["url"])

        if new_count > 0:
            await db.commit()

        logger.info(
            "IB 수집 완료: %s (수집=%d, 신규=%d, 중복=%d)", adapter.source_name, collected, new_count, duplicates
        )
        return {"collected": collected, "new": new_count, "duplicates": duplicates}

    @staticmethod
    async def _check_duplicates(db: AsyncSession, url_hashes: list[str]) -> set[str]:
        """DB에서 이미 존재하는 URL 해시를 조회한다."""
        if not url_hashes:
            return set()
        result = await db.execute(select(IBArticle.url_hash).where(IBArticle.url_hash.in_(url_hashes)))
        return set(result.scalars().all())

    async def close(self) -> None:
        """HTTP 클라이언트를 종료한다."""
        await self.client.close()
