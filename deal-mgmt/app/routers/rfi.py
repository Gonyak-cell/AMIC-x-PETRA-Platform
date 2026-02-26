"""RFI (Request for Information) API 라우터."""

from __future__ import annotations

import re
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.schemas.rfi import (
    RFIAutoGenerateFromDDRequest,
    RFIAutoGenerateResult,
    RFIChecklistMappingOut,
    RFICreate,
    RFIDetailOut,
    RFIExcelImportResult,
    RFIExtendDeadlineInput,
    RFIItemBatchCreate,
    RFIItemCreate,
    RFIItemOut,
    RFIItemRespondInput,
    RFIItemReviewInput,
    RFIItemUpdate,
    RFIOut,
    RFISummary,
    RFIUpdate,
)
from app.services import rfi_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/rfis", tags=["RFI"])


# ── RFI CRUD ───────────────────────────────────────────────


@router.get("", response_model=list[RFIOut])
async def list_rfis(
    txn_id: uuid.UUID,
    rfi_status: str | None = Query(None, alias="status"),
    round_number: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    rfis = await rfi_service.list_rfis(
        db, txn_id, rfi_status=rfi_status, round_number=round_number, limit=limit, offset=offset
    )
    return [RFIOut.model_validate(r) for r in rfis]


@router.get("/summary", response_model=RFISummary)
async def rfi_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return await rfi_service.get_rfi_summary(db, txn_id)


@router.post("", response_model=RFIOut, status_code=201)
async def create_rfi(
    txn_id: uuid.UUID,
    body: RFICreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIOut.model_validate(await rfi_service.create_rfi(db, txn_id, body, claims.email))


@router.get("/{rfi_id}", response_model=RFIDetailOut)
async def get_rfi(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    rfi = await rfi_service.get_rfi(db, txn_id, rfi_id)
    return RFIDetailOut.model_validate(rfi)


@router.patch("/{rfi_id}", response_model=RFIOut)
async def update_rfi(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    body: RFIUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIOut.model_validate(await rfi_service.update_rfi(db, txn_id, rfi_id, body, claims.email))


@router.delete("/{rfi_id}", status_code=204)
async def delete_rfi(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    await rfi_service.delete_rfi(db, txn_id, rfi_id, claims.email)


# ── RFI 워크플로우 ─────────────────────────────────────────


@router.post("/{rfi_id}/send", response_model=RFIOut)
async def send_rfi(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIOut.model_validate(await rfi_service.send_rfi(db, txn_id, rfi_id, claims.email))


@router.post("/{rfi_id}/close", response_model=RFIOut)
async def close_rfi(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIOut.model_validate(await rfi_service.close_rfi(db, txn_id, rfi_id, claims.email))


@router.patch("/{rfi_id}/extend-deadline", response_model=RFIOut)
async def extend_deadline(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    body: RFIExtendDeadlineInput,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIOut.model_validate(await rfi_service.extend_deadline(db, txn_id, rfi_id, body.due_date, claims.email))


# ── RFI Item CRUD ──────────────────────────────────────────


@router.get("/{rfi_id}/items", response_model=list[RFIItemOut])
async def list_rfi_items(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    category: str | None = None,
    item_status: str | None = Query(None, alias="status"),
    priority: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    items = await rfi_service.list_rfi_items(
        db,
        txn_id,
        rfi_id,
        category=category,
        item_status=item_status,
        priority=priority,
        limit=limit,
        offset=offset,
    )
    return [RFIItemOut.model_validate(i) for i in items]


@router.post("/{rfi_id}/items", response_model=RFIItemOut, status_code=201)
async def create_rfi_item(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    body: RFIItemCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIItemOut.model_validate(await rfi_service.add_rfi_item(db, txn_id, rfi_id, body, claims.email))


@router.post("/{rfi_id}/items/batch", response_model=list[RFIItemOut], status_code=201)
async def batch_create_rfi_items(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    body: RFIItemBatchCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    items = await rfi_service.batch_add_items(db, txn_id, rfi_id, body.items, claims.email)
    return [RFIItemOut.model_validate(i) for i in items]


@router.patch("/{rfi_id}/items/{item_id}", response_model=RFIItemOut)
async def update_rfi_item(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RFIItemUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIItemOut.model_validate(await rfi_service.update_rfi_item(db, txn_id, rfi_id, item_id, body, claims.email))


@router.delete("/{rfi_id}/items/{item_id}", status_code=204)
async def delete_rfi_item(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    await rfi_service.delete_rfi_item(db, txn_id, rfi_id, item_id, claims.email)


# ── 응답 / 검토 ───────────────────────────────────────────


@router.post("/{rfi_id}/items/{item_id}/respond", response_model=RFIItemOut)
async def respond_to_item(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RFIItemRespondInput,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return RFIItemOut.model_validate(await rfi_service.respond_to_item(db, txn_id, rfi_id, item_id, body, claims.email))


@router.post("/{rfi_id}/items/{item_id}/review", response_model=RFIItemOut)
async def review_item(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RFIItemReviewInput,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    return RFIItemOut.model_validate(await rfi_service.review_item(db, txn_id, rfi_id, item_id, body, claims.email))


# ── 자동 생성 ──────────────────────────────────────────────


@router.post("/generate-from-dd", response_model=RFIAutoGenerateResult, status_code=201)
async def generate_from_dd(
    txn_id: uuid.UUID,
    body: RFIAutoGenerateFromDDRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    rfi, count = await rfi_service.generate_from_dd_checklist(db, txn_id, body.title, claims.email)
    return RFIAutoGenerateResult(rfi_id=rfi.id, items_created=count)


# ── Excel ──────────────────────────────────────────────────


@router.get("/{rfi_id}/export")
async def export_rfi_excel(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    from app.excel.rfi_excel import export_rfi_to_excel

    rfi = await rfi_service.get_rfi(db, txn_id, rfi_id)
    output = export_rfi_to_excel(rfi)
    safe_title = re.sub(r"[^\w\s가-힣-]", "", rfi.title[:30]).strip() or "RFI"
    filename = f"RFI_{safe_title}_{rfi.round_number}.xlsx"
    encoded = quote(filename)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


MAX_EXCEL_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/{rfi_id}/import", response_model=RFIExcelImportResult)
async def import_rfi_excel(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    # 확장자 검증
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Excel 파일(.xlsx, .xls)만 업로드 가능합니다")
    # 크기 검증
    content = await file.read()
    if len(content) > MAX_EXCEL_UPLOAD_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="파일 크기가 10MB를 초과합니다")
    from app.excel.rfi_excel import import_rfi_from_excel

    result = await import_rfi_from_excel(db, txn_id, rfi_id, content, claims.email)
    return result


# ── 동기화 ─────────────────────────────────────────────────


@router.post("/{rfi_id}/sync-to-checklists", response_model=dict)
async def sync_to_checklists(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    from app.services.rfi_sync_service import sync_accepted_to_checklists

    synced_count = await sync_accepted_to_checklists(db, txn_id, rfi_id, claims.email)
    return {"synced": synced_count}


# ── 매핑 조회 ──────────────────────────────────────────────


@router.get("/{rfi_id}/items/{item_id}/mappings", response_model=list[RFIChecklistMappingOut])
async def get_item_mappings(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    mappings = await rfi_service.get_item_mappings(db, txn_id, rfi_id, item_id)
    return [RFIChecklistMappingOut.model_validate(m) for m in mappings]
