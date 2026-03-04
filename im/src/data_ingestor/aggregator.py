"""데이터 집계기 (Aggregator).

DART API, 파서, 크롤러에서 수집한 데이터를 병합하여
IM 문서 생성에 필요한 통합 데이터 구조로 변환합니다.

사용 예시:
    aggregator = DataAggregator()

    # 데이터 추가
    aggregator.add_dart_company(dart_company_info)
    aggregator.add_dart_financials(dart_financials)
    aggregator.add_parsed_financials(excel_data)
    aggregator.add_news_articles(news_list)
    aggregator.add_company_web_info(web_info)

    # 통합 데이터 빌드
    im_data = aggregator.build()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from src.data_ingestor.exceptions import MissingRequiredDataError

if TYPE_CHECKING:
    from src.data_ingestor.crawler.company_crawler import CompanyWebInfo
    from src.data_ingestor.crawler.news_crawler import NewsArticle
    from src.data_ingestor.dart.models import (
        DartCompanyInfo,
        DartDividend,
        DartMajorShareholder,
        FinancialStatementsCollection,
    )

logger = logging.getLogger(__name__)


@dataclass
class CompanyProfile:
    """기업 프로필 정보."""

    corp_code: str = ""
    """DART 고유번호."""

    corp_name: str = ""
    """회사명."""

    corp_name_eng: str = ""
    """영문 회사명."""

    stock_code: str = ""
    """종목코드."""

    ceo_name: str = ""
    """대표이사."""

    establishment_date: datetime | None = None
    """설립일."""

    listing_date: datetime | None = None
    """상장일."""

    industry: str = ""
    """업종."""

    homepage_url: str = ""
    """홈페이지 URL."""

    ir_url: str = ""
    """IR 페이지 URL."""

    address: str = ""
    """주소."""

    phone: str = ""
    """전화번호."""

    fax: str = ""
    """팩스번호."""

    employee_count: int = 0
    """직원 수."""

    fiscal_month: int = 12
    """결산월."""

    description: str = ""
    """회사 소개."""

    vision: str = ""
    """비전/미션."""

    logo_url: str = ""
    """로고 URL."""

    brand_colors: list[str] = field(default_factory=list)
    """브랜드 컬러."""


@dataclass
class FinancialMetric:
    """재무 지표."""

    name: str
    """지표명."""

    current_value: Decimal | None = None
    """당기 값."""

    previous_value: Decimal | None = None
    """전기 값."""

    unit: str = "원"
    """단위."""

    growth_rate: float | None = None
    """성장률 (%)."""

    def calculate_growth(self) -> float | None:
        """전기 대비 성장률 계산."""
        if self.current_value is None or self.previous_value is None:
            return None
        if self.previous_value == 0:
            return None
        rate = float(
            (self.current_value - self.previous_value) / self.previous_value * 100
        )
        self.growth_rate = rate
        return rate


@dataclass
class FinancialSummary:
    """재무 요약."""

    bsns_year: str = ""
    """사업연도."""

    fs_div: str = "CFS"
    """재무제표 구분 (CFS/OFS)."""

    # 주요 수익성 지표
    revenue: FinancialMetric = field(default_factory=lambda: FinancialMetric("매출액"))
    operating_profit: FinancialMetric = field(
        default_factory=lambda: FinancialMetric("영업이익")
    )
    net_income: FinancialMetric = field(
        default_factory=lambda: FinancialMetric("당기순이익")
    )

    # 주요 재무상태 지표
    total_assets: FinancialMetric = field(
        default_factory=lambda: FinancialMetric("자산총계")
    )
    total_liabilities: FinancialMetric = field(
        default_factory=lambda: FinancialMetric("부채총계")
    )
    total_equity: FinancialMetric = field(
        default_factory=lambda: FinancialMetric("자본총계")
    )

    # 추가 지표들
    additional_metrics: dict[str, FinancialMetric] = field(default_factory=dict)

    # 비율 지표
    operating_margin: float | None = None
    """영업이익률 (%)."""

    net_margin: float | None = None
    """순이익률 (%)."""

    roe: float | None = None
    """자기자본이익률 (ROE, %)."""

    debt_ratio: float | None = None
    """부채비율 (%)."""

    def calculate_ratios(self) -> None:
        """비율 지표 계산."""
        # 영업이익률
        if self.revenue.current_value and self.operating_profit.current_value:
            self.operating_margin = float(
                self.operating_profit.current_value / self.revenue.current_value * 100
            )

        # 순이익률
        if self.revenue.current_value and self.net_income.current_value:
            self.net_margin = float(
                self.net_income.current_value / self.revenue.current_value * 100
            )

        # ROE
        if self.total_equity.current_value and self.net_income.current_value:
            self.roe = float(
                self.net_income.current_value / self.total_equity.current_value * 100
            )

        # 부채비율
        if self.total_equity.current_value and self.total_liabilities.current_value:
            self.debt_ratio = float(
                self.total_liabilities.current_value
                / self.total_equity.current_value
                * 100
            )


@dataclass
class ShareholderInfo:
    """주주 정보."""

    name: str
    """주주명."""

    share_count: int = 0
    """보유 주식수."""

    share_ratio: float = 0.0
    """지분율 (%)."""

    is_major: bool = False
    """최대주주 여부."""


@dataclass
class NewsInfo:
    """뉴스 정보."""

    title: str
    """제목."""

    url: str
    """URL."""

    source: str
    """출처."""

    published_at: datetime | None = None
    """게시일."""

    summary: str = ""
    """요약."""

    sentiment: float | None = None
    """감성 점수."""


@dataclass
class IMDocumentData:
    """IM 문서 생성을 위한 통합 데이터."""

    # 기업 정보
    company: CompanyProfile = field(default_factory=CompanyProfile)

    # 재무 정보
    financials: FinancialSummary = field(default_factory=FinancialSummary)
    historical_financials: list[FinancialSummary] = field(default_factory=list)

    # 주주 정보
    shareholders: list[ShareholderInfo] = field(default_factory=list)
    dividend_info: list[dict[str, Any]] = field(default_factory=list)

    # 뉴스 및 시장 정보
    recent_news: list[NewsInfo] = field(default_factory=list)

    # 제품/서비스 정보
    products: list[dict[str, str]] = field(default_factory=list)

    # 경영진 정보
    executives: list[dict[str, str]] = field(default_factory=list)

    # 연혁
    history: list[dict[str, str]] = field(default_factory=list)

    # 메타데이터
    collected_at: datetime = field(default_factory=datetime.now)
    data_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "company": {
                "corp_code": self.company.corp_code,
                "corp_name": self.company.corp_name,
                "stock_code": self.company.stock_code,
                "ceo_name": self.company.ceo_name,
                "industry": self.company.industry,
                "description": self.company.description,
            },
            "financials": {
                "bsns_year": self.financials.bsns_year,
                "revenue": float(self.financials.revenue.current_value or 0),
                "operating_profit": float(
                    self.financials.operating_profit.current_value or 0
                ),
                "net_income": float(self.financials.net_income.current_value or 0),
                "operating_margin": self.financials.operating_margin,
                "roe": self.financials.roe,
            },
            "shareholders": [
                {"name": s.name, "ratio": s.share_ratio} for s in self.shareholders
            ],
            "news_count": len(self.recent_news),
            "collected_at": self.collected_at.isoformat(),
        }


class DataAggregator:
    """데이터 집계기.

    다양한 소스에서 수집한 데이터를 병합하여
    IM 문서 생성에 필요한 통합 데이터 구조를 생성합니다.

    Example:
        >>> aggregator = DataAggregator()
        >>> aggregator.add_dart_company(company_info)
        >>> aggregator.add_dart_financials(financials)
        >>> im_data = aggregator.build()
    """

    def __init__(self) -> None:
        """DataAggregator 초기화."""
        self._company: DartCompanyInfo | None = None
        self._financials: FinancialStatementsCollection | None = None
        self._historical_financials: list[FinancialStatementsCollection] = []
        self._shareholders: list[DartMajorShareholder] = []
        self._dividends: list[DartDividend] = []
        self._parsed_financials: dict[str, Any] = {}
        self._news_articles: list[NewsArticle] = []
        self._web_info: CompanyWebInfo | None = None
        self._data_sources: list[str] = []

    def add_dart_company(self, info: DartCompanyInfo) -> DataAggregator:
        """DART 기업 정보를 추가합니다.

        Args:
            info: DartCompanyInfo 객체.

        Returns:
            self (체이닝 지원).
        """
        self._company = info
        if "DART" not in self._data_sources:
            self._data_sources.append("DART")
        logger.info("DART 기업 정보 추가: %s", info.corp_name)
        return self

    def add_dart_financials(
        self,
        financials: FinancialStatementsCollection,
        *,
        is_historical: bool = False,
    ) -> DataAggregator:
        """DART 재무제표를 추가합니다.

        Args:
            financials: FinancialStatementsCollection 객체.
            is_historical: 과거 데이터 여부. True면 historical에 추가.

        Returns:
            self (체이닝 지원).
        """
        if is_historical:
            self._historical_financials.append(financials)
        else:
            self._financials = financials

        if "DART" not in self._data_sources:
            self._data_sources.append("DART")

        logger.info("DART 재무제표 추가: %s년", financials.bsns_year)
        return self

    def add_dart_shareholders(
        self,
        shareholders: list[DartMajorShareholder],
    ) -> DataAggregator:
        """DART 주주 정보를 추가합니다.

        Args:
            shareholders: DartMajorShareholder 리스트.

        Returns:
            self (체이닝 지원).
        """
        self._shareholders = shareholders
        if "DART" not in self._data_sources:
            self._data_sources.append("DART")
        logger.info("DART 주주 정보 추가: %d명", len(shareholders))
        return self

    def add_dart_dividends(
        self,
        dividends: list[DartDividend],
    ) -> DataAggregator:
        """DART 배당 정보를 추가합니다.

        Args:
            dividends: DartDividend 리스트.

        Returns:
            self (체이닝 지원).
        """
        self._dividends = dividends
        logger.info("DART 배당 정보 추가: %d건", len(dividends))
        return self

    def add_parsed_financials(
        self,
        data: dict[str, Any],
        *,
        source: str = "Excel",
    ) -> DataAggregator:
        """파싱된 재무 데이터를 추가합니다.

        Excel, PDF 등에서 추출한 추가 재무 데이터를 병합합니다.

        Args:
            data: 파싱된 재무 데이터 딕셔너리.
            source: 데이터 소스 이름.

        Returns:
            self (체이닝 지원).
        """
        self._parsed_financials.update(data)
        if source not in self._data_sources:
            self._data_sources.append(source)
        logger.info("파싱된 재무 데이터 추가 (%s): %d개 항목", source, len(data))
        return self

    def add_news_articles(
        self,
        articles: list[NewsArticle],
    ) -> DataAggregator:
        """뉴스 기사를 추가합니다.

        Args:
            articles: NewsArticle 리스트.

        Returns:
            self (체이닝 지원).
        """
        self._news_articles.extend(articles)
        if "News" not in self._data_sources:
            self._data_sources.append("News")
        logger.info("뉴스 기사 추가: %d건", len(articles))
        return self

    def add_company_web_info(
        self,
        web_info: CompanyWebInfo,
    ) -> DataAggregator:
        """기업 웹사이트 정보를 추가합니다.

        Args:
            web_info: CompanyWebInfo 객체.

        Returns:
            self (체이닝 지원).
        """
        self._web_info = web_info
        if "Web" not in self._data_sources:
            self._data_sources.append("Web")
        logger.info("웹사이트 정보 추가: %s", web_info.url)
        return self

    def validate(self) -> list[str]:
        """데이터 유효성을 검증합니다.

        Returns:
            오류 메시지 리스트 (비어 있으면 유효).
        """
        errors: list[str] = []

        if self._company is None:
            errors.append("기업 정보가 필요합니다. (add_dart_company)")

        if self._financials is None and not self._parsed_financials:
            errors.append(
                "재무 정보가 필요합니다. (add_dart_financials 또는 add_parsed_financials)"
            )

        return errors

    def build(self, *, require_all: bool = False) -> IMDocumentData:
        """통합 데이터를 빌드합니다.

        Args:
            require_all: True면 모든 필수 데이터가 있어야 함.

        Returns:
            IMDocumentData 객체.

        Raises:
            MissingRequiredDataError: require_all=True이고 필수 데이터가 없는 경우.
        """
        errors = self.validate()
        if require_all and errors:
            raise MissingRequiredDataError(missing_fields=errors)

        # 결과 데이터 생성
        result = IMDocumentData()
        result.data_sources = self._data_sources.copy()

        # 기업 정보 병합
        result.company = self._build_company_profile()

        # 재무 정보 병합
        result.financials = self._build_financial_summary()
        result.historical_financials = self._build_historical_financials()

        # 주주 정보
        result.shareholders = self._build_shareholders()

        # 배당 정보
        result.dividend_info = [d.model_dump() for d in self._dividends]

        # 뉴스 정보
        result.recent_news = self._build_news_info()

        # 웹 정보
        if self._web_info:
            result.products = self._web_info.products
            result.executives = self._web_info.executives
            result.history = self._web_info.history

        return result

    def _build_company_profile(self) -> CompanyProfile:
        """기업 프로필을 빌드합니다."""
        profile = CompanyProfile()

        # DART 정보
        if self._company:
            profile.corp_code = self._company.corp_code
            profile.corp_name = self._company.corp_name
            profile.corp_name_eng = self._company.corp_name_eng or ""
            profile.stock_code = self._company.stock_code or ""
            profile.ceo_name = self._company.ceo_nm or ""
            profile.industry = self._company.induty_code or ""
            profile.homepage_url = self._company.hm_url or ""
            profile.ir_url = self._company.ir_url or ""
            profile.address = self._company.adres or ""
            profile.phone = self._company.phn_no or ""
            profile.fax = self._company.fax_no or ""
            profile.fiscal_month = (
                int(self._company.acc_mt) if self._company.acc_mt else 12
            )

            if self._company.est_dt:
                try:
                    profile.establishment_date = datetime.strptime(
                        self._company.est_dt, "%Y%m%d"
                    )
                except Exception:
                    pass

        # 웹 정보로 보완
        if self._web_info:
            if not profile.corp_name and self._web_info.name:
                profile.corp_name = self._web_info.name

            if not profile.description:
                profile.description = self._web_info.description

            profile.vision = self._web_info.vision
            profile.logo_url = self._web_info.logo_url
            profile.brand_colors = self._web_info.brand_colors

            if not profile.ir_url and self._web_info.ir_url:
                profile.ir_url = self._web_info.ir_url

            if self._web_info.contact:
                if not profile.phone and self._web_info.contact.get("phone"):
                    profile.phone = self._web_info.contact["phone"]

        return profile

    def _build_financial_summary(self) -> FinancialSummary:
        """재무 요약을 빌드합니다."""
        summary = FinancialSummary()

        if self._financials:
            summary.bsns_year = self._financials.bsns_year
            summary.fs_div = self._financials.fs_div

            # 주요 계정과목 매핑
            account_mapping = {
                "매출액": summary.revenue,
                "영업이익": summary.operating_profit,
                "당기순이익": summary.net_income,
                "자산총계": summary.total_assets,
                "부채총계": summary.total_liabilities,
                "자본총계": summary.total_equity,
            }

            for account_name, metric in account_mapping.items():
                item = self._financials.get_by_account(account_name)
                if item:
                    metric.current_value = item.current_amount
                    metric.previous_value = item.previous_amount
                    metric.calculate_growth()

            # 비율 지표 계산
            summary.calculate_ratios()

        # 파싱된 재무 데이터로 보완
        if self._parsed_financials:
            for key, value in self._parsed_financials.items():
                if key not in summary.additional_metrics:
                    try:
                        amount = Decimal(str(value).replace(",", ""))
                        summary.additional_metrics[key] = FinancialMetric(
                            name=key,
                            current_value=amount,
                        )
                    except Exception:
                        pass

        return summary

    def _build_historical_financials(self) -> list[FinancialSummary]:
        """과거 재무 요약 리스트를 빌드합니다."""
        result: list[FinancialSummary] = []

        for fs in self._historical_financials:
            summary = FinancialSummary()
            summary.bsns_year = fs.bsns_year
            summary.fs_div = fs.fs_div

            # 주요 계정과목
            for account_name, attr_name in [
                ("매출액", "revenue"),
                ("영업이익", "operating_profit"),
                ("당기순이익", "net_income"),
                ("자산총계", "total_assets"),
                ("부채총계", "total_liabilities"),
                ("자본총계", "total_equity"),
            ]:
                item = fs.get_by_account(account_name)
                if item:
                    metric = getattr(summary, attr_name)
                    metric.current_value = item.current_amount
                    metric.previous_value = item.previous_amount
                    metric.calculate_growth()

            summary.calculate_ratios()
            result.append(summary)

        # 연도순 정렬
        result.sort(key=lambda s: s.bsns_year, reverse=True)
        return result

    def _build_shareholders(self) -> list[ShareholderInfo]:
        """주주 정보를 빌드합니다."""
        result: list[ShareholderInfo] = []

        for i, sh in enumerate(self._shareholders):
            info = ShareholderInfo(
                name=sh.repror or "",
                share_count=sh.share_count or 0,
                share_ratio=sh.share_ratio or 0.0,
                is_major=(i == 0),  # 첫 번째가 최대주주
            )
            result.append(info)

        return result

    def _build_news_info(self) -> list[NewsInfo]:
        """뉴스 정보를 빌드합니다."""
        result: list[NewsInfo] = []

        for article in self._news_articles:
            info = NewsInfo(
                title=article.title,
                url=article.url,
                source=article.source,
                published_at=article.published_at,
                summary=article.summary,
                sentiment=article.sentiment,
            )
            result.append(info)

        # 날짜순 정렬
        result.sort(key=lambda n: n.published_at or datetime.min, reverse=True)
        return result

    def reset(self) -> None:
        """모든 데이터를 초기화합니다."""
        self._company = None
        self._financials = None
        self._historical_financials = []
        self._shareholders = []
        self._dividends = []
        self._parsed_financials = {}
        self._news_articles = []
        self._web_info = None
        self._data_sources = []
        logger.info("DataAggregator 초기화됨")
