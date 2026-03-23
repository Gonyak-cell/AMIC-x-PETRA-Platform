"""VDR 문서 텍스트 추출 + 캐싱 서비스.

VDR에 업로드된 문서(PDF, DOCX, XLSX 등)에서 텍스트를 추출하고,
vdr_text_caches 테이블에 캐싱하여 동일 문서의 반복 추출을 방지한다.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blob_storage import blob_client
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.models.vdr_text_cache import VdrTextCache
from app.ralph.parsers import parse_file
from app.ralph.parsers.base import ParsedFile, ParsedTable
from app.ralph.parsers.file_classifier import classify_file
from app.services.evidence_store_service import replace_document_chunks

logger = logging.getLogger(__name__)

# ── VDR 폴더 카테고리 → LDD 섹션 매핑 ────────────────────────────────────────

VDR_CATEGORY_TO_LDD_SECTION: dict[str, list[str]] = {
    "CORPORATE": ["GOVERNANCE"],
    "FINANCIAL": ["CAPITAL", "TAX"],
    "LEGAL": ["CONTRACTS", "LITIGATION"],
    "TAX": ["TAX"],
    "HR": ["LABOR"],
    "TECHNICAL": ["DATA_IT"],
    "COMMERCIAL": ["CONTRACTS"],
    "REAL_ESTATE": ["REAL_ESTATE"],
    "ENVIRONMENT": ["REAL_ESTATE", "PERMITS"],
    "IP": ["IP"],
    "INSURANCE": ["CONTRACTS"],
}


@dataclass
class VdrSourceFile:
    """ParsedFile + VDR 메타데이터 래퍼."""

    parsed: ParsedFile
    vdr_document_id: uuid.UUID
    vdr_folder_id: uuid.UUID
    vdr_category: str
    original_name: str


class TextExtractionService:
    """VDR 문서 텍스트 추출 + 캐싱."""

    async def extract_from_vdr_documents(
        self,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        folder_ids: list[uuid.UUID] | None = None,
        document_ids: list[uuid.UUID] | None = None,
        *,
        use_cache_only: bool = False,
    ) -> list[VdrSourceFile]:
        """VDR 문서를 ParsedFile로 변환한다 (캐시 활용).

        Args:
            db: 데이터베이스 세션
            transaction_id: 거래 ID
            folder_ids: 특정 폴더만 추출 (None이면 전체)
            document_ids: 특정 문서만 추출 (None이면 전체)

        Returns:
            VdrSourceFile 리스트 (ParsedFile + VDR 메타데이터)
        """
        # VDR 문서 조회 (ACTIVE만)
        stmt = (
            select(VdrDocument, VdrFolder)
            .join(VdrFolder, VdrDocument.folder_id == VdrFolder.id)
            .where(
                VdrDocument.transaction_id == transaction_id,
                VdrDocument.status == "ACTIVE",
            )
        )
        if folder_ids:
            stmt = stmt.where(VdrDocument.folder_id.in_(folder_ids))
        if document_ids:
            stmt = stmt.where(VdrDocument.id.in_(document_ids))

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            logger.warning("VDR 문서가 없습니다: transaction_id=%s", transaction_id)
            return []

        logger.info("VDR 문서 %d개 추출 시작: transaction_id=%s", len(rows), transaction_id)

        source_files: list[VdrSourceFile] = []
        for doc, folder in rows:
            parsed = await self._get_or_extract(db, doc, use_cache_only=use_cache_only)
            if parsed.is_valid or parsed.parse_error:
                source_files.append(
                    VdrSourceFile(
                        parsed=parsed,
                        vdr_document_id=doc.id,
                        vdr_folder_id=folder.id,
                        vdr_category=folder.category,
                        original_name=doc.original_name,
                    )
                )

        logger.info("VDR 문서 추출 완료: %d/%d 유효", len(source_files), len(rows))
        return source_files

    async def _get_or_extract(
        self,
        db: AsyncSession,
        doc: VdrDocument,
        *,
        use_cache_only: bool = False,
    ) -> ParsedFile:
        """캐시에 있으면 캐시 반환, 없거나 해시 불일치면 새로 추출."""
        stmt = select(VdrTextCache).where(VdrTextCache.vdr_document_id == doc.id)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        if cache and cache.sha256_hash == doc.sha256_hash and cache.is_valid:
            logger.debug("캐시 히트: %s (hash=%s)", doc.original_name, doc.sha256_hash[:8])
            parsed = self._cache_to_parsed_file(cache, doc)
            if not use_cache_only:
                try:
                    await replace_document_chunks(
                        db,
                        transaction_id=doc.transaction_id,
                        vdr_document_id=doc.id,
                        vdr_text_cache_id=cache.id,
                        chunks=list((parsed.metadata or {}).get("chunks") or []),
                    )
                except SQLAlchemyError as exc:
                    await db.rollback()
                    logger.warning(
                        "VDR cached chunk sync skipped for %s: %s",
                        doc.original_name,
                        exc,
                    )
            return parsed

        logger.debug("캐시 미스: %s → 추출 시작", doc.original_name)
        if use_cache_only:
            return self._build_placeholder_parsed_file(doc)
        return await self._extract_and_cache(db, doc, existing_cache=cache)

    def _cache_to_parsed_file(self, cache: VdrTextCache, doc: VdrDocument) -> ParsedFile:
        """캐시 엔트리를 ParsedFile로 변환."""
        tables: list[ParsedTable] = []
        if cache.tables_json:
            for t in cache.tables_json:
                tables.append(ParsedTable(headers=t.get("headers", []), rows=t.get("rows", [])))

        parsed = ParsedFile(
            source_path=doc.file_path or "",
            file_type=cache.file_type,
            text=cache.extracted_text or "",
            tables=tables,
            metadata={"chunks": cache.chunks_json or []},
            ddrl_sections=cache.ddrl_sections or [],
            parse_error=cache.parse_error,
        )
        self._ensure_trace_chunks(parsed)
        return parsed

    async def _extract_and_cache(
        self,
        db: AsyncSession,
        doc: VdrDocument,
        existing_cache: VdrTextCache | None = None,
    ) -> ParsedFile:
        """파일을 파싱하고 캐시에 저장."""
        file_path = doc.file_path or ""
        ext = Path(doc.original_name).suffix
        tmp_path: str | None = None

        # 동기 파서를 비동기로 실행
        try:
            await blob_client.ensure_initialized()
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp_path = tmp.name

            await blob_client.download_blob_to_file(file_path, Path(tmp_path))
            parsed = await asyncio.to_thread(parse_file, tmp_path)
        except FileNotFoundError:
            logger.warning("VDR source blob missing during extraction: %s", file_path)
            parsed = ParsedFile(
                source_path=file_path,
                file_type=ext.lstrip(".") or "unknown",
                parse_error="Source file not found in blob storage.",
            )
        except Exception as exc:
            logger.warning("VDR extraction preprocessing failed %s: %s", file_path, exc)
            parsed = ParsedFile(
                source_path=file_path,
                file_type=ext.lstrip(".") or "unknown",
                parse_error=str(exc),
            )
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    logger.debug("Temporary extraction file cleanup failed: %s", tmp_path, exc_info=True)

        # DDRL 섹션 분류
        parsed.ddrl_sections = classify_file(file_path, parsed)
        self._ensure_trace_chunks(parsed)

        # 테이블 직렬화
        tables_data = None
        if parsed.tables:
            tables_data = [{"headers": t.headers, "rows": t.rows} for t in parsed.tables]
        chunks_data = list((parsed.metadata or {}).get("chunks") or [])

        # 파일 타입 추출
        ext_name = doc.original_name.rsplit(".", 1)[-1].lower() if "." in doc.original_name else "unknown"

        if existing_cache:
            # 기존 캐시 업데이트
            existing_cache.sha256_hash = doc.sha256_hash
            existing_cache.file_type = ext_name
            existing_cache.extracted_text = parsed.text
            existing_cache.tables_json = tables_data
            existing_cache.chunks_json = chunks_data
            existing_cache.ddrl_sections = parsed.ddrl_sections
            existing_cache.parse_error = parsed.parse_error
            existing_cache.text_length = len(parsed.text)
            existing_cache.is_valid = parsed.is_valid
        else:
            # 신규 캐시 생성
            cache = VdrTextCache(
                vdr_document_id=doc.id,
                sha256_hash=doc.sha256_hash,
                file_type=ext_name,
                extracted_text=parsed.text,
                tables_json=tables_data,
                chunks_json=chunks_data,
                ddrl_sections=parsed.ddrl_sections,
                parse_error=parsed.parse_error,
                text_length=len(parsed.text),
                is_valid=parsed.is_valid,
            )
            db.add(cache)

        try:
            await db.flush()
            cache_record = existing_cache or cache
            await replace_document_chunks(
                db,
                transaction_id=doc.transaction_id,
                vdr_document_id=doc.id,
                vdr_text_cache_id=cache_record.id if cache_record else None,
                chunks=chunks_data,
            )
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning(
                "VDR text cache persistence skipped for %s: %s",
                doc.original_name,
                exc,
            )
        return parsed

    def _ensure_trace_chunks(self, parsed: ParsedFile) -> None:
        metadata = dict(parsed.metadata or {})
        existing_chunks = list(metadata.get("chunks") or [])
        if existing_chunks:
            metadata["chunks"] = existing_chunks
            parsed.metadata = metadata
            return

        text = parsed.text or ""
        if not text.strip():
            parsed.metadata = metadata
            return

        chunks: list[dict] = []
        if parsed.file_type == "pdf":
            current_page: int | None = None
            current_lines: list[str] = []
            ordinal = 0
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    if current_lines:
                        ordinal += 1
                        chunks.append(
                            {
                                "chunk_id": f"page-{current_page or ordinal}",
                                "locator_type": "page",
                                "page": current_page,
                                "ordinal": ordinal,
                                "text": "\n".join(current_lines),
                            }
                        )
                        current_lines = []
                    try:
                        current_page = int(line.split()[-1].rstrip("]"))
                    except ValueError:
                        current_page = None
                    continue
                current_lines.append(line)
            if current_lines:
                ordinal += 1
                chunks.append(
                    {
                        "chunk_id": f"page-{current_page or ordinal}",
                        "locator_type": "page",
                        "page": current_page,
                        "ordinal": ordinal,
                        "text": "\n".join(current_lines),
                    }
                )
        else:
            for ordinal, part in enumerate((line.strip() for line in text.splitlines() if line.strip()), start=1):
                chunks.append(
                    {
                        "chunk_id": f"chunk-{ordinal}",
                        "locator_type": "paragraph",
                        "paragraph": ordinal,
                        "ordinal": ordinal,
                        "text": part,
                    }
                )

        metadata["chunks"] = chunks
        parsed.metadata = metadata

    def _build_placeholder_parsed_file(self, doc: VdrDocument) -> ParsedFile:
        suffix = Path(doc.original_name).suffix.lower().lstrip(".") or "unknown"
        parsed = ParsedFile(
            source_path=doc.file_path or doc.original_name,
            file_type=suffix,
            text="",
            metadata={},
            ddrl_sections=classify_file(doc.original_name),
            parse_error="cache_miss_preview_placeholder",
        )
        self._ensure_trace_chunks(parsed)
        return parsed


def build_source_map(
    source_files: list[VdrSourceFile],
) -> dict[str, list[VdrSourceFile]]:
    """VDR 카테고리 + 키워드 이중 매핑으로 섹션별 source_map 구축.

    Returns:
        {section_type: [VdrSourceFile, ...]} 형태의 매핑
    """
    source_map: dict[str, list[VdrSourceFile]] = {}

    for vsf in source_files:
        # 1차: VDR 폴더 카테고리 기반 매핑
        category_sections = VDR_CATEGORY_TO_LDD_SECTION.get(vsf.vdr_category, [])

        # 2차: 파일 분류기 키워드 기반 매핑
        keyword_sections = vsf.parsed.ddrl_sections

        # 합산 (중복 제거)
        all_sections = set(category_sections) | set(keyword_sections)

        # 매핑 없으면 파일 타입에 따라 기본 섹션 할당
        if not all_sections:
            all_sections = {"GOVERNANCE"}  # 분류 불가 시 기본 섹션

        for section in all_sections:
            source_map.setdefault(section, []).append(vsf)

    logger.info(
        "source_map 구축 완료: %s",
        {k: len(v) for k, v in source_map.items()},
    )
    return source_map
