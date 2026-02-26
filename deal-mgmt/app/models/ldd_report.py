"""LDD(법률실사) 보고서 모델 — DDRL 체크리스트 기반 .docx 생성 및 관리."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import LDDReportStatus, LDDReportType


class LDDReport(Base, TimestampMixin):
    """거래에 귀속되는 법률실사(LDD) 보고서.

    DDRL 10개 섹션 체크리스트를 sections JSONB에 저장하고,
    docxtpl로 FULL 또는 REDFLAG 형식의 .docx 보고서를 자동 생성한다.

    Ralph Loop 2회 적용 워크플로우:
    1. Ralph Loop #1 (ANALYZING): VDR 문서 → 초안 분석
    2. 사용자 체크리스트 검수 (REVIEW)
    3. Ralph Loop #2 (FINALIZING): 피드백 반영 최종 Refine
    """

    __tablename__ = "ldd_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[LDDReportType] = mapped_column(
        Enum(LDDReportType), nullable=False, default=LDDReportType.FULL
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[LDDReportStatus] = mapped_column(
        Enum(LDDReportStatus), nullable=False, default=LDDReportStatus.DRAFT
    )

    # 거래유형별 템플릿
    deal_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True,
        comment="거래유형 (STOCK_ACQUISITION, REAL_ESTATE, IPO 등)",
    )
    template_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="적용된 템플릿 식별자 (deal_type과 동일하거나 커스텀)",
    )

    # 대상 회사 정보
    target_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dd_period: Mapped[str | None] = mapped_column(String(100), nullable=True)   # 예: "2026-02-01 ~ 2026-02-28"
    law_firm: Mapped[str | None] = mapped_column(String(200), nullable=True)    # 법무법인 명칭
    prepared_by: Mapped[str | None] = mapped_column(String(200), nullable=True) # 담당 변호사

    # 체크리스트 데이터 (10개 섹션, JSONB)
    sections: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 집계 카운트 (자동 계산)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    red_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # CRITICAL → Red
    amber_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # HIGH+MEDIUM → Amber
    green_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # LOW → Green
    ok_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    na_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rfi_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # RFI 요청 항목 수

    # 파일 정보
    template_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── VDR 연동 + Ralph Loop 2회 적용 ─────────────────────
    vdr_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    draft_ralph_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ralph_sessions.id", ondelete="SET NULL"), nullable=True
    )
    final_ralph_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ralph_sessions.id", ondelete="SET NULL"), nullable=True
    )
    draft_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 6블록 서술(Narrative) 데이터 ─────────────────────
    narrative_sections: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="6블록 서술 결과 (section_type → [NarrativeResult])",
    )

    # ── 법률 인용 검증 결과 ───────────────────────────────
    legal_citations: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="법률 인용 검증 결과 (section_type → citation_verification)",
    )

    # ── 별첨(Appendix) 데이터 ──────────────────────────────
    appendices: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="별첨 테이블 데이터 (6종: 소송/IP/부동산/계약/보험/인허가)",
    )

    # ── 법무법인 스타일 (LAW_FIRM) ────────────────────────
    law_firm_toc: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="법무법인 8개 목차 구조 (I~VIII 매핑 결과)",
    )
    law_firm_sections: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="법무법인 3단 서술 결과 (section → {현황/검토/Recommendation})",
    )
    irl_items: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment="D 라벨 수집: Information Request List 항목",
    )

    # ── 멀티 LLM 파이프라인 결과 ─────────────────────────
    dual_risk_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    gap_detection: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    jurisdiction_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    qa_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pipeline_stages: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 워크플로우 타임스탬프
    analysis_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalize_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalize_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
