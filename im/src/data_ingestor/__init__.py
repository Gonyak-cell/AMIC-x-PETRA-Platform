"""Data Ingestor 패키지.

DART API, 웹 크롤링, 문서 파싱을 통해 IM 문서 생성에 필요한 데이터를 수집합니다.

Usage::
    from src.data_ingestor import DartAPIClient, DataAggregator
    from src.data_ingestor.parsers import PDFParser, ExcelParser
    from src.data_ingestor.crawler import PlaywrightEngine, NewsCrawler
    from src.data_ingestor import DataCollectionPipeline, PipelineConfig
"""

from src.data_ingestor.aggregator import (
    CompanyProfile,
    DataAggregator,
    FinancialMetric,
    FinancialSummary,
    IMDocumentData,
    NewsInfo,
    ShareholderInfo,
)
from src.data_ingestor.cache import (
    CacheConfig,
    CachedDartClient,
    CacheManager,
    CacheTTL,
)
from src.data_ingestor.dart import (
    DartAPIClient,
    DartCompanyInfo,
    DartDividend,
    DartFinancialStatement,
    DartMajorShareholder,
    DartSearchResult,
    FinancialStatementDivision,
    FinancialStatementsCollection,
    RateLimiter,
    ReportCode,
)
from src.data_ingestor.exceptions import (
    AggregationError,
    CacheError,
    ContentExtractionError,
    CrawlerBlockedError,
    CrawlerError,
    CrawlerNetworkError,
    CrawlerTimeoutError,
    DartAPIError,
    DartAuthenticationError,
    DartNetworkError,
    DartNotFoundError,
    DartRateLimitError,
    DartResponseError,
    DataIngestorError,
    DataMergeConflictError,
    DataValidationError,
    ExcelParserError,
    MissingRequiredDataError,
    PageRenderError,
    ParserError,
    PDFParserError,
    PipelineError,
    TableExtractionError,
)
from src.data_ingestor.pipeline import (
    CollectionResult,
    DataCollectionPipeline,
    DataPriority,
    PipelineConfig,
    StepResult,
)

__all__ = [
    # Core
    "DataAggregator",
    "IMDocumentData",
    "CompanyProfile",
    "FinancialSummary",
    "FinancialMetric",
    "ShareholderInfo",
    "NewsInfo",
    # DART Client
    "DartAPIClient",
    "DartCompanyInfo",
    "DartFinancialStatement",
    "DartMajorShareholder",
    "DartDividend",
    "DartSearchResult",
    "FinancialStatementsCollection",
    "FinancialStatementDivision",
    "ReportCode",
    "RateLimiter",
    # Cache
    "CacheManager",
    "CachedDartClient",
    "CacheConfig",
    "CacheTTL",
    # Pipeline
    "DataCollectionPipeline",
    "PipelineConfig",
    "CollectionResult",
    "StepResult",
    "DataPriority",
    # Exceptions - Base
    "DataIngestorError",
    # Exceptions - DART API
    "DartAPIError",
    "DartAuthenticationError",
    "DartRateLimitError",
    "DartNotFoundError",
    "DartResponseError",
    "DartNetworkError",
    # Exceptions - Parser
    "ParserError",
    "PDFParserError",
    "ExcelParserError",
    "TableExtractionError",
    "DataValidationError",
    # Exceptions - Crawler
    "CrawlerError",
    "CrawlerNetworkError",
    "CrawlerTimeoutError",
    "CrawlerBlockedError",
    "PageRenderError",
    "ContentExtractionError",
    # Exceptions - Aggregation
    "AggregationError",
    "MissingRequiredDataError",
    "DataMergeConflictError",
    # Exceptions - Cache & Pipeline
    "CacheError",
    "PipelineError",
]

__version__ = "0.2.1"
