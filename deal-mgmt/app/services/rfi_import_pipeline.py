"""RFI V2 역방향 Excel Import 파이프라인 — 원자적 처리 + 퍼지 매칭.

Step 0: 트랜잭션 시작 (All-or-Nothing)
Step 1: 유효성 검사 — item_id 파싱, CLOSED 거부, 변동 행 발췌
Step 2: 낙관적 락 검증 — version 비교
Step 3: 스레드 누적 — 답변 INSERT + 상태 전환
Step 4: 퍼지 매칭 — rapidfuzz로 파일 자동 매핑
Step 5: 결과 반환
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import UTC, datetime

from rapidfuzz import fuzz
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, RFIAuthorRole, RFICategoryV2, RFIItemStatusV2, RFIPriority
from app.models.rfi_attachment import RFIAttachment
from app.models.rfi_item_v2 import RFIItemV2
from app.models.rfi_thread import RFIThread
from app.schemas.rfi_v2 import RFIExcelImportResult, RFIItemCreateV2
from app.services import audit_service, rfi_v2_service

logger = logging.getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────────

_FUZZY_THRESHOLD = 80  # fuzz.ratio 최소 점수
_ITEM_ID_COL = 0  # A열: item_id (숨김)
_VERSION_COL = 1  # B열: version (숨김)
_ANSWER_COL = 8  # I열: 답변 입력란 (0-indexed)
_FILE_REF_COL = 9  # J열: 증빙 파일명/인덱스 기재란


_QUESTION_HEADERS = ("question", "질문", "질의", "요청", "요청자료", "request", "rfi", "자료요청")
_ANSWER_HEADERS = ("answer", "답변", "회사답변", "수령현황", "response", "reply")
_CATEGORY_HEADERS = ("category", "분류", "구분", "area")
_PRIORITY_HEADERS = ("priority", "우선", "중요")
_TARGET_DOC_HEADERS = ("target", "document", "자료", "문서")
_FILE_REF_HEADERS = ("file", "attachment", "첨부", "증빙", "evidence", "비고")


def _normalize_header(value: object) -> str:
    return str(value or "").strip().lower()


def _find_header(headers: list[str], keywords: tuple[str, ...]) -> int | None:
    for index, header in enumerate(headers):
        if any(keyword in header for keyword in keywords):
            return index
    return None


def _cell_text(row: tuple[object, ...], index: int | None) -> str:
    if index is None or index < 0 or index >= len(row):
        return ""
    return str(row[index] or "").strip()


def _detect_external_columns(headers: list[str]) -> dict[str, int] | None:
    question_col = _find_header(headers, ("question", "질문", "질의", "요청자료", "자료요청"))
    if question_col is None:
        question_col = _find_header(headers, ("request", "요청"))
    if question_col is None:
        return None
    if len(headers[question_col]) > 40:
        return None
    item_id_col = _find_header(headers, ("item_id", "item id"))
    if item_id_col == 0:
        return None
    answer_col = _find_header(headers, _ANSWER_HEADERS)
    category_col = _find_header(headers, _CATEGORY_HEADERS)
    priority_col = _find_header(headers, _PRIORITY_HEADERS)
    target_doc_col = _find_header(headers, _TARGET_DOC_HEADERS)
    file_ref_col = _find_header(headers, _FILE_REF_HEADERS)
    if target_doc_col == question_col:
        target_doc_col = None
    supporting_cols = (answer_col, category_col, priority_col, target_doc_col, file_ref_col)
    if all(col is None for col in supporting_cols):
        return None
    return {
        "question": question_col,
        "answer": answer_col if answer_col is not None else -1,
        "category": category_col if category_col is not None else -1,
        "priority": priority_col if priority_col is not None else -1,
        "target_doc": target_doc_col if target_doc_col is not None else -1,
        "file_ref": file_ref_col if file_ref_col is not None else -1,
    }


def _parse_external_category(raw_value: str) -> RFICategoryV2:
    lowered = raw_value.lower()
    keyword_map = {
        RFICategoryV2.FINANCIAL: ("financial", "finance", "재무", "회계", "원장", "잔액"),
        RFICategoryV2.LEGAL: ("legal", "법무", "계약", "소송"),
        RFICategoryV2.TAX: ("tax", "세무", "세금"),
        RFICategoryV2.CORPORATE: ("corporate", "법인", "등기", "사업자"),
        RFICategoryV2.HR: ("hr", "인사", "급여", "임직원"),
        RFICategoryV2.COMMERCIAL: ("commercial", "영업", "매출", "고객"),
        RFICategoryV2.IP: ("ip", "지식재산", "상표", "특허"),
        RFICategoryV2.IT: ("it", "시스템", "보안"),
        RFICategoryV2.VALUATION: ("valuation", "밸류", "가치평가"),
    }
    for category, keywords in keyword_map.items():
        if any(keyword in lowered or keyword in raw_value for keyword in keywords):
            return category
    try:
        return RFICategoryV2(raw_value.upper())
    except ValueError:
        return RFICategoryV2.OTHER


def _parse_external_priority(raw_value: str) -> RFIPriority:
    lowered = raw_value.lower()
    if lowered in {"high", "h", "높음"} or "긴급" in raw_value or "상" in raw_value:
        return RFIPriority.HIGH
    if lowered in {"low", "l", "낮음"} or "하" in raw_value:
        return RFIPriority.LOW
    return RFIPriority.MEDIUM


async def _import_external_rfi_workbook(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rows: list[tuple[object, ...]],
    columns: dict[str, int],
    *,
    author_email: str,
    first_data_row_number: int = 2,
) -> RFIExcelImportResult:
    warnings: list[str] = []
    errors: list[dict[str, str | int]] = []
    created_threads: list[tuple[RFIThread, str]] = []
    items_created = 0
    threads_created = 0

    for excel_row, row in enumerate(rows, start=first_data_row_number):
        question = _cell_text(row, columns.get("question"))
        if not question:
            continue
        try:
            item = await rfi_v2_service.create_item(
                db,
                txn_id,
                RFIItemCreateV2(
                    category=_parse_external_category(_cell_text(row, columns.get("category"))),
                    priority=_parse_external_priority(_cell_text(row, columns.get("priority"))),
                    target_doc=_cell_text(row, columns.get("target_doc")) or None,
                    question_text=question,
                ),
                created_by=author_email,
            )
            items_created += 1
        except Exception as exc:
            logger.exception("External RFI item creation failed: txn=%s row=%s", txn_id, excel_row)
            errors.append({"row": excel_row, "reason": str(exc)})
            continue

        answer = _cell_text(row, columns.get("answer"))
        file_ref = _cell_text(row, columns.get("file_ref"))
        if answer:
            thread = RFIThread(
                item_id=item.id,
                round_num=1,
                author_email=author_email,
                author_role=RFIAuthorRole.TARGET,
                content_text=answer,
                is_published=True,
            )
            db.add(thread)
            item.current_status = RFIItemStatusV2.ANSWERED
            item.version += 1
            item.updated_at = datetime.now(UTC)
            threads_created += 1
            created_threads.append((thread, file_ref))

    if not items_created and not errors:
        warnings.append("No question rows were found in the external RFI workbook.")

    await db.flush()
    for thread, _ in created_threads:
        await audit_service.record(
            db,
            entity_type="rfi_thread",
            entity_id=thread.id,
            action=AuditAction.CREATE,
            actor_email=author_email,
        )

    files_matched = 0
    files_unmatched = 0
    if created_threads:
        unassigned_result = await db.execute(
            select(RFIAttachment).where(
                RFIAttachment.transaction_id == txn_id,
                RFIAttachment.is_mapped.is_(False),
            )
        )
        unassigned_files = list(unassigned_result.scalars().all())
        for thread, file_ref_text in created_threads:
            if not file_ref_text:
                continue
            file_refs = [f.strip() for f in file_ref_text.split(",") if f.strip()]
            for ref in file_refs:
                candidates = [
                    (attachment, fuzz.ratio(ref, attachment.file_name))
                    for attachment in unassigned_files
                    if fuzz.ratio(ref, attachment.file_name) >= _FUZZY_THRESHOLD
                ]
                if len(candidates) == 1:
                    matched_attachment = candidates[0][0]
                    matched_attachment.thread_id = thread.id
                    matched_attachment.item_id = thread.item_id
                    matched_attachment.is_mapped = True
                    unassigned_files.remove(matched_attachment)
                    files_matched += 1
                else:
                    files_unmatched += 1

    await db.flush()
    return RFIExcelImportResult(
        mode="external_workbook",
        items_updated=0,
        items_created=items_created,
        threads_created=threads_created,
        files_matched=files_matched,
        files_unmatched=files_unmatched,
        warnings=warnings,
        errors=errors,
        conflicts=[],
    )


async def import_rfi_excel(
    db: AsyncSession,
    txn_id: uuid.UUID,
    file_bytes: bytes,
    *,
    author_email: str = "target@import",
) -> RFIExcelImportResult:
    """역방향 Excel Import — 원자적 처리.

    에러/충돌이 1건이라도 있으면 DB 변경 없이 결과만 반환 (롤백).
    """
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl이 설치되지 않았습니다: pip install openpyxl") from exc

    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return RFIExcelImportResult(
            items_updated=0,
            threads_created=0,
            files_matched=0,
            files_unmatched=0,
            errors=[{"row": 0, "reason": "엑셀 시트를 찾을 수 없습니다"}],
            conflicts=[],
        )

    worksheet_rows = list(ws.iter_rows(values_only=True))
    external_columns: dict[str, int] | None = None
    external_header_index: int | None = None
    for row_index, candidate_header in enumerate(worksheet_rows[:30]):
        headers = [_normalize_header(value) for value in candidate_header]
        external_columns = _detect_external_columns(headers)
        if external_columns is not None:
            external_header_index = row_index
            break
    if external_columns is not None:
        result = await _import_external_rfi_workbook(
            db,
            txn_id,
            worksheet_rows[(external_header_index or 0) + 1 :],
            external_columns,
            author_email=author_email,
            first_data_row_number=(external_header_index or 0) + 2,
        )
        wb.close()
        return result
    wb.close()

    rows = worksheet_rows[1:]
    if not rows:
        return RFIExcelImportResult(
            items_updated=0, threads_created=0, files_matched=0, files_unmatched=0, errors=[], conflicts=[]
        )

    # ── Step 1: 유효성 검사 + 변동 행 발췌 ──────────────────

    errors: list[dict[str, str | int]] = []
    conflicts: list[dict[str, str | int]] = []
    changed_rows: list[tuple[int, uuid.UUID, int, str, str]] = []
    # (excel_row_num, item_id, version, answer_text, file_ref_text)

    for idx, row in enumerate(rows, start=2):
        raw_item_id = row[_ITEM_ID_COL] if len(row) > _ITEM_ID_COL else None
        raw_version = row[_VERSION_COL] if len(row) > _VERSION_COL else None
        raw_answer = row[_ANSWER_COL] if len(row) > _ANSWER_COL else None
        raw_file_ref = row[_FILE_REF_COL] if len(row) > _FILE_REF_COL else None

        # item_id 파싱
        if not raw_item_id:
            continue  # 빈 행 건너뛰기
        try:
            item_id = uuid.UUID(str(raw_item_id))
        except ValueError:
            errors.append({"row": idx, "reason": f"유효하지 않은 item_id: {raw_item_id}"})
            continue

        # version 파싱
        try:
            version = int(raw_version) if raw_version is not None else 0
        except (ValueError, TypeError):
            errors.append({"row": idx, "reason": f"유효하지 않은 version: {raw_version}"})
            continue

        # 답변 변동 감지 — 빈 칸이면 건너뛰기
        answer_text = str(raw_answer).strip() if raw_answer else ""
        if not answer_text:
            continue

        file_ref_text = str(raw_file_ref).strip() if raw_file_ref else ""
        changed_rows.append((idx, item_id, version, answer_text, file_ref_text))

    if not changed_rows and not errors:
        return RFIExcelImportResult(
            items_updated=0, threads_created=0, files_matched=0, files_unmatched=0, errors=[], conflicts=[]
        )

    # ── Step 1b: CLOSED 상태 및 존재 여부 검증 ────────────────

    item_ids = [row[1] for row in changed_rows]
    if item_ids:
        result = await db.execute(
            select(RFIItemV2).where(
                RFIItemV2.id.in_(item_ids),
                RFIItemV2.transaction_id == txn_id,
            )
        )
        db_items = {item.id: item for item in result.scalars().all()}
    else:
        db_items = {}

    valid_rows: list[tuple[int, RFIItemV2, str, str]] = []
    # (excel_row_num, db_item, answer_text, file_ref_text)

    for excel_row, item_id, version, answer_text, file_ref_text in changed_rows:
        item = db_items.get(item_id)
        if item is None:
            errors.append({"row": excel_row, "reason": f"DB에서 항목을 찾을 수 없습니다: {item_id}"})
            continue
        if item.is_deleted:
            errors.append({"row": excel_row, "reason": "삭제된 항목입니다"})
            continue
        if item.current_status == RFIItemStatusV2.CLOSED:
            errors.append({"row": excel_row, "reason": "CLOSED 상태의 항목은 수정할 수 없습니다"})
            continue

        # ── Step 2: 낙관적 락 검증 ───────────────────────────
        if item.version != version:
            conflicts.append(
                {
                    "row": excel_row,
                    "reason": f"버전 충돌 (엑셀: {version}, DB: {item.version}) — 새로고침 후 다시 시도하세요",
                }
            )
            continue

        valid_rows.append((excel_row, item, answer_text, file_ref_text))

    # 에러/충돌이 있으면 전체 롤백 (All-or-Nothing)
    if errors or conflicts:
        return RFIExcelImportResult(
            items_updated=0,
            threads_created=0,
            files_matched=0,
            files_unmatched=0,
            errors=errors,
            conflicts=conflicts,
        )

    # ── Step 3: 스레드 누적 ─────────────────────────────────

    threads_created = 0
    updated_item_ids: set[uuid.UUID] = set()
    created_threads: list[tuple[RFIThread, str]] = []
    # (thread, file_ref_text) — Step 4에서 매핑용

    # 배치로 모든 item의 max round_num 조회 (N+1 방지)
    valid_item_ids = [item.id for _, item, _, _ in valid_rows]
    max_rounds: dict[uuid.UUID, int] = {}
    if valid_item_ids:
        round_result = await db.execute(
            select(RFIThread.item_id, func.max(RFIThread.round_num))
            .where(RFIThread.item_id.in_(valid_item_ids))
            .group_by(RFIThread.item_id)
        )
        max_rounds = {row[0]: row[1] or 0 for row in round_result.all()}

    for _excel_row, item, answer_text, file_ref_text in valid_rows:
        next_round = max_rounds.get(item.id, 0) + 1
        # 같은 item에 대해 여러 행이 있을 수 있으므로 카운터 증가
        max_rounds[item.id] = next_round

        thread = RFIThread(
            item_id=item.id,
            round_num=next_round,
            author_email=author_email,
            author_role=RFIAuthorRole.TARGET,
            content_text=answer_text,
            is_published=True,
        )
        db.add(thread)

        # 상태 전환: TARGET 답변 → ANSWERED
        item.current_status = RFIItemStatusV2.ANSWERED
        item.version += 1
        item.updated_at = datetime.now(UTC)
        threads_created += 1
        updated_item_ids.add(item.id)

        created_threads.append((thread, file_ref_text))

    await db.flush()  # thread.id 확보

    # 감사 로그
    for thread, _ in created_threads:
        await audit_service.record(
            db, entity_type="rfi_thread", entity_id=thread.id, action=AuditAction.CREATE, actor_email=author_email
        )

    # ── Step 4: 퍼지 매칭 ──────────────────────────────────

    files_matched = 0
    files_unmatched = 0

    # 미할당 파일 목록 조회
    unassigned_result = await db.execute(
        select(RFIAttachment).where(
            RFIAttachment.transaction_id == txn_id,
            RFIAttachment.is_mapped.is_(False),
        )
    )
    unassigned_files = list(unassigned_result.scalars().all())

    for thread, file_ref_text in created_threads:
        if not file_ref_text:
            continue

        # 여러 파일명이 쉼표로 구분될 수 있음
        file_refs = [f.strip() for f in file_ref_text.split(",") if f.strip()]
        for ref in file_refs:
            candidates: list[tuple[RFIAttachment, float]] = []
            for attachment in unassigned_files:
                score = fuzz.ratio(ref, attachment.file_name)
                if score >= _FUZZY_THRESHOLD:
                    candidates.append((attachment, score))

            # 단일 후보만 자동 매핑 (경합 시 미할당 유지)
            if len(candidates) == 1:
                matched_attachment = candidates[0][0]
                matched_attachment.thread_id = thread.id
                matched_attachment.item_id = thread.item_id
                matched_attachment.is_mapped = True
                unassigned_files.remove(matched_attachment)
                files_matched += 1
            else:
                files_unmatched += 1

    await db.flush()

    # ── Step 5: 결과 반환 ──────────────────────────────────

    items_updated = len(updated_item_ids)
    logger.info(
        "RFI Excel Import 완료: txn=%s, updated=%d, threads=%d, matched=%d, unmatched=%d",
        txn_id,
        items_updated,
        threads_created,
        files_matched,
        files_unmatched,
    )
    return RFIExcelImportResult(
        items_updated=items_updated,
        threads_created=threads_created,
        files_matched=files_matched,
        files_unmatched=files_unmatched,
        errors=[],
        conflicts=[],
    )
