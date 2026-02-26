"""LDD 체크리스트 리뷰 서비스 — 항목별 승인/반려 + VDR 참조 관리."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError, WorkflowError
from app.models.enums import LDDReportStatus
from app.models.ldd_report import LDDReport
from app.models.ldd_vdr_reference import LddVdrReference
from app.schemas.ldd_report import (
    LDDBulkReview,
    LDDItemReview,
    LDDReviewProgress,
    LddVdrReferenceCreate,
)

logger = logging.getLogger(__name__)


class LDDReviewService:
    """LDD 체크리스트 항목별 리뷰 + VDR 참조 관리."""

    async def review_item(
        self,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        report_id: uuid.UUID,
        review: LDDItemReview,
    ) -> dict:
        """개별 항목 리뷰 (승인/반려/코멘트/status 수정)."""
        report = await self._get_review_report(db, transaction_id, report_id)
        sections = report.sections or []
        updated = False

        for section in sections:
            for item in section.get("items", []):
                if item.get("item_id") == review.item_id:
                    item["user_approved"] = review.user_approved
                    item["user_comment"] = review.user_comment

                    if review.user_override_status:
                        item["user_override_status"] = review.user_override_status
                    if review.user_override_level:
                        item["user_override_level"] = review.user_override_level

                    updated = True
                    break
            if updated:
                break

        if not updated:
            raise DocumentNotFoundError(f"항목 '{review.item_id}'를 찾을 수 없습니다.")

        # risk_color 재계산 + counts 갱신 (user_override_status가 있는 경우)
        from app.services.ldd_report_service import _compute_counts, _compute_risk_colors

        report.sections = _compute_risk_colors(sections)
        if review.user_override_status:
            counts = _compute_counts(sections)
            for k, v in counts.items():
                setattr(report, k, v)
        await db.commit()
        await db.refresh(report)

        return {"item_id": review.item_id, "status": "reviewed"}

    async def bulk_review(
        self,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        report_id: uuid.UUID,
        body: LDDBulkReview,
    ) -> dict:
        """여러 항목 일괄 리뷰."""
        report = await self._get_review_report(db, transaction_id, report_id)
        sections = report.sections or []

        # item_id → review 매핑
        review_map = {r.item_id: r for r in body.items}
        applied = 0

        for section in sections:
            for item in section.get("items", []):
                item_id = item.get("item_id", "")
                if item_id in review_map:
                    r = review_map[item_id]
                    item["user_approved"] = r.user_approved
                    item["user_comment"] = r.user_comment
                    if r.user_override_status:
                        item["user_override_status"] = r.user_override_status
                    if r.user_override_level:
                        item["user_override_level"] = r.user_override_level
                    applied += 1

        from app.services.ldd_report_service import _compute_counts, _compute_risk_colors

        report.sections = _compute_risk_colors(sections)
        # override_status가 하나라도 있으면 counts 재계산
        has_override = any(r.user_override_status for r in body.items)
        if has_override:
            counts = _compute_counts(sections)
            for k, v in counts.items():
                setattr(report, k, v)
        await db.commit()
        await db.refresh(report)

        return {"applied": applied, "requested": len(body.items)}

    async def get_review_progress(
        self,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> LDDReviewProgress:
        """리뷰 진행률 반환."""
        report = await self._get_report(db, transaction_id, report_id)
        sections = report.sections or []

        total = approved = rejected = pending = 0
        for section in sections:
            for item in section.get("items", []):
                total += 1
                ua = item.get("user_approved")
                if ua is True:
                    approved += 1
                elif ua is False:
                    rejected += 1
                else:
                    pending += 1

        return LDDReviewProgress(
            total=total,
            approved=approved,
            rejected=rejected,
            pending=pending,
            progress_pct=round((approved + rejected) / max(total, 1) * 100, 1),
        )

    # ── VDR 참조 관리 ────────────────────────────────────────

    async def list_references(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
    ) -> list[LddVdrReference]:
        """보고서의 VDR 참조 목록 반환."""
        stmt = (
            select(LddVdrReference)
            .where(LddVdrReference.ldd_report_id == report_id)
            .order_by(LddVdrReference.item_id, LddVdrReference.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def add_reference(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        body: LddVdrReferenceCreate,
    ) -> LddVdrReference:
        """VDR 참조 수동 추가."""
        # 해당 item의 section_type 찾기
        report = await self._get_report_by_id(db, report_id)
        section_type = self._find_section_type(report, body.item_id)

        ref = LddVdrReference(
            ldd_report_id=report_id,
            item_id=body.item_id,
            vdr_document_id=body.vdr_document_id,
            section_type=section_type,
            relevance_score=1.0,  # 사용자 수동 추가 = 최대 관련도
            evidence_snippet=body.evidence_snippet,
            page_reference=body.page_reference,
            is_user_confirmed=True,
        )
        db.add(ref)
        await db.commit()
        await db.refresh(ref)
        return ref

    async def remove_reference(
        self,
        db: AsyncSession,
        reference_id: uuid.UUID,
    ) -> None:
        """VDR 참조 삭제."""
        stmt = select(LddVdrReference).where(LddVdrReference.id == reference_id)
        result = await db.execute(stmt)
        ref = result.scalar_one_or_none()
        if not ref:
            raise DocumentNotFoundError("VDR 참조를 찾을 수 없습니다.")
        await db.delete(ref)
        await db.commit()

    # ── 내부 헬퍼 ────────────────────────────────────────────

    async def _get_review_report(
        self,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> LDDReport:
        """REVIEW 상태 보고서 조회 (상태 검증 포함)."""
        report = await self._get_report(db, transaction_id, report_id)
        if report.status != LDDReportStatus.REVIEW:
            raise WorkflowError(f"리뷰는 REVIEW 상태에서만 가능합니다 (현재: {report.status})")
        return report

    async def _get_report(
        self,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> LDDReport:
        """보고서 조회."""
        stmt = select(LDDReport).where(
            LDDReport.id == report_id,
            LDDReport.transaction_id == transaction_id,
        )
        result = await db.execute(stmt)
        report = result.scalar_one_or_none()
        if not report:
            raise DocumentNotFoundError("LDD 보고서를 찾을 수 없습니다.")
        return report

    async def _get_report_by_id(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
    ) -> LDDReport:
        """보고서 ID로만 조회."""
        stmt = select(LDDReport).where(LDDReport.id == report_id)
        result = await db.execute(stmt)
        report = result.scalar_one_or_none()
        if not report:
            raise DocumentNotFoundError("LDD 보고서를 찾을 수 없습니다.")
        return report

    def _find_section_type(self, report: LDDReport, item_id: str) -> str:
        """item_id가 속한 section_type을 찾는다."""
        for section in report.sections or []:
            for item in section.get("items", []):
                if item.get("item_id") == item_id:
                    return section.get("section_type", "UNKNOWN")
        return "UNKNOWN"
