"""법률 문서 서비스 — docxtpl 기반 .docx 생성 및 CRUD."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import LegalDocStatus
from app.models.legal_document import LegalDocument
from app.schemas.legal_document import LegalDocumentCreate

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "legal"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "legal"
TEMPLATE_VERSION = "1.0"


# ── CRUD ─────────────────────────────────────────────────────────────────────


async def list_legal_documents(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[LegalDocument]:
    q = (
        select(LegalDocument)
        .where(LegalDocument.transaction_id == transaction_id)
        .order_by(LegalDocument.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_legal_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> LegalDocument:
    q = select(LegalDocument).where(
        LegalDocument.id == doc_id,
        LegalDocument.transaction_id == transaction_id,
    )
    result = await db.execute(q)
    doc = result.scalar_one_or_none()
    if not doc:
        raise DocumentNotFoundError("법률 문서를 찾을 수 없습니다.")
    return doc


async def create_legal_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: LegalDocumentCreate,
    created_by_email: str | None = None,
) -> LegalDocument:
    doc = LegalDocument(
        transaction_id=transaction_id,
        doc_type=body.doc_type,
        title=body.title,
        parameters=body.parameters,
        template_version=TEMPLATE_VERSION,
        created_by_email=created_by_email,
        status=LegalDocStatus.DRAFT,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 즉시 렌더링
    doc = await generate_document(db, doc)
    return doc


async def delete_legal_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> None:
    doc = await get_legal_document(db, transaction_id, doc_id)

    # 파일 삭제
    if doc.file_path:
        with contextlib.suppress(OSError):
            Path(doc.file_path).unlink(missing_ok=True)

    await db.delete(doc)
    await db.commit()


# ── docxtpl 렌더링 ────────────────────────────────────────────────────────────


async def generate_document(
    db: AsyncSession,
    legal_doc: LegalDocument,
) -> LegalDocument:
    """
    asyncio.to_thread을 통해 블로킹 docxtpl 렌더링을 수행한다.
    렌더링 완료 시 status=READY, 실패 시 status=FAILED로 업데이트한다.
    """
    template_path = TEMPLATE_DIR / f"{legal_doc.doc_type.lower()}_template.docx"

    # 템플릿 존재성 사전 검증 — 렌더링 스레드에서 실패하기 전에 조기 확인
    if not template_path.exists():
        legal_doc.status = LegalDocStatus.FAILED
        legal_doc.error_message = (
            f"템플릿 파일을 찾을 수 없습니다: {template_path.name}. "
            "관리자에게 문의하거나 'python scripts/create_legal_templates.py'를 실행하세요."
        )
        await db.commit()
        await db.refresh(legal_doc)
        return legal_doc

    doc_id = legal_doc.id
    doc_type = legal_doc.doc_type
    params = legal_doc.parameters or {}

    def _render() -> tuple[str, str, int]:
        """동기 렌더링 — 별도 스레드에서 실행."""
        from docxtpl import DocxTemplate

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tpl = DocxTemplate(str(template_path))
        tpl.render(params)
        fname = f"{doc_type}_{doc_id}.docx"
        out = OUTPUT_DIR / fname
        tpl.save(str(out))
        return fname, str(out), out.stat().st_size

    # GENERATING 상태로 먼저 저장
    legal_doc.status = LegalDocStatus.GENERATING
    await db.commit()

    try:
        fname, fpath, fsize = await asyncio.to_thread(_render)
        legal_doc.status = LegalDocStatus.READY
        legal_doc.file_name = fname
        legal_doc.file_path = fpath
        legal_doc.file_size_bytes = fsize
        legal_doc.error_message = None
    except Exception as exc:
        legal_doc.status = LegalDocStatus.FAILED
        legal_doc.error_message = str(exc)

    await db.commit()
    await db.refresh(legal_doc)
    return legal_doc


async def regenerate_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
    new_parameters: dict | None = None,
) -> LegalDocument:
    """파라미터를 갱신하고 문서를 재렌더링한다."""
    doc = await get_legal_document(db, transaction_id, doc_id)

    if new_parameters is not None:
        doc.parameters = new_parameters

    # 기존 파일 삭제
    if doc.file_path:
        with contextlib.suppress(OSError):
            Path(doc.file_path).unlink(missing_ok=True)

    doc.file_path = None
    doc.file_name = None
    doc.file_size_bytes = None

    return await generate_document(db, doc)
