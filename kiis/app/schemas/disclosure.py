"""전자공시 Deep Link 스키마"""

from pydantic import BaseModel, ConfigDict, Field


class DisclosureDeepLinkItem(BaseModel):
    """공시 Deep Link 상세 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str | None = Field(None, description="종목명")
    report_nm: str = Field(..., description="보고서명")
    rcept_no: str = Field(..., description="접수번호")
    rcept_dt: str | None = Field(None, description="접수일자 (YYYYMMDD)")
    flr_nm: str | None = Field(None, description="공시 제출인명")
    dart_viewer_url: str = Field(..., description="DART 뷰어 URL")
    dart_pdf_url: str | None = Field(None, description="DART PDF 다운로드 URL")
    disclosure_type: str | None = Field(None, description="공시 유형")
    source: str = Field("dart", description="데이터 출처")


class DisclosureListItem(BaseModel):
    """공시 목록 아이템 (간략)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_nm: str = Field(..., description="보고서명")
    rcept_no: str = Field(..., description="접수번호")
    rcept_dt: str | None = Field(None, description="접수일자")
    disclosure_type: str | None = Field(None, description="공시 유형")
    dart_viewer_url: str = Field(..., description="DART 뷰어 URL")
    kofia_url: str | None = Field(None, description="KOFIA 공시 원문 URL")
    source: str = Field("dart", description="데이터 출처 (dart/kofia)")


class DisclosureListResponse(BaseModel):
    """공시 목록 응답 (페이지네이션)"""

    total: int = Field(..., description="총 건수")
    page: int = Field(..., description="페이지 번호")
    size: int = Field(..., description="페이지 크기")
    items: list[DisclosureListItem] = Field(default_factory=list, description="공시 목록")


class DisclosureSyncResponse(BaseModel):
    """공시 동기화 결과"""

    corp_code: str | None = Field(None, description="DART 고유번호")
    fund_code: str | None = Field(None, description="펀드 코드 (KOFIA)")
    source: str = Field("dart", description="데이터 출처 (dart/kofia)")
    synced_count: int = Field(..., description="신규 동기화 건수")
    skipped_count: int = Field(..., description="스킵(중복) 건수")


class DeepLinkResponse(BaseModel):
    """단일 Deep Link 응답"""

    rcept_no: str = Field(..., description="접수번호")
    dart_viewer_url: str = Field(..., description="DART 뷰어 URL")
    dart_pdf_url: str | None = Field(None, description="DART PDF 다운로드 URL")
    kofia_url: str | None = Field(None, description="KOFIA 공시 원문 URL")
    report_nm: str = Field(..., description="보고서명")
    source: str = Field("dart", description="데이터 출처 (dart/kofia)")
