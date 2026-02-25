# RFI 모듈 백엔드 코드 리뷰 리포트

**리뷰 대상**: deal-mgmt RFI (Request for Information) 모듈 11개 파일
**리뷰 일시**: 2026-02-25 21:36
**브랜치**: feat/ma-workflow

---

## 발견사항 (심각도 순 정렬)

---

### BE-SEC-01: Content-Disposition 헤더 인젝션 취약점

- **파일:줄번호**: `deal-mgmt/app/routers/rfi.py:287-291`
- **실제 코드**:
```python
rfi = await rfi_service.get_rfi(db, txn_id, rfi_id)
output = export_rfi_to_excel(rfi)
filename = f"RFI_{rfi.title[:30]}_{rfi.round_number}.xlsx"
return StreamingResponse(
    output,
    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
)
```
- **문제**: `rfi.title`은 사용자 입력 문자열이다. `"`, `\n`, `\r` 등의 특수 문자가 포함되면 Content-Disposition 헤더가 깨지거나 HTTP Response Splitting 공격에 노출된다. 예: `title = 'test"\r\nSet-Cookie: admin=true'` 입력 시 헤더 인젝션 가능.
- **심각도**: 🔴 Critical
- **신뢰도**: HIGH (90%+)
- **수정안**:
```python
import re

safe_title = re.sub(r'[^\w\s가-힣-]', '', rfi.title[:30]).strip()
filename = f"RFI_{safe_title}_{rfi.round_number}.xlsx"
# RFC 5987 인코딩 사용
from urllib.parse import quote
encoded = quote(filename)
headers = {
    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"
}
```
- **검증**: ☑ Read로 확인 / ☑ 참조 패턴 비교 확인

---

### BE-SEC-02: Excel Import 파일 검증 부재

- **파일:줄번호**: `deal-mgmt/app/routers/rfi.py:295-307`
- **실제 코드**:
```python
@router.post("/{rfi_id}/import", response_model=RFIExcelImportResult)
async def import_rfi_excel(
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    from app.excel.rfi_excel import import_rfi_from_excel
    result = await import_rfi_from_excel(db, txn_id, rfi_id, file, claims.email)
    return result
```
- **문제**: (1) 파일 확장자 검증 없음 - `.exe`, `.py` 등 악의적 파일도 수락. (2) 파일 크기 제한 없음 - 수백 MB Excel로 서버 메모리 고갈 가능. (3) MIME 타입 검증 없음. `rfi_excel.py:278`에서 `content = await file.read()`로 전체 파일을 메모리에 로딩한다.
- **심각도**: 🔴 Critical
- **신뢰도**: HIGH (90%+)
- **수정안**:
```python
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/{rfi_id}/import", response_model=RFIExcelImportResult)
async def import_rfi_excel(
    txn_id: uuid.UUID, rfi_id: uuid.UUID, file: UploadFile,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    # 확장자 검증
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(400, detail="Excel 파일(.xlsx, .xls)만 업로드 가능합니다")
    # 크기 검증
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, detail="파일 크기가 10MB를 초과합니다")
    # ... 이후 content를 직접 전달
```
- **검증**: ☑ Read로 확인 (`rfi_excel.py:278` — `await file.read()` 전체 로딩 확인)

---

### BE-DATA-01: 날짜 필드 `due_date`가 `String(10)` — 형식 검증 없음

- **파일:줄번호**: `deal-mgmt/app/models/rfi.py:33`, `deal-mgmt/app/schemas/rfi.py:30,84,214`
- **실제 코드**:
```python
# 모델 (rfi.py:33)
due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

# 스키마 (rfi.py:30)
due_date: str | None = Field(None, max_length=10)

# 마감일 연장 (rfi.py:213-214)
class RFIExtendDeadlineInput(BaseModel):
    due_date: str = Field(..., min_length=10, max_length=10)
```
- **문제**: `max_length=10`만 검증하므로 `"1234567890"`, `"ABCDEFGHIJ"` 같은 잘못된 문자열이 그대로 저장된다. 같은 프로젝트의 `legal_document.py:17-33`에서는 `DateStr = Annotated[str, BeforeValidator(_validate_date_str)]`로 YYYY-MM-DD 형식 + 실제 달력 유효성까지 검증한다.
- **심각도**: 🟠 Major
- **신뢰도**: HIGH (90%+)
- **수정안**:
```python
from app.schemas.legal_document import DateStr

class RFICreate(BaseModel):
    due_date: DateStr | None = Field(None)

class RFIExtendDeadlineInput(BaseModel):
    due_date: DateStr = Field(...)
```
- **검증**: ☑ Read로 확인 / ☑ 참조 패턴 비교 확인 (legal_document.py:17-33)

---

### BE-DATA-02: 모델 `sent_at`, `closed_at` 타입 힌트가 `str | None`이지만 실제 컬럼은 `DateTime`

- **파일:줄번호**: `deal-mgmt/app/models/rfi.py:34-35`
- **실제 코드**:
```python
sent_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
closed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
```
- **문제**: `Mapped[str | None]`으로 선언했지만 실제 DB 컬럼은 `DateTime`. `datetime | None`이어야 맞다. 동일한 문제가 `rfi_item.py:38`의 `responded_at`, `rfi_checklist_mapping.py:28`의 `synced_at`에도 있다.
- **심각도**: 🟠 Major
- **신뢰도**: HIGH (90%+)
- **수정안**:
```python
from datetime import datetime
sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```
- **검증**: ☑ Read로 확인 (rfi.py:34-35, rfi_item.py:38, rfi_checklist_mapping.py:28)

---

### BE-DATA-05: `RFIUpdate` 스키마에서 `status` 직접 변경 가능 → 워크플로우 우회

- **파일:줄번호**: `deal-mgmt/app/schemas/rfi.py:34-42`
- **실제 코드**:
```python
class RFIUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    # ...
    status: RFIStatus | None = None
```
- **문제**: `PATCH /{rfi_id}` 엔드포인트를 통해 `status` 필드를 직접 수정할 수 있다. 이는 `send_rfi`, `close_rfi` 등의 워크플로우 전환 엔드포인트를 우회하여 DRAFT→FULLY_RESPONDED, CLOSED→DRAFT 등 비정상 전환이 가능하게 한다.
- **심각도**: 🟠 Major
- **신뢰도**: HIGH (90%+)
- **수정안**: `RFIUpdate`에서 `status` 필드 제거.
- **검증**: ☑ Read로 확인 (rfi.py 스키마:42, rfi_service.py:98-100)

---

### BE-WF-01: `close_rfi`가 DRAFT 상태에서도 직접 CLOSED로 전환 허용

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:158-175`
- **실제 코드**:
```python
async def close_rfi(...) -> RFI:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    if rfi.status == RFIStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 마감된 RFI입니다")
    rfi.status = RFIStatus.CLOSED
    rfi.closed_at = datetime.now(timezone.utc)
```
- **문제**: `DRAFT` 상태의 RFI도 바로 `CLOSED`로 전환 가능. 비교: `send_rfi`는 `DRAFT`에서만 `SENT`로 가능하도록 엄격히 제한.
- **심각도**: 🟠 Major
- **신뢰도**: MEDIUM (60-89%)
- **수정안**:
```python
if rfi.status in (RFIStatus.DRAFT, RFIStatus.CLOSED, RFIStatus.CANCELLED):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"현재 상태({rfi.status.value})에서는 마감할 수 없습니다.",
    )
```
- **검증**: ☑ Read로 확인

---

### BE-WF-02: `respond_to_item`에서 이미 ACCEPTED 상태 아이템 재응답 가능

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:324-347`
- **실제 코드**:
```python
async def respond_to_item(...) -> RFIItem:
    item = await _get_rfi_item(db, txn_id, rfi_id, item_id)
    item.response = body.response
    item.response_documents = body.response_documents
    item.responded_at = datetime.now(timezone.utc)
    item.responded_by = responder_email
    item.status = RFIItemStatus.RESPONDED
```
- **문제**: ACCEPTED로 최종 승인된 아이템을 다시 RESPONDED로 되돌릴 수 있다.
- **심각도**: 🟠 Major
- **신뢰도**: HIGH (90%+)
- **수정안**: ACCEPTED/NOT_APPLICABLE 상태 아이템 재응답 차단.
- **검증**: ☑ Read로 확인

---

### BE-WF-03: `review_item`에서 PENDING 상태 아이템도 직접 ACCEPTED 가능

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:350-372`
- **실제 코드**:
```python
async def review_item(...) -> RFIItem:
    item = await _get_rfi_item(db, txn_id, rfi_id, item_id)
    item.status = RFIItemStatus(body.status)
    item.reviewer_comment = body.reviewer_comment
```
- **문제**: 응답 없는 PENDING 아이템도 곧바로 ACCEPTED 처리 가능.
- **심각도**: 🟠 Major
- **신뢰도**: HIGH (90%+)
- **수정안**: RESPONDED/CLARIFICATION_NEEDED 상태에서만 리뷰 가능하도록 검증 추가.
- **검증**: ☑ Read로 확인

---

### BE-SYNC-01: DD 자동생성 시 `RFIChecklistMapping` 레코드 미생성 → sync 불가

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:429-496`
- **실제 코드**:
```python
for i, dd in enumerate(dd_items):
    item = RFIItem(
        rfi_id=rfi.id,
        source_type=RFISourceType.DD_CHECKLIST,
        source_ref_id=dd.id,  # ← DD 체크리스트 ID만 저장
    )
    db.add(item)
# RFIChecklistMapping은 생성하지 않음
```
- **문제**: `source_ref_id`에 원본 DD ID를 설정하지만, `RFIChecklistMapping` 레코드를 생성하지 않는다. `rfi_sync_service.py`는 매핑 테이블을 조회하여 동기화하므로, 자동 생성된 RFI 아이템은 절대 sync되지 않는다.
- **심각도**: 🟠 Major
- **신뢰도**: HIGH (90%+)
- **수정안**: 자동 생성 시 매핑 레코드도 함께 생성.
- **검증**: ☑ Read로 확인 (rfi_service.py:473-487, rfi_sync_service.py:42-47)

---

### BE-WF-04: CLARIFICATION_NEEDED 재응답 시나리오 미테스트

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:526-547`
- **문제**: CLARIFICATION_NEEDED → 재응답 → FULLY_RESPONDED 전환 시나리오에 대한 테스트 없음.
- **심각도**: 🟡 Moderate
- **신뢰도**: MEDIUM (60-89%)
- **검증**: ☑ Read로 확인

---

### BE-WF-05: `extend_deadline` — 과거 날짜 및 기존 마감일 이전으로 연장 가능

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:178-196`
- **문제**: 기존 마감일보다 이전 날짜로 "연장" 가능. 과거 날짜도 허용.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-PERF-01: `list_rfis` 및 `list_rfi_items` 페이지네이션 없음

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:39-53`, `202-220`
- **문제**: 두 목록 API 모두 `limit`/`offset` 파라미터 없음. 참조 패턴 `transaction_service.py:43-89`에는 페이지네이션 구현됨.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인 / ☑ 참조 패턴 비교 확인

---

### BE-PERF-02: `get_rfi_summary` — 전체 아이템 메모리 로딩 후 Python 집계

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:378-423`
- **문제**: 전체 RFI 아이템을 ORM 객체로 메모리에 로딩한 후 Python에서 집계. SQL GROUP BY 활용 가능.
- **심각도**: 🟡 Moderate
- **신뢰도**: MEDIUM (60-89%)
- **검증**: ☑ Read로 확인 / ☑ 참조 패턴 비교 확인 (dd_checklists.py 동일 패턴)

---

### BE-PERF-03: `batch_add_items` — N회 개별 `db.refresh()` 호출

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:250-278`
- **문제**: N개 아이템에 대해 개별 `db.refresh()` 호출이 N회 발생. 단일 IN 쿼리로 대체 가능.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-DATA-03: `response_documents` JSONB 내부 구조 미정의

- **파일:줄번호**: `deal-mgmt/app/models/rfi_item.py:37`, `deal-mgmt/app/schemas/rfi.py:108`
- **문제**: 모델은 `Mapped[dict | None]`이지만 스키마는 `list[dict]` — 타입 불일치. dict 내부 구조도 미정의.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-DATA-04: `question_number` 유니크 제약 없음

- **파일:줄번호**: `deal-mgmt/migrations/versions/021_rfi_request_for_information.py:49`
- **문제**: `(rfi_id, question_number)` 복합 유니크 제약 없음. Excel import에서 번호 중복 가능.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-EXCEL-01: 헤더 감지 조건 `matched >= 2` 오탐 위험

- **파일:줄번호**: `deal-mgmt/app/excel/rfi_excel.py:289-300`
- **문제**: HEADER_MAPPING에 `"date"`, `"no"`, `"#"` 등 일반적 키워드 포함. 데이터 행을 헤더로 오인 가능.
- **심각도**: 🟡 Moderate
- **신뢰도**: MEDIUM (60-89%)
- **수정안**: `"question"` 매칭 필수 조건 추가.
- **검증**: ☑ Read로 확인

---

### BE-EXCEL-02: Import 에러 수집 미구현 (항상 빈 리스트)

- **파일:줄번호**: `deal-mgmt/app/excel/rfi_excel.py:282,329-380,390`
- **문제**: `errors` 리스트가 선언만 되고 행별 에러를 추가하는 코드 없음. 항상 빈 리스트 반환.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-SEC-03: 라우터에서 서비스 private 함수 직접 호출 + 인라인 쿼리

- **파일:줄번호**: `deal-mgmt/app/routers/rfi.py:340`
- **문제**: `_get_rfi_item` (private 함수) 직접 호출 + SQLAlchemy select를 라우터에 인라인.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인 / ☑ 참조 패턴 비교 확인

---

### BE-TEST-01: Excel import/export 테스트 없음

- **파일:줄번호**: `deal-mgmt/tests/test_rfi.py` (전체)
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-TEST-02: `sync_to_checklists` 엔드포인트 테스트 없음

- **파일:줄번호**: `deal-mgmt/tests/test_rfi.py` (전체)
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-TEST-03: `respond_to_item` deal-level 접근 제어 누락

- **파일:줄번호**: `deal-mgmt/app/routers/rfi.py:226-238`
- **문제**: `get_jwt_claims`만 사용하고 `check_client_deal_access` 미호출. 인증된 사용자가 배정되지 않은 거래의 RFI에도 응답 가능.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-SEC-04: `create_rfi`에서 `check_client_deal_access` 미호출

- **파일:줄번호**: `deal-mgmt/app/routers/rfi.py:64-72`
- **문제**: `require_write_access()`가 CLIENT 차단하므로 실질적 위험 낮음. dd_checklists.py 동일 패턴.
- **심각도**: 🔵 Minor
- **신뢰도**: MEDIUM (60-89%)
- **검증**: ☑ Read로 확인 / ☑ 참조 패턴 비교 확인

---

### BE-SYNC-02: `ws_category_map` 하드코딩 (일부 dead code)

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:464-471`
- **심각도**: 🔵 Minor
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### BE-SYNC-03: `synced_count == 0`이면 commit 미호출

- **파일:줄번호**: `deal-mgmt/app/services/rfi_sync_service.py:68-78`
- **심각도**: 🔵 Minor
- **신뢰도**: LOW (<60%)
- **검증**: ☑ Read로 확인

---

### BE-AUDIT-01: `respond_to_item` audit 로그에서 response 100자 절삭

- **파일:줄번호**: `deal-mgmt/app/services/rfi_service.py:341-343`
- **문제**: 응답 전문이 아닌 처음 100자만 감사 로그에 기록. rfi_sync_service.py는 500자.
- **심각도**: 🔵 Minor
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

## 요약 표

| ID | 심각도 | 신뢰도 | 파일 | 문제 요약 |
|---|---|---|---|---|
| BE-SEC-01 | 🔴 Critical | HIGH | routers/rfi.py:287 | Content-Disposition 헤더 인젝션 |
| BE-SEC-02 | 🔴 Critical | HIGH | routers/rfi.py:295 | Excel import 파일 검증 부재 |
| BE-DATA-01 | 🟠 Major | HIGH | schemas/rfi.py:30 | due_date 날짜 형식 검증 없음 |
| BE-DATA-02 | 🟠 Major | HIGH | models/rfi.py:34-35 | DateTime 컬럼의 Mapped 타입이 str |
| BE-DATA-05 | 🟠 Major | HIGH | schemas/rfi.py:42 | RFIUpdate에서 status 직접 변경 → 워크플로우 우회 |
| BE-WF-01 | 🟠 Major | MEDIUM | rfi_service.py:165 | DRAFT→CLOSED 직접 전환 허용 |
| BE-WF-02 | 🟠 Major | HIGH | rfi_service.py:332 | ACCEPTED 아이템 재응답 가능 |
| BE-WF-03 | 🟠 Major | HIGH | rfi_service.py:358 | PENDING 아이템 직접 ACCEPTED 가능 |
| BE-SYNC-01 | 🟠 Major | HIGH | rfi_service.py:473 | DD 자동생성 시 매핑 미생성 → sync 불가 |
| BE-WF-04 | 🟡 Moderate | MEDIUM | rfi_service.py:538 | CLARIFICATION_NEEDED 재응답 미테스트 |
| BE-WF-05 | 🟡 Moderate | HIGH | rfi_service.py:187 | extend_deadline 과거 날짜 허용 |
| BE-PERF-01 | 🟡 Moderate | HIGH | rfi_service.py:39,202 | list 페이지네이션 없음 |
| BE-PERF-02 | 🟡 Moderate | MEDIUM | rfi_service.py:378 | Summary 전체 아이템 메모리 집계 |
| BE-PERF-03 | 🟡 Moderate | HIGH | rfi_service.py:276 | batch에서 N회 개별 refresh |
| BE-DATA-03 | 🟡 Moderate | HIGH | rfi_item.py:37 | response_documents JSONB 구조 미정의 |
| BE-DATA-04 | 🟡 Moderate | HIGH | migration:49 | question_number 유니크 제약 없음 |
| BE-EXCEL-01 | 🟡 Moderate | MEDIUM | rfi_excel.py:297 | 헤더 감지 오탐 위험 |
| BE-EXCEL-02 | 🟡 Moderate | HIGH | rfi_excel.py:282 | import 에러 수집 미구현 |
| BE-SEC-03 | 🟡 Moderate | HIGH | routers/rfi.py:340 | private 함수 직접 호출 + 인라인 쿼리 |
| BE-TEST-01 | 🟡 Moderate | HIGH | test_rfi.py | Excel import/export 테스트 없음 |
| BE-TEST-02 | 🟡 Moderate | HIGH | test_rfi.py | sync_to_checklists 테스트 없음 |
| BE-TEST-03 | 🟡 Moderate | HIGH | routers/rfi.py:233 | respond_to_item deal-level 접근 제어 누락 |
| BE-SEC-04 | 🔵 Minor | MEDIUM | routers/rfi.py:64 | create_rfi check_client_deal_access 미호출 |
| BE-SYNC-02 | 🔵 Minor | HIGH | rfi_service.py:464 | ws_category_map 하드코딩 |
| BE-SYNC-03 | 🔵 Minor | LOW | rfi_sync_service.py:68 | synced_count==0일 때 commit 미호출 |
| BE-AUDIT-01 | 🔵 Minor | HIGH | rfi_service.py:343 | audit 로그 response 100자 절삭 |

---

## 통계

- **총 발견사항**: 26개
- 🔴 Critical: 2개
- 🟠 Major: 7개
- 🟡 Moderate: 13개
- 🔵 Minor: 4개

---

## 검증 투명성

### 거부된 가설: 5개

1. **"HTTPException을 서비스에서 사용하면 안 된다"** — 거부. `transaction_service.py`, `dd_checklists.py` 등 프로젝트 전반에서 서비스 레이어에 HTTPException 사용이 일관적 패턴.

2. **"audit 로깅이 누락됐다"** — 거부. 모든 CRUD 함수에서 `audit_service.record()` 호출을 Read로 확인.

3. **"enum 비교가 잘못됐다"** — 거부. 모든 enum이 `StrEnum`을 상속하므로 문자열 비교 정상 동작.

4. **"create_rfi에서 check_client_deal_access가 보안 위험"** — Minor로 하향. `require_write_access()`가 CLIENT 차단.

5. **"rfi_sync_service commit 누락이 데이터 손실 위험"** — Minor/LOW로 하향. `synced_count == 0`일 때 실제 변경사항 없음.

---

## 우선 수정 권장 순서

1. **즉시 (Critical)**: BE-SEC-01, BE-SEC-02
2. **단기 (Major)**: BE-DATA-05, BE-WF-02/03, BE-SYNC-01, BE-DATA-01, BE-DATA-02
3. **중기 (Moderate)**: BE-PERF-01, BE-DATA-04, BE-EXCEL-01/02, BE-TEST-01/02
4. **장기 (Minor)**: BE-SYNC-02, BE-AUDIT-01
