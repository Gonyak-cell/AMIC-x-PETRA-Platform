"""DART 임원·주요주주 소유보고 모델

임원·주요주주 소유보고(elestock.json) 데이터를 저장하고
임원/주요주주 지분 변동 딜 신호 자동 생성에 활용한다.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DartExecutiveHolding(TimestampMixin, Base):
    """DART 임원·주요주주 소유보고 레코드"""

    __tablename__ = "dart_executive_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # DART API 원본 필드
    rcept_no: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="접수번호 (중복 방지 키)")
    rcept_dt: Mapped[str] = mapped_column(String(10), index=True, comment="접수일자 (YYYYMMDD)")
    corp_code: Mapped[str] = mapped_column(String(20), index=True, comment="대상 기업 DART 고유번호")
    corp_name: Mapped[str] = mapped_column(String(300), comment="법인명")
    repror: Mapped[str] = mapped_column(String(300), index=True, comment="보고자명")

    # 임원/주요주주 구분
    isu_exctv_rgist_at: Mapped[str | None] = mapped_column(String(5), comment="임원 등록 여부 (Y/N)")
    isu_exctv_ofcps: Mapped[str | None] = mapped_column(String(100), comment="직책 (대표이사, 사외이사 등)")
    isu_main_shrholdr: Mapped[str | None] = mapped_column(String(5), comment="주요주주 여부 (Y/N)")

    # 주식 보유 현황
    sp_stock_lmp_cnt: Mapped[str | None] = mapped_column(String(50), comment="소유 주식수")
    sp_stock_lmp_irds_cnt: Mapped[str | None] = mapped_column(String(50), comment="소유 주식수 증감")
    sp_stock_lmp_rate: Mapped[str | None] = mapped_column(String(20), comment="소유 비율 (%)")
    sp_stock_lmp_irds_rate: Mapped[str | None] = mapped_column(String(20), comment="소유 비율 증감")
    ctr_stkqy: Mapped[str | None] = mapped_column(String(50), comment="특정증권등 소유 주식수")
    ctr_stkrt: Mapped[str | None] = mapped_column(String(20), comment="특정증권등 소유 비율")
    report_resn: Mapped[str | None] = mapped_column(String(200), comment="변동사유")

    # FK
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="대상 기업 ID",
    )
    reporter_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="보고자 소속 기업 ID",
    )
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"),
        index=True,
        comment="생성된 딜 ID",
    )
    disclosure_id: Mapped[int | None] = mapped_column(
        ForeignKey("disclosures.id", ondelete="SET NULL"),
        index=True,
        comment="원문 공시 ID (감사추적)",
    )

    # 관계
    company: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[company_id],
    )
    reporter_company: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[reporter_company_id],
    )
    deal: Mapped["Deal | None"] = relationship(  # noqa: F821
        foreign_keys=[deal_id],
    )
    disclosure: Mapped["Disclosure | None"] = relationship(  # noqa: F821
        foreign_keys=[disclosure_id],
    )
