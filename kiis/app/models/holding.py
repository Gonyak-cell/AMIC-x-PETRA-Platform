"""DART 대량보유상황보고서 모델

주식등의대량보유상황보고서(majorstock.json) 데이터를 저장하고
GP 딜 신호 자동 생성에 활용한다.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DartMajorHolding(TimestampMixin, Base):
    """DART 대량보유상황보고서 레코드"""

    __tablename__ = "dart_major_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # DART API 원본 필드
    rcept_no: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="접수번호 (중복 방지 키)")
    rcept_dt: Mapped[str] = mapped_column(String(10), index=True, comment="접수일자 (YYYYMMDD)")
    corp_code: Mapped[str] = mapped_column(String(20), index=True, comment="피보유 기업 DART 고유번호")
    corp_name: Mapped[str] = mapped_column(String(300), comment="피보유 기업명")
    report_tp: Mapped[str | None] = mapped_column(String(20), comment="보고구분 (신규/변경/종료)")
    repror: Mapped[str] = mapped_column(String(300), index=True, comment="대표보고자명")
    stkqy: Mapped[str | None] = mapped_column(String(50), comment="보유주식수")
    stkrt: Mapped[str | None] = mapped_column(String(20), comment="보유비율 (%)")
    stkqy_irds: Mapped[str | None] = mapped_column(String(50), comment="보유주식수 증감")
    stkrt_irds: Mapped[str | None] = mapped_column(String(20), comment="보유비율 증감")
    ctr_stkqy: Mapped[str | None] = mapped_column(String(50), comment="주요체결 주식수")
    ctr_stkrt: Mapped[str | None] = mapped_column(String(20), comment="주요체결 지분율")
    report_resn: Mapped[str | None] = mapped_column(String(200), comment="보고사유")

    # FK — entity resolution 매칭 결과
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="피보유 기업 ID",
    )
    reporter_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="보고자(GP) 기업 ID",
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
