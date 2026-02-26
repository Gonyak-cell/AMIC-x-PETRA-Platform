"""재무모델 API 라우터 — 모델 CRUD + 체크리스트 CRUD + 생성/다운로드."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.enums import FinancialModelStatus
from app.schemas.financial_model import (
    FinancialModelCreate,
    FinancialModelOut,
    FMChecklistBulkUpdate,
    FMChecklistFinalizeRequest,
    FMChecklistItemOut,
    FMChecklistItemUpdate,
    FMChecklistOut,
)
from app.services import financial_model_service as fm_svc
from app.services.fm_checklist_service import FMChecklistService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions/{txn_id}/financial-models",
    tags=["Financial Models"],
)


# ── 모델 CRUD ────────────────────────────────────────────────────────────


@router.get("", response_model=list[FinancialModelOut])
async def list_models(
    txn_id: UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    return await fm_svc.list_financial_models(db, txn_id)


@router.post("", response_model=FinancialModelOut, status_code=status.HTTP_201_CREATED)
async def create_model(
    txn_id: UUID,
    body: FinancialModelCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    return await fm_svc.create_financial_model(db, txn_id, body, claims.email or "unknown")


@router.get("/{fm_id}", response_model=FinancialModelOut)
async def get_model(
    txn_id: UUID,
    fm_id: UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    return await fm_svc.get_financial_model(db, fm_id, txn_id)


@router.post("/{fm_id}/regenerate", response_model=FinancialModelOut)
async def regenerate_model(
    txn_id: UUID,
    fm_id: UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    return await fm_svc.regenerate_financial_model(db, fm_id, txn_id)


@router.delete("/{fm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    txn_id: UUID,
    fm_id: UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await fm_svc.delete_financial_model(db, fm_id, txn_id)


@router.get("/{fm_id}/download")
async def download_model(
    txn_id: UUID,
    fm_id: UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    fm = await fm_svc.get_financial_model(db, fm_id, txn_id)
    if fm.status != FinancialModelStatus.READY or not fm.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial model file not ready for download",
        )
    # 경로 순회(path traversal) 방지
    allowed_dir = fm_svc.FM_OUTPUT_DIR.resolve()
    file_path = Path(fm.file_path).resolve()
    if not str(file_path).startswith(str(allowed_dir)):
        logger.warning("Path traversal attempt: %s (allowed: %s)", file_path, allowed_dir)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path",
        )
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated file not found on disk",
        )
    return FileResponse(
        path=str(file_path),
        filename=fm.file_name or f"{fm.title}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── 체크리스트 ────────────────────────────────────────────────────────────


@router.get("/{fm_id}/checklist", response_model=FMChecklistOut)
async def get_checklist(
    txn_id: UUID,
    fm_id: UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await fm_svc.get_financial_model(db, fm_id, txn_id)
    svc = FMChecklistService(db)
    checklist = await svc.get_checklist(fm_id)
    summary = svc.compute_summary(checklist)
    out = FMChecklistOut.model_validate(checklist)
    out.total_items = summary["total_items"]
    out.confirmed_count = summary["confirmed_count"]
    out.corrected_count = summary["corrected_count"]
    out.flagged_count = summary["flagged_count"]
    out.pending_count = summary["pending_count"]
    out.not_applicable_count = summary["not_applicable_count"]
    return out


@router.put("/{fm_id}/checklist/items/{item_id}", response_model=FMChecklistItemOut)
async def update_checklist_item(
    txn_id: UUID,
    fm_id: UUID,
    item_id: UUID,
    body: FMChecklistItemUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await fm_svc.get_financial_model(db, fm_id, txn_id)
    svc = FMChecklistService(db)
    item = await svc.update_item(item_id, body, claims.email or "unknown")
    await db.commit()
    return item


@router.put("/{fm_id}/checklist/{cl_id}/bulk-update", response_model=list[FMChecklistItemOut])
async def bulk_update_checklist_items(
    txn_id: UUID,
    fm_id: UUID,
    cl_id: UUID,
    body: FMChecklistBulkUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await fm_svc.get_financial_model(db, fm_id, txn_id)
    svc = FMChecklistService(db)
    items = await svc.bulk_update_items(cl_id, body.items, claims.email or "unknown")
    await db.commit()
    return items


@router.post("/{fm_id}/checklist/{cl_id}/finalize", response_model=FMChecklistOut)
async def finalize_checklist(
    txn_id: UUID,
    fm_id: UUID,
    cl_id: UUID,
    body: FMChecklistFinalizeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    fm = await fm_svc.get_financial_model(db, fm_id, txn_id)

    # 상태 가드: GENERATING/FINALIZING 중이면 거부
    if fm.status in (FinancialModelStatus.GENERATING, FinancialModelStatus.FINALIZING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot finalize: model is currently {fm.status.value}",
        )

    svc = FMChecklistService(db)
    actor = claims.email or "unknown"
    checklist = await svc.finalize_checklist(cl_id, actor, notes=body.notes if body else None)

    # Finalize + FM 상태 변경을 단일 트랜잭션으로 커밋
    fm.status = FinancialModelStatus.FINALIZING
    await db.commit()

    from app.tasks.fm_tasks import run_finalize_and_generate_task

    run_finalize_and_generate_task.delay(
        fm_id=str(fm.id),
        transaction_id=str(txn_id),
    )

    summary = svc.compute_summary(checklist)
    out = FMChecklistOut.model_validate(checklist)
    out.total_items = summary["total_items"]
    out.confirmed_count = summary["confirmed_count"]
    out.corrected_count = summary["corrected_count"]
    out.flagged_count = summary["flagged_count"]
    out.pending_count = summary["pending_count"]
    out.not_applicable_count = summary["not_applicable_count"]
    return out
