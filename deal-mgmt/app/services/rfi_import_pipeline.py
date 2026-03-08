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
import uuid
from datetime import UTC, datetime

from rapidfuzz import fuzz
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, RFIAuthorRole, RFIItemStatusV2
from app.models.rfi_attachment import RFIAttachment
from app.models.rfi_item_v2 import RFIItemV2
from app.models.rfi_thread import RFIThread
from app.schemas.rfi_v2 import RFIExcelImportResult
from app.services import audit_service

# ── 상수 ──────────────────────────────────────────────────

_FUZZY_THRESHOLD = 80  # fuzz.ratio 최소 점수
_ITEM_ID_COL = 0  # A열: item_id (숨김)
_VERSION_COL = 1  # B열: version (숨김)
_ANSWER_COL = 8  # I열: 답변 입력란 (0-indexed)
_FILE_REF_COL = 9  # J열: 증빙 파일명/인덱스 기재란


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

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()

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
    items_updated = 0
    created_threads: list[tuple[RFIThread, str]] = []
    # (thread, file_ref_text) — Step 4에서 매핑용

    for _excel_row, item, answer_text, file_ref_text in valid_rows:
        # 다음 round_num
        max_round_result = await db.execute(select(func.max(RFIThread.round_num)).where(RFIThread.item_id == item.id))
        next_round = (max_round_result.scalar() or 0) + 1

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
        items_updated += 1

        created_threads.append((thread, file_ref_text))

    await db.flush()  # thread.id 확보

    # 감사 로그
    for thread, _ in created_threads:
        await audit_service.log(db, txn_id, AuditAction.CREATE, "rfi_thread", str(thread.id), author_email)

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

    return RFIExcelImportResult(
        items_updated=items_updated,
        threads_created=threads_created,
        files_matched=files_matched,
        files_unmatched=files_unmatched,
        errors=[],
        conflicts=[],
    )
