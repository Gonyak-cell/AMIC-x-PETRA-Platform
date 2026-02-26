"""기존 로컬 VDR 파일 → Azure Blob Storage 일회성 마이그레이션 스크립트.

> 마지막 수정: 2026-02-26

사용법:
    # 드라이런 (실제 업로드 없이 대상 파일 목록만 출력)
    python scripts/migrate_vdr_to_blob.py --dry-run

    # 실제 마이그레이션 실행
    python scripts/migrate_vdr_to_blob.py

    # 커스텀 로컬 경로
    python scripts/migrate_vdr_to_blob.py --local-dir /app/generated/vdr

필수 환경변수:
    AZURE_STORAGE_CONNECTION_STRING — Azure Storage 연결 문자열
    AZURE_VDR_CONTAINER_NAME — 컨테이너명 (기본: amic-vdr)
    DATABASE_URL — PostgreSQL 동기 URL (예: postgresql://user:pw@host:5432/db)
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 기본 로컬 VDR 경로 (Docker 컨테이너 내부)
_DEFAULT_LOCAL_DIR = Path("/app/generated/vdr")


def _get_sync_engine():
    """동기 SQLAlchemy 엔진을 생성한다."""
    from sqlalchemy import create_engine

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    # asyncpg URL이면 동기 URL로 변환
    sync_url = db_url.replace("+asyncpg", "")
    return create_engine(sync_url, pool_pre_ping=True)


def _get_blob_client():
    """Azure Blob 컨테이너 클라이언트를 생성한다."""
    from azure.storage.blob import BlobServiceClient, ContentSettings  # noqa: F401

    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
    if not conn_str:
        logger.error("AZURE_STORAGE_CONNECTION_STRING 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    container_name = os.environ.get("AZURE_VDR_CONTAINER_NAME", "amic-vdr")
    service_client = BlobServiceClient.from_connection_string(conn_str)
    container_client = service_client.get_container_client(container_name)

    # 컨테이너 존재 확인
    if not container_client.exists():
        logger.info("컨테이너 '%s' 생성 중...", container_name)
        container_client.create_container()

    return container_client


def _guess_mime_type(file_path: Path) -> str:
    """확장자 기반 MIME 타입 추정."""
    ext = file_path.suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".doc": "application/msword",
        ".xls": "application/vnd.ms-excel",
        ".ppt": "application/vnd.ms-powerpoint",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".zip": "application/zip",
    }
    return mime_map.get(ext, "application/octet-stream")


def main() -> None:
    parser = argparse.ArgumentParser(description="VDR 로컬 → Azure Blob 마이그레이션")
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=_DEFAULT_LOCAL_DIR,
        help="로컬 VDR 파일 디렉토리 (기본: /app/generated/vdr)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 업로드 없이 대상 파일 목록만 출력",
    )
    args = parser.parse_args()

    local_dir: Path = args.local_dir
    dry_run: bool = args.dry_run

    if not local_dir.exists():
        logger.error("로컬 VDR 디렉토리가 존재하지 않습니다: %s", local_dir)
        sys.exit(1)

    # DB 연결
    engine = _get_sync_engine()

    from sqlalchemy import text
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        # 절대 경로(기존 형식)를 가진 문서 조회
        rows = session.execute(
            text(
                "SELECT id, file_path, mime_type, sha256_hash "
                "FROM vdr_documents "
                "WHERE file_path LIKE '/app/generated/vdr/%' "
                "  AND status = 'ACTIVE' "
                "ORDER BY created_at"
            )
        ).fetchall()

        logger.info("마이그레이션 대상 문서: %d건", len(rows))

        if not rows:
            logger.info("마이그레이션할 문서가 없습니다.")
            engine.dispose()
            return

        if dry_run:
            logger.info("=== DRY RUN 모드 ===")
            for row in rows:
                doc_id, file_path, mime_type, _ = row
                local_path = Path(file_path)
                exists = local_path.exists()
                logger.info(
                    "  [%s] %s (존재: %s, MIME: %s)",
                    doc_id, file_path, exists, mime_type,
                )
            logger.info("=== DRY RUN 종료 — 실제 업로드 없음 ===")
            engine.dispose()
            return

        # Azure Blob 클라이언트
        container_client = _get_blob_client()

        from azure.storage.blob import ContentSettings

        success_count = 0
        fail_count = 0
        skip_count = 0

        for row in rows:
            doc_id, file_path, mime_type, expected_hash = row

            local_path = Path(file_path)
            if not local_path.exists():
                logger.warning("파일 없음 (건너뜀): %s", file_path)
                skip_count += 1
                continue

            # blob_name: 절대 경로 → 상대 경로 변환
            # /app/generated/vdr/txn-id/folder-id/uuid.ext → txn-id/folder-id/uuid.ext
            blob_name = str(local_path.relative_to("/app/generated/vdr"))

            try:
                # 1. 파일 읽기
                data = local_path.read_bytes()

                # 2. SHA256 해시 검증
                actual_hash = hashlib.sha256(data).hexdigest()
                if expected_hash and actual_hash != expected_hash:
                    logger.error(
                        "해시 불일치! doc_id=%s expected=%s actual=%s",
                        doc_id, expected_hash, actual_hash,
                    )
                    fail_count += 1
                    continue

                # 3. Azure Blob 업로드
                content_type = mime_type or _guess_mime_type(local_path)
                blob_client = container_client.get_blob_client(blob_name)
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                )

                # 4. DB file_path 업데이트 (절대 경로 → blob_name)
                session.execute(
                    text(
                        "UPDATE vdr_documents SET file_path = :blob_name "
                        "WHERE id = :doc_id"
                    ),
                    {"blob_name": blob_name, "doc_id": doc_id},
                )

                success_count += 1
                logger.info(
                    "  [OK] %s → %s (%d bytes)",
                    doc_id, blob_name, len(data),
                )

            except Exception as exc:
                logger.error(
                    "  [FAIL] %s — %s: %s",
                    doc_id, type(exc).__name__, exc,
                )
                fail_count += 1

        # 커밋
        session.commit()

    engine.dispose()

    logger.info("=" * 60)
    logger.info("마이그레이션 완료")
    logger.info("  성공: %d건", success_count)
    logger.info("  실패: %d건", fail_count)
    logger.info("  건너뜀 (파일 없음): %d건", skip_count)
    logger.info("=" * 60)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
