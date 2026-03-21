"""VDR (Virtual Data Room) 라우터 — 폴더 트리 + 문서 업로드/다운로드."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blob_storage import blob_client
from app.core.database import get_db
from app.core.exceptions import DocumentNotFoundError
from app.core.rate_limiter import InMemoryRateLimiter
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import VdrAccessAction, VdrDocumentStatus
from app.models.transaction import Transaction
from app.models.vdr_folder import VdrFolder
from app.schemas.vdr import (
    VdrDocumentOut,
    VdrDocumentUpdate,
    VdrFolderCreate,
    VdrFolderOut,
    VdrFolderTreeOut,
    VdrFolderUpdate,
    VdrInitRequest,
    VdrSummaryOut,
)
from app.services import transaction_service, vdr_access_service, vdr_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions/{txn_id}/vdr",
    tags=["VDR"],
)

# 업로드 허용 MIME 타입
_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "image/png",
    "image/jpeg",
    "text/plain",
    "text/csv",
    "application/zip",
    # 신규: M&A 실사 특화 포맷
    "application/haansofthwp",  # .hwp
    "application/x-hwp",  # .hwp 변형
    "image/vnd.dwg",  # .dwg
    "application/dxf",  # .dxf
    "application/x-tar",  # .tar
    "application/gzip",  # .gz
    "application/json",  # .json
    # NOTE: application/octet-stream은 의도적으로 제외.
    # .dwg/.shp 등은 _EXTENSION_MIME_MAP에서 확장자별로만 허용.
    "application/vnd.google-earth.kml+xml",  # .kml
    "application/x-iwork-keynote-sffkey",  # .key
    "message/rfc822",  # .eml
    "application/vnd.ms-outlook",  # .msg
}

# 최대 파일 크기: 100MB
_MAX_FILE_SIZE = 100 * 1024 * 1024

# 확장자 → 허용 MIME 타입 매핑 (클라이언트 MIME 조작 방어)
_EXTENSION_MIME_MAP: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".doc": {"application/msword"},
    ".xls": {"application/vnd.ms-excel"},
    ".ppt": {"application/vnd.ms-powerpoint"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".txt": {"text/plain"},
    ".csv": {"text/csv", "text/plain"},
    ".zip": {"application/zip"},
    # 신규: M&A 실사 특화 포맷
    ".hwp": {"application/haansofthwp", "application/x-hwp"},
    ".dwg": {"image/vnd.dwg", "application/octet-stream"},
    ".dxf": {"application/dxf", "application/octet-stream"},
    ".tar": {"application/x-tar"},
    ".gz": {"application/gzip"},
    ".sql": {"text/plain"},
    ".json": {"application/json"},
    ".shp": {"application/octet-stream"},
    ".kml": {"application/vnd.google-earth.kml+xml"},
    ".key": {"application/x-iwork-keynote-sffkey"},
    ".eml": {"message/rfc822"},
    ".msg": {"application/vnd.ms-outlook"},
}
_ALLOWED_EXTENSIONS = frozenset(_EXTENSION_MIME_MAP.keys())

# VDR 업로드 엔드포인트 Rate Limiter (분당 20건/사용자)
_upload_limiter = InMemoryRateLimiter(max_calls=20, window_seconds=60.0)


def _validate_upload_metadata(file: UploadFile) -> tuple[str, str, str]:
    """업로드 파일의 확장자·MIME·Content-Length 헤더를 검증한다 (파일 내용 읽지 않음).

    Returns:
        (filename, ext, content_type)
    """
    # 경로 탐색 방지: 파일명에서 디렉토리 구성 요소 제거
    raw_name = file.filename or "untitled"
    filename = Path(raw_name).name
    ext = Path(filename).suffix.lower()

    # 1) 확장자 화이트리스트 검증
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 확장자입니다: {ext}",
        )

    # 2) MIME 검증: 확장자별 매핑이 있으면 교차 검증, 없으면 전역 화이트리스트
    content_type = file.content_type or "application/octet-stream"
    expected_mimes = _EXTENSION_MIME_MAP.get(ext)
    if expected_mimes:
        if content_type not in expected_mimes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 확장자({ext})와 MIME 타입({content_type})이 일치하지 않습니다.",
            )
    elif content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 형식입니다: {content_type}",
        )

    # 3) 파일 크기 사전검증 (Content-Length 헤더 기반, OOM 방어)
    if file.size is not None and file.size > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"파일 크기가 최대 허용량({_MAX_FILE_SIZE // 1024 // 1024}MB)을 초과합니다.",
        )

    return filename, ext, content_type


async def _validate_upload(file: UploadFile) -> tuple[str, str, str, bytes]:
    """업로드 파일의 확장자·MIME·크기를 검증하고 콘텐츠를 읽는다.

    단일 파일 업로드 엔드포인트 하위호환용.
    배치 업로드는 _validate_upload_metadata + _stream_hash_and_size 조합을 사용한다.

    Returns:
        (filename, ext, content_type, content)
    """
    filename, ext, content_type = _validate_upload_metadata(file)

    # 파일 크기 실측 검증 (Content-Length 조작 방어)
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"파일 크기가 최대 허용량({_MAX_FILE_SIZE // 1024 // 1024}MB)을 초과합니다.",
        )

    return filename, ext, content_type, content


async def _validate_upload_streaming(
    file: UploadFile,
) -> tuple[str, str, str, str, int]:
    """스트리밍 검증: 메타데이터 + 청크 단위 해시/크기 계산. O(1MB) 메모리.

    완료 후 file은 seek(0) 상태 — 후속 blob 업로드에 바로 사용 가능.

    Returns:
        (filename, ext, content_type, sha256_hex, file_size)
    """
    filename, ext, content_type = _validate_upload_metadata(file)
    sha256_hex, file_size = await vdr_service.stream_hash_and_size(file, _MAX_FILE_SIZE)
    return filename, ext, content_type, sha256_hex, file_size


async def _get_and_authorize_txn(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
) -> Transaction:
    """거래 존재 확인 및 접근 권한 검증."""
    txn = await transaction_service.get_transaction(db, txn_id)
    # CLIENT 역할: deal_clients 테이블 기반 접근 제어
    if claims.role == "CLIENT":
        await check_client_deal_access(db, txn_id, claims)
        return txn
    if claims.role != "ADMIN":
        if claims.email is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 거래에 접근할 권한이 없습니다",
            )
        if txn.lead_advisor_email != claims.email and txn.deal_captain_email != claims.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 거래에 접근할 권한이 없습니다",
            )
    return txn


# ── 요약/초기화 ─────────────────────────────────────────────


@router.get("/summary", response_model=VdrSummaryOut)
async def get_vdr_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """VDR 요약 통계 조회."""
    await _get_and_authorize_txn(db, txn_id, claims)
    return await vdr_service.get_vdr_summary(db, txn_id)


@router.post(
    "/init",
    response_model=list[VdrFolderOut],
    status_code=status.HTTP_201_CREATED,
)
async def init_vdr(
    txn_id: uuid.UUID,
    body: VdrInitRequest | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """기본 VDR 폴더 구조를 생성한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        folders = await vdr_service.init_vdr_folders(db, txn_id)
        return [VdrFolderOut.model_validate(f) for f in folders]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 폴더 CRUD ───────────────────────────────────────────────


@router.get("/folders", response_model=list[VdrFolderTreeOut])
async def list_folders(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """VDR 폴더 트리 조회."""
    await _get_and_authorize_txn(db, txn_id, claims)
    folders = await vdr_service.list_folders(db, txn_id)
    doc_counts = await vdr_service.get_folder_document_counts(db, txn_id)
    return _build_tree(folders, doc_counts)


@router.post(
    "/folders",
    response_model=VdrFolderOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    txn_id: uuid.UUID,
    body: VdrFolderCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """새 VDR 폴더를 생성한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        folder = await vdr_service.create_folder(db, txn_id, body)
        return VdrFolderOut.model_validate(folder)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/folders/{folder_id}", response_model=VdrFolderOut)
async def update_folder(
    txn_id: uuid.UUID,
    folder_id: uuid.UUID,
    body: VdrFolderUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR 폴더를 수정한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        folder = await vdr_service.update_folder(db, txn_id, folder_id, body)
        return VdrFolderOut.model_validate(folder)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    txn_id: uuid.UUID,
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR 폴더를 삭제한다 (필수 폴더 제외)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        await vdr_service.delete_folder(db, txn_id, folder_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 문서 CRUD ───────────────────────────────────────────────


@router.get("/documents", response_model=list[VdrDocumentOut])
async def list_all_documents(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """거래의 전체 문서 목록 조회 (폴더 무관)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    docs = await vdr_service.list_all_documents(db, txn_id)
    return [VdrDocumentOut.model_validate(d) for d in docs]


@router.get("/folders/{folder_id}/documents", response_model=list[VdrDocumentOut])
async def list_documents(
    txn_id: uuid.UUID,
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """폴더 내 문서 목록 조회."""
    await _get_and_authorize_txn(db, txn_id, claims)
    docs = await vdr_service.list_documents(db, txn_id, folder_id)
    return [VdrDocumentOut.model_validate(d) for d in docs]


@router.post(
    "/folders/{folder_id}/documents",
    response_model=VdrDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    txn_id: uuid.UUID,
    folder_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR에 파일을 업로드한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    _upload_limiter.check(f"vdr_upload:{claims.email or claims.user_id}")
    filename, _ext, content_type, sha256_hex, file_size = await _validate_upload_streaming(file)

    try:
        doc = await vdr_service.upload_document_stream(
            db=db,
            transaction_id=txn_id,
            folder_id=folder_id,
            original_name=filename,
            file_obj=file,
            file_size=file_size,
            sha256_hex=sha256_hex,
            mime_type=content_type,
            uploaded_by_email=claims.email,
        )
        return VdrDocumentOut.model_validate(doc)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── 2차 심사 상태 조회 (must precede /documents/{doc_id}) ──────


@router.get("/documents/{doc_id}", response_model=VdrDocumentOut)
async def get_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """VDR 문서 메타데이터 조회."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        doc = await vdr_service.get_document(db, txn_id, doc_id)
        # VIEW 접근 기록 (BackgroundTasks로 비동기 처리)
        background_tasks.add_task(
            vdr_access_service.record_access_background,
            transaction_id=txn_id,
            document_id=doc_id,
            folder_id=doc.folder_id,
            user_email=claims.email or "",
            user_id=claims.user_id,
            action=VdrAccessAction.VIEW,
        )
        return VdrDocumentOut.model_validate(doc)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/documents/{doc_id}/download")
async def download_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """VDR 문서를 다운로드한다.

    Azure 모드: SAS URL로 307 리다이렉트.
    로컬 모드: 파일 콘텐츠 직접 반환.
    """
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        doc = await vdr_service.get_document(db, txn_id, doc_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if doc.status != VdrDocumentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="이 문서는 삭제 또는 아카이브되었습니다.",
        )

    # VDR 접근 기록 (BackgroundTasks로 비동기 처리)
    background_tasks.add_task(
        vdr_access_service.record_access_background,
        transaction_id=txn_id,
        document_id=doc_id,
        folder_id=doc.folder_id,
        user_email=claims.email or "",
        user_id=claims.user_id,
        action=VdrAccessAction.DOWNLOAD,
    )

    if blob_client.is_local_mode:
        try:
            content = await blob_client.download_blob(doc.file_path)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="파일을 찾을 수 없습니다.",
            )
        return Response(
            content=content,
            media_type=doc.mime_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc.original_name)}"},
        )

    sas_url = blob_client.generate_sas_url(doc.file_path, expiry_minutes=15)
    return RedirectResponse(url=sas_url, status_code=307)


@router.put("/documents/{doc_id}", response_model=VdrDocumentOut)
async def update_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: VdrDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR 문서 설명 수정 또는 폴더 이동."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        doc = await vdr_service.update_document(db, txn_id, doc_id, body)
        return VdrDocumentOut.model_validate(doc)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR 문서를 소프트 삭제한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    try:
        await vdr_service.delete_document(db, txn_id, doc_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── 헬퍼: flat → tree 변환 ───────────────────────────────────


def _build_tree(
    folders: list[VdrFolder],
    doc_counts: dict[uuid.UUID, int],
) -> list[VdrFolderTreeOut]:
    """flat 폴더 리스트를 계층적 트리로 변환한다."""
    node_map: dict[uuid.UUID, VdrFolderTreeOut] = {}

    for folder in folders:
        tree_node = VdrFolderTreeOut.model_validate(folder)
        tree_node.document_count = doc_counts.get(folder.id, 0)
        tree_node.children = []
        node_map[folder.id] = tree_node

    roots: list[VdrFolderTreeOut] = []
    for folder in folders:
        node = node_map[folder.id]
        if folder.parent_id and folder.parent_id in node_map:
            node_map[folder.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots
