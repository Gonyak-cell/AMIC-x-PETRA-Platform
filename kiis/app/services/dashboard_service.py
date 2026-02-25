"""대시보드 요약 서비스

asyncio.gather()로 집계 쿼리를 병렬 실행하여 대시보드 요약을 구성한다.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import Deal
from app.models.disclosure import Disclosure
from app.models.fund import Fund
from app.models.news import NewsArticle
from app.models.reits import REITs
from app.models.reputation import ReputationScore


class DashboardService:
    """대시보드 요약 데이터를 집계하는 서비스"""

    async def get_summary(self, db: AsyncSession) -> dict[str, Any]:
        """대시보드 요약을 반환한다.

        AsyncSession은 동시 사용이 불가하므로 순차 실행한다.
        """
        company_count = await self._count(db, Company)
        fund_count = await self._count(db, Fund)
        reits_count = await self._count(db, REITs)
        news_count = await self._count(db, NewsArticle)
        deal_count = await self._count(db, Deal)
        recent_news_count = await self._count_recent_news(db)
        recent_deals = await self._get_recent_deals(db)
        risk_companies = await self._get_risk_companies(db)

        counts = [
            {"label": "기업", "count": company_count},
            {"label": "펀드", "count": fund_count},
            {"label": "리츠", "count": reits_count},
            {"label": "뉴스", "count": news_count},
            {"label": "딜", "count": deal_count},
        ]

        freshness = await self._get_data_freshness(db)

        return {
            "counts": counts,
            "recent_news_count": recent_news_count,
            "recent_deals": recent_deals,
            "risk_companies": risk_companies,
            "data_freshness": freshness,
        }

    async def _count(self, db: AsyncSession, model: type) -> int:
        """모델의 전체 레코드 수를 반환한다."""
        result = await db.execute(select(func.count(model.id)))
        return result.scalar() or 0

    async def _count_recent_news(self, db: AsyncSession) -> int:
        """최근 7일 이내 뉴스 수를 반환한다."""
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)
        result = await db.execute(
            select(func.count(NewsArticle.id)).where(
                NewsArticle.published_at >= seven_days_ago,
            )
        )
        return result.scalar() or 0

    async def _get_recent_deals(self, db: AsyncSession, limit: int = 5) -> list[dict[str, Any]]:
        """최근 딜 N건을 반환한다."""
        result = await db.execute(select(Deal).order_by(Deal.deal_date.desc().nulls_last()).limit(limit))
        deals = result.scalars().all()
        return [
            {
                "target_company": d.target_company,
                "amount_display": d.amount_display,
                "sector": d.sector,
                "deal_date": d.deal_date,
            }
            for d in deals
        ]

    async def _get_risk_companies(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Risk 상태 기업 목록을 반환한다 (점수 오름차순, 최대 10건)."""
        result = await db.execute(
            select(ReputationScore, Company)
            .join(Company, ReputationScore.company_id == Company.id)
            .where(ReputationScore.status_tag == "risk")
            .order_by(ReputationScore.total_score.asc())
            .limit(10)
        )
        rows = result.all()
        return [
            {
                "corp_code": company.corp_code,
                "corp_name": company.corp_name,
                "status_tag": score.status_tag,
                "total_score": float(score.total_score),
            }
            for score, company in rows
        ]

    async def _get_data_freshness(self, db: AsyncSession) -> list[dict[str, Any]]:
        """주요 엔티티별 데이터 신선도를 반환한다."""
        entities: list[tuple[str, type, Any]] = [
            ("뉴스", NewsArticle, NewsArticle.created_at),
            ("딜", Deal, Deal.created_at),
            ("공시", Disclosure, Disclosure.created_at),
        ]
        freshness: list[dict[str, Any]] = []
        for label, model, date_col in entities:
            count_result = await db.execute(select(func.count(model.id)))
            latest_result = await db.execute(select(func.max(date_col)))
            freshness.append(
                {
                    "entity": label,
                    "count": count_result.scalar() or 0,
                    "latest_at": latest_result.scalar(),
                }
            )
        return freshness
