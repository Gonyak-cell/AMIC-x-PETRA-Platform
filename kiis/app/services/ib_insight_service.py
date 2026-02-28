"""IB 인사이트 서비스

NLP 파이프라인 (카테고리 분류 + 감성 분석 + 키워드 추출 + GP 매칭)을 수행하고,
GP별 인사이트를 Fact/Opinion으로 분리하여 조회한다.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.ib_article import CATEGORY_DOMAIN_MAP, MAX_GP_MATCH_TOKENS, IBArticle, get_category_display
from app.services.nlp_service import NLPService
from app.utils.entity_resolver import EntityResolver

logger = logging.getLogger(__name__)

# 분류 규칙 사전 로딩
_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "ib_category_rules.json"


def _load_category_rules() -> dict:
    """카테고리 분류 규칙 사전을 로드한다."""
    if not _RULES_PATH.exists():
        logger.warning("IB 카테고리 규칙 파일 미발견: %s", _RULES_PATH)
        return {}
    with open(_RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


_CATEGORY_RULES: dict = _load_category_rules()


def classify_article_rule_based(title: str, lead_text: str | None) -> tuple[str | None, str | None, float]:
    """Rule-based 1차 카테고리 분류.

    Args:
        title: 기사 제목
        lead_text: 첫 문단 (없을 수 있음)

    Returns:
        (category, domain, confidence) — 미분류 시 (None, None, 0.0)
    """
    text = f"{title} {lead_text or ''}"
    scores: dict[str, float] = {}

    for category, rule in _CATEGORY_RULES.items():
        keywords = rule.get("keywords", [])
        weight = rule.get("weight", 1.0)
        matched = sum(1 for kw in keywords if kw in text)
        if matched > 0:
            scores[category] = matched * weight

    if not scores:
        return None, None, 0.0

    best_category = max(scores, key=lambda k: scores[k])
    domain = CATEGORY_DOMAIN_MAP.get(best_category)
    # 정규화된 신뢰도 (매칭 키워드 수 / 카테고리 키워드 수)
    total_keywords = len(_CATEGORY_RULES.get(best_category, {}).get("keywords", []))
    confidence = min(scores[best_category] / max(total_keywords * 0.3, 1), 1.0)
    return best_category, domain, round(confidence, 4)


class IBInsightService:
    """IB 인사이트 서비스"""

    def __init__(self) -> None:
        self.nlp = NLPService()
        self.resolver = EntityResolver()
        # corp_code → company_id 캐시 (배치 처리 시 N+1 쿼리 방지)
        self._corp_code_cache: dict[str, int] = {}

    async def classify_and_match(self, db: AsyncSession, article_id: int) -> bool:
        """단일 기사에 대해 NLP 분류 + GP 매칭을 수행한다 (ID 기반 편의 메서드).

        Returns:
            성공 여부
        """
        article = await db.get(IBArticle, article_id)
        if not article:
            return False
        return await self._classify_article(db, article)

    async def _classify_article(self, db: AsyncSession, article: IBArticle) -> bool:
        """단일 IBArticle 객체에 대해 NLP 분류 + GP 매칭을 수행한다."""
        text = f"{article.title} {article.lead_text or ''}"

        # 1. 카테고리 분류 (Rule-based)
        category, domain, _confidence = classify_article_rule_based(article.title, article.lead_text)
        article.category = category
        article.domain = domain

        # 2. 감성 분석 (기존 NLPService 재사용)
        sentiment = await asyncio.to_thread(self.nlp.analyze_sentiment, text)
        article.sentiment_score = sentiment["score"]

        # 3. 키워드 추출
        keywords = await self.nlp.extract_keywords_async(text, top_n=5)
        article.keywords = json.dumps([kw["keyword"] for kw in keywords], ensure_ascii=False) if keywords else None

        # 4. GP 엔터티 매칭
        company_id, confidence = await self._match_gp(db, text)
        if company_id:
            article.company_id = company_id
            article.match_confidence = confidence

        await db.flush()
        return True

    async def classify_unprocessed(self, db: AsyncSession, batch_size: int = 50) -> int:
        """미분류 기사를 모두 소진할 때까지 배치 처리한다.

        Returns:
            처리된 기사 수
        """
        total_processed = 0

        while True:
            stmt = (
                select(IBArticle)
                .where(IBArticle.category.is_(None))
                .order_by(IBArticle.created_at.desc())
                .limit(batch_size)
            )
            result = await db.execute(stmt)
            articles = list(result.scalars().all())

            if not articles:
                break

            batch_processed = 0
            for article in articles:
                success = await self._classify_article(db, article)
                if success:
                    batch_processed += 1

            if batch_processed > 0:
                await db.commit()

            total_processed += batch_processed

            # 배치 크기보다 적으면 잔여 기사 없음
            if len(articles) < batch_size:
                break

        logger.info("IB 미분류 기사 처리 완료: %d건", total_processed)
        return total_processed

    async def _match_gp(self, db: AsyncSession, text: str) -> tuple[int | None, float | None]:
        """텍스트에서 GP 엔터티를 매칭한다.

        kiwipiepy로 고유명사(NNP)를 추출하고, EntityResolver로 DB 매칭한다.

        Returns:
            (company_id, confidence) — 매칭 실패 시 (None, None)
        """
        # 고유명사 추출 (kiwipiepy)
        tokens = await asyncio.to_thread(self.nlp.kiwi.tokenize, text)
        proper_nouns: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if token.tag == "NNP" and len(token.form) >= 2 and token.form not in seen:
                seen.add(token.form)
                proper_nouns.append(token.form)

        # 각 고유명사를 EntityResolver로 매칭 (최고 신뢰도 우선)
        best_match: tuple[int | None, float | None] = (None, None)
        best_score = 0.0

        for noun in proper_nouns[:MAX_GP_MATCH_TOKENS]:
            result = await self.resolver.resolve(db, noun, threshold=0.75)
            if result["match"]:
                similarity = result["match"]["similarity"]
                if similarity > best_score:
                    # corp_code → company_id 변환 (캐시 우선)
                    corp_code = result["match"]["corp_code"]
                    company_id = self._corp_code_cache.get(corp_code)
                    if company_id is None:
                        stmt = select(Company.id).where(Company.corp_code == corp_code)
                        row = await db.execute(stmt)
                        company_id = row.scalar_one_or_none()
                        if company_id is not None:
                            self._corp_code_cache[corp_code] = company_id
                    if company_id is not None:
                        best_match = (company_id, round(similarity, 4))
                        best_score = similarity

        return best_match

    async def get_insights_for_gp(
        self,
        db: AsyncSession,
        corp_code: str,
        months: int = 6,
        category: str | None = None,
    ) -> dict | None:
        """GP별 IB 인사이트를 Fact/Opinion으로 분리하여 조회한다.

        Returns:
            {
                "corp_code": ..., "corp_name": ..., "total_articles": ...,
                "facts": [...], "opinions": [...], "last_collected_at": ...
            }
            또는 Company 미발견 시 None
        """
        # Company 조회
        stmt = select(Company).where(Company.corp_code == corp_code)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()
        if not company:
            return None

        # IBArticle 필터링 (published_at NULL인 기사도 포함)
        cutoff = datetime.now(UTC) - timedelta(days=months * 30)
        filters = [
            IBArticle.company_id == company.id,
            or_(IBArticle.published_at >= cutoff, IBArticle.published_at.is_(None)),
        ]
        if category:
            filters.append(IBArticle.category == category)

        stmt = select(IBArticle).where(and_(*filters)).order_by(IBArticle.published_at.desc().nullslast()).limit(100)
        result = await db.execute(stmt)
        articles = list(result.scalars().all())

        # Fact / Opinion 분리
        facts: list[dict] = []
        opinions: list[dict] = []
        for article in articles:
            item = self._article_to_dict(article)
            if article.domain == "fact":
                facts.append(item)
            elif article.domain == "opinion":
                opinions.append(item)
            else:
                # 미분류는 fact로 분류
                facts.append(item)

        # 마지막 수집 시간
        last_stmt = select(func.max(IBArticle.created_at)).where(IBArticle.company_id == company.id)
        last_result = await db.execute(last_stmt)
        last_collected_at = last_result.scalar_one_or_none()

        return {
            "corp_code": corp_code,
            "corp_name": company.corp_name,
            "total_articles": len(articles),
            "facts": facts,
            "opinions": opinions,
            "last_collected_at": last_collected_at,
        }

    @staticmethod
    def _article_to_dict(article: IBArticle) -> dict:
        """IBArticle을 API 응답용 dict로 변환한다."""
        return {
            "id": article.id,
            "title": article.title,
            "lead_text": article.lead_text,
            "canonical_url": article.canonical_url,
            "source": article.source,
            "published_at": article.published_at,
            "category": article.category,
            "category_display": get_category_display(article.category),
            "sentiment_score": article.sentiment_score,
            "is_paywalled": article.is_paywalled,
        }
