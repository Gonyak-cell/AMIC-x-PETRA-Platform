"""DART API 응답 Pydantic 모델.

Open DART API 응답을 파이썬 객체로 변환하기 위한 데이터 모델 정의.
모든 모델은 API 응답 JSON을 직접 파싱할 수 있도록 설계되었습니다.

DART API 문서: https://opendart.fss.or.kr/intro/main.do
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportCode(str, Enum):
    """DART 보고서 코드."""

    ANNUAL = "11011"  # 사업보고서
    HALF = "11012"  # 반기보고서
    Q1 = "11013"  # 1분기보고서
    Q3 = "11014"  # 3분기보고서


class FinancialStatementType(str, Enum):
    """재무제표 구분."""

    CONSOLIDATED = "CFS"  # 연결재무제표
    SEPARATE = "OFS"  # 별도재무제표


class DartBaseModel(BaseModel):
    """DART API 응답 기본 모델."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="ignore",  # API에서 추가 필드가 오면 무시
    )


class DartAPIResponse(DartBaseModel):
    """DART API 공통 응답 래퍼.

    모든 DART API 응답은 status와 message를 포함합니다.
    """

    status: str = Field(description="응답 상태 코드")
    message: str = Field(description="응답 메시지")

    @property
    def is_success(self) -> bool:
        """성공 응답 여부."""
        return self.status == "000"

    @property
    def is_no_data(self) -> bool:
        """데이터 없음 응답 여부."""
        return self.status == "013"


class DartSearchResult(DartBaseModel):
    """기업 검색 결과.

    DART company.json API의 개별 결과 항목.
    """

    corp_code: str = Field(description="고유번호 (8자리)")
    corp_name: str = Field(description="정식명칭")
    stock_code: str | None = Field(default=None, description="종목코드 (6자리, 비상장시 None)")
    modify_date: str = Field(description="최종변경일자 (YYYYMMDD)")

    @field_validator("stock_code", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> str | None:
        """빈 문자열을 None으로 변환."""
        if v == "" or v == " ":
            return None
        return v

    @property
    def is_listed(self) -> bool:
        """상장 여부."""
        return self.stock_code is not None


class DartCompanyInfo(DartBaseModel):
    """기업 개요 정보.

    DART company.json API의 상세 응답.
    """

    corp_code: str = Field(description="고유번호 (8자리)")
    corp_name: str = Field(description="정식명칭")
    corp_name_eng: str | None = Field(default=None, description="영문명칭")
    stock_name: str | None = Field(default=None, description="종목명")
    stock_code: str | None = Field(default=None, description="종목코드 (6자리)")
    ceo_nm: str | None = Field(default=None, description="대표이사명")
    corp_cls: str = Field(description="법인구분 (Y:유가, K:코스닥, N:코넥스, E:기타)")
    jurir_no: str | None = Field(default=None, description="법인등록번호")
    bizr_no: str | None = Field(default=None, description="사업자등록번호")
    adres: str | None = Field(default=None, description="주소")
    hm_url: str | None = Field(default=None, description="홈페이지 URL")
    ir_url: str | None = Field(default=None, description="IR 홈페이지 URL")
    phn_no: str | None = Field(default=None, description="전화번호")
    fax_no: str | None = Field(default=None, description="팩스번호")
    induty_code: str | None = Field(default=None, description="업종코드")
    est_dt: str | None = Field(default=None, description="설립일 (YYYYMMDD)")
    acc_mt: str | None = Field(default=None, description="결산월 (MM)")

    @field_validator("stock_code", "corp_name_eng", "stock_name", "hm_url", "ir_url", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> str | None:
        """빈 문자열을 None으로 변환."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def is_listed(self) -> bool:
        """상장 여부."""
        return self.stock_code is not None

    @property
    def market_type(self) -> str:
        """시장 구분 (한글)."""
        mapping = {
            "Y": "유가증권",
            "K": "코스닥",
            "N": "코넥스",
            "E": "기타",
        }
        return mapping.get(self.corp_cls, "기타")

    @property
    def establishment_date(self) -> date | None:
        """설립일 (date 객체)."""
        if self.est_dt and len(self.est_dt) == 8:
            try:
                return datetime.strptime(self.est_dt, "%Y%m%d").date()
            except ValueError:
                return None
        return None


class DartFinancialStatement(DartBaseModel):
    """단일회사 주요계정 재무제표 항목.

    DART fnlttSinglAcnt.json API의 개별 항목.
    """

    rcept_no: str = Field(description="접수번호")
    reprt_code: str = Field(description="보고서 코드 (11011:사업, 11012:반기, 11013:1분기, 11014:3분기)")
    bsns_year: str = Field(description="사업연도")
    corp_code: str = Field(description="고유번호")
    stock_code: str | None = Field(default=None, description="종목코드")
    fs_div: str = Field(description="재무제표구분 (CFS:연결, OFS:별도)")
    fs_nm: str = Field(description="재무제표명")
    sj_div: str = Field(description="재무제표항목구분")
    sj_nm: str = Field(description="재무제표항목명")
    account_id: str | None = Field(default=None, description="계정ID")
    account_nm: str = Field(description="계정명 (한글)")
    account_detail: str | None = Field(default=None, description="계정상세")
    thstrm_nm: str | None = Field(default=None, description="당기명")
    thstrm_amount: str | None = Field(default=None, description="당기금액")
    thstrm_add_amount: str | None = Field(default=None, description="당기누적금액")
    frmtrm_nm: str | None = Field(default=None, description="전기명")
    frmtrm_amount: str | None = Field(default=None, description="전기금액")
    frmtrm_q_nm: str | None = Field(default=None, description="전기분기명")
    frmtrm_q_amount: str | None = Field(default=None, description="전기분기금액")
    frmtrm_add_amount: str | None = Field(default=None, description="전기누적금액")
    bfefrmtrm_nm: str | None = Field(default=None, description="전전기명")
    bfefrmtrm_amount: str | None = Field(default=None, description="전전기금액")
    ord: str | None = Field(default=None, description="계정과목 정렬순서")
    currency: str = Field(default="KRW", description="통화")

    @field_validator(
        "thstrm_amount",
        "frmtrm_amount",
        "bfefrmtrm_amount",
        "thstrm_add_amount",
        "frmtrm_add_amount",
        "frmtrm_q_amount",
        mode="before",
    )
    @classmethod
    def clean_amount(cls, v: Any) -> str | None:
        """금액 문자열 정리 (콤마 제거 등)."""
        if v is None or v == "" or v == "-":
            return None
        if isinstance(v, str):
            return v.replace(",", "").strip()
        return str(v)

    @property
    def current_amount(self) -> Decimal | None:
        """당기 금액 (Decimal)."""
        if self.thstrm_amount:
            try:
                return Decimal(self.thstrm_amount)
            except Exception:
                return None
        return None

    @property
    def previous_amount(self) -> Decimal | None:
        """전기 금액 (Decimal)."""
        if self.frmtrm_amount:
            try:
                return Decimal(self.frmtrm_amount)
            except Exception:
                return None
        return None

    @property
    def before_previous_amount(self) -> Decimal | None:
        """전전기 금액 (Decimal)."""
        if self.bfefrmtrm_amount:
            try:
                return Decimal(self.bfefrmtrm_amount)
            except Exception:
                return None
        return None

    @property
    def is_consolidated(self) -> bool:
        """연결재무제표 여부."""
        return self.fs_div == "CFS"


class DartMajorShareholder(DartBaseModel):
    """주요주주 정보.

    DART majorstock.json API의 개별 항목.
    """

    rcept_no: str = Field(description="접수번호")
    rcept_dt: str = Field(description="접수일자")
    corp_code: str = Field(description="고유번호")
    corp_name: str = Field(description="법인명")
    report_tp: str = Field(description="보고구분")
    repror: str = Field(description="보고자")
    stkqy: str | None = Field(default=None, description="보유주식수")
    stkqy_irds: str | None = Field(default=None, description="증감")
    stkrt: str | None = Field(default=None, description="지분율")
    stkrt_irds: str | None = Field(default=None, description="지분율 증감")
    ctr_stkqy: str | None = Field(default=None, description="주요체결 주식수")
    ctr_stkrt: str | None = Field(default=None, description="주요체결 지분율")
    report_resn: str | None = Field(default=None, description="보고사유")

    @field_validator("stkqy", "stkrt", "stkqy_irds", "stkrt_irds", mode="before")
    @classmethod
    def clean_numeric(cls, v: Any) -> str | None:
        """숫자 문자열 정리."""
        if v is None or v == "" or v == "-":
            return None
        if isinstance(v, str):
            return v.replace(",", "").strip()
        return str(v)

    @property
    def share_count(self) -> int | None:
        """보유주식수 (int)."""
        if self.stkqy:
            try:
                return int(self.stkqy)
            except ValueError:
                return None
        return None

    @property
    def share_ratio(self) -> Decimal | None:
        """지분율 (Decimal, %)."""
        if self.stkrt:
            try:
                return Decimal(self.stkrt)
            except Exception:
                return None
        return None


class DartDividend(DartBaseModel):
    """배당 정보.

    DART alotMatter.json API 응답.
    """

    rcept_no: str = Field(description="접수번호")
    corp_cls: str = Field(description="법인구분")
    corp_code: str = Field(description="고유번호")
    corp_name: str = Field(description="법인명")
    se: str = Field(description="구분 (주당배당금, 시가배당율 등)")
    stock_knd: str = Field(description="주식종류")
    thstrm: str | None = Field(default=None, description="당기")
    frmtrm: str | None = Field(default=None, description="전기")
    lwfr: str | None = Field(default=None, description="전전기")


class FinancialStatementsCollection(DartBaseModel):
    """재무제표 항목 컬렉션.

    여러 회계연도의 재무제표를 담는 컨테이너.
    """

    corp_code: str
    items: list[DartFinancialStatement] = Field(default_factory=list)

    def filter_by_year(self, year: str) -> list[DartFinancialStatement]:
        """특정 연도의 항목만 필터링."""
        return [item for item in self.items if item.bsns_year == year]

    def filter_by_account(self, account_nm: str) -> list[DartFinancialStatement]:
        """특정 계정명의 항목만 필터링."""
        return [item for item in self.items if item.account_nm == account_nm]

    def filter_consolidated(self) -> list[DartFinancialStatement]:
        """연결재무제표 항목만 필터링."""
        return [item for item in self.items if item.is_consolidated]

    def filter_separate(self) -> list[DartFinancialStatement]:
        """별도재무제표 항목만 필터링."""
        return [item for item in self.items if not item.is_consolidated]

    def get_account_values(
        self,
        account_nm: str,
        consolidated: bool = True,
    ) -> dict[str, Decimal | None]:
        """특정 계정의 연도별 값 반환.

        Args:
            account_nm: 계정명
            consolidated: 연결재무제표 여부

        Returns:
            {연도: 금액} 딕셔너리
        """
        result: dict[str, Decimal | None] = {}
        for item in self.items:
            if item.account_nm == account_nm and item.is_consolidated == consolidated:
                if item.bsns_year not in result:
                    result[item.bsns_year] = item.current_amount
        return result

    @property
    def years(self) -> list[str]:
        """포함된 회계연도 목록 (정렬됨)."""
        return sorted(set(item.bsns_year for item in self.items))

    @property
    def account_names(self) -> list[str]:
        """포함된 계정명 목록."""
        return list(set(item.account_nm for item in self.items))


# Type aliases for better readability
CorpCode = Annotated[str, Field(min_length=8, max_length=8, pattern=r"^\d{8}$")]
StockCode = Annotated[str, Field(min_length=6, max_length=6, pattern=r"^\d{6}$")]
