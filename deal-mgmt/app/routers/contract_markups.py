"""계약 마크업 버전 관리 라우터 — 파일 업로드/다운로드 지원."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.contract import Contract
from app.models.contract_markup import ContractMarkup
from app.models.enums import AuditAction
from app.schemas.contract_markup import ContractMarkupListResponse, ContractMarkupOut
from app.services import audit_service, document_version_service, transaction_service

UPLOAD_DIR = Path("uploads/markups")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt", ".hwp", ".hwpx", ".txt"}

router = APIRouter(
    prefix="/transactions/{txn_id}/contracts/{contract_id}/markups",
    tags=["Contract Markups"],
)


@router.get("", response_model=ContractMarkupListResponse)
async def list_markups(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_contract_or_404(db, txn_id, contract_id)

    q = select(ContractMarkup).where(ContractMarkup.contract_id == contract_id)
    count_q = select(func.count(ContractMarkup.id)).where(ContractMarkup.contract_id == contract_id)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(ContractMarkup.version_number.asc())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    items = [ContractMarkupOut.model_validate(m) for m in result.scalars().all()]
    return ContractMarkupListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{markup_id}", response_model=ContractMarkupOut)
async def get_markup(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_contract_or_404(db, txn_id, contract_id)
    markup = await _get_markup_or_404(db, contract_id, markup_id)
    return ContractMarkupOut.model_validate(markup)


@router.post("", response_model=ContractMarkupOut, status_code=201)
async def create_markup(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    file: UploadFile = File(...),
    version_label: str = Form(...),
    source_party: str | None = Form(None),
    markup_type: str | None = Form(None),
    changes_summary: str | None = Form(None),
    meeting_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    contract_obj = await _get_contract_or_404(db, txn_id, contract_id)

    # 파일 크기 검증
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        logging.getLogger(__name__).warning(
            "대용량 파일 업로드 (계약 마크업) size=%d contract_id=%s",
            len(content),
            contract_id,
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="파일 크기가 50MB를 초과합니다")

    # 확장자 검증
    safe_filename = file.filename or "markup"
    safe_filename = Path(safe_filename).name
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 다음 버전 번호 결정 (FOR UPDATE로 동시 업로드 레이스 컨디션 방지)
    lock_q = select(Contract).where(Contract.id == contract_id).with_for_update()
    await db.execute(lock_q)

    max_ver_q = select(func.max(ContractMarkup.version_number)).where(
        ContractMarkup.contract_id == contract_id,
    )
    max_ver = (await db.execute(max_ver_q)).scalar() or 0
    next_ver = max_ver + 1

    # 파일 저장
    contract_dir = UPLOAD_DIR / str(contract_id)
    contract_dir.mkdir(parents=True, exist_ok=True)

    dest_path = contract_dir / f"{next_ver}_{safe_filename}"

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    markup = ContractMarkup(
        contract_id=contract_id,
        meeting_id=_parse_optional_uuid(meeting_id),
        version_label=version_label,
        version_number=next_ver,
        source_party=source_party,
        markup_type=markup_type,
        file_path=str(dest_path),
        file_name=safe_filename,
        file_size_bytes=len(content),
        changes_summary=changes_summary,
        created_by_email=claims.email,
    )
    db.add(markup)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="ContractMarkup",
        entity_id=markup.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"version": next_ver, "label": version_label},
    )

    # VCS 연동 — DocumentMaster + Revision 자동 생성 (savepoint로 격리)
    try:
        async with db.begin_nested():
            from app.models.enums import UploadSource

            doc_master = await document_version_service.find_or_create_for_contract(
                db,
                transaction_id=txn_id,
                contract_id=contract_id,
                contract_type=contract_obj.contract_type.value
                if hasattr(contract_obj.contract_type, "value")
                else str(contract_obj.contract_type),
                doc_name=version_label,
                created_by_email=claims.email,
            )
            await document_version_service.upload_revision(
                db,
                document_id=doc_master.id,
                file_content=content,
                file_name=safe_filename,
                mime_type=file.content_type,
                upload_source=UploadSource.CONTRACT_MARKUP,
                changes_summary=changes_summary,
                uploaded_by_email=claims.email,
                source_entity_type="ContractMarkup",
                source_entity_id=str(markup.id),
            )
    except Exception:
        logging.getLogger(__name__).error(
            "VCS 연동 실패 (계약 마크업) contract_id=%s markup_id=%s",
            contract_id,
            markup.id,
            exc_info=True,
        )

    try:
        await db.commit()
    except Exception:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise
    await db.refresh(markup)
    return ContractMarkupOut.model_validate(markup)


@router.get("/{markup_id}/download")
async def download_markup(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_contract_or_404(db, txn_id, contract_id)
    markup = await _get_markup_or_404(db, contract_id, markup_id)

    if not markup.file_path:
        raise HTTPException(status_code=404, detail="파일이 없습니다")

    file_path = Path(markup.file_path)
    # 경로 탐색 방어: UPLOAD_DIR 내부인지 확인
    try:
        file_path.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="잘못된 파일 경로입니다")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    return FileResponse(
        path=str(file_path),
        filename=markup.file_name or file_path.name,
        media_type="application/octet-stream",
    )


@router.delete("/{markup_id}", status_code=204)
async def delete_markup(
    txn_id: uuid.UUID,
    contract_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_contract_or_404(db, txn_id, contract_id)
    markup = await _get_markup_or_404(db, contract_id, markup_id)

    # 파일 삭제 (경로 탐색 방어)
    if markup.file_path:
        file_path = Path(markup.file_path)
        try:
            file_path.resolve().relative_to(UPLOAD_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="잘못된 파일 경로입니다")
        if file_path.exists():
            file_path.unlink()

    await audit_service.record(
        db,
        entity_type="ContractMarkup",
        entity_id=markup.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(markup)
    await db.commit()


# ── 헬퍼 ────────────────────────────────────────────────


def _parse_optional_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 UUID 형식입니다")


async def _get_contract_or_404(db: AsyncSession, txn_id: uuid.UUID, contract_id: uuid.UUID) -> Contract:
    q = select(Contract).where(Contract.id == contract_id, Contract.transaction_id == txn_id)
    contract = (await db.execute(q)).scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계약을 찾을 수 없습니다")
    return contract


async def _get_markup_or_404(db: AsyncSession, contract_id: uuid.UUID, markup_id: uuid.UUID) -> ContractMarkup:
    q = select(ContractMarkup).where(
        ContractMarkup.id == markup_id,
        ContractMarkup.contract_id == contract_id,
    )
    markup = (await db.execute(q)).scalar_one_or_none()
    if markup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="마크업 버전을 찾을 수 없습니다")
    return markup
