"""전자공시 Deep Link 모델

DART/KOFIA 전자공시 원문에 대한 Deep Link URL을 관리한다.
"""

from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DisclosureType(StrEnum):
    """공시 유형"""

    ANNUAL_REPORT = "annual_report"  # 사업보고서
    AUDIT_REPORT = "audit_report"  # 감사보고서
    QUARTERLY = "quarterly"  # 분기보고서
    SEMI_ANNUAL = "semi_annual"  # 반기보고서
    MATERIAL = "material"  # 주요사항보고서
    SANCTION = "sanction"  # 제재/조치
    OTHER = "other"  # 기타


class Disclosure(TimestampMixin, Base):
    """전자공시 Deep Link 모델"""

    __tablename__ = "disclosures"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 기업 정보
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="기업 ID",
    )
    corp_code: Mapped[str] = mapped_column(String(20), index=True, comment="DART 고유번호")
    corp_name: Mapped[str | None] = mapped_column(String(300), comment="종목명")
    corp_cls: Mapped[str | None] = mapped_column(String(5), comment="법인구분")

    # 공시 정보
    report_nm: Mapped[str] = mapped_column(String(500), index=True, comment="보고서명")
    rcept_no: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="접수번호")
    rcept_dt: Mapped[str | None] = mapped_column(String(10), comment="접수일자 (YYYYMMDD)")
    flr_nm: Mapped[str | None] = mapped_column(String(200), comment="공시 제출인명")
    rm: Mapped[str | None] = mapped_column(Text, comment="비고")

    # Deep Link URL
    dart_viewer_url: Mapped[str] = mapped_column(String(500), comment="DART 뷰어 URL")
    dart_pdf_url: Mapped[str | None] = mapped_column(String(500), comment="DART PDF 다운로드 URL")

    # 분류
    disclosure_type: Mapped[str | None] = mapped_column(
        String(50), index=True, comment="공시 유형 (annual_report/audit_report/...)"
    )

    # KOFIA 연동
    kofia_url: Mapped[str | None] = mapped_column(String(500), comment="KOFIA 공시 원문 URL")

    # 출처
    source: Mapped[str] = mapped_column(String(20), default="dart", comment="데이터 출처 (dart/kofia)")

    # 관계
    company: Mapped["Company | None"] = relationship()  # noqa: F821
