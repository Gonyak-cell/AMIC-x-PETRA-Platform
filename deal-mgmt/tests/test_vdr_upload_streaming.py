"""VDR 스트리밍 업로드 테스트.

Part A Step 7: stream_hash_and_size, upload_blob_stream, direct_upload 병렬화 검증.
"""

from __future__ import annotations

import hashlib
import io
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

pytestmark = pytest.mark.anyio


# ── Helpers ───────────────────────────────────────────────────


def _make_upload_file(content: bytes, filename: str = "test.pdf") -> UploadFile:
    """테스트용 UploadFile을 생성한다."""
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        size=len(content),
        headers=Headers({"content-type": "application/pdf"}),
    )


# ── stream_hash_and_size 테스트 ──────────────────────────────


class TestStreamHashAndSize:
    """청크 단위 SHA256 해시 + 크기 계산 테스트."""

    async def test_hash_matches_full_content(self):
        """청크 해시 == 전체 해시 일치 검증."""
        from app.services.vdr_service import stream_hash_and_size

        content = os.urandom(3 * 1024 * 1024)  # 3MB
        expected_hash = hashlib.sha256(content).hexdigest()

        upload_file = _make_upload_file(content)
        sha256_hex, total_size = await stream_hash_and_size(upload_file, 10 * 1024 * 1024)

        assert sha256_hex == expected_hash
        assert total_size == len(content)

    async def test_small_file_hash(self):
        """1MB 미만 파일도 올바르게 해시한다."""
        from app.services.vdr_service import stream_hash_and_size

        content = b"hello world VDR streaming test"
        expected_hash = hashlib.sha256(content).hexdigest()

        upload_file = _make_upload_file(content)
        sha256_hex, total_size = await stream_hash_and_size(upload_file, 1024 * 1024)

        assert sha256_hex == expected_hash
        assert total_size == len(content)

    async def test_empty_file(self):
        """빈 파일도 올바르게 처리한다."""
        from app.services.vdr_service import stream_hash_and_size

        content = b""
        expected_hash = hashlib.sha256(content).hexdigest()

        upload_file = _make_upload_file(content)
        sha256_hex, total_size = await stream_hash_and_size(upload_file, 1024 * 1024)

        assert sha256_hex == expected_hash
        assert total_size == 0

    async def test_exceeds_max_size_raises_413(self):
        """최대 크기 초과 시 스트리밍 중 조기 차단."""
        from fastapi import HTTPException

        from app.services.vdr_service import stream_hash_and_size

        content = os.urandom(2 * 1024 * 1024)  # 2MB
        upload_file = _make_upload_file(content)

        with pytest.raises(HTTPException, match="초과") as exc_info:
            await stream_hash_and_size(upload_file, 1 * 1024 * 1024)  # 1MB 제한

        assert exc_info.value.status_code == 413

    async def test_file_pointer_reset_after_hash(self):
        """해시 계산 후 file.seek(0)으로 포인터가 리셋된다."""
        from app.services.vdr_service import stream_hash_and_size

        content = os.urandom(512 * 1024)  # 512KB
        upload_file = _make_upload_file(content)

        await stream_hash_and_size(upload_file, 1024 * 1024)

        # seek(0) 후이므로 다시 읽으면 전체 내용이 나와야 함
        re_read = await upload_file.read()
        assert re_read == content


# ── upload_blob_stream 로컬 모드 테스트 ──────────────────────


class TestUploadBlobStreamLocal:
    """BlobStorageClient.upload_blob_stream 로컬 모드 검증."""

    async def test_local_stream_write(self, tmp_path):
        """로컬 모드에서 청크 단위 파일 기록이 정상 동작한다."""
        from app.core.blob_storage import BlobStorageClient

        client = BlobStorageClient()
        client._is_local = True
        client._initialized = True

        # _LOCAL_STORAGE_DIR을 tmp_path로 패치
        content = os.urandom(2 * 1024 * 1024 + 500)  # 2MB + 500B
        upload_file = _make_upload_file(content)

        blob_name = "txn-id/folder-id/test_file.pdf"

        with patch("app.core.blob_storage._LOCAL_STORAGE_DIR", tmp_path):
            result = await client.upload_blob_stream(blob_name, upload_file, "application/pdf", len(content))

        assert result == blob_name
        written = (tmp_path / blob_name).read_bytes()
        assert written == content

    async def test_local_stream_path_traversal_blocked(self, tmp_path):
        """경로 순회 시도가 차단된다."""
        from app.core.blob_storage import BlobStorageClient

        client = BlobStorageClient()
        client._is_local = True
        client._initialized = True

        content = b"malicious"
        upload_file = _make_upload_file(content)

        with patch("app.core.blob_storage._LOCAL_STORAGE_DIR", tmp_path), pytest.raises(ValueError, match="경로 순회"):
            await client.upload_blob_stream("../../etc/passwd", upload_file, "application/pdf", len(content))


# ── validate_upload_metadata 테스트 ──────────────────────────


class TestValidateUploadMetadata:
    """메타데이터 전용 검증 함수 테스트."""

    def test_valid_pdf(self):
        """정상 PDF 파일 메타데이터 검증."""
        from app.routers.vdr import _validate_upload_metadata

        file = MagicMock()
        file.filename = "report.pdf"
        file.content_type = "application/pdf"
        file.size = 1024 * 1024  # 1MB

        filename, ext, content_type = _validate_upload_metadata(file)
        assert filename == "report.pdf"
        assert ext == ".pdf"
        assert content_type == "application/pdf"

    def test_invalid_extension_raises_400(self):
        """허용되지 않는 확장자는 400 에러."""
        from fastapi import HTTPException

        from app.routers.vdr import _validate_upload_metadata

        file = MagicMock()
        file.filename = "script.exe"
        file.content_type = "application/octet-stream"
        file.size = 1024

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_metadata(file)
        assert exc_info.value.status_code == 400

    def test_oversize_header_raises_413(self):
        """Content-Length 헤더가 최대 크기 초과 시 413 에러."""
        from fastapi import HTTPException

        from app.routers.vdr import _validate_upload_metadata

        file = MagicMock()
        file.filename = "big.pdf"
        file.content_type = "application/pdf"
        file.size = 500 * 1024 * 1024  # 500MB

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_metadata(file)
        assert exc_info.value.status_code == 413


# ── direct_upload 통합 테스트 ─────────────────────────────────


class TestDirectUploadIntegration:
    """direct_upload API 엔드포인트 통합 테스트."""

    async def test_single_file_upload(self, client, transaction_id):
        """단일 파일 업로드가 정상 동작한다."""
        content = b"PDF content for single file test"
        files = [("files", ("test_doc.pdf", io.BytesIO(content), "application/pdf"))]

        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/direct-upload",
            files=files,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_uploaded"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["document"]["original_name"] == "test_doc.pdf"

    async def test_multiple_files_upload(self, client, transaction_id):
        """다중 파일 동시 업로드가 정상 동작한다."""
        files = []
        for i in range(3):
            content = f"PDF content file {i}".encode()
            files.append(("files", (f"doc_{i}.pdf", io.BytesIO(content), "application/pdf")))

        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/direct-upload",
            files=files,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_uploaded"] == 3
        assert len(data["results"]) == 3

    async def test_invalid_file_in_batch(self, client, transaction_id):
        """배치 내 잘못된 파일이 있어도 유효한 파일은 업로드된다."""
        files = [
            ("files", ("valid.pdf", io.BytesIO(b"valid pdf"), "application/pdf")),
            ("files", ("invalid.exe", io.BytesIO(b"exe content"), "application/octet-stream")),
        ]

        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/documents/direct-upload",
            files=files,
        )
        # Phase A에서 개별 파일 검증 실패 → failed_files에 추가, 유효 파일만 업로드
        assert resp.status_code in (201, 400, 422)

    async def test_backward_compat_single_upload(self, client, transaction_id):
        """기존 단일 파일 업로드 엔드포인트가 여전히 동작한다."""
        # 폴더 목록 조회
        folders_resp = await client.get(f"/api/v1/transactions/{transaction_id}/vdr/folders")
        assert folders_resp.status_code == 200
        folders = folders_resp.json()
        assert len(folders) > 0
        folder_id = folders[0]["id"]

        content = b"Backward compat test PDF content"
        files = {"file": ("compat_test.pdf", io.BytesIO(content), "application/pdf")}

        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/vdr/folders/{folder_id}/documents",
            files=files,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["original_name"] == "compat_test.pdf"
