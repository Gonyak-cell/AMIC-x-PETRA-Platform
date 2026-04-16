"""RFI V2 API 라우터 — 질의 원장 + 스레드 이력 + 첨부 + 대시보드."""

from __future__ import annotations

import os
import re
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blob_storage import blob_client
from app.core.database import get_db
from app.core.security import (
    JWTClaims,
    check_client_deal_access,
    get_jwt_claims,
    get_rfi_author_role,
    require_write_access,
)
from app.models.enums import RFIAuthorRole
from app.schemas.rfi_v2 import (
    RFIAttachmentMapInput,
    RFIAttachmentOut,
    RFIAutoGenerateRequest,
    RFIAutoGenerateResult,
    RFIDashboardSummary,
    RFIExcelImportResult,
    RFIItemBatchCreate,
    RFIItemCreateV2,
    RFIItemListOut,
    RFIItemListResponse,
    RFIItemOut,
    RFIItemUpdateV2,
    RFIReportPayload,
    RFIThreadCreate,
    RFIThreadOut,
    RFIThreadUpdate,
)
from app.services import rfi_attachment_service, rfi_v2_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/rfi", tags=["RFI"])


# ── Item CRUD ─────────────────────────────────────────────


@router.get("/items", response_model=RFIItemListResponse)
async def list_items(
    txn_id: uuid.UUID,
    category: str | None = Query(None),
    item_status: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> RFIItemListResponse:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    is_advisor = get_rfi_author_role(claims) == RFIAuthorRole.ADVISOR

    # 총 건수 조회
    from app.models.rfi_item_v2 import RFIItemV2 as RFIItemModel

    count_base = select(func.count(RFIItemModel.id)).where(
        RFIItemModel.transaction_id == txn_id,
        RFIItemModel.is_deleted.is_(False),
    )
    if category:
        count_base = count_base.where(RFIItemModel.category == category)
    if item_status:
        count_base = count_base.where(RFIItemModel.current_status == item_status)
    if priority:
        count_base = count_base.where(RFIItemModel.priority == priority)
    if search:
        escaped = search.replace("%", r"\%").replace("_", r"\_")
        count_base = count_base.where(RFIItemModel.question_text.ilike(f"%{escaped}%", escape="\\"))
    total = (await db.execute(count_base)).scalar() or 0

    items = await rfi_v2_service.list_items(
        db,
        txn_id,
        category=category,
        item_status=item_status,
        priority=priority,
        search=search,
        limit=limit,
        offset=offset,
        is_advisor=is_advisor,
    )
    result = []
    for item in items:
        out = RFIItemListOut.model_validate(item)
        out.thread_count = len(item.threads) if hasattr(item, "threads") and item.threads else 0
        out.attachment_count = len(item.attachments) if hasattr(item, "attachments") and item.attachments else 0
        result.append(out)
    return RFIItemListResponse(items=result, total=total, limit=limit, offset=offset)


@router.get("/items/{item_id}", response_model=RFIItemOut)
async def get_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> RFIItemOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    is_advisor = get_rfi_author_role(claims) == RFIAuthorRole.ADVISOR

    item = await rfi_v2_service.get_item(db, txn_id, item_id, is_advisor=is_advisor)
    return RFIItemOut.model_validate(item)


@router.post("/items", response_model=RFIItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    txn_id: uuid.UUID,
    payload: RFIItemCreateV2,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIItemOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    item = await rfi_v2_service.create_item(db, txn_id, payload, created_by=claims.email)
    await db.commit()
    await db.refresh(item)
    return RFIItemOut.model_validate(item)


@router.post("/items/batch", response_model=list[RFIItemOut], status_code=status.HTTP_201_CREATED)
async def create_items_batch(
    txn_id: uuid.UUID,
    payload: RFIItemBatchCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> list[RFIItemOut]:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    items = await rfi_v2_service.create_items_batch(db, txn_id, payload.items, created_by=claims.email)
    await db.commit()
    for item in items:
        await db.refresh(item)
    return [RFIItemOut.model_validate(i) for i in items]


@router.patch("/items/{item_id}", response_model=RFIItemOut)
async def update_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: RFIItemUpdateV2,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIItemOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    item = await rfi_v2_service.update_item(db, txn_id, item_id, payload, updated_by=claims.email)
    await db.commit()
    await db.refresh(item)
    return RFIItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await rfi_v2_service.soft_delete_item(db, txn_id, item_id, deleted_by=claims.email)
    await db.commit()


@router.patch("/items/{item_id}/close", response_model=RFIItemOut)
async def close_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    version: int = Query(..., description="현재 버전"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIItemOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    item = await rfi_v2_service.close_item(db, txn_id, item_id, version, closed_by=claims.email)
    await db.commit()
    await db.refresh(item)
    return RFIItemOut.model_validate(item)


# ── Thread ────────────────────────────────────────────────


@router.get("/items/{item_id}/threads", response_model=list[RFIThreadOut])
async def list_threads(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[RFIThreadOut]:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    threads = await rfi_v2_service.list_threads(db, txn_id, item_id)
    return [RFIThreadOut.model_validate(t) for t in threads]


@router.post("/items/{item_id}/threads", response_model=RFIThreadOut, status_code=status.HTTP_201_CREATED)
async def create_thread(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: RFIThreadCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIThreadOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    author_role = get_rfi_author_role(claims)

    thread = await rfi_v2_service.create_thread(
        db,
        txn_id,
        item_id,
        payload,
        author_email=claims.email or "unknown",
        author_role=author_role,
    )
    await db.commit()
    return RFIThreadOut.model_validate(thread)


@router.patch("/items/{item_id}/threads/{tid}", response_model=RFIThreadOut)
async def update_thread(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    tid: uuid.UUID,
    payload: RFIThreadUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIThreadOut:
    """게시 상태 변경. 거래 접근 + 쓰기 권한 검증. thread 소유자 검증은 팀 워크플로우 특성상 미적용."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    thread = await rfi_v2_service.update_thread_publish(db, txn_id, item_id, tid, payload.is_published)
    await db.commit()
    return RFIThreadOut.model_validate(thread)


# ── Attachment ────────────────────────────────────────────


@router.get("/attachments", response_model=list[RFIAttachmentOut])
async def list_attachments(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[RFIAttachmentOut]:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    attachments = await rfi_attachment_service.list_attachments(db, txn_id)
    return [RFIAttachmentOut.model_validate(a) for a in attachments]


@router.get("/attachments/unassigned", response_model=list[RFIAttachmentOut])
async def list_unassigned(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[RFIAttachmentOut]:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    attachments = await rfi_attachment_service.list_unassigned(db, txn_id)
    return [RFIAttachmentOut.model_validate(a) for a in attachments]


_ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".csv",
    ".txt",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".hwp",
    ".hwpx",
}
_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9가-힣._ ()\[\]-]+")


def _sanitize_upload_filename(filename: str | None) -> str:
    base_name = os.path.basename(filename or "attachment")
    safe_name = _SAFE_FILENAME_PATTERN.sub("_", base_name).strip(" .")
    return safe_name or "attachment"


@router.post("/attachments", response_model=list[RFIAttachmentOut], status_code=status.HTTP_201_CREATED)
async def upload_attachments(
    txn_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> list[RFIAttachmentOut]:
    """다중 파일 업로드 → Azure Blob → DB 메타 생성."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # Step 1: 모든 파일 사전 검증 (확장자 + 크기) — 부분 업로드 방지
    file_contents: list[tuple[str, bytes, str]] = []
    for f in files:
        filename = _sanitize_upload_filename(f.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"허용되지 않는 파일 형식입니다: {ext}",
            )
        content = await f.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Empty files cannot be uploaded: {filename}",
            )
        if len(content) > _MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"파일 크기가 제한(50MB)을 초과합니다: {f.filename}",
            )
        file_contents.append((filename, content, f.content_type or "application/octet-stream"))

    # Step 2: 검증 통과 후 Blob 업로드 + DB 메타 생성
    results: list[RFIAttachmentOut] = []
    await blob_client.ensure_initialized()
    for filename, content, content_type in file_contents:
        blob_path = f"rfi/{txn_id}/{uuid.uuid4()}/{filename}"
        file_url = await blob_client.upload_blob(blob_path, content, content_type)

        attachment = await rfi_attachment_service.create_attachment(
            db,
            txn_id,
            file_name=filename,
            file_url=file_url,
            created_by=claims.email,
        )
        results.append(RFIAttachmentOut.model_validate(attachment))

    await db.commit()
    return results


@router.post("/attachments/{file_id}/map", response_model=RFIAttachmentOut)
async def map_attachment(
    txn_id: uuid.UUID,
    file_id: uuid.UUID,
    payload: RFIAttachmentMapInput,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIAttachmentOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    attachment = await rfi_attachment_service.map_attachment(
        db,
        txn_id,
        file_id,
        item_id=payload.item_id,
        thread_id=payload.thread_id,
        mapped_by=claims.email,
    )
    await db.commit()
    return RFIAttachmentOut.model_validate(attachment)


@router.delete("/attachments/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    txn_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await rfi_attachment_service.delete_attachment(db, txn_id, file_id, deleted_by=claims.email)
    await db.commit()


@router.get("/attachments/{file_id}/download")
async def download_attachment(
    txn_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> StreamingResponse:
    """파일 다운로드 — Pre-signed URL 또는 서버 프록시."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    attachment = await rfi_attachment_service.get_attachment(db, txn_id, file_id)

    data = await blob_client.download_blob(attachment.file_url)
    encoded_name = quote(attachment.file_name)
    return StreamingResponse(
        iter([data]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


# ── Dashboard ─────────────────────────────────────────────


@router.get("/dashboard", response_model=RFIDashboardSummary)
async def rfi_dashboard(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> RFIDashboardSummary:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return await rfi_v2_service.get_dashboard(db, txn_id)


# ── Report Bridge ────────────────────────────────────────


@router.get("/report-payload", response_model=list[RFIReportPayload])
async def report_payload(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[RFIReportPayload]:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return await rfi_v2_service.get_report_payload(db, txn_id)


# ── Excel Export / Import ─────────────────────────────────


@router.get("/export")
async def export_excel(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> StreamingResponse:
    """동적 Excel 내보내기 — role에 따라 Internal Memo 포함/제외."""
    from app.excel.rfi_excel_v2 import export_rfi_excel

    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    is_advisor = get_rfi_author_role(claims) == RFIAuthorRole.ADVISOR

    output = await export_rfi_excel(db, txn_id, is_advisor=is_advisor)
    filename = f"RFI_{txn_id}.xlsx"
    encoded_name = quote(filename)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


@router.post("/import", response_model=RFIExcelImportResult)
async def import_excel(
    txn_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIExcelImportResult:
    """역방향 Excel 가져오기 — 엑셀만 전송, 파일은 사전 업로드."""
    from app.services.rfi_import_pipeline import import_rfi_excel

    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    file_bytes = await file.read()
    result = await import_rfi_excel(
        db,
        txn_id,
        file_bytes,
        author_email=claims.email or "target@import",
    )

    # 에러/충돌이 없으면 커밋, 있으면 롤백
    if not result.errors and not result.conflicts:
        await db.commit()
    else:
        await db.rollback()

    return result


# ── AI Generate ──────────────────────────────────────────


@router.post("/generate", response_model=RFIAutoGenerateResult)
async def generate_rfi(
    txn_id: uuid.UUID,
    payload: RFIAutoGenerateRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RFIAutoGenerateResult:
    """AI 기반 초기 RFI 질의 자동 생성."""
    from app.core.config import settings
    from app.ralph.llm_client import RalphLLMClient
    from app.services.rfi_ai_generator import generate_rfi_items

    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    llm_client = RalphLLMClient.from_settings(settings)
    if not llm_client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 프로바이더가 설정되지 않았습니다. API 키를 확인하세요.",
        )

    items_created, cost_usd, model_used = await generate_rfi_items(
        db,
        txn_id,
        industry=payload.industry,
        deal_purpose=payload.deal_purpose,
        focus_areas=payload.focus_areas,
        additional_context=payload.additional_context,
        created_by_email=claims.email or "ai-generator",
        llm_client=llm_client,
    )

    await db.commit()

    return RFIAutoGenerateResult(
        items_created=items_created,
        cost_usd=round(cost_usd, 4),
        model_used=model_used,
    )
