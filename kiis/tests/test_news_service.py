"""S1-C-05: 뉴스 수집 서비스 테스트"""

import re
from datetime import datetime

import pytest
from sqlalchemy import select

from app.models.news import NewsArticle
from app.services.news_service import NewsService

# --- Mock RSS 응답 ---

MOCK_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>스타트업 A, 100억원 시리즈A 투자 유치</title>
        <link>https://example.com/article/1</link>
        <description>&lt;p&gt;스타트업 A가 벤처캐피탈로부터 100억원의 시리즈A 투자를 유치했다.&lt;/p&gt;</description>
        <author>김기자</author>
        <pubDate>Mon, 03 Feb 2026 09:00:00 +0900</pubDate>
    </item>
    <item>
        <title>VC 업계 동향: 바이오 투자 증가</title>
        <link>https://example.com/article/2</link>
        <description>바이오 분야 투자가 전년 대비 30% 증가했다.</description>
        <author>박기자</author>
        <pubDate>Tue, 04 Feb 2026 10:00:00 +0900</pubDate>
    </item>
    <item>
        <title>중복 기사 테스트</title>
        <link>https://example.com/article/1</link>
        <description>같은 URL의 중복 기사</description>
        <pubDate>Wed, 05 Feb 2026 11:00:00 +0900</pubDate>
    </item>
</channel>
</rss>"""


# --- 유틸리티 함수 테스트 ---


def test_generate_url_hash():
    """URL 해시 생성"""
    hash1 = NewsService.generate_url_hash("https://example.com/1")
    hash2 = NewsService.generate_url_hash("https://example.com/2")
    hash3 = NewsService.generate_url_hash("https://example.com/1")

    assert len(hash1) == 64
    assert hash1 != hash2
    assert hash1 == hash3


def test_clean_html_basic():
    """HTML 태그 제거"""
    assert NewsService.clean_html("<p>Hello <b>World</b></p>") == "Hello World"


def test_clean_html_entities():
    """HTML 엔티티 변환"""
    assert NewsService.clean_html("A &amp; B &lt; C &gt; D") == "A & B < C > D"
    assert NewsService.clean_html("&nbsp;space&nbsp;") == "space"


def test_clean_html_whitespace():
    """연속 공백 정리"""
    assert NewsService.clean_html("  Hello   World  ") == "Hello World"


def test_clean_html_empty():
    """빈 문자열 처리"""
    assert NewsService.clean_html("") == ""
    assert NewsService.clean_html(None) == ""  # type: ignore[arg-type]


# --- RSS 파싱 테스트 ---


@pytest.mark.asyncio
async def test_fetch_rss(httpx_mock):
    """RSS 피드 파싱 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*example\.com/feed"),
        text=MOCK_RSS_XML,
    )

    service = NewsService()
    articles = await service._fetch_rss("test", "https://example.com/feed")
    await service.close()

    # URL 중복 포함 3개 엔트리
    assert len(articles) == 3

    # 첫 번째 기사 검증
    assert articles[0]["title"] == "스타트업 A, 100억원 시리즈A 투자 유치"
    assert articles[0]["source"] == "test"
    assert articles[0]["url"] == "https://example.com/article/1"
    assert len(articles[0]["url_hash"]) == 64
    assert articles[0]["author"] == "김기자"
    # HTML 태그가 제거된 본문
    assert "<p>" not in articles[0]["content"]


@pytest.mark.asyncio
async def test_fetch_rss_error(httpx_mock):
    """RSS 피드 에러 시 빈 목록 반환"""
    # AsyncHTTPClient는 500 에러 시 3회 재시도
    for _ in range(3):
        httpx_mock.add_response(
            url=re.compile(r".*example\.com/feed"),
            status_code=500,
        )

    service = NewsService()
    articles = await service._fetch_rss("test", "https://example.com/feed")
    await service.close()

    assert articles == []


# --- 중복 감지 테스트 ---


@pytest.mark.asyncio
async def test_check_duplicates(async_session):
    """DB 중복 감지 테스트"""
    # 기존 기사 저장
    existing = NewsArticle(
        title="기존 기사",
        source="test",
        url="https://example.com/existing",
        url_hash=NewsArticle.generate_url_hash("https://example.com/existing"),
    )
    async_session.add(existing)
    await async_session.commit()

    service = NewsService()
    existing_hashes = await service._check_duplicates(
        async_session,
        [
            NewsArticle.generate_url_hash("https://example.com/existing"),
            NewsArticle.generate_url_hash("https://example.com/new"),
        ],
    )

    assert len(existing_hashes) == 1
    assert NewsArticle.generate_url_hash("https://example.com/existing") in existing_hashes


# --- 수집 + 저장 통합 테스트 ---


@pytest.mark.asyncio
async def test_collect_from_source(httpx_mock, async_session):
    """소스별 수집 + DB 저장 통합 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*example\.com/feed"),
        text=MOCK_RSS_XML,
    )

    service = NewsService()
    result = await service.collect_from_source(async_session, "test", "https://example.com/feed")
    await service.close()

    assert result.source == "test"
    assert result.collected == 3  # RSS에서 3개 파싱
    # URL 중복(article/1)이 RSS 내에 있으므로 2개만 신규
    assert result.new_articles == 2
    assert result.duplicates == 0  # DB에는 아직 없으므로 DB 중복은 0

    # DB에 저장 확인
    db_result = await async_session.execute(select(NewsArticle))
    saved = db_result.scalars().all()
    assert len(saved) == 2


@pytest.mark.asyncio
async def test_collect_from_source_with_existing(httpx_mock, async_session):
    """기존 기사가 있을 때 중복 제외 수집"""
    # 기존 기사 1건 저장
    existing = NewsArticle(
        title="기존 기사",
        source="test",
        url="https://example.com/article/1",
        url_hash=NewsArticle.generate_url_hash("https://example.com/article/1"),
    )
    async_session.add(existing)
    await async_session.commit()

    httpx_mock.add_response(
        url=re.compile(r".*example\.com/feed"),
        text=MOCK_RSS_XML,
    )

    service = NewsService()
    result = await service.collect_from_source(async_session, "test", "https://example.com/feed")
    await service.close()

    assert result.collected == 3
    assert result.duplicates >= 1  # article/1이 이미 DB에 있음
    assert result.new_articles == 1  # article/2만 신규


@pytest.mark.asyncio
async def test_published_date_parsing():
    """발행일 파싱 테스트"""
    entry = {"published": "Mon, 03 Feb 2026 09:00:00 +0900"}
    result = NewsService._parse_published_date(entry)
    assert result is not None
    assert isinstance(result, datetime)
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 3


def test_published_date_none():
    """발행일 없는 경우"""
    result = NewsService._parse_published_date({})
    assert result is None
