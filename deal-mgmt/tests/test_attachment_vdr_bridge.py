"""attachment_vdr_bridge 서비스 단위 테스트.

4개 시나리오:
1. 1차 심사 통과 → DIRECT 상태로 VDR 문서 생성
2. 1차 미통과 → 폴백 폴더 + 2차 심사 BackgroundTask 예약
3. VDR 미초기화 → 자동 초기화 후 정상 진행
4. best-effort 실패 → None 반환 (attachment 영향 없음)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import VdrClassificationStatus, VdrFolderCategory
from app.services.attachment_vdr_bridge import sync_attachment_to_vdr

pytestmark = pytest.mark.anyio


# ── Helpers ──────────────────────────────────────────────


def _make_db() -> AsyncMock:
    """테스트용 AsyncSession mock — commit/refresh/flush 모두 no-op."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_attachment(
    *,
    file_name: str = "재무제표.pdf",
    mime_type: str = "application/pdf",
    uploaded_by_email: str = "test@example.com",
) -> MagicMock:
    att = MagicMock()
    att.id = uuid.uuid4()
    att.file_name = file_name
    att.mime_type = mime_type
    att.uploaded_by_email = uploaded_by_email
    att.vdr_document_id = None
    return att


def _make_folder(
    *,
    category: VdrFolderCategory = VdrFolderCategory.CORPORATE,
    name: str = "기업 일반",
) -> MagicMock:
    f = MagicMock()
    f.id = uuid.uuid4()
    f.name = name
    f.category = category
    return f


def _make_doc(folder_id: uuid.UUID) -> MagicMock:
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.folder_id = folder_id
    doc.classification_status = None
    doc.classification_score = None
    return doc


# ── Test 1: 1차 심사 통과 → DIRECT ─────────────────────


@patch("app.services.attachment_vdr_bridge.vdr_service")
@patch("app.services.attachment_vdr_bridge.auto_route")
@patch("app.services.attachment_vdr_bridge.score_document")
@patch("app.services.attachment_vdr_bridge.audit_service")
async def test_sync_first_pass_direct(
    mock_audit: MagicMock,
    mock_score: MagicMock,
    mock_route: MagicMock,
    mock_vdr: MagicMock,
    tmp_path: Path,
) -> None:
    """1차 심사 통과 시 DIRECT 상태로 VDR 문서가 생성된다."""
    db = _make_db()
    txn_id = uuid.uuid4()
    attachment = _make_attachment()
    folder = _make_folder(category=VdrFolderCategory.FINANCIAL)
    doc = _make_doc(folder.id)

    # 파일 생성 — _UPLOAD_DIR 검증을 패치로 우회
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4 test content")

    # Mock 설정
    mock_vdr.init_vdr_folders = AsyncMock()
    mock_route.return_value = VdrFolderCategory.FINANCIAL
    mock_score.return_value = [(VdrFolderCategory.FINANCIAL, 85)]
    mock_vdr.resolve_folder_by_category = AsyncMock(return_value=folder)
    mock_vdr.check_duplicate_filename = AsyncMock(return_value=False)
    mock_vdr.resolve_unique_filename.return_value = attachment.file_name
    mock_vdr.upload_document = AsyncMock(return_value=doc)
    mock_audit.record = AsyncMock()
    bg_tasks = MagicMock()

    # _UPLOAD_DIR 패치 — tmp_path를 업로드 디렉토리로 인식
    with patch("app.services.attachment_vdr_bridge._UPLOAD_DIR", tmp_path):
        result = await sync_attachment_to_vdr(
            db=db,
            transaction_id=txn_id,
            attachment=attachment,
            file_path=file_path,
            background_tasks=bg_tasks,
        )

    assert result is not None
    assert result.classification_status == VdrClassificationStatus.DIRECT
    assert result.routing_score == 85
    assert result.needs_secondary is False
    assert result.folder is folder

    # upload_document이 auto_commit=False로 호출되었는지 확인 (C-1)
    mock_vdr.upload_document.assert_awaited_once()
    call_kwargs = mock_vdr.upload_document.call_args.kwargs
    assert call_kwargs.get("auto_commit") is False

    # attachment.vdr_document_id가 설정되었는지 확인
    assert attachment.vdr_document_id == doc.id


# ── Test 2: 1차 미통과 → 폴백 + 2차 심사 예약 ──────────


@patch("app.services.attachment_vdr_bridge.vdr_service")
@patch("app.services.attachment_vdr_bridge.auto_route")
@patch("app.services.attachment_vdr_bridge.score_document")
@patch("app.services.attachment_vdr_bridge.audit_service")
async def test_sync_fallback_with_secondary(
    mock_audit: MagicMock,
    mock_score: MagicMock,
    mock_route: MagicMock,
    mock_vdr: MagicMock,
    tmp_path: Path,
) -> None:
    """1차 미통과 시 PENDING_REVIEW + BackgroundTask로 2차 심사 예약."""
    db = _make_db()
    txn_id = uuid.uuid4()
    attachment = _make_attachment(file_name="misc_document.txt", mime_type="text/plain")
    fallback_folder = _make_folder(name="기업 일반")
    doc = _make_doc(fallback_folder.id)

    file_path = tmp_path / "misc_document.txt"
    file_path.write_bytes(b"some text content")

    mock_vdr.init_vdr_folders = AsyncMock()
    mock_route.return_value = None  # 1차 심사 미통과
    mock_score.return_value = [(VdrFolderCategory.CORPORATE, 30)]
    mock_vdr.resolve_fallback_folder = AsyncMock(return_value=fallback_folder)
    mock_vdr.upload_document = AsyncMock(return_value=doc)
    mock_audit.record = AsyncMock()
    bg_tasks = MagicMock()

    with patch("app.services.attachment_vdr_bridge._UPLOAD_DIR", tmp_path):
        result = await sync_attachment_to_vdr(
            db=db,
            transaction_id=txn_id,
            attachment=attachment,
            file_path=file_path,
            background_tasks=bg_tasks,
        )

    assert result is not None
    assert result.classification_status == VdrClassificationStatus.PENDING_REVIEW
    assert result.routing_score == 30
    assert result.needs_secondary is True
    assert result.folder is fallback_folder

    # 2차 심사 BackgroundTask가 예약되었는지 확인
    bg_tasks.add_task.assert_called_once()

    # auto_commit=False 확인 (C-1)
    call_kwargs = mock_vdr.upload_document.call_args.kwargs
    assert call_kwargs.get("auto_commit") is False


# ── Test 3: VDR 미초기화 → 자동 초기화 ─────────────────


@patch("app.services.attachment_vdr_bridge.vdr_service")
@patch("app.services.attachment_vdr_bridge.auto_route")
@patch("app.services.attachment_vdr_bridge.score_document")
@patch("app.services.attachment_vdr_bridge.audit_service")
async def test_sync_auto_initializes_vdr(
    mock_audit: MagicMock,
    mock_score: MagicMock,
    mock_route: MagicMock,
    mock_vdr: MagicMock,
    tmp_path: Path,
) -> None:
    """VDR 미초기화 상태에서 init_vdr_folders가 자동 호출된다."""
    db = _make_db()
    txn_id = uuid.uuid4()
    attachment = _make_attachment()
    folder = _make_folder()
    doc = _make_doc(folder.id)

    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4 content")

    # init_vdr_folders가 성공 (ValueError 미발생 = 첫 초기화)
    mock_vdr.init_vdr_folders = AsyncMock(return_value=None)
    mock_route.return_value = VdrFolderCategory.CORPORATE
    mock_score.return_value = [(VdrFolderCategory.CORPORATE, 70)]
    mock_vdr.resolve_folder_by_category = AsyncMock(return_value=folder)
    mock_vdr.check_duplicate_filename = AsyncMock(return_value=False)
    mock_vdr.resolve_unique_filename.return_value = attachment.file_name
    mock_vdr.upload_document = AsyncMock(return_value=doc)
    mock_audit.record = AsyncMock()
    bg_tasks = MagicMock()

    with patch("app.services.attachment_vdr_bridge._UPLOAD_DIR", tmp_path):
        result = await sync_attachment_to_vdr(
            db=db,
            transaction_id=txn_id,
            attachment=attachment,
            file_path=file_path,
            background_tasks=bg_tasks,
        )

    assert result is not None
    # init_vdr_folders가 호출되었는지 확인
    mock_vdr.init_vdr_folders.assert_awaited_once_with(db, txn_id)


# ── Test 4: best-effort 실패 → None ────────────────────


@patch("app.services.attachment_vdr_bridge.vdr_service")
@patch("app.services.attachment_vdr_bridge.auto_route")
@patch("app.services.attachment_vdr_bridge.score_document")
async def test_sync_failure_returns_none(
    mock_score: MagicMock,
    mock_route: MagicMock,
    mock_vdr: MagicMock,
    tmp_path: Path,
) -> None:
    """VDR 연동 중 예외 발생 시 None 반환 (attachment 영향 없음)."""
    db = _make_db()
    txn_id = uuid.uuid4()
    attachment = _make_attachment()

    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4 content")

    # init_vdr_folders에서 예외 발생
    mock_vdr.init_vdr_folders = AsyncMock(side_effect=RuntimeError("DB connection lost"))

    bg_tasks = MagicMock()

    with patch("app.services.attachment_vdr_bridge._UPLOAD_DIR", tmp_path):
        result = await sync_attachment_to_vdr(
            db=db,
            transaction_id=txn_id,
            attachment=attachment,
            file_path=file_path,
            background_tasks=bg_tasks,
        )

    assert result is None
    # attachment에 vdr_document_id가 설정되지 않았는지 확인
    assert attachment.vdr_document_id is None


# ── Test 5: 경로 순회 시도 차단 (M-5) ──────────────────


async def test_sync_path_traversal_blocked(
    tmp_path: Path,
) -> None:
    """업로드 디렉토리 외부 경로 시도 시 None 반환."""
    db = _make_db()
    txn_id = uuid.uuid4()
    attachment = _make_attachment()
    bg_tasks = MagicMock()

    # file_path가 _UPLOAD_DIR 밖을 가리킴
    outside_path = tmp_path / "outside" / "evil.pdf"
    outside_path.parent.mkdir(parents=True)
    outside_path.write_bytes(b"%PDF-1.4 malicious")

    # _UPLOAD_DIR을 tmp_path/uploads로 설정 → outside_path가 범위 밖
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    with patch("app.services.attachment_vdr_bridge._UPLOAD_DIR", upload_dir):
        result = await sync_attachment_to_vdr(
            db=db,
            transaction_id=txn_id,
            attachment=attachment,
            file_path=outside_path,
            background_tasks=bg_tasks,
        )

    assert result is None
