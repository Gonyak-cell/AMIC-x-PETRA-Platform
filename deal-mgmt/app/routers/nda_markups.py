"""NDA 마크업 버전 관리 라우터 — 파일 업로드/다운로드 + Redline 생성."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import AuditAction
from app.models.nda import NDA
from app.models.nda_markup import NdaMarkup
from app.schemas.nda_markup import NdaMarkupListResponse, NdaMarkupOut
from app.services import audit_service, transaction_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/nda_markups")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt", ".hwp", ".hwpx", ".txt"}
_VERSION_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

router = APIRouter(
    prefix="/transactions/{txn_id}/ndas/{nda_id}/markups",
    tags=["NDA Markups"],
)


# ── 목록 조회 ───────────────────────────────────────────────────────


@router.get("", response_model=NdaMarkupListResponse)
async def list_nda_markups(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> NdaMarkupListResponse:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)

    q = select(NdaMarkup).where(NdaMarkup.nda_id == nda_id)
    count_q = select(func.count(NdaMarkup.id)).where(NdaMarkup.nda_id == nda_id)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(NdaMarkup.version_number.asc())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    items = [NdaMarkupOut.model_validate(m) for m in result.scalars().all()]
    return NdaMarkupListResponse(items=items, total=total)


# ── 상세 조회 ───────────────────────────────────────────────────────


@router.get("/{markup_id}", response_model=NdaMarkupOut)
async def get_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> NdaMarkupOut:
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)
    markup = await _get_markup_or_404(db, nda_id, markup_id)
    return NdaMarkupOut.model_validate(markup)


# ── 새 버전 업로드 ──────────────────────────────────────────────────


@router.post("", response_model=NdaMarkupOut, status_code=201)
async def create_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    file: UploadFile = File(...),
    version_label: str = Form(...),
    version_date: str = Form(...),
    source_party: str | None = Form(None),
    markup_type: str | None = Form(None),
    changes_summary: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> NdaMarkupOut:
    await transaction_service.get_transaction(db, txn_id)
    nda = await _get_nda_or_404(db, txn_id, nda_id)

    # version_date 형식 검증 (YYYY-MM-DD)
    if not _VERSION_DATE_RE.match(version_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="version_date는 YYYY-MM-DD 형식이어야 합니다",
        )

    # 파일 크기 검증
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="파일 크기가 50MB를 초과합니다",
        )

    # 확장자 검증
    safe_filename = file.filename or "markup"
    safe_filename = Path(safe_filename).name
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 다음 버전 번호 결정 (FOR UPDATE로 레이스 컨디션 방지)
    lock_q = select(NDA).where(NDA.id == nda_id).with_for_update()
    await db.execute(lock_q)

    max_ver_q = select(func.max(NdaMarkup.version_number)).where(NdaMarkup.nda_id == nda_id)
    max_ver = (await db.execute(max_ver_q)).scalar() or 0
    next_ver = max_ver + 1

    # 파일 저장
    nda_dir = UPLOAD_DIR / str(nda.id)
    nda_dir.mkdir(parents=True, exist_ok=True)

    dest_path = nda_dir / f"{next_ver}_{safe_filename}"

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    markup = NdaMarkup(
        nda_id=nda_id,
        version_label=version_label,
        version_number=next_ver,
        version_date=version_date,
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
        entity_type="NdaMarkup",
        entity_id=markup.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"version": next_ver, "label": version_label, "date": version_date},
    )

    # VCS 연동 — DocumentMaster + Revision 자동 생성
    try:
        from app.models.enums import UploadSource
        from app.services import document_version_service

        doc_master = await document_version_service.find_or_create_for_nda(
            db,
            transaction_id=txn_id,
            nda_id=nda_id,
            doc_name=version_label,
            created_by_email=claims.email,
        )
        await document_version_service.upload_revision(
            db,
            document_id=doc_master.id,
            file_content=content,
            file_name=safe_filename,
            mime_type=file.content_type,
            upload_source=UploadSource.NDA_MARKUP,
            changes_summary=changes_summary,
            uploaded_by_email=claims.email,
            source_entity_type="NdaMarkup",
            source_entity_id=str(markup.id),
        )
    except Exception:
        logger.warning("VCS 연동 실패 (NDA 마크업)", exc_info=True)

    await db.commit()
    await db.refresh(markup)
    return NdaMarkupOut.model_validate(markup)


# ── 파일 다운로드 ───────────────────────────────────────────────────


@router.get("/{markup_id}/download")
async def download_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> FileResponse:
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)
    markup = await _get_markup_or_404(db, nda_id, markup_id)

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


# ── 삭제 ────────────────────────────────────────────────────────────


@router.delete("/{markup_id}", status_code=204)
async def delete_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)
    markup = await _get_markup_or_404(db, nda_id, markup_id)

    # 업로드 파일 삭제
    _try_delete_file(markup.file_path)
    # Redline 파일 삭제
    _try_delete_file(markup.redline_file_path)

    await audit_service.record(
        db,
        entity_type="NdaMarkup",
        entity_id=markup.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(markup)
    await db.commit()


# ── Redline 생성 ────────────────────────────────────────────────────


@router.post("/{markup_id}/generate-redline")
async def generate_nda_redline(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    base_markup_id: str | None = Form(None),
    party_side: str = Form("SELL"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> StreamingResponse:
    """지정 버전의 NDA에 대해 Tracked Changes .docx를 생성한다.

    base_markup_id가 지정되면 해당 버전 대비, 미지정이면 직전 버전 대비 비교.
    """
    from app.services import nda_analysis_service, redline_engine

    await check_client_deal_access(db, txn_id, claims)
    nda = await _get_nda_or_404(db, txn_id, nda_id)
    current_markup = await _get_markup_or_404(db, nda_id, markup_id)

    if not current_markup.file_path or not Path(current_markup.file_path).exists():
        raise HTTPException(status_code=404, detail="현재 버전의 파일이 없습니다")

    # party_side 검증
    if party_side not in ("SELL", "BUY"):
        raise HTTPException(status_code=400, detail="party_side는 SELL 또는 BUY여야 합니다")

    # 현재 버전 파일 읽기 (async)
    current_file_path = Path(current_markup.file_path)
    current_bytes = await run_in_threadpool(current_file_path.read_bytes)

    # 참조 버전 결정
    reference_text: str
    base_id = _parse_optional_uuid(base_markup_id) if base_markup_id else None

    if base_id:
        base_markup = await _get_markup_or_404(db, nda_id, base_id)
        if not base_markup.file_path or not Path(base_markup.file_path).exists():
            raise HTTPException(status_code=404, detail="기준 버전의 파일이 없습니다")
        base_path = Path(base_markup.file_path)
        reference_text = await run_in_threadpool(lambda: redline_engine.extract_paragraphs_text(base_path.read_bytes()))
    else:
        # 직전 버전 자동 선택
        prev_q = (
            select(NdaMarkup)
            .where(
                NdaMarkup.nda_id == nda_id,
                NdaMarkup.version_number < current_markup.version_number,
            )
            .order_by(NdaMarkup.version_number.desc())
            .limit(1)
        )
        prev_markup = (await db.execute(prev_q)).scalar_one_or_none()
        if prev_markup and prev_markup.file_path and Path(prev_markup.file_path).exists():
            prev_path = Path(prev_markup.file_path)
            reference_text = await run_in_threadpool(
                lambda: redline_engine.extract_paragraphs_text(prev_path.read_bytes())
            )
            base_id = prev_markup.id
        else:
            reference_text = "(참조 문서 없음 — 표준 NDA 조항 대비 검토)"

    # Redline 생성 (LLM 호출 포함)
    try:
        result_docx, cost, model_name, issues_count, skipped_count = await nda_analysis_service.generate_nda_redline(
            current_bytes,
            reference_text,
            nda_type=nda.nda_type.value if hasattr(nda.nda_type, "value") else str(nda.nda_type),
            party_side=party_side,
            owner_user_id=claims.email or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        logger.exception("NDA Redline 생성 중 런타임 에러")
        raise HTTPException(status_code=503, detail=f"Redline 생성 실패: {exc}")

    # Redline 파일 저장 (async)
    nda_dir = UPLOAD_DIR / str(nda_id)
    nda_dir.mkdir(parents=True, exist_ok=True)
    redline_path = nda_dir / f"{current_markup.version_number}_redline.docx"
    async with aiofiles.open(redline_path, "wb") as f:
        await f.write(result_docx.getvalue())

    # DB 메타데이터 업데이트
    current_markup.redline_file_path = str(redline_path)
    current_markup.redline_issues_count = issues_count
    current_markup.base_version_id = base_id
    await audit_service.record(
        db,
        entity_type="NdaMarkup",
        entity_id=current_markup.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={
            "action": "generate_redline",
            "issues_count": issues_count,
            "skipped_count": skipped_count,
            "cost_usd": cost,
            "model": model_name,
        },
    )
    await db.commit()

    # StreamingResponse로 반환
    result_docx.seek(0)
    safe_name = f"NDA_v{current_markup.version_number}_redline.docx"
    return StreamingResponse(
        result_docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Issues-Count": str(issues_count),
            "X-Skipped-Count": str(skipped_count),
        },
    )


# ── 헬퍼 ────────────────────────────────────────────────────────────


def _parse_optional_uuid(value: str | None) -> uuid.UUID | None:
    """Form 필드로 받은 문자열을 UUID로 파싱. 빈 문자열/None이면 None 반환."""
    if not value or not value.strip():
        return None
    try:
        return uuid.UUID(value.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 UUID입니다: {value}")


def _try_delete_file(file_path_str: str | None) -> None:
    """파일 경로가 유효하면 삭제 시도. 실패해도 DB 트랜잭션을 차단하지 않는다."""
    if not file_path_str:
        return
    try:
        fp = Path(file_path_str)
        if fp.exists():
            fp.unlink()
    except OSError:
        logger.warning("파일 삭제 실패 (무시): %s", file_path_str)


async def _get_nda_or_404(db: AsyncSession, txn_id: uuid.UUID, nda_id: uuid.UUID) -> NDA:
    q = select(NDA).where(NDA.id == nda_id, NDA.transaction_id == txn_id)
    nda = (await db.execute(q)).scalar_one_or_none()
    if nda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NDA를 찾을 수 없습니다")
    return nda


async def _get_markup_or_404(db: AsyncSession, nda_id: uuid.UUID, markup_id: uuid.UUID) -> NdaMarkup:
    q = select(NdaMarkup).where(
        NdaMarkup.id == markup_id,
        NdaMarkup.nda_id == nda_id,
    )
    markup = (await db.execute(q)).scalar_one_or_none()
    if markup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NDA 마크업 버전을 찾을 수 없습니다")
    return markup
