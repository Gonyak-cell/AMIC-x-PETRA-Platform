"""RFI Excel 내보내기/가져오기 서비스.

- 내보내기: 샘플 14개 분석 기반 표준 형식
- 가져오기: 한/영 이중 키워드 자동 감지
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    RFICategory,
    RFIItemPriority,
    RFIItemStatus,
    RFISourceType,
)
from app.models.rfi import RFI
from app.models.rfi_item import RFIItem
from app.schemas.rfi import RFIExcelImportResult

# ── 헤더 매핑 (한/영 이중 키워드 — 샘플 14개에서 추출) ───


HEADER_MAPPING: dict[str, str] = {
    # 번호
    "no": "question_number",
    "no.": "question_number",
    "번호": "question_number",
    "#": "question_number",
    "seq": "question_number",
    # 요청일
    "request date": "request_date",
    "요청일": "request_date",
    "date": "request_date",
    # 우선순위
    "priority": "priority",
    "우선순위": "priority",
    # 분류
    "category": "category",
    "분류": "category",
    "카테고리": "category",
    "module": "category",
    # 질문
    "question": "question",
    "질문": "question",
    "요청사항": "question",
    "요청 사항": "question",
    "request": "question",
    "description": "question",
    "요청자료": "question",
    # 상세
    "detail": "question_detail",
    "상세": "question_detail",
    "상세 설명": "question_detail",
    # 응답
    "response": "response",
    "응답": "response",
    "회신": "response",
    "seller's response": "response",
    "seller response": "response",
    "회신자료": "response",
    "응답내용": "response",
    # 응답일
    "response date": "responded_at",
    "응답일": "responded_at",
    # 상태
    "status": "status",
    "상태": "status",
    "응답상태": "status",
    "회신 여부": "status",
    # 비고
    "comment": "notes",
    "comments": "notes",
    "비고": "notes",
    "메모": "notes",
    "note": "notes",
    "remark": "notes",
    "remarks": "notes",
}

# 카테고리 매핑 (한/영)
CATEGORY_MAPPING: dict[str, str] = {
    "일반": "GENERAL",
    "general": "GENERAL",
    "재무": "FINANCIAL",
    "financial": "FINANCIAL",
    "finance": "FINANCIAL",
    "세무": "TAX",
    "tax": "TAX",
    "법률": "LEGAL",
    "legal": "LEGAL",
    "운영": "OPERATIONAL",
    "operational": "OPERATIONAL",
    "operations": "OPERATIONAL",
    "영업": "COMMERCIAL",
    "commercial": "COMMERCIAL",
    "인사": "HR",
    "hr": "HR",
    "it": "IT",
    "기술": "IT",
    "환경": "ENVIRONMENTAL",
    "environmental": "ENVIRONMENTAL",
    "보험": "INSURANCE",
    "insurance": "INSURANCE",
    "지재": "IP",
    "ip": "IP",
    "부동산": "REAL_ESTATE",
    "real estate": "REAL_ESTATE",
    "밸류에이션": "VALUATION",
    "valuation": "VALUATION",
    "기타": "OTHER",
    "other": "OTHER",
}

# 우선순위 매핑
PRIORITY_MAPPING: dict[str, str] = {
    "critical": "CRITICAL",
    "긴급": "CRITICAL",
    "high": "HIGH",
    "높음": "HIGH",
    "medium": "MEDIUM",
    "중간": "MEDIUM",
    "보통": "MEDIUM",
    "low": "LOW",
    "낮음": "LOW",
}

# 상태 매핑
STATUS_MAPPING: dict[str, str] = {
    "pending": "PENDING",
    "대기": "PENDING",
    "미회신": "PENDING",
    "responded": "RESPONDED",
    "회신": "RESPONDED",
    "완료": "RESPONDED",
    "accepted": "ACCEPTED",
    "확인": "ACCEPTED",
    "clarification": "CLARIFICATION_NEEDED",
    "추가확인": "CLARIFICATION_NEEDED",
    "n/a": "NOT_APPLICABLE",
    "해당없음": "NOT_APPLICABLE",
}


def export_rfi_to_excel(rfi: RFI) -> io.BytesIO:
    """RFI를 Excel 파일로 내보낸다."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        raise RuntimeError("openpyxl이 설치되지 않았습니다: pip install openpyxl")

    wb = Workbook()
    ws = wb.active
    ws.title = "RFI"

    # 헤더 스타일
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    header_font = Font(bold=True, size=10)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 우선순위 색상
    priority_fills = {
        "CRITICAL": PatternFill(start_color="FF4444", end_color="FF4444", fill_type="solid"),
        "HIGH": PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid"),
        "MEDIUM": PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid"),
        "LOW": PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid"),
    }

    # 상태 색상
    status_fills = {
        "PENDING": PatternFill(start_color="C0C0C0", end_color="C0C0C0", fill_type="solid"),
        "RESPONDED": PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid"),
        "ACCEPTED": PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid"),
        "CLARIFICATION_NEEDED": PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid"),
        "NOT_APPLICABLE": PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid"),
    }

    # 메타 정보 행
    ws.append(["RFI 제목", rfi.title])
    ws.append(["라운드", rfi.round_number])
    ws.append(["수신자", rfi.recipient_name or ""])
    ws.append(["마감일", rfi.due_date or ""])
    ws.append(["상태", rfi.status.value if rfi.status else ""])
    ws.append([])

    # 헤더 행
    headers = [
        "No.", "우선순위\nPriority", "분류\nCategory", "요청 사항\nQuestion",
        "상세 설명\nDetail", "응답\nResponse", "응답자료\nDocuments",
        "응답일\nResponse Date", "상태\nStatus", "검토 의견\nReviewer Comment", "비고\nNotes",
    ]
    ws.append(headers)
    header_row = ws.max_row
    for col_idx, _ in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    # 데이터 행
    items = sorted(rfi.items, key=lambda x: x.question_number) if rfi.items else []
    for item in items:
        docs_str = ""
        if item.response_documents:
            docs_str = ", ".join(
                d.get("name", "") for d in item.response_documents if isinstance(d, dict)
            )
        responded_str = item.responded_at.strftime("%Y-%m-%d") if item.responded_at else ""
        row_data = [
            item.question_number,
            item.priority.value if item.priority else "",
            item.category.value if item.category else "",
            item.question or "",
            item.question_detail or "",
            item.response or "",
            docs_str,
            responded_str,
            item.status.value if item.status else "",
            item.reviewer_comment or "",
            item.notes or "",
        ]
        ws.append(row_data)
        row_idx = ws.max_row

        # 조건부 서식
        priority_val = item.priority.value if item.priority else ""
        if priority_val in priority_fills:
            ws.cell(row=row_idx, column=2).fill = priority_fills[priority_val]

        status_val = item.status.value if item.status else ""
        if status_val in status_fills:
            ws.cell(row=row_idx, column=9).fill = status_fills[status_val]

        for col_idx in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col_idx).border = thin_border

    # 열 너비 자동 조정
    col_widths = [6, 12, 14, 40, 30, 40, 20, 14, 18, 30, 20]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


async def import_rfi_from_excel(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    content: bytes,
    actor_email: str | None = None,
) -> RFIExcelImportResult:
    """Excel 파일에서 RFI 질문/응답을 가져온다.

    - 헤더 행 자동 감지 (한/영 이중 키워드, "question" 매칭 필수)
    - question_number 기준 매칭 (기존 항목 업데이트)
    - 새 질문은 추가
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise RuntimeError("openpyxl이 설치되지 않았습니다: pip install openpyxl")

    wb = load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active

    errors: list[str] = []
    items_imported = 0
    items_updated = 0

    # 헤더 행 찾기
    header_map: dict[int, str] = {}
    header_row_idx = 0
    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=False), 1):
        matched = 0
        has_question = False
        temp_map: dict[int, str] = {}
        for col_idx, cell in enumerate(row, 1):
            val = str(cell.value or "").strip().lower()
            if val in HEADER_MAPPING:
                field = HEADER_MAPPING[val]
                temp_map[col_idx] = field
                matched += 1
                if field == "question":
                    has_question = True
        # BE-EXCEL-01: "question" 매칭 필수 + 최소 2개 컬럼
        if matched >= 2 and has_question:
            header_map = temp_map
            header_row_idx = row_idx
            break

    if not header_map:
        return RFIExcelImportResult(items_imported=0, items_updated=0, errors=["헤더 행을 찾을 수 없습니다"])

    # 기존 아이템 조회
    existing_q = select(RFIItem).where(RFIItem.rfi_id == rfi_id, RFIItem.transaction_id == txn_id)
    existing_items = {
        item.question_number: item for item in (await db.execute(existing_q)).scalars().all()
    }

    # 다음 질문 번호
    from sqlalchemy import func

    max_num_q = select(func.coalesce(func.max(RFIItem.question_number), 0)).where(RFIItem.rfi_id == rfi_id)
    next_num = (await db.execute(max_num_q)).scalar_one() + 1

    # 데이터 행 파싱
    for row_idx, row in enumerate(ws.iter_rows(min_row=header_row_idx + 1, values_only=False), header_row_idx + 1):
        row_data: dict[str, str] = {}
        for col_idx, cell in enumerate(row, 1):
            if col_idx in header_map:
                row_data[header_map[col_idx]] = str(cell.value or "").strip()

        # 빈 행 스킵
        question_text = row_data.get("question", "")
        if not question_text:
            continue

        try:
            q_num = int(row_data.get("question_number", "0")) if row_data.get("question_number", "").isdigit() else 0
        except (ValueError, TypeError):
            q_num = 0

        # 카테고리 파싱
        cat_raw = row_data.get("category", "").lower()
        category = CATEGORY_MAPPING.get(cat_raw, "GENERAL")

        # 우선순위 파싱
        pri_raw = row_data.get("priority", "").lower()
        priority = PRIORITY_MAPPING.get(pri_raw, "MEDIUM")

        # 상태 파싱
        status_raw = row_data.get("status", "").lower()
        item_status = STATUS_MAPPING.get(status_raw, "PENDING")

        response_text = row_data.get("response", "")
        notes_text = row_data.get("notes", "")

        # BE-EXCEL-02: 행별 에러 수집
        try:
            parsed_category = RFICategory(category)
        except ValueError:
            errors.append(f"행 {row_idx}: 알 수 없는 카테고리 '{row_data.get('category', '')}'")
            parsed_category = RFICategory.GENERAL

        try:
            parsed_priority = RFIItemPriority(priority)
        except ValueError:
            errors.append(f"행 {row_idx}: 알 수 없는 우선순위 '{row_data.get('priority', '')}'")
            parsed_priority = RFIItemPriority.MEDIUM

        try:
            parsed_status = RFIItemStatus(item_status)
        except ValueError:
            errors.append(f"행 {row_idx}: 알 수 없는 상태 '{row_data.get('status', '')}'")
            parsed_status = RFIItemStatus.PENDING

        if q_num > 0 and q_num in existing_items:
            # 기존 항목 업데이트
            existing = existing_items[q_num]
            if response_text:
                existing.response = response_text
                existing.responded_at = datetime.now(timezone.utc)
                existing.status = parsed_status
            if notes_text:
                existing.notes = notes_text
            items_updated += 1
        else:
            # 새 항목 추가
            new_item = RFIItem(
                rfi_id=rfi_id,
                transaction_id=txn_id,
                question_number=q_num if q_num > 0 else next_num,
                category=parsed_category,
                question=question_text,
                question_detail=row_data.get("question_detail", "") or None,
                priority=parsed_priority,
                response=response_text or None,
                status=parsed_status,
                notes=notes_text or None,
                source_type=RFISourceType.EXCEL_IMPORT,
            )
            if response_text:
                new_item.responded_at = datetime.now(timezone.utc)
            db.add(new_item)
            items_imported += 1
            if q_num == 0:
                next_num += 1

    # RFI 카운트 갱신
    from app.services.rfi_service import _get_rfi_simple, _update_rfi_counts

    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    await db.flush()
    await _update_rfi_counts(db, rfi)
    await db.commit()

    return RFIExcelImportResult(items_imported=items_imported, items_updated=items_updated, errors=errors)
