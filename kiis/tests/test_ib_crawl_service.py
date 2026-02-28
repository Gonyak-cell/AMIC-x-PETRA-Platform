"""IB 매체 크롤링 서비스 테스트

URL 해시 생성, HTML 정제, Paywall 감지, 중복 체크, RSS 파싱, 어댑터 행동 검증.
"""

from unittest.mock import AsyncMock, MagicMock

import feedparser
import httpx
import pytest
from sqlalchemy import select

from app.models.ib_article import IBArticle
from app.services.ib_crawl_service import (
    IBCrawlService,
    IBSourceAdapter,
    InvestChosunAdapter,
    _parse_rss_date,
    clean_html,
    detect_paywall_common,
    generate_url_hash,
)

# --- 유틸리티 함수 테스트 ---


def test_generate_url_hash() -> None:
    """URL 해시 생성 (SHA256, 64자)"""
    hash1 = generate_url_hash("https://example.com/1")
    hash2 = generate_url_hash("https://example.com/2")
    hash3 = generate_url_hash("https://example.com/1")

    assert len(hash1) == 64
    assert hash1 != hash2
    assert hash1 == hash3


def test_clean_html_basic() -> None:
    """HTML 태그 제거"""
    assert clean_html("<p>Hello <b>World</b></p>") == "Hello World"


def test_clean_html_entities() -> None:
    """HTML 엔티티 변환"""
    result = clean_html("A &amp; B &lt; C &gt; D")
    assert "A & B" in result
    assert "C > D" in result


def test_clean_html_empty() -> None:
    """빈 문자열 / None 처리"""
    assert clean_html("") == ""
    assert clean_html(None) == ""  # type: ignore[arg-type]


# --- Paywall 감지 테스트 ---


def test_paywall_detection_korean() -> None:
    """한국어 Paywall 패턴 감지"""
    assert detect_paywall_common("이 기사는 구독자 전용 콘텐츠입니다.") is True
    assert detect_paywall_common("유료 회원만 열람 가능합니다.") is True
    assert detect_paywall_common("로그인 후 열람 가능합니다.") is True


def test_paywall_detection_english() -> None:
    """영어 Paywall 패턴 감지"""
    assert detect_paywall_common("This is premium content for subscribers only.") is True


def test_no_paywall_normal_content() -> None:
    """일반 기사에서 Paywall 미감지"""
    assert detect_paywall_common("A운용사가 B기업 인수를 추진하고 있다.") is False


# --- 중복 체크 테스트 ---


@pytest.mark.asyncio
async def test_check_duplicates(async_session) -> None:
    """DB 중복 URL 해시 감지"""
    existing = IBArticle(
        title="기존 기사",
        source="dealsite",
        canonical_url="https://example.com/existing",
        url_hash=generate_url_hash("https://example.com/existing"),
    )
    async_session.add(existing)
    await async_session.commit()

    from app.services.ib_crawl_service import IBCrawlService

    existing_hashes = await IBCrawlService._check_duplicates(
        async_session,
        [
            generate_url_hash("https://example.com/existing"),
            generate_url_hash("https://example.com/new"),
        ],
    )

    assert len(existing_hashes) == 1
    assert generate_url_hash("https://example.com/existing") in existing_hashes


@pytest.mark.asyncio
async def test_check_duplicates_empty(async_session) -> None:
    """빈 해시 목록 처리"""
    from app.services.ib_crawl_service import IBCrawlService

    result = await IBCrawlService._check_duplicates(async_session, [])
    assert result == set()


# --- RSS 어댑터 테스트 (딜사이트) ---

MOCK_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Dealsite</title>
    <item>
        <title>A운용사, B기업 인수 추진</title>
        <link>https://dealsite.co.kr/articles/1</link>
        <description>A운용사가 B기업의 경영권 인수를 추진 중이다.</description>
        <pubDate>Mon, 28 Feb 2026 09:00:00 +0900</pubDate>
    </item>
    <item>
        <title>C투자, 시리즈B 200억 유치</title>
        <link>https://dealsite.co.kr/articles/2</link>
        <description>C투자가 시리즈B 라운드에서 200억원을 유치했다.</description>
        <pubDate>Tue, 28 Feb 2026 10:00:00 +0900</pubDate>
    </item>
</channel>
</rss>"""


def test_rss_parsing_with_feedparser() -> None:
    """feedparser를 사용한 RSS 파싱 테스트 (네트워크 불필요)"""
    feed = feedparser.parse(MOCK_RSS_XML)

    assert len(feed.entries) == 2

    entry = feed.entries[0]
    assert entry.get("title") == "A운용사, B기업 인수 추진"
    assert entry.get("link") == "https://dealsite.co.kr/articles/1"
    assert entry.get("description") is not None

    entry2 = feed.entries[1]
    assert entry2.get("title") == "C투자, 시리즈B 200억 유치"
    assert entry2.get("link") == "https://dealsite.co.kr/articles/2"


# --- IBArticle 모델 테스트 ---


@pytest.mark.asyncio
async def test_ib_article_creation(async_session) -> None:
    """IBArticle 모델 생성 + DB 저장"""
    article = IBArticle(
        title="테스트 IB 기사",
        lead_text="이것은 첫 문단입니다.",
        source="investchosun",
        canonical_url="https://investchosun.com/article/123",
        url_hash=generate_url_hash("https://investchosun.com/article/123"),
        is_paywalled=False,
    )
    async_session.add(article)
    await async_session.commit()

    result = await async_session.execute(select(IBArticle))
    saved = result.scalars().all()
    assert len(saved) == 1
    assert saved[0].title == "테스트 IB 기사"
    assert saved[0].source == "investchosun"
    assert saved[0].is_paywalled is False


# --- 어댑터 fetch_article_detail 행동 테스트 (Mock HTML) ---

MOCK_ARTICLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta property="og:description" content="OG 설명문입니다.">
</head>
<body>
  <div class="article-body">
    <p>이것은 본문 첫 번째 문단으로 30자 이상 작성된 리드 텍스트 예시입니다.</p>
    <p>두 번째 문단입니다.</p>
  </div>
  <span class="byline">홍길동 기자</span>
</body>
</html>"""

MOCK_PAYWALL_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta property="og:description" content="유료 기사의 OG 설명입니다.">
</head>
<body>
  <p>이 기사는 구독자 전용 콘텐츠입니다.</p>
  <div class="article-body"><p>짧음</p></div>
</body>
</html>"""


def _make_mock_client(html: str) -> MagicMock:
    """AsyncHTTPClient mock을 생성한다."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.text = html
    client = MagicMock()
    client.get = AsyncMock(return_value=mock_response)
    return client


@pytest.mark.asyncio
async def test_adapter_detail_extracts_lead_text() -> None:
    """어댑터 fetch_article_detail이 본문 첫 문단(lead_text)을 추출한다."""
    client = _make_mock_client(MOCK_ARTICLE_HTML)
    adapter = InvestChosunAdapter(client)

    result = await adapter.fetch_article_detail("https://example.com/article/1")

    assert result is not None
    assert result["is_paywalled"] is False
    assert "리드 텍스트 예시" in result["lead_text"]
    assert result["author"] == "홍길동 기자"


@pytest.mark.asyncio
async def test_adapter_detail_paywall_falls_back_to_og() -> None:
    """Paywall 감지 시 og:description으로 폴백한다."""
    client = _make_mock_client(MOCK_PAYWALL_HTML)
    adapter = InvestChosunAdapter(client)

    result = await adapter.fetch_article_detail("https://example.com/paywall/1")

    assert result is not None
    assert result["is_paywalled"] is True
    assert "유료 기사의 OG 설명" in (result["lead_text"] or "")


@pytest.mark.asyncio
async def test_adapter_detail_returns_none_on_error() -> None:
    """HTTP 요청 실패 시 None을 반환한다."""
    client = MagicMock()
    client.get = AsyncMock(side_effect=Exception("Connection error"))
    adapter = InvestChosunAdapter(client)

    result = await adapter.fetch_article_detail("https://example.com/fail")

    assert result is None


@pytest.mark.asyncio
async def test_adapter_selectors_override() -> None:
    """서브클래스 content_selectors가 올바르게 적용된다."""
    adapter = InvestChosunAdapter(_make_mock_client(""))
    assert ".news-content" in adapter.content_selectors
    assert ".article-info .name" in adapter.author_selectors


# --- _parse_rss_date 테스트 (#4) ---


def test_parse_rss_date_rfc2822() -> None:
    """RFC 2822 형식 날짜 파싱"""
    from datetime import datetime

    entry = {"published": "Mon, 28 Feb 2026 09:00:00 +0900"}
    result = _parse_rss_date(entry)
    assert result is not None
    assert isinstance(result, datetime)


def test_parse_rss_date_with_parsed_tuple() -> None:
    """published 문자열 파싱 실패 시 published_parsed tuple 폴백"""
    from datetime import datetime

    # published 문자열이 있지만 parsedate_to_datetime 실패 → published_parsed 폴백
    entry = {
        "published": "invalid-date-format",
        "published_parsed": (2026, 2, 28, 9, 0, 0, 0, 59, 0),
    }
    result = _parse_rss_date(entry)
    assert result is not None
    assert isinstance(result, datetime)
    assert result.year == 2026
    assert result.month == 2


def test_parse_rss_date_empty_entry() -> None:
    """빈 엔트리 → None"""
    assert _parse_rss_date({}) is None


def test_parse_rss_date_malformed() -> None:
    """잘못된 날짜 형식 → None (예외 없이)"""
    entry = {"published": "not-a-date-at-all"}
    result = _parse_rss_date(entry)
    # parsedate_to_datetime 실패 + parsed 키도 없으면 None
    assert result is None


def test_parse_rss_date_updated_fallback() -> None:
    """published 없으면 updated 사용"""
    from datetime import datetime

    entry = {"updated": "Tue, 01 Mar 2026 10:00:00 +0900"}
    result = _parse_rss_date(entry)
    assert result is not None
    assert isinstance(result, datetime)


# --- collect_all 어댑터 격리 테스트 (#5) ---


class _SuccessAdapter(IBSourceAdapter):
    """항상 성공하는 테스트 어댑터"""

    source_name = "success_adapter"
    base_url = "https://example.com"

    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        return [{"title": "성공 기사", "url": "https://example.com/ok/1"}]


class _FailAdapter(IBSourceAdapter):
    """항상 예외를 발생시키는 테스트 어댑터"""

    source_name = "fail_adapter"
    base_url = "https://example.com"

    async def fetch_article_list(self, max_pages: int = 3) -> list[dict]:
        raise RuntimeError("어댑터 크래시 시뮬레이션")


@pytest.mark.asyncio
async def test_collect_all_isolates_adapter_failure(async_session) -> None:
    """한 어댑터 실패 시 다른 어댑터 결과는 정상 반환된다."""
    svc = IBCrawlService()
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=MagicMock(text="<html></html>"))
    mock_client.close = AsyncMock()

    success = _SuccessAdapter(mock_client)
    fail = _FailAdapter(mock_client)
    svc.adapters = [fail, success]

    results = await svc.collect_all(async_session)

    # 실패 어댑터: 0건 결과
    assert results["fail_adapter"]["collected"] == 0
    assert results["fail_adapter"]["new"] == 0

    # 성공 어댑터: 수집 시도 (1건 수집, 상세 페이지에서 0건 추가)
    assert "success_adapter" in results
    assert results["success_adapter"]["collected"] >= 1
