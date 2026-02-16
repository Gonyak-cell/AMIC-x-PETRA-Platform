"""딜 소싱 서비스

투자 딜 데이터를 분석하고 섹터/단계별 집계를 제공한다.
"""

import json
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import (
    SECTOR_DISPLAY_NAMES,
    STAGE_DISPLAY_NAMES,
    Deal,
    DealSector,
    DealStage,
)
from app.models.news import NewsArticle
from app.services.nlp_service import NLPService

logger = logging.getLogger(__name__)


class DealService:
    """딜 소싱 서비스"""

    # 섹터 분류 키워드
    SECTOR_KEYWORDS: dict[str, list[str]] = {
        DealSector.AI_DEEPTECH: [
            "AI",
            "인공지능",
            "딥러닝",
            "머신러닝",
            "자율주행",
            "로봇",
            "반도체",
            "양자",
            "LLM",
            "생성형",
        ],
        DealSector.BIO_HEALTH: [
            "바이오",
            "헬스케어",
            "의료",
            "제약",
            "신약",
            "디지털헬스",
            "의료기기",
            "진단",
        ],
        DealSector.SAAS: [
            "SaaS",
            "클라우드",
            "B2B",
            "기업용",
            "소프트웨어",
            "플랫폼",
            "엔터프라이즈",
        ],
        DealSector.CONSUMER: [
            "소비재",
            "뷰티",
            "패션",
            "F&B",
            "식품",
            "라이프스타일",
            "D2C",
        ],
        DealSector.FINTECH: [
            "핀테크",
            "금융",
            "페이",
            "결제",
            "보험",
            "자산관리",
            "암호화폐",
            "블록체인",
        ],
        DealSector.MOBILITY: [
            "모빌리티",
            "전기차",
            "EV",
            "충전",
            "배터리",
            "물류",
            "라스트마일",
        ],
        DealSector.ECOMMERCE: [
            "이커머스",
            "커머스",
            "쇼핑",
            "유통",
            "마켓플레이스",
            "리테일",
        ],
        DealSector.CONTENT: [
            "콘텐츠",
            "미디어",
            "엔터",
            "게임",
            "OTT",
            "웹툰",
            "영상",
            "스트리밍",
        ],
        DealSector.PROPTECH: [
            "프롭테크",
            "부동산",
            "건설",
            "인테리어",
            "공간",
        ],
        DealSector.EDTECH: [
            "에드테크",
            "교육",
            "이러닝",
            "학습",
            "온라인교육",
        ],
    }

    # 투자 단계 추정 기준 (억원)
    STAGE_AMOUNT_RANGES: dict[str, tuple[float, float]] = {
        DealStage.SEED: (0, 10),
        DealStage.PRE_A: (10, 30),
        DealStage.SERIES_A: (30, 100),
        DealStage.SERIES_B: (100, 300),
        DealStage.SERIES_C: (300, 1000),
        DealStage.PRE_IPO: (1000, float("inf")),
    }

    def __init__(self, nlp_service: NLPService | None = None) -> None:
        self.nlp_service = nlp_service or NLPService()

    def classify_sector(self, text: str, keywords: list[str] | None = None) -> tuple[str, list[str]]:
        """텍스트와 키워드를 기반으로 섹터를 자동 분류한다.

        Args:
            text: 분석할 텍스트
            keywords: 추가 키워드 목록

        Returns:
            (섹터 코드, 매칭된 키워드 목록)
        """
        combined = f"{text} {' '.join(keywords or [])}"
        combined_lower = combined.lower()

        scores: dict[str, int] = {}
        matched_keywords: dict[str, list[str]] = {}

        for sector, sector_keywords in self.SECTOR_KEYWORDS.items():
            matches = [kw for kw in sector_keywords if kw.lower() in combined_lower]
            if matches:
                scores[sector] = len(matches)
                matched_keywords[sector] = matches

        if not scores:
            return DealSector.OTHER, []

        best_sector = max(scores, key=lambda k: scores[k])
        return best_sector, matched_keywords.get(best_sector, [])

    def estimate_stage(self, amount: Decimal | None, round_text: str | None) -> str:
        """투자 금액과 라운드 텍스트로 투자 단계를 추정한다.

        Args:
            amount: 투자 금액 (원)
            round_text: 라운드 텍스트 (예: "시리즈A")

        Returns:
            투자 단계 코드
        """
        # 1. 라운드 텍스트 우선 매칭
        if round_text:
            round_lower = round_text.lower().replace(" ", "").replace("-", "")

            if "seed" in round_lower or "시드" in round_lower:
                if "pre" in round_lower or "프리" in round_lower:
                    return DealStage.SEED
                return DealStage.SEED

            if "pre" in round_lower and "a" in round_lower:
                return DealStage.PRE_A

            if "series" in round_lower or "시리즈" in round_lower:
                # 시리즈 뒤의 문자로 판단 (series 단어 자체에 e가 있으므로 주의)
                if any(x in round_lower for x in ["seriesc", "seriesd", "seriese", "시리즈c", "시리즈d", "시리즈e"]):
                    return DealStage.SERIES_C
                if any(x in round_lower for x in ["seriesb", "시리즈b"]):
                    return DealStage.SERIES_B
                if any(x in round_lower for x in ["seriesa", "시리즈a"]):
                    return DealStage.SERIES_A

            if "ipo" in round_lower:
                return DealStage.PRE_IPO

            if "bridge" in round_lower or "브릿지" in round_lower:
                return DealStage.BRIDGE

        # 2. 금액 기반 추정
        if amount:
            amount_bok = float(amount) / 100_000_000  # 억원 단위로 변환
            for stage, (min_amt, max_amt) in self.STAGE_AMOUNT_RANGES.items():
                if min_amt <= amount_bok < max_amt:
                    return stage

        return DealStage.SEED  # 기본값

    def format_amount_display(self, amount: Decimal | None) -> str | None:
        """금액을 표시용 문자열로 변환한다."""
        if amount is None:
            return None

        amount_float = float(amount)

        if amount_float >= 1_000_000_000_000:  # 1조 이상
            return f"{amount_float / 1_000_000_000_000:.1f}조원"
        elif amount_float >= 100_000_000:  # 1억 이상
            return f"{int(amount_float / 100_000_000)}억원"
        elif amount_float >= 10_000:  # 1만원 이상
            return f"{int(amount_float / 10_000)}만원"
        else:
            return f"{int(amount_float)}원"

    async def extract_deal_from_news(
        self,
        db: AsyncSession,
        news_article_id: int,
        investor_corp_code: str | None = None,
    ) -> Deal | None:
        """뉴스 기사에서 딜 정보를 추출한다.

        Args:
            db: DB 세션
            news_article_id: 뉴스 기사 ID
            investor_corp_code: 투자사 DART 고유번호 (선택)

        Returns:
            추출된 딜 (금액이 없으면 None)
        """
        # 뉴스 기사 조회
        stmt = select(NewsArticle).where(NewsArticle.id == news_article_id)
        result = await db.execute(stmt)
        article = result.scalar_one_or_none()

        if not article:
            return None

        text = f"{article.title or ''} {article.content or ''}"

        # NLP 투자 정보 추출 (asyncio.to_thread로 실행하여 이벤트 루프 blocking 방지)
        investment_info = await self.nlp_service.extract_investment_info_async(text)

        if not investment_info["amounts"]:
            return None  # 투자 금액이 없으면 딜로 인식하지 않음

        # 금액 파싱
        amount = self._parse_amount(investment_info["amounts"][0])

        # 키워드 추출
        keywords_result = await self.nlp_service.extract_keywords_async(text, top_n=10)
        keywords = [kw["keyword"] for kw in keywords_result]

        # 섹터 분류
        sector, sector_keywords = self.classify_sector(text, keywords)

        # 투자 단계 추정
        stage = self.estimate_stage(amount, investment_info.get("round"))

        # 투자사 조회
        company_id = None
        if investor_corp_code:
            investor = await self._get_company(db, investor_corp_code)
            if investor:
                company_id = investor.id

        # 피투자사명
        target_company = investment_info["investees"][0] if investment_info["investees"] else "미확인"

        # 거래일
        deal_date = None
        if investment_info["dates"]:
            date_info = investment_info["dates"][0]
            try:
                year = int(date_info["year"])
                month = int(date_info["month"])
                day = int(date_info.get("day") or 1)
                deal_date = date(year, month, day)
            except (ValueError, TypeError):
                deal_date = article.published_at.date() if article.published_at else None

        # Deal 생성
        deal = Deal(
            company_id=company_id,
            target_company=target_company,
            amount=amount,
            amount_display=self.format_amount_display(amount),
            round_stage=stage,
            sector=sector,
            sector_keywords=json.dumps(sector_keywords, ensure_ascii=False),
            deal_date=deal_date,
            deal_year=deal_date.year if deal_date else None,
            source_url=article.url,
            source_type="news",
            news_article_id=article.id,
        )

        db.add(deal)
        await db.flush()
        return deal

    def _parse_amount(self, amount_info: dict) -> Decimal | None:
        """금액 정보를 원 단위로 변환한다."""
        try:
            value = int(amount_info["value"].replace(",", ""))
            unit = amount_info["unit"].replace(" ", "")

            multiplier = 1
            if "조" in unit:
                multiplier = 1_000_000_000_000
            elif "억" in unit:
                multiplier = 100_000_000
            elif "만" in unit:
                multiplier = 10_000

            # 달러인 경우 환율 적용 (대략 1,300원)
            if "달러" in unit:
                multiplier *= 1300

            return Decimal(str(value * multiplier))
        except (ValueError, KeyError, TypeError):
            return None

    async def _get_company(self, db: AsyncSession, corp_code: str) -> Company | None:
        """기업을 조회한다."""
        stmt = select(Company).where(Company.corp_code == corp_code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_deals_by_company(
        self,
        db: AsyncSession,
        corp_code: str,
        years: int = 5,
        sector: str | None = None,
        stage: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Deal], int]:
        """특정 투자사의 딜 목록을 조회한다.

        Returns:
            (딜 목록, 총 건수)
        """
        # 기업 조회
        company = await self._get_company(db, corp_code)
        if not company:
            return [], 0

        cutoff = datetime.now(UTC) - timedelta(days=years * 365)

        # 기본 쿼리
        base_query = select(Deal).where(
            Deal.company_id == company.id,
            Deal.deal_date >= cutoff.date(),
        )

        # 필터 적용
        if sector:
            base_query = base_query.where(Deal.sector == sector)
        if stage:
            base_query = base_query.where(Deal.round_stage == stage)

        # 총 건수
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        query = base_query.order_by(Deal.deal_date.desc()).offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        deals = list(result.scalars().all())

        return deals, total

    async def aggregate_by_sector(
        self,
        db: AsyncSession,
        corp_code: str | None = None,
        year: int | None = None,
        min_year: int | None = None,
    ) -> list[dict]:
        """섹터별 딜을 집계한다."""
        query = select(
            Deal.sector,
            func.count(Deal.id).label("deal_count"),
            func.sum(Deal.amount).label("total_amount"),
        )

        # 필터
        if corp_code:
            company = await self._get_company(db, corp_code)
            if company:
                query = query.where(Deal.company_id == company.id)
        if year:
            query = query.where(Deal.deal_year == year)
        elif min_year:
            query = query.where(Deal.deal_year >= min_year)

        query = query.where(Deal.sector.isnot(None)).group_by(Deal.sector)

        result = await db.execute(query)
        rows = result.all()

        aggregations = []
        for row in rows:
            sector = row.sector or DealSector.OTHER
            aggregations.append(
                {
                    "sector": sector,
                    "sector_name": SECTOR_DISPLAY_NAMES.get(sector, "기타"),
                    "deal_count": row.deal_count,
                    "total_amount": row.total_amount,
                }
            )

        return sorted(aggregations, key=lambda x: x["deal_count"], reverse=True)

    async def aggregate_by_stage(
        self,
        db: AsyncSession,
        corp_code: str | None = None,
        year: int | None = None,
        min_year: int | None = None,
    ) -> list[dict]:
        """투자 단계별 딜을 집계한다."""
        query = select(
            Deal.round_stage,
            func.count(Deal.id).label("deal_count"),
            func.sum(Deal.amount).label("total_amount"),
        )

        # 필터
        if corp_code:
            company = await self._get_company(db, corp_code)
            if company:
                query = query.where(Deal.company_id == company.id)
        if year:
            query = query.where(Deal.deal_year == year)
        elif min_year:
            query = query.where(Deal.deal_year >= min_year)

        query = query.where(Deal.round_stage.isnot(None)).group_by(Deal.round_stage)

        result = await db.execute(query)
        rows = result.all()

        aggregations = []
        for row in rows:
            stage = row.round_stage or DealStage.SEED
            aggregations.append(
                {
                    "stage": stage,
                    "stage_name": STAGE_DISPLAY_NAMES.get(stage, "시드"),
                    "deal_count": row.deal_count,
                    "total_amount": row.total_amount,
                }
            )

        # 단계 순서대로 정렬
        stage_order = list(DealStage)
        return sorted(
            aggregations,
            key=lambda x: stage_order.index(x["stage"]) if x["stage"] in stage_order else 999,
        )

    async def get_yearly_trends(
        self,
        db: AsyncSession,
        corp_code: str | None = None,
        years: int = 5,
    ) -> list[dict]:
        """연도별 투자 트렌드를 조회한다."""
        current_year = datetime.now(UTC).year
        start_year = current_year - years + 1

        query = select(
            Deal.deal_year,
            func.count(Deal.id).label("deal_count"),
            func.sum(Deal.amount).label("total_amount"),
        )

        # 필터
        if corp_code:
            company = await self._get_company(db, corp_code)
            if company:
                query = query.where(Deal.company_id == company.id)

        query = (
            query.where(Deal.deal_year >= start_year)
            .where(Deal.deal_year.isnot(None))
            .group_by(Deal.deal_year)
            .order_by(Deal.deal_year)
        )

        result = await db.execute(query)
        rows = result.all()

        trends = []
        for row in rows:
            trends.append(
                {
                    "year": row.deal_year,
                    "deal_count": row.deal_count,
                    "total_amount": row.total_amount,
                }
            )

        return trends
