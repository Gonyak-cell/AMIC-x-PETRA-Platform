"""Gemini File API 래퍼 — VDR 문서 업로드, 캐싱, 만료 관리.

Gemini File API를 통해 VDR 문서를 업로드하면 1M 토큰 컨텍스트 윈도우로
전체 문서를 LLM에 전달할 수 있다. 업로드된 파일은 48시간 후 자동 삭제된다.

사용처:
- A1: VDR 문서 분류 (전체 본문 기반 정확도 향상)
- C1: VDR 자연어 Q&A (다수 문서 동시 참조)
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Gemini File API 제약
_FILE_TTL_HOURS = 47  # 48h 제한보다 1h 여유
_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


@dataclass(frozen=True)
class GeminiFileRef:
    """Gemini File API에 업로드된 파일 참조."""

    uri: str  # "https://generativelanguage.googleapis.com/..." 형태
    display_name: str
    expires_at: datetime


async def upload_vdr_document(
    file_path: str | Path,
    display_name: str,
    *,
    api_key: str,
) -> GeminiFileRef:
    """VDR 문서를 Gemini File API에 업로드한다.

    Args:
        file_path: 로컬 파일 경로 (Blob Storage에서 다운로드한 임시 파일).
        display_name: Gemini에 표시될 파일명.
        api_key: Google API 키.

    Returns:
        GeminiFileRef: 업로드된 파일 참조 (uri + 만료 시각).

    Raises:
        FileUploadError: 파일 크기 초과, 업로드 실패 등.
    """
    from google import genai as google_genai

    path = Path(file_path)
    if not path.exists():
        raise FileUploadError(f"파일이 존재하지 않습니다: {path}")

    file_size = path.stat().st_size
    if file_size > _MAX_FILE_SIZE_BYTES:
        raise FileUploadError(f"파일 크기 초과: {file_size / 1024 / 1024:.1f}MB > 50MB 제한")

    client = google_genai.Client(api_key=api_key)

    def _sync_upload() -> GeminiFileRef:
        uploaded = client.files.upload(
            file=str(path),
            config={"display_name": display_name},
        )
        return GeminiFileRef(
            uri=uploaded.uri,
            display_name=display_name,
            expires_at=datetime.now(UTC) + timedelta(hours=_FILE_TTL_HOURS),
        )

    ref = await asyncio.wait_for(
        asyncio.to_thread(_sync_upload),
        timeout=120.0,
    )
    logger.info(
        "Gemini File 업로드 완료: display_name=%s, uri=%s, expires=%s",
        display_name,
        ref.uri,
        ref.expires_at.isoformat(),
    )
    return ref


async def get_cached_file_uri(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> str | None:
    """DB에 캐싱된 gemini_file_uri를 조회한다. 만료된 경우 None."""
    from app.models.vdr_document import VdrDocument

    stmt = select(
        VdrDocument.gemini_file_uri,
        VdrDocument.gemini_file_expires_at,
    ).where(VdrDocument.id == document_id)
    result = await db.execute(stmt)
    row = result.one_or_none()

    if row is None:
        return None

    uri, expires_at = row
    if not uri or not expires_at:
        return None

    # 만료 여부 확인
    if expires_at.tzinfo is None:
        # naive datetime → UTC 가정
        if datetime.now(UTC).replace(tzinfo=None) > expires_at:
            return None
    elif datetime.now(UTC) > expires_at:
        return None

    return uri


async def save_file_uri(
    db: AsyncSession,
    document_id: uuid.UUID,
    ref: GeminiFileRef,
) -> None:
    """업로드된 Gemini 파일 URI를 DB에 캐싱한다."""
    from app.models.vdr_document import VdrDocument

    stmt = (
        update(VdrDocument)
        .where(VdrDocument.id == document_id)
        .values(
            gemini_file_uri=ref.uri,
            gemini_file_expires_at=ref.expires_at,
        )
    )
    await db.execute(stmt)
    await db.flush()


async def upload_and_cache(
    db: AsyncSession,
    document_id: uuid.UUID,
    blob_name: str,
    display_name: str,
    *,
    api_key: str,
) -> GeminiFileRef:
    """Blob Storage → 임시 파일 → Gemini 업로드 → DB 캐싱.

    캐시 히트 시 업로드를 건너뛴다.
    """
    # 1. 캐시 확인
    cached_uri = await get_cached_file_uri(db, document_id)
    if cached_uri:
        logger.debug("Gemini File 캐시 히트: doc=%s", document_id)
        return GeminiFileRef(
            uri=cached_uri,
            display_name=display_name,
            expires_at=datetime.now(UTC) + timedelta(hours=_FILE_TTL_HOURS),
        )

    # 2. Blob Storage에서 임시 파일로 다운로드
    from app.core.blob_storage import blob_client

    await blob_client.ensure_initialized()

    tmp_dir = Path(tempfile.gettempdir()) / "gemini_uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{document_id}_{display_name}"

    try:
        await blob_client.download_blob_to_file(blob_name, tmp_path)

        # 3. Gemini File API 업로드
        ref = await upload_vdr_document(tmp_path, display_name, api_key=api_key)

        # 4. DB 캐싱
        await save_file_uri(db, document_id, ref)
        return ref
    finally:
        # 임시 파일 정리
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


async def cleanup_expired_files(db: AsyncSession) -> int:
    """만료된 Gemini 파일 URI를 DB에서 정리한다.

    Returns:
        정리된 레코드 수.
    """
    from app.models.vdr_document import VdrDocument

    now = datetime.now(UTC)
    stmt = (
        update(VdrDocument)
        .where(
            VdrDocument.gemini_file_uri.isnot(None),
            VdrDocument.gemini_file_expires_at < now,
        )
        .values(gemini_file_uri=None, gemini_file_expires_at=None)
    )
    result = await db.execute(stmt)
    await db.flush()

    count = result.rowcount or 0
    if count > 0:
        logger.info("만료된 Gemini File URI %d건 정리 완료", count)
    return count


class FileUploadError(Exception):
    """Gemini File API 업로드 실패."""
