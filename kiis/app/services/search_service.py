"""통합 검색 서비스

ElasticSearch를 활용하여 기업, 펀드, 뉴스, 딜 데이터를 통합 검색한다.
ES 클라이언트가 None이면 빈 결과를 반환하여 ES 미설치 환경에서도 안전하게 동작한다.
"""

import logging
from typing import AsyncGenerator

from elasticsearch.helpers import async_bulk
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.elasticsearch import get_es_client

logger = logging.getLogger(__name__)

# 검색 가능한 인덱스 목록
VALID_SEARCH_TYPES: set[str] = {"companies", "funds", "news", "deals"}
ALL_INDICES: str = "kiis_companies,kiis_funds,kiis_news,kiis_deals"

# 인덱스별 검색 대상 필드 (와일드카드 대신 명시 지정)
SEARCH_FIELDS: dict[str, list[str]] = {
    "kiis_companies": ["corp_name", "stock_name", "ceo_nm"],
    "kiis_funds": ["fund_name", "company_name", "fund_type"],
    "kiis_news": ["title", "content", "source"],
    "kiis_deals": ["target_company", "sector", "round_stage"],
}


class SearchService:
    """ElasticSearch 기반 통합 검색 서비스"""

    async def search(
        self,
        q: str,
        type: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict], int]:
        """통합 검색을 수행한다.

        Args:
            q: 검색어
            type: 검색 대상 (companies/funds/news/deals). None이면 전체 검색.
            page: 페이지 번호 (1-based)
            size: 페이지당 결과 수

        Returns:
            (검색 결과 리스트, 총 결과 수) 튜플
        """
        es = get_es_client()
        if not es:
            return [], 0

        # 검색 대상 인덱스 및 필드 결정
        if type and type in VALID_SEARCH_TYPES:
            indices = f"kiis_{type}"
            fields = SEARCH_FIELDS[indices]
        else:
            indices = ALL_INDICES
            fields = [f for fs in SEARCH_FIELDS.values() for f in fs]

        body: dict = {
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": fields,
                    "type": "best_fields",
                },
            },
            "from": (page - 1) * size,
            "size": size,
        }

        try:
            result = await es.search(index=indices, body=body)
        except Exception:
            logger.exception("ElasticSearch search failed for query: %s", q)
            return [], 0

        hits = result["hits"]
        total = hits["total"]["value"]
        items = [
            {
                "index": h["_index"],
                "id": h["_id"],
                "score": h["_score"],
                "source": h["_source"],
            }
            for h in hits["hits"]
        ]
        return items, total

    async def reindex_all(self, db: AsyncSession) -> dict[str, int]:
        """DB에서 모든 데이터를 읽어 ES에 리인덱싱한다.

        Args:
            db: 비동기 DB 세션

        Returns:
            인덱스별 인덱싱된 문서 수
        """
        es = get_es_client()
        if not es:
            return {"companies": 0, "funds": 0, "news": 0, "deals": 0}

        counts: dict[str, int] = {}

        # Companies 리인덱싱
        counts["companies"] = await self._reindex_companies(es, db)

        # Funds 리인덱싱
        counts["funds"] = await self._reindex_funds(es, db)

        # News 리인덱싱
        counts["news"] = await self._reindex_news(es, db)

        # Deals 리인덱싱
        counts["deals"] = await self._reindex_deals(es, db)

        return counts

    BATCH_SIZE = 500

    async def _reindex_companies(self, es: "AsyncElasticsearch", db: AsyncSession) -> int:  # noqa: F821
        """기업 데이터를 ES에 bulk 인덱싱한다."""
        from app.models.company import Company

        total = (await db.execute(select(func.count(Company.id)))).scalar_one()

        async def _gen() -> AsyncGenerator[dict, None]:
            result = await db.execute(select(Company))
            for c in result.scalars():
                yield {
                    "_index": "kiis_companies",
                    "_id": str(c.id),
                    "_source": {
                        "corp_code": c.corp_code,
                        "corp_name": c.corp_name,
                        "stock_name": c.stock_name,
                        "ceo_nm": c.ceo_nm,
                        "corp_cls": c.corp_cls,
                        "induty_code": c.induty_code,
                    },
                }

        success, errors = await async_bulk(es, _gen(), chunk_size=self.BATCH_SIZE, raise_on_error=False)
        if errors:
            logger.warning("Company bulk indexing had %d errors", len(errors))
        return total

    async def _reindex_funds(self, es: "AsyncElasticsearch", db: AsyncSession) -> int:  # noqa: F821
        """펀드 데이터를 ES에 bulk 인덱싱한다."""
        from app.models.fund import Fund

        total = (await db.execute(select(func.count(Fund.id)))).scalar_one()

        async def _gen() -> AsyncGenerator[dict, None]:
            result = await db.execute(select(Fund))
            for f in result.scalars():
                yield {
                    "_index": "kiis_funds",
                    "_id": str(f.id),
                    "_source": {
                        "fund_code": f.fund_code,
                        "fund_name": f.fund_name,
                        "company_name": f.company_name,
                        "fund_type": f.fund_type,
                        "fund_category": f.fund_category,
                    },
                }

        success, errors = await async_bulk(es, _gen(), chunk_size=self.BATCH_SIZE, raise_on_error=False)
        if errors:
            logger.warning("Fund bulk indexing had %d errors", len(errors))
        return total

    async def _reindex_news(self, es: "AsyncElasticsearch", db: AsyncSession) -> int:  # noqa: F821
        """뉴스 데이터를 ES에 bulk 인덱싱한다."""
        from app.models.news import NewsArticle

        total = (await db.execute(select(func.count(NewsArticle.id)))).scalar_one()

        async def _gen() -> AsyncGenerator[dict, None]:
            result = await db.execute(select(NewsArticle))
            for a in result.scalars():
                yield {
                    "_index": "kiis_news",
                    "_id": str(a.id),
                    "_source": {
                        "title": a.title,
                        "content": a.content,
                        "source": a.source,
                        "published_at": a.published_at.isoformat() if a.published_at else None,
                        "sentiment_score": a.sentiment_score,
                    },
                }

        success, errors = await async_bulk(es, _gen(), chunk_size=self.BATCH_SIZE, raise_on_error=False)
        if errors:
            logger.warning("News bulk indexing had %d errors", len(errors))
        return total

    async def _reindex_deals(self, es: "AsyncElasticsearch", db: AsyncSession) -> int:  # noqa: F821
        """딜 데이터를 ES에 bulk 인덱싱한다."""
        from app.models.deal import Deal

        total = (await db.execute(select(func.count(Deal.id)))).scalar_one()

        async def _gen() -> AsyncGenerator[dict, None]:
            result = await db.execute(select(Deal))
            for d in result.scalars():
                yield {
                    "_index": "kiis_deals",
                    "_id": str(d.id),
                    "_source": {
                        "target_company": d.target_company,
                        "sector": d.sector,
                        "amount_display": d.amount_display,
                        "round_stage": d.round_stage,
                        "deal_year": d.deal_year,
                    },
                }

        success, errors = await async_bulk(es, _gen(), chunk_size=self.BATCH_SIZE, raise_on_error=False)
        if errors:
            logger.warning("Deal bulk indexing had %d errors", len(errors))
        return total

    async def get_index_status(self) -> dict[str, dict]:
        """각 인덱스의 문서 수와 크기를 반환한다.

        Returns:
            인덱스별 상태 정보 (docs_count, size_bytes)
        """
        es = get_es_client()
        if not es:
            return {}

        indices: dict[str, dict] = {}
        for name in ["kiis_companies", "kiis_funds", "kiis_news", "kiis_deals"]:
            try:
                stats = await es.indices.stats(index=name)
                idx_stats = stats["indices"][name]["total"]
                indices[name] = {
                    "docs_count": idx_stats["docs"]["count"],
                    "size_bytes": idx_stats["store"]["size_in_bytes"],
                }
            except Exception:
                indices[name] = {"docs_count": 0, "size_bytes": 0}
        return indices
