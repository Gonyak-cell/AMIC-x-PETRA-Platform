"""DART API 엔드포인트 정의.

Open DART API의 모든 엔드포인트 URL과 관련 상수를 정의합니다.
API 문서: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001

DART API 응답 코드:
    - 000: 정상
    - 010: 등록되지 않은 키
    - 011: 사용할 수 없는 키
    - 012: 접근할 수 없는 IP
    - 013: 조회된 데이터가 없음
    - 014: 파일이 존재하지 않음
    - 020: 요청 제한 초과
    - 100: 필드의 부적절한 값
    - 800: 시스템 점검
    - 900: 정의되지 않은 오류
"""

from __future__ import annotations

from enum import Enum
from typing import Final


# ============================================================================
# Base URL
# ============================================================================

DART_BASE_URL: Final[str] = "https://opendart.fss.or.kr/api"


# ============================================================================
# 공시정보 (Disclosure)
# ============================================================================


class DisclosureEndpoints:
    """공시정보 API 엔드포인트."""

    # 공시검색
    LIST: Final[str] = f"{DART_BASE_URL}/list.json"

    # 기업개황
    COMPANY: Final[str] = f"{DART_BASE_URL}/company.json"

    # 고유번호 (corp_code) 조회용 ZIP 파일
    CORP_CODE_ZIP: Final[str] = f"{DART_BASE_URL}/corpCode.xml"


# ============================================================================
# 사업보고서 주요정보 (Business Report)
# ============================================================================


class BusinessReportEndpoints:
    """사업보고서 주요정보 API 엔드포인트."""

    # 증자(감자) 현황
    INCREASE_CAPITAL: Final[str] = f"{DART_BASE_URL}/irdsSttus.json"

    # 배당에 관한 사항
    DIVIDEND: Final[str] = f"{DART_BASE_URL}/alotMatter.json"

    # 자기주식 취득 및 처분 현황
    TREASURY_STOCK: Final[str] = f"{DART_BASE_URL}/tesstkAcqsDspsSttus.json"

    # 최대주주 현황
    MAJOR_SHAREHOLDER: Final[str] = f"{DART_BASE_URL}/hyslrSttus.json"

    # 최대주주 변동현황
    MAJOR_SHAREHOLDER_CHANGE: Final[str] = f"{DART_BASE_URL}/hyslrChgSttus.json"

    # 소액주주 현황
    MINORITY_SHAREHOLDER: Final[str] = f"{DART_BASE_URL}/mrhlSttus.json"

    # 임원 현황
    EXECUTIVES: Final[str] = f"{DART_BASE_URL}/exctvSttus.json"

    # 직원 현황
    EMPLOYEES: Final[str] = f"{DART_BASE_URL}/empSttus.json"

    # 이사·감사의 개인별 보수 현황
    EXEC_COMPENSATION: Final[str] = f"{DART_BASE_URL}/hmvAuditIndvdlBySttus.json"

    # 이사·감사 전체의 보수현황
    EXEC_TOTAL_COMPENSATION: Final[str] = f"{DART_BASE_URL}/hmvAuditAllSttus.json"

    # 개인별 보수지급 금액 (5억원 이상)
    INDIVIDUAL_COMPENSATION: Final[str] = f"{DART_BASE_URL}/indvdlByPay.json"

    # 타법인 출자 현황
    INVESTMENT_OTHER: Final[str] = f"{DART_BASE_URL}/otrCprInvstmntSttus.json"


# ============================================================================
# 재무정보 (Financial Statements)
# ============================================================================


class FinancialEndpoints:
    """재무정보 API 엔드포인트."""

    # 단일회사 주요계정 (요약 재무제표)
    SINGLE_COMPANY_ACCOUNT: Final[str] = f"{DART_BASE_URL}/fnlttSinglAcnt.json"

    # 다중회사 주요계정
    MULTI_COMPANY_ACCOUNT: Final[str] = f"{DART_BASE_URL}/fnlttMultiAcnt.json"

    # 단일회사 전체 재무제표
    SINGLE_COMPANY_FULL: Final[str] = f"{DART_BASE_URL}/fnlttSinglAcntAll.json"

    # XBRL 재무제표 원본 파일
    XBRL_TAXONOMY: Final[str] = f"{DART_BASE_URL}/fnlttXbrl.xml"


# ============================================================================
# 지분공시 (Shareholding Disclosure)
# ============================================================================


class ShareholdingEndpoints:
    """지분공시 API 엔드포인트."""

    # 주요사항보고서 - 주식등의 대량보유상황보고서
    MAJOR_STOCK: Final[str] = f"{DART_BASE_URL}/majorstock.json"

    # 임원·주요주주 특정증권등 소유상황보고서
    EXECUTIVE_STOCK: Final[str] = f"{DART_BASE_URL}/elestock.json"


# ============================================================================
# 보고서 코드 (Report Codes)
# ============================================================================


class ReportCode(str, Enum):
    """보고서 종류 코드."""

    ANNUAL = "11011"  # 사업보고서
    SEMI_ANNUAL = "11012"  # 반기보고서
    Q1 = "11013"  # 1분기보고서
    Q3 = "11014"  # 3분기보고서


class FinancialStatementDivision(str, Enum):
    """재무제표 구분 코드."""

    CONSOLIDATED = "CFS"  # 연결재무제표
    SEPARATE = "OFS"  # 별도재무제표


class CorporateClass(str, Enum):
    """법인 구분 코드."""

    KOSPI = "Y"  # 유가증권시장
    KOSDAQ = "K"  # 코스닥
    KONEX = "N"  # 코넥스
    ETC = "E"  # 기타 (비상장 등)


# ============================================================================
# API 응답 상태 코드
# ============================================================================


class DartStatusCode:
    """DART API 응답 상태 코드."""

    SUCCESS: Final[str] = "000"
    INVALID_KEY: Final[str] = "010"
    DISABLED_KEY: Final[str] = "011"
    BLOCKED_IP: Final[str] = "012"
    NO_DATA: Final[str] = "013"
    FILE_NOT_FOUND: Final[str] = "014"
    RATE_LIMIT_EXCEEDED: Final[str] = "020"
    INVALID_PARAMETER: Final[str] = "100"
    SYSTEM_MAINTENANCE: Final[str] = "800"
    UNKNOWN_ERROR: Final[str] = "900"

    @classmethod
    def is_success(cls, code: str) -> bool:
        """성공 코드 여부."""
        return code == cls.SUCCESS

    @classmethod
    def is_retryable(cls, code: str) -> bool:
        """재시도 가능한 오류 여부."""
        return code in (cls.RATE_LIMIT_EXCEEDED, cls.SYSTEM_MAINTENANCE)

    @classmethod
    def get_message(cls, code: str) -> str:
        """상태 코드에 대한 한글 메시지."""
        messages = {
            cls.SUCCESS: "정상",
            cls.INVALID_KEY: "등록되지 않은 키입니다",
            cls.DISABLED_KEY: "사용할 수 없는 키입니다",
            cls.BLOCKED_IP: "접근할 수 없는 IP입니다",
            cls.NO_DATA: "조회된 데이터가 없습니다",
            cls.FILE_NOT_FOUND: "파일이 존재하지 않습니다",
            cls.RATE_LIMIT_EXCEEDED: "요청 제한을 초과했습니다",
            cls.INVALID_PARAMETER: "필드의 부적절한 값입니다",
            cls.SYSTEM_MAINTENANCE: "시스템 점검 중입니다",
            cls.UNKNOWN_ERROR: "정의되지 않은 오류입니다",
        }
        return messages.get(code, f"알 수 없는 코드: {code}")


# ============================================================================
# 주요 계정과목 코드
# ============================================================================


class AccountCode:
    """표준 계정과목 코드 (DART 기준)."""

    # 재무상태표 - 자산
    TOTAL_ASSETS: Final[str] = "ifrs-full_Assets"
    CURRENT_ASSETS: Final[str] = "ifrs-full_CurrentAssets"
    NON_CURRENT_ASSETS: Final[str] = "ifrs-full_NoncurrentAssets"
    CASH: Final[str] = "ifrs-full_CashAndCashEquivalents"
    INVENTORY: Final[str] = "ifrs-full_Inventories"
    TRADE_RECEIVABLES: Final[str] = "ifrs-full_TradeAndOtherCurrentReceivables"

    # 재무상태표 - 부채
    TOTAL_LIABILITIES: Final[str] = "ifrs-full_Liabilities"
    CURRENT_LIABILITIES: Final[str] = "ifrs-full_CurrentLiabilities"
    NON_CURRENT_LIABILITIES: Final[str] = "ifrs-full_NoncurrentLiabilities"
    BORROWINGS: Final[str] = "ifrs-full_Borrowings"
    TRADE_PAYABLES: Final[str] = "ifrs-full_TradeAndOtherCurrentPayables"

    # 재무상태표 - 자본
    TOTAL_EQUITY: Final[str] = "ifrs-full_Equity"
    SHARE_CAPITAL: Final[str] = "ifrs-full_IssuedCapital"
    RETAINED_EARNINGS: Final[str] = "ifrs-full_RetainedEarnings"

    # 손익계산서
    REVENUE: Final[str] = "ifrs-full_Revenue"
    COST_OF_SALES: Final[str] = "ifrs-full_CostOfSales"
    GROSS_PROFIT: Final[str] = "ifrs-full_GrossProfit"
    OPERATING_INCOME: Final[str] = "dart_OperatingIncomeLoss"
    NET_INCOME: Final[str] = "ifrs-full_ProfitLoss"
    EPS: Final[str] = "ifrs-full_BasicEarningsLossPerShare"


# ============================================================================
# API 요청 기본값
# ============================================================================


class DartDefaults:
    """DART API 요청 기본값."""

    # 분당 호출 제한
    RATE_LIMIT_CALLS: Final[int] = 100
    RATE_LIMIT_PERIOD: Final[float] = 60.0

    # 타임아웃 (초)
    REQUEST_TIMEOUT: Final[float] = 30.0
    CONNECT_TIMEOUT: Final[float] = 10.0

    # 기본 조회 연도 (최근 5년)
    DEFAULT_YEARS: Final[int] = 5

    # 재시도 설정
    MAX_RETRIES: Final[int] = 3
    RETRY_BASE_DELAY: Final[float] = 1.0
    RETRY_FACTOR: Final[float] = 2.0


# ============================================================================
# 편의 함수
# ============================================================================


def get_financial_statements_url() -> str:
    """단일회사 주요계정 API URL 반환."""
    return FinancialEndpoints.SINGLE_COMPANY_ACCOUNT


def get_company_info_url() -> str:
    """기업개황 API URL 반환."""
    return DisclosureEndpoints.COMPANY


def get_major_stock_url() -> str:
    """대량보유상황보고서 API URL 반환."""
    return ShareholdingEndpoints.MAJOR_STOCK


def get_dividend_url() -> str:
    """배당정보 API URL 반환."""
    return BusinessReportEndpoints.DIVIDEND


def get_executives_url() -> str:
    """임원현황 API URL 반환."""
    return BusinessReportEndpoints.EXECUTIVES


def get_employees_url() -> str:
    """직원현황 API URL 반환."""
    return BusinessReportEndpoints.EMPLOYEES
