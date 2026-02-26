"""LDD(법률실사) 보고서 라우터 — CRUD + 다운로드."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DocumentNotReadyError
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import LDDReportStatus
from app.models.transaction import Transaction
from app.schemas.ldd_report import (
    DEFAULT_LDD_SECTIONS,
    LDDBulkReview,
    LDDFinalizeRequest,
    LDDItemReview,
    LDDReportCreate,
    LDDReportCreateAuto,
    LDDReportCreateFromVdr,
    LDDReportOut,
    LDDReviewProgress,
    LDDSectionsUpdate,
    LddVdrReferenceCreate,
    LddVdrReferenceOut,
)
from app.services import ldd_report_service, transaction_service
from app.services.ldd_review_service import LDDReviewService

router = APIRouter(prefix="/transactions/{txn_id}/ldd-reports", tags=["LDD Reports"])

# Path Traversal 방어: 생성 파일은 반드시 이 디렉터리 내에 위치해야 한다
_SAFE_OUTPUT_DIR = (Path(__file__).resolve().parent.parent.parent / "generated" / "ldd").resolve()


async def _get_and_authorize_txn(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
) -> Transaction:
    txn = await transaction_service.get_transaction(db, txn_id)
    # CLIENT 역할: deal_clients 테이블 기반 접근 제어
    if claims.role == "CLIENT":
        await check_client_deal_access(db, txn_id, claims)
        return txn
    if (
        claims.role != "ADMIN"
        and claims.email is not None
        and txn.lead_advisor_email != claims.email
        and txn.deal_captain_email != claims.email
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 거래에 접근할 권한이 없습니다",
        )
    return txn


# ── 기본 섹션 구조 (독립 엔드포인트) ─────────────────────────────────────────

_default_sections_router = APIRouter(tags=["LDD Reports"])


@_default_sections_router.get("/ldd-reports")
async def list_all_ldd_reports(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """모든 거래의 LDD 보고서 목록을 반환한다."""
    return [LDDReportOut.model_validate(r) for r in await ldd_report_service.list_all_ldd_reports(db)]


@_default_sections_router.get("/ldd-reports/default-sections")
async def get_default_sections():
    """기본 DDRL 10개 섹션 구조를 반환한다 (인증 불필요)."""
    return {"sections": DEFAULT_LDD_SECTIONS}


# ── CRUD 엔드포인트 ───────────────────────────────────────────────────────────


@router.get("", response_model=list[LDDReportOut])
async def list_ldd_reports(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """거래에 속한 LDD 보고서 목록을 반환한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    return [LDDReportOut.model_validate(r) for r in await ldd_report_service.list_ldd_reports(db, txn_id)]


@router.post("", response_model=LDDReportOut, status_code=status.HTTP_201_CREATED)
async def create_ldd_report(
    txn_id: uuid.UUID,
    body: LDDReportCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """LDD 보고서를 생성하고 즉시 .docx를 렌더링한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.create_ldd_report(
        db,
        transaction_id=txn_id,
        body=body,
        created_by_email=claims.email,
    )
    return LDDReportOut.model_validate(report)


@router.post("/auto", response_model=LDDReportOut, status_code=status.HTTP_202_ACCEPTED)
async def create_ldd_report_auto(
    txn_id: uuid.UUID,
    body: LDDReportCreateAuto,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """Ralph Loop 기반 LDD 보고서 자동 생성 (실사자료 → AI 분석 → DOCX)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.create_ldd_report_auto(
        db,
        transaction_id=txn_id,
        body=body,
        created_by_email=claims.email,
    )
    return LDDReportOut.model_validate(report)


@router.get("/{report_id}", response_model=LDDReportOut)
async def get_ldd_report(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """LDD 보고서 단건 조회."""
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.get_ldd_report(db, txn_id, report_id)
    return LDDReportOut.model_validate(report)


@router.put("/{report_id}/sections", response_model=LDDReportOut)
async def update_ldd_sections(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LDDSectionsUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """체크리스트 섹션을 업데이트하고 보고서를 재렌더링한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.update_ldd_sections(db, txn_id, report_id, body)
    return LDDReportOut.model_validate(report)


@router.post("/{report_id}/regenerate", response_model=LDDReportOut)
async def regenerate_ldd_report(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """기존 섹션 데이터로 보고서를 재렌더링한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.regenerate_ldd_report(db, txn_id, report_id)
    return LDDReportOut.model_validate(report)


@router.get("/{report_id}/download")
async def download_ldd_report(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """생성된 .docx 파일을 다운로드한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.get_ldd_report(db, txn_id, report_id)

    if report.status != LDDReportStatus.READY:
        raise DocumentNotReadyError(report.status.value if hasattr(report.status, "value") else str(report.status))

    if not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일 경로가 없습니다. 보고서를 재생성해 주세요.",
        )

    # Path Traversal 방어
    file_path = Path(report.file_path).resolve()
    if not str(file_path).startswith(str(_SAFE_OUTPUT_DIR)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 파일 경로입니다.",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일을 찾을 수 없습니다. 보고서를 재생성해 주세요.",
        )

    return FileResponse(
        path=str(file_path),
        filename=report.file_name or f"LDD_{report.id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ldd_report(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """LDD 보고서를 삭제한다 (.docx 파일 포함)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    await ldd_report_service.delete_ldd_report(db, txn_id, report_id)


# ── VDR 기반 워크플로우 ──────────────────────────────────────────────────────

_review_service = LDDReviewService()


@router.post("/from-vdr", response_model=LDDReportOut, status_code=status.HTTP_202_ACCEPTED)
async def create_ldd_report_from_vdr(
    txn_id: uuid.UUID,
    body: LDDReportCreateFromVdr,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """Ralph Loop #1: VDR 문서 기반 초안 보고서 생성.

    VDR에 업로드된 문서를 분석 소스로 활용하여
    AI가 초안 보고서를 생성한다 (Ralph Loop로 품질 최대화).
    완료 후 REVIEW 상태로 전환된다.
    """
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.create_ldd_report_from_vdr(
        db,
        transaction_id=txn_id,
        body=body,
        created_by_email=claims.email,
    )
    return LDDReportOut.model_validate(report)


@router.get("/{report_id}/review-progress", response_model=LDDReviewProgress)
async def get_review_progress(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """체크리스트 리뷰 진행률을 반환한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    return await _review_service.get_review_progress(db, txn_id, report_id)


@router.put("/{report_id}/items/{item_id}/review")
async def review_item(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    item_id: str,
    body: LDDItemReview,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """개별 체크리스트 항목을 리뷰한다 (승인/반려/코멘트)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    # URL path의 item_id가 body와 일치하는지 확인
    if body.item_id != item_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"URL item_id '{item_id}'와 body item_id '{body.item_id}'가 불일치합니다",
        )
    return await _review_service.review_item(db, txn_id, report_id, body)


@router.put("/{report_id}/items/bulk-review")
async def bulk_review_items(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LDDBulkReview,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """여러 체크리스트 항목을 일괄 리뷰한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    return await _review_service.bulk_review(db, txn_id, report_id, body)


@router.post("/{report_id}/finalize", response_model=LDDReportOut, status_code=status.HTTP_202_ACCEPTED)
async def finalize_ldd_report(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LDDFinalizeRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """Ralph Loop #2: 사용자 피드백 반영 최종 보고서 생성.

    사용자가 리뷰한 체크리스트 피드백을 반영하여
    AI가 최종 보고서를 Refine한다 (Ralph Loop으로 품질 최대화).
    완료 후 DOCX 렌더링 → READY 상태로 전환된다.
    """
    await _get_and_authorize_txn(db, txn_id, claims)
    report = await ldd_report_service.finalize_ldd_report(
        db,
        transaction_id=txn_id,
        report_id=report_id,
        body=body,
    )
    return LDDReportOut.model_validate(report)


@router.get("/{report_id}/references", response_model=list[LddVdrReferenceOut])
async def list_vdr_references(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """LDD 보고서의 VDR 소스 문서 참조 목록을 반환한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    refs = await _review_service.list_references(db, report_id)
    return [LddVdrReferenceOut.model_validate(r) for r in refs]


@router.post(
    "/{report_id}/references",
    response_model=LddVdrReferenceOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_vdr_reference(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    body: LddVdrReferenceCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR 소스 문서 참조를 수동으로 추가한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    ref = await _review_service.add_reference(db, report_id, body)
    return LddVdrReferenceOut.model_validate(ref)


@router.delete("/{report_id}/references/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_vdr_reference(
    txn_id: uuid.UUID,
    report_id: uuid.UUID,
    ref_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR 소스 문서 참조를 삭제한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    await _review_service.remove_reference(db, ref_id)
