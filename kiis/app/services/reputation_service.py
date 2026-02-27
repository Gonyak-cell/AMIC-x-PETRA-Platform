"""평판 스코어링 서비스

KIIS 평판 지수 = (트렌드 점수 × 0.3) + (뉴스 평판 × 0.4) + (성과 지표 × 0.3)
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_decorators import log_error_with_input
from app.models.company import Company
from app.models.news import NewsArticle
from app.models.reputation import ReputationHistory, ReputationScore
from app.services.nlp_service import NLPService
from app.services.reputation_themes import (
    NEGATIVE_THEME_MAP,
    POSITIVE_THEME_MAP,
    RISK_ABSENCE_THEMES,
    THEME_DISPLAY_NAMES,
)

logger = logging.getLogger(__name__)


class ReputationService:
    """평판 스코어링 서비스

    기업의 평판 지수를 계산하고 관리한다.
    """

    # 가중치
    WEIGHT_TREND = Decimal("0.3")
    WEIGHT_NEWS = Decimal("0.4")
    WEIGHT_PERFORMANCE = Decimal("0.3")

    # 상태 태그 임계값
    RISING_THRESHOLD = Decimal("0.7")
    RISING_TREND_THRESHOLD = Decimal("0.6")
    RISK_THRESHOLD = Decimal("0.4")

    # 성과 점수 계산 키워드 — reputation_themes의 exit_ipo + mna 키워드 사용
    EXIT_KEYWORDS = [k for k, v in POSITIVE_THEME_MAP.items() if v in ("exit_ipo", "mna")]
    # 전체 감성 사전 키워드 (테마 분류에 사용)
    _ALL_THEME_KEYWORDS = {**POSITIVE_THEME_MAP, **NEGATIVE_THEME_MAP}

    def __init__(self, nlp_service: NLPService | None = None) -> None:
        self.nlp_service = nlp_service or NLPService()

    async def get_reputation(
        self, db: AsyncSession, corp_code: str, *, company_id: int | None = None,
    ) -> ReputationScore | None:
        """기업의 현재 평판 점수를 조회한다.

        company_id가 주어지면 JOIN 없이 직접 조회한다 (라우터에서 이미 Company 조회 시 사용).
        """
        if company_id is not None:
            stmt = select(ReputationScore).where(ReputationScore.company_id == company_id)
        else:
            stmt = (
                select(ReputationScore)
                .join(Company, ReputationScore.company_id == Company.id)
                .where(Company.corp_code == corp_code)
            )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reputation_history(
        self, db: AsyncSession, corp_code: str, limit: int = 30, *, company_id: int | None = None,
    ) -> list[ReputationHistory]:
        """기업의 평판 이력을 조회한다."""
        if company_id is not None:
            stmt = (
                select(ReputationHistory)
                .where(ReputationHistory.company_id == company_id)
                .order_by(ReputationHistory.recorded_at.desc())
                .limit(limit)
            )
        else:
            stmt = (
                select(ReputationHistory)
                .join(Company, ReputationHistory.company_id == Company.id)
                .where(Company.corp_code == corp_code)
                .order_by(ReputationHistory.recorded_at.desc())
                .limit(limit)
            )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @log_error_with_input
    async def calculate_reputation(
        self,
        db: AsyncSession,
        corp_code: str,
        months: int = 6,
        save_history: bool = True,
    ) -> ReputationScore | None:
        """기업의 평판 지수를 계산한다.

        Args:
            db: DB 세션
            corp_code: DART 고유번호
            months: 뉴스 분석 기간 (개월)
            save_history: 이력 저장 여부

        Returns:
            계산된 평판 점수 (기업이 없으면 None)
        """
        # 기업 조회
        company = await self._get_company(db, corp_code)
        if not company:
            return None

        # 1. 뉴스 점수 계산 (최근 N개월 평균 감성 점수)
        news_score, news_count = await self._calculate_news_score(db, company.id, months)

        # 2. 성과 점수 계산 (엑시트 키워드 기반)
        performance_score, exit_count = await self._calculate_performance_score(db, company.id, months)

        # 3. 트렌드 점수 계산 (이전 기간 대비 감성 변화)
        trend_score = await self._calculate_trend_score(db, company.id, months)

        # 4. 총합 계산
        normalized_news = self._normalize_news_score(news_score)
        total_score = (
            trend_score * self.WEIGHT_TREND
            + normalized_news * self.WEIGHT_NEWS
            + performance_score * self.WEIGHT_PERFORMANCE
        )

        # 5. 상태 태그 결정
        status_tag = self._determine_status_tag(total_score, trend_score)

        # 6. 저장
        now = datetime.now(UTC)
        reputation = await self._save_reputation(
            db=db,
            company_id=company.id,
            trend_score=trend_score,
            news_score=news_score,
            performance_score=performance_score,
            total_score=total_score,
            status_tag=status_tag,
            scored_at=now,
            news_count=news_count,
            exit_count=exit_count,
        )

        # 7. 이력 저장
        if save_history:
            await self._save_history(
                db=db,
                company_id=company.id,
                total_score=total_score,
                status_tag=status_tag,
                trend_score=trend_score,
                news_score=news_score,
                performance_score=performance_score,
                recorded_at=now,
            )

        await db.flush()
        return reputation

    async def _get_company(self, db: AsyncSession, corp_code: str) -> Company | None:
        """기업을 조회한다."""
        stmt = select(Company).where(Company.corp_code == corp_code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _calculate_news_score(self, db: AsyncSession, company_id: int, months: int) -> tuple[Decimal, int]:
        """뉴스 감성 점수 평균을 계산한다.

        Returns:
            (평균 감성 점수, 뉴스 개수)
        """
        cutoff = datetime.now(UTC) - timedelta(days=months * 30)

        stmt = select(
            func.avg(NewsArticle.sentiment_score),
            func.count(NewsArticle.id),
        ).where(
            NewsArticle.company_id == company_id,
            NewsArticle.published_at >= cutoff,
            NewsArticle.sentiment_score.isnot(None),
        )

        result = await db.execute(stmt)
        row = result.one()

        avg_score = row[0] if row[0] is not None else 0.0
        count = row[1] or 0

        return Decimal(str(round(avg_score, 4))), count

    async def _calculate_performance_score(
        self, db: AsyncSession, company_id: int, months: int = 12
    ) -> tuple[Decimal, int]:
        """성과 점수를 계산한다 (엑시트 키워드 기반).

        Returns:
            (성과 점수 0~1, 엑시트 횟수)
        """
        cutoff = datetime.now(UTC) - timedelta(days=months * 30)

        # 엑시트 키워드가 포함된 긍정 뉴스 조회
        stmt = select(NewsArticle).where(
            NewsArticle.company_id == company_id,
            NewsArticle.published_at >= cutoff,
            NewsArticle.sentiment_score > 0.3,  # 긍정 뉴스만
        )
        result = await db.execute(stmt)
        articles = result.scalars().all()

        exit_count = 0
        for article in articles:
            text = f"{article.title or ''} {article.content or ''}"
            if any(kw in text for kw in self.EXIT_KEYWORDS):
                exit_count += 1

        # 점수 계산: 엑시트 1회당 0.2점, 최대 1.0
        score = min(Decimal("1.0"), Decimal(str(exit_count)) * Decimal("0.2"))
        return score, exit_count

    async def _calculate_trend_score(self, db: AsyncSession, company_id: int, months: int) -> Decimal:
        """트렌드 점수를 계산한다 (이전 기간 대비 변화).

        Returns:
            트렌드 점수 (0.0 ~ 1.0)
        """
        now = datetime.now(UTC)
        current_start = now - timedelta(days=months * 30)
        previous_start = current_start - timedelta(days=months * 30)

        # 현재 기간 평균
        current_stmt = select(func.avg(NewsArticle.sentiment_score)).where(
            NewsArticle.company_id == company_id,
            NewsArticle.published_at >= current_start,
            NewsArticle.sentiment_score.isnot(None),
        )
        current_result = await db.execute(current_stmt)
        current_avg = current_result.scalar() or 0.0

        # 이전 기간 평균
        previous_stmt = select(func.avg(NewsArticle.sentiment_score)).where(
            NewsArticle.company_id == company_id,
            NewsArticle.published_at >= previous_start,
            NewsArticle.published_at < current_start,
            NewsArticle.sentiment_score.isnot(None),
        )
        previous_result = await db.execute(previous_stmt)
        previous_avg = previous_result.scalar() or 0.0

        # 변화율 기반 트렌드 점수
        # 상승: 0.5 ~ 1.0, 하락: 0.0 ~ 0.5
        diff = current_avg - previous_avg
        # diff 범위: -2.0 ~ 2.0 → 0.0 ~ 1.0으로 매핑
        trend = (diff + 2.0) / 4.0
        trend = max(0.0, min(1.0, trend))

        return Decimal(str(round(trend, 4)))

    def _normalize_news_score(self, score: Decimal) -> Decimal:
        """뉴스 점수(-1~1)를 0~1로 정규화한다."""
        normalized = (float(score) + 1.0) / 2.0
        return Decimal(str(round(normalized, 4)))

    def _determine_status_tag(self, total: Decimal, trend: Decimal) -> str:
        """상태 태그를 결정한다."""
        if total >= self.RISING_THRESHOLD and trend >= self.RISING_TREND_THRESHOLD:
            return "rising"
        elif total < self.RISK_THRESHOLD:
            return "risk"
        return "stable"

    async def _save_reputation(
        self,
        db: AsyncSession,
        company_id: int,
        trend_score: Decimal,
        news_score: Decimal,
        performance_score: Decimal,
        total_score: Decimal,
        status_tag: str,
        scored_at: datetime,
        news_count: int,
        exit_count: int,
    ) -> ReputationScore:
        """평판 점수를 저장한다 (upsert)."""
        # 기존 점수 조회
        stmt = select(ReputationScore).where(ReputationScore.company_id == company_id)
        result = await db.execute(stmt)
        reputation = result.scalar_one_or_none()

        if reputation:
            # 업데이트
            reputation.trend_score = trend_score
            reputation.news_score = news_score
            reputation.performance_score = performance_score
            reputation.total_score = total_score
            reputation.status_tag = status_tag
            reputation.scored_at = scored_at
            reputation.news_count = news_count
            reputation.exit_count = exit_count
        else:
            # 생성
            reputation = ReputationScore(
                company_id=company_id,
                trend_score=trend_score,
                news_score=news_score,
                performance_score=performance_score,
                total_score=total_score,
                status_tag=status_tag,
                scored_at=scored_at,
                news_count=news_count,
                exit_count=exit_count,
            )
            db.add(reputation)

        await db.flush()
        return reputation

    async def _save_history(
        self,
        db: AsyncSession,
        company_id: int,
        total_score: Decimal,
        status_tag: str,
        trend_score: Decimal,
        news_score: Decimal,
        performance_score: Decimal,
        recorded_at: datetime,
    ) -> ReputationHistory:
        """평판 이력을 저장한다."""
        history = ReputationHistory(
            company_id=company_id,
            total_score=total_score,
            status_tag=status_tag,
            trend_score=trend_score,
            news_score=news_score,
            performance_score=performance_score,
            recorded_at=recorded_at,
        )
        db.add(history)
        await db.flush()
        return history

    async def classify_by_theme(
        self,
        db: AsyncSession,
        company_id: int,
        months: int = 6,
    ) -> dict:
        """뉴스 기사를 reputation_themes로 분류하여 테마별 건수를 반환한다.

        Returns:
            {
                "theme_counts": {"exit_ipo": 3, "mna": 5, ...},
                "total_articles": 20,
                "risk_absence_notices": ["법적/규제 리스크 보도 없음", ...],
            }
        """
        cutoff = datetime.now(UTC) - timedelta(days=months * 30)
        stmt = select(NewsArticle.title, NewsArticle.content).where(
            NewsArticle.company_id == company_id,
            NewsArticle.published_at >= cutoff,
        )
        result = await db.execute(stmt)
        rows = result.all()

        theme_counts: dict[str, int] = {}
        for row in rows:
            text = f"{row.title or ''} {row.content or ''}"
            for keyword, theme_code in self._ALL_THEME_KEYWORDS.items():
                if keyword in text:
                    theme_counts[theme_code] = theme_counts.get(theme_code, 0) + 1

        # 리스크 부재 알림 생성
        risk_absence_notices: list[str] = []
        for theme_code in RISK_ABSENCE_THEMES:
            if theme_counts.get(theme_code, 0) == 0:
                display = THEME_DISPLAY_NAMES.get(theme_code, theme_code)
                risk_absence_notices.append(f"{display} 보도 없음")

        return {
            "theme_counts": theme_counts,
            "total_articles": len(rows),
            "risk_absence_notices": risk_absence_notices,
        }
