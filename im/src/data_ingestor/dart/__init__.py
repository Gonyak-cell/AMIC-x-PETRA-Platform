"""DART API 클라이언트 패키지.

이 패키지는 Open DART API와의 통신을 담당합니다.

Usage::
    from src.data_ingestor.dart import DartAPIClient, DartCompanyInfo

    async with DartAPIClient() as client:
        info = await client.get_company_info("00123456")
"""

from src.data_ingestor.dart.client import DartAPIClient
from src.data_ingestor.dart.endpoints import (
    FinancialStatementDivision,
    ReportCode,
)
from src.data_ingestor.dart.models import (
    DartCompanyInfo,
    DartDividend,
    DartFinancialStatement,
    DartMajorShareholder,
    DartSearchResult,
    FinancialStatementsCollection,
)
from src.data_ingestor.dart.rate_limiter import RateLimiter

__all__ = [
    "DartAPIClient",
    "DartCompanyInfo",
    "DartDividend",
    "DartFinancialStatement",
    "DartMajorShareholder",
    "DartSearchResult",
    "FinancialStatementDivision",
    "FinancialStatementsCollection",
    "RateLimiter",
    "ReportCode",
]
