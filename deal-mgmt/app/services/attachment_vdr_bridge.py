"""첨부파일 → VDR 자동 연동 서비스.

마케팅 자료 탭 등에서 첨부 파일 업로드 시 VDR에도 자동으로 문서를 등록하고
AI 기반 폴더 분류를 수행한다.  연동은 best-effort — 실패 시에도 attachment 자체는 유지.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blob_storage import blob_client
from app.models.attachment import Attachment
from app.models.enums import AuditAction, VdrClassificationStatus
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.services import audit_service, vdr_service
from app.services.vdr_categorization_service import auto_route, score_document

logger = logging.getLogger(__name__)

# 업로드 디렉토리 — file_path 경로 검증용 (M-5)
_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "attachments"


async def _record_vdr_sync_audit(
    db: AsyncSession,
    attachment: Attachment,
    doc: VdrDocument,
    folder: VdrFolder,
    classification_status: VdrClassificationStatus,
) -> None:
    """VDR 자동 연동 감사 로그 기록."""
    await audit_service.record(
        db,
        entity_type="VdrDocument",
        entity_id=doc.id,
        action=AuditAction.CREATE,
        actor_email=attachment.uploaded_by_email,
        new_value={
            "source": "attachment_vdr_bridge",
            "attachment_id": str(attachment.id),
            "folder_name": folder.name,
            "classification_status": classification_status.value,
        },
    )


@dataclass
class VdrSyncResult:
    """VDR 연동 결과."""

    document: VdrDocument
    folder: VdrFolder
    category: str | None
    classification_status: VdrClassificationStatus
    routing_score: int  # 1차 심사 점수 (0–100)
    needs_secondary: bool  # 2차 심사 필요 여부


async def _ensure_vdr_initialized(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> None:
    """VDR이 초기화되지 않았으면 기본 폴더를 자동 생성한다."""
    try:
        await vdr_service.init_vdr_folders(db, transaction_id)
        logger.info("VDR 자동 초기화 완료: txn=%s", transaction_id)
    except ValueError:
        # "이미 초기화되어 있습니다" — 정상 케이스
        pass


async def sync_attachment_to_vdr(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    attachment: Attachment,
    file_path: Path,
) -> VdrSyncResult | None:
    """첨부 파일을 VDR에 자동 연동한다.

    1) file_path 경로 검증 (경로 순회 방지)
    2) VDR 미초기화 시 자동 초기화
    3) 1차 심사(메타데이터 스코어링)로 폴더 배치
    4) 1차 미통과 시 2차 심사(LLM) 비동기 예약
    5) attachment.vdr_document_id 설정

    Args:
        file_path: 디스크에 저장된 첨부파일 경로 (메모리 적재 최소화)

    Returns:
        VdrSyncResult — 성공 시
        None — 연동 실패 시 (attachment 자체는 영향 없음)
    """
    doc: VdrDocument | None = None
    try:
        # M-5: 경로 순회 방지 — file_path가 업로드 디렉토리 내에 있는지 검증
        resolved = file_path.resolve()
        if not resolved.is_relative_to(_UPLOAD_DIR.resolve()):
            logger.error(
                "경로 순회 시도 차단: file_path=%s, expected_dir=%s",
                file_path,
                _UPLOAD_DIR,
            )
            return None

        # VDR 초기화 확인/자동 생성
        await _ensure_vdr_initialized(db, transaction_id)

        # 파일 콘텐츠 읽기 — VDR blob 저장에 필요
        file_content = await asyncio.to_thread(file_path.read_bytes)

        # 1차 심사
        ext = Path(attachment.file_name).suffix.lower()
        scores = score_document(attachment.file_name, ext, attachment.mime_type, len(file_content))
        top_score = scores[0][1] if scores else 0
        routed_category = auto_route(attachment.file_name, ext, attachment.mime_type, len(file_content))

        if routed_category is not None:
            # 1차 심사 통과 → 해당 카테고리 폴더에 직접 배치
            folder = await vdr_service.resolve_folder_by_category(db, transaction_id, routed_category)
            if folder is None:
                folder = await vdr_service.resolve_fallback_folder(db, transaction_id)
            if folder is None:
                logger.error("VDR 폴더 없음: txn=%s, category=%s", transaction_id, routed_category)
                return None

            has_dup = await vdr_service.check_duplicate_filename(
                db,
                transaction_id,
                folder.id,
                attachment.file_name,
            )
            final_name = vdr_service.resolve_unique_filename(attachment.file_name, has_dup)

            # C-1 fix: auto_commit=False로 이중 커밋 방지 — 단일 커밋으로 통합
            doc = await vdr_service.upload_document(
                db=db,
                transaction_id=transaction_id,
                folder_id=folder.id,
                original_name=final_name,
                file_content=file_content,
                mime_type=attachment.mime_type,
                uploaded_by_email=attachment.uploaded_by_email,
                description=f"첨부파일 자동 연동 (attachment_id={attachment.id})",
                _folder_verified=True,
                auto_commit=False,
            )
            doc.classification_status = VdrClassificationStatus.DIRECT
            doc.classification_score = top_score

            # attachment ↔ VDR 문서 참조 연결
            attachment.vdr_document_id = doc.id

            await _record_vdr_sync_audit(db, attachment, doc, folder, VdrClassificationStatus.DIRECT)
            await db.commit()
            await db.refresh(doc)

            return VdrSyncResult(
                document=doc,
                folder=folder,
                category=routed_category.value if routed_category else None,
                classification_status=VdrClassificationStatus.DIRECT,
                routing_score=top_score,
                needs_secondary=False,
            )
        else:
            # 1차 미통과 → CORPORATE 폴백 + 2차 심사 예약
            fallback = await vdr_service.resolve_fallback_folder(db, transaction_id)
            if fallback is None:
                logger.error("VDR 폴백 폴더 없음: txn=%s", transaction_id)
                return None

            # C-1 fix: auto_commit=False로 이중 커밋 방지 — 단일 커밋으로 통합
            doc = await vdr_service.upload_document(
                db=db,
                transaction_id=transaction_id,
                folder_id=fallback.id,
                original_name=attachment.file_name,
                file_content=file_content,
                mime_type=attachment.mime_type,
                uploaded_by_email=attachment.uploaded_by_email,
                description=f"첨부파일 자동 연동 (attachment_id={attachment.id})",
                _folder_verified=True,
                auto_commit=False,
            )
            doc.classification_status = VdrClassificationStatus.PENDING_REVIEW
            doc.classification_score = top_score

            # attachment ↔ VDR 문서 참조 연결
            attachment.vdr_document_id = doc.id

            await _record_vdr_sync_audit(db, attachment, doc, fallback, VdrClassificationStatus.PENDING_REVIEW)
            await db.commit()
            await db.refresh(doc)

            # 2차 심사 비동기 디스패치
            from app.services.vdr_classification_service import run_secondary_classification

            await run_secondary_classification(doc.id, transaction_id)

            return VdrSyncResult(
                document=doc,
                folder=fallback,
                category=None,
                classification_status=VdrClassificationStatus.PENDING_REVIEW,
                routing_score=top_score,
                needs_secondary=True,
            )

    except Exception:
        # E-02: 세션 정리 — auto_commit=False 사용 시 호출자 책임
        try:
            await db.rollback()
        except Exception:
            pass

        # E-01: 고아 blob 정리 — doc이 생성됐으면 blob 삭제 시도
        if doc is not None and getattr(doc, "file_path", None):
            try:
                await blob_client.delete_blob(doc.file_path)
                logger.info("고아 blob 삭제 성공: %s", doc.file_path)
            except Exception as cleanup_err:
                logger.warning("고아 blob 삭제 실패: %s (error=%s)", doc.file_path, cleanup_err)

        logger.exception(
            "VDR 연동 실패: txn=%s, attachment=%s, file=%s",
            transaction_id,
            attachment.id,
            attachment.file_name,
        )
        return None
