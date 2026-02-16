"""대시보드 API 스키마"""

from datetime import datetime

from pydantic import BaseModel


class DataCount(BaseModel):
    """데이터 건수"""

    label: str
    count: int


class RecentDeal(BaseModel):
    """최근 딜 요약"""

    target_company: str
    amount_display: str | None = None
    sector: str | None = None
    deal_date: datetime | None = None


class RiskCompany(BaseModel):
    """리스크 기업"""

    corp_code: str
    corp_name: str
    status_tag: str
    total_score: float


class DataFreshness(BaseModel):
    """데이터 신선도"""

    entity: str
    latest_at: datetime | None = None
    count: int


class DashboardSummary(BaseModel):
    """대시보드 요약 응답"""

    counts: list[DataCount]
    recent_news_count: int
    recent_deals: list[RecentDeal]
    risk_companies: list[RiskCompany]
    data_freshness: list[DataFreshness]
