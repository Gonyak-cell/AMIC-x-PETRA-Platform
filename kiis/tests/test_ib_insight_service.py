"""IB 인사이트 서비스 테스트

카테고리 분류, GP 매칭, Fact/Opinion 분리 조회 검증.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.models.company import Company
from app.models.ib_article import IBArticle
from app.services.ib_crawl_service import generate_url_hash
from app.services.ib_insight_service import IBInsightService, classify_article_rule_based

# --- Rule-based 분류 테스트 ---


def test_classify_deal_progress() -> None:
    """딜 진행 카테고리 분류"""
    cat, dom, conf = classify_article_rule_based(
        "인수 추진 LOI 체결 실사 착수",
        "경영권 이전 절차가 시작되었다.",
    )
    assert cat == "deal_progress"
    assert dom == "fact"
    assert conf > 0.0


def test_classify_no_match() -> None:
    """매칭 키워드 없는 기사"""
    cat, dom, conf = classify_article_rule_based("축구 경기 결과", "한국팀이 3:0으로 승리했다.")
    assert cat is None
    assert dom is None
    assert conf == 0.0


# --- IBArticle Fact/Opinion 분리 조회 ---


@pytest.mark.asyncio
async def test_fact_opinion_split(async_session) -> None:
    """기사 Fact/Opinion 분리 저장 검증"""
    # Company 생성
    company = Company(corp_code="00999001", corp_name="테스트운용")
    async_session.add(company)
    await async_session.flush()

    # Fact 기사
    fact_article = IBArticle(
        title="테스트운용, A기업 인수 추진",
        lead_text="인수 실사에 돌입했다.",
        source="dealsite",
        canonical_url="https://example.com/fact/1",
        url_hash=generate_url_hash("https://example.com/fact/1"),
        is_paywalled=False,
        category="deal_progress",
        domain="fact",
        company_id=company.id,
        published_at=datetime.now(UTC),
    )

    # Opinion 기사
    opinion_article = IBArticle(
        title="테스트운용 업계 평판 논란",
        lead_text="트랙레코드에 대한 시장 평판이 엇갈린다.",
        source="investchosun",
        canonical_url="https://example.com/opinion/1",
        url_hash=generate_url_hash("https://example.com/opinion/1"),
        is_paywalled=False,
        category="reputation",
        domain="opinion",
        company_id=company.id,
        published_at=datetime.now(UTC),
    )

    async_session.add_all([fact_article, opinion_article])
    await async_session.commit()

    # DB에 2건 저장 확인
    result = await async_session.execute(select(IBArticle).where(IBArticle.company_id == company.id))
    articles = list(result.scalars().all())
    assert len(articles) == 2

    facts = [a for a in articles if a.domain == "fact"]
    opinions = [a for a in articles if a.domain == "opinion"]
    assert len(facts) == 1
    assert len(opinions) == 1
    assert facts[0].category == "deal_progress"
    assert opinions[0].category == "reputation"


@pytest.mark.asyncio
async def test_unprocessed_article_detection(async_session) -> None:
    """미분류 기사 감지"""
    article = IBArticle(
        title="미분류 테스트 기사",
        source="bloter",
        canonical_url="https://example.com/unclassified/1",
        url_hash=generate_url_hash("https://example.com/unclassified/1"),
        is_paywalled=False,
        category=None,
    )
    async_session.add(article)
    await async_session.commit()

    result = await async_session.execute(
        select(IBArticle).where(IBArticle.category.is_(None)),
    )
    unprocessed = list(result.scalars().all())
    assert len(unprocessed) == 1
    assert unprocessed[0].title == "미분류 테스트 기사"


# --- classify_unprocessed 실제 동작 테스트 (#3) ---


@pytest.mark.asyncio
async def test_classify_unprocessed_updates_category(async_session) -> None:
    """classify_unprocessed가 미분류 기사의 category/domain을 업데이트한다."""
    # 미분류 기사 생성 (deal_progress 키워드 포함)
    article = IBArticle(
        title="인수 추진 LOI 체결 실사 착수",
        lead_text="경영권 이전 절차가 시작되었다.",
        source="dealsite",
        canonical_url="https://example.com/classify-test/1",
        url_hash=generate_url_hash("https://example.com/classify-test/1"),
        is_paywalled=False,
        category=None,
        domain=None,
    )
    async_session.add(article)
    await async_session.commit()

    # NLPService Mock (Kiwi 모델 로딩 회피)
    mock_nlp = MagicMock()
    mock_nlp.analyze_sentiment.return_value = {"score": 0.3, "label": "positive"}
    mock_nlp.kiwi = MagicMock()
    mock_nlp.kiwi.tokenize.return_value = []

    mock_extract = AsyncMock(return_value=[{"keyword": "인수", "score": 0.9}])

    service = IBInsightService.__new__(IBInsightService)
    service.nlp = mock_nlp
    service.resolver = MagicMock()
    service._corp_code_cache = {}

    with patch.object(service.nlp, "extract_keywords_async", mock_extract):
        processed = await service.classify_unprocessed(async_session, batch_size=10)

    assert processed == 1

    # DB에서 업데이트 확인
    result = await async_session.execute(select(IBArticle).where(IBArticle.id == article.id))
    updated = result.scalar_one()
    assert updated.category == "deal_progress"
    assert updated.domain == "fact"
    assert updated.sentiment_score is not None


def _make_mock_insight_service() -> IBInsightService:
    """Kiwi 모델 로딩 없이 IBInsightService를 생성한다."""
    mock_nlp = MagicMock()
    mock_nlp.analyze_sentiment.return_value = {"score": 0.1, "label": "neutral"}
    mock_nlp.kiwi = MagicMock()
    mock_nlp.kiwi.tokenize.return_value = []
    mock_nlp.extract_keywords_async = AsyncMock(return_value=[])

    svc = IBInsightService.__new__(IBInsightService)
    svc.nlp = mock_nlp
    svc.resolver = MagicMock()
    svc._corp_code_cache = {}
    return svc


@pytest.mark.asyncio
async def test_classify_unprocessed_drains_all_batches(async_session) -> None:
    """classify_unprocessed가 다중 배치를 순회하여 모든 미분류 기사를 처리한다."""
    # 3건 미분류 기사 생성 (batch_size=2 → 2회 배치 순회 필요)
    for i in range(3):
        async_session.add(
            IBArticle(
                title=f"인수 추진 실사 기사 {i}",
                source="dealsite",
                canonical_url=f"https://example.com/batch/{i}",
                url_hash=generate_url_hash(f"https://example.com/batch/{i}"),
                is_paywalled=False,
                category=None,
                domain=None,
            )
        )
    await async_session.commit()

    service = _make_mock_insight_service()

    with patch.object(service.nlp, "extract_keywords_async", service.nlp.extract_keywords_async):
        processed = await service.classify_unprocessed(async_session, batch_size=2)

    assert processed == 3

    # 미분류 기사 0건 확인
    result = await async_session.execute(select(IBArticle).where(IBArticle.category.is_(None)))
    remaining = list(result.scalars().all())
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_classify_unprocessed_zero_articles(async_session) -> None:
    """미분류 기사가 없으면 즉시 0을 반환한다."""
    service = _make_mock_insight_service()
    processed = await service.classify_unprocessed(async_session, batch_size=10)
    assert processed == 0
