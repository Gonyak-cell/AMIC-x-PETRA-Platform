"""웹 크롤링 패키지.

Playwright를 사용하여 JavaScript 렌더링이 필요한 페이지를 포함한
다양한 웹 사이트에서 데이터를 수집합니다.

Usage::
    from src.data_ingestor.crawler import PlaywrightEngine, NewsCrawler, CompanyCrawler

    # Playwright 엔진으로 페이지 렌더링
    async with PlaywrightEngine() as engine:
        html = await engine.get_page_content("https://example.com")

    # 뉴스 크롤링
    news_crawler = NewsCrawler()
    articles = await news_crawler.search("삼성전자", days=30)

    # 기업 웹사이트 크롤링
    company_crawler = CompanyCrawler()
    info = await company_crawler.extract_company_info("https://company.com")
"""

from src.data_ingestor.crawler.company_crawler import CompanyCrawler, CompanyWebInfo
from src.data_ingestor.crawler.news_crawler import NewsArticle, NewsCrawler
from src.data_ingestor.crawler.playwright_engine import PlaywrightEngine

__all__ = [
    "CompanyCrawler",
    "CompanyWebInfo",
    "NewsArticle",
    "NewsCrawler",
    "PlaywrightEngine",
]
