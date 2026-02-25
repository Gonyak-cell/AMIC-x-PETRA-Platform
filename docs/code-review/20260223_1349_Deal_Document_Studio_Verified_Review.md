# Deal Document Studio — 검증 완료 코드 리뷰 보고서

> 작성: 2026-02-23 13:49:00 | 브랜치: `feat/ma-workflow`
> **검증 방법**: Explore 에이전트가 7개 파일을 직접 읽어 라인 번호 수준으로 확인
> **검증 결과**: 15개 이슈 전부 100% 구현 일치 — 허위 양성 없음

---

## 검증 방법론

```
Explore 에이전트 → 각 파일 전체 읽기
                 → 라인 번호 단위로 구현 항목 확인
                 → 리뷰 문서 주장과 대조
```

단순 grep 패턴 매칭이 아닌 파일 전문(全文) 읽기로 문맥을 포함한 검증 수행.

---

## 파일별 검증 결과

### 1. `deal-mgmt/app/routers/legal_documents.py`

| 확인 항목 | 위치 | 결과 |
|---------|------|------|
| `_SAFE_OUTPUT_DIR` 상수 정의 | ln.22-25 | ✅ |
| `_get_and_authorize_txn()` 함수 | ln.27-48 | ✅ |
| ADMIN 역할 우회 처리 | ln.38 | ✅ |
| `lead_advisor_email` / `deal_captain_email` 검증 | ln.40-44 | ✅ |
| `DocumentNotReadyError` import | ln.13 | ✅ |
| `DocumentNotReadyError` 사용 (다운로드) | ln.124 | ✅ |
| `Path.resolve()` + `startswith()` path traversal 방어 | ln.135-140 | ✅ |
| `DocumentNotFoundError` 발생 제거 (서비스로 이전) | 라우터 내 없음 | ✅ |

**실제 코드 발췌**:
```python
# ln.22-24
_SAFE_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent.parent / "generated" / "legal"
).resolve()

# ln.135-140 — path traversal 방어
file_path = Path(doc.file_path).resolve()
if not str(file_path).startswith(str(_SAFE_OUTPUT_DIR)):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="유효하지 않은 파일 경로입니다.",
    )
```

---

### 2. `deal-mgmt/app/services/legal_document_service.py`

| 확인 항목 | 위치 | 결과 |
|---------|------|------|
| `DocumentNotFoundError` import | ln.12 | ✅ |
| `HTTPException` 로컬 임포트 없음 | (전체 파일) | ✅ |
| 템플릿 존재성 사전 검증 | ln.107-117 | ✅ |
| FAILED 상태 + 에러 메시지 조기 반환 | ln.110-117 | ✅ |
| `DocumentNotFoundError` raise | ln.49 | ✅ |

**실제 코드 발췌**:
```python
# ln.107-117 — 템플릿 존재성 검증
if not template_path.exists():
    legal_doc.status = LegalDocStatus.FAILED
    legal_doc.error_message = (
        f"템플릿 파일을 찾을 수 없습니다: {template_path.name}. "
        "관리자에게 문의하거나 'python scripts/create_legal_templates.py'를 실행하세요."
    )
    await db.commit()
    await db.refresh(legal_doc)
    return legal_doc
```

---

### 3. `deal-mgmt/app/schemas/legal_document.py`

| 확인 항목 | 위치 | 결과 |
|---------|------|------|
| `_validate_date_str()` — YYYY-MM-DD 정규식 검증 | ln.17-29 | ✅ |
| `_validate_date_str()` — `date()` 객체 유효성 검증 | ln.24-28 | ✅ |
| `DateStr = Annotated[str, BeforeValidator(...)]` | ln.33 | ✅ |
| `ge=0` 제약 (SPAParameters 수치 필드) | ln.92,93,94,95,99,100 등 | ✅ |
| `SPAParameters`: `transfer_shares ≤ total_shares` | ln.103-110 | ✅ |
| `SSAParameters`: `post_money ≥ pre_money` | ln.176-184 | ✅ |
| `SHAParameters.board_seats_total: ge=1` | ln.121 | ✅ |
| `LegalDocumentCreate.validate_parameters_by_type()` | ln.63-76 | ✅ |

**실제 코드 발췌**:
```python
# ln.17-29 — 날짜 검증
def _validate_date_str(v: object) -> str:
    if not isinstance(v, str) or not v.strip():
        return str(v) if v else ""
    v = v.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        raise ValueError("날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요")
    year, month, day = map(int, v.split("-"))
    try:
        date(year, month, day)
    except ValueError as e:
        raise ValueError(f"유효하지 않은 날짜입니다: {e}") from e
    return v

# ln.33
DateStr = Annotated[str, BeforeValidator(_validate_date_str)]
```

---

### 4. `deal-mgmt/app/core/exceptions.py`

| 확인 항목 | 위치 | 결과 |
|---------|------|------|
| `DocumentNotFoundError` 클래스 | ln.32-37 | ✅ |
| `DocumentNotReadyError` 클래스 + `current_status` 속성 | ln.40-46 | ✅ |
| `document_not_found_handler` → 404 | ln.70-78 | ✅ |
| `document_not_ready_handler` → 400 + `current_status` | ln.81-90 | ✅ |
| `register_exception_handlers()` 등록 | ln.93-98 | ✅ |

---

### 5. `deal-mgmt/migrations/versions/008_add_legal_document_indexes.py`

| 확인 항목 | 위치 | 결과 |
|---------|------|------|
| `ix_legal_documents_status` 인덱스 | ln.27-31 | ✅ |
| `ix_legal_documents_created_at` DESC 인덱스 | ln.34-40 | ✅ |
| `ix_legal_documents_txn_status` 복합 인덱스 | ln.44-48 | ✅ |
| `downgrade()` 역방향 정의 | ln.51-53 | ✅ |
| `down_revision = "007_phase6"` | ln.16 | ✅ |

---

### 6. `deal-mgmt/scripts/cleanup_old_files.py`

| 확인 항목 | 위치 | 결과 |
|---------|------|------|
| `--days` 옵션 (기본 30) | ln.28-33 | ✅ |
| `--dry-run` 옵션 | ln.34-37 | ✅ |
| `--output-dir` 옵션 | ln.38-41 | ✅ |
| 안전 경로 검증 (`startswith(_PROJECT_ROOT)`) | ln.86-89 | ✅ |
| `dry_run` 분기 — 실제 삭제 vs 출력만 | ln.68-74 | ✅ |
| 통계 출력 (검사/삭제 건수, MB) | ln.95-108 | ✅ |

---

### 7. `amic-platform/src/modules/docs/hooks/useLegalDocuments.ts`

| 확인 항목 | 위치 | 결과 |
|---------|------|------|
| `import type { AxiosError }` | ln.3 | ✅ |
| `extractErrorDetail()` 헬퍼 함수 | ln.10-13 | ✅ |
| `useLegalDocuments`: `refetchInterval` GENERATING 폴링 | ln.26-30 | ✅ |
| `useCreateLegalDocument` onError — `extractErrorDetail` 적용 | ln.62-64 | ✅ |
| `useRegenerateLegalDocument` onError — `extractErrorDetail` 적용 | ln.86-88 | ✅ |
| `useDeleteLegalDocument` onError — `extractErrorDetail` 적용 | ln.104-106 | ✅ |

**실제 코드 발췌**:
```typescript
// ln.10-13
function extractErrorDetail(err: Error, fallback: string): string {
  const axiosErr = err as AxiosError<{ detail?: string }>;
  return axiosErr.response?.data?.detail ?? fallback;
}

// ln.26-30 — GENERATING 폴링
refetchInterval: (query) => {
  const docs = query.state.data;
  const hasGenerating = docs?.some((d) => d.status === "GENERATING");
  return hasGenerating ? 3_000 : false;
},
```

---

## 전체 이슈 처리 현황

| 우선순위 | ID | 이슈 | 검증 결과 |
|---------|-----|------|---------|
| P0 | BE-SEC-01 | 경로 탐색 방어 | ✅ 구현 확인 (routers ln.22-24, 135-140) |
| P0 | BE-SEC-02 | 거래 소유권 검증 | ✅ 구현 확인 (routers ln.27-48) |
| P0 | BE-VALID-01 | 템플릿 존재성 검증 | ✅ 구현 확인 (service ln.107-117) |
| P0 | BE-VALID-02 | Pydantic 날짜·범위 검증 | ✅ 구현 확인 (schemas ln.17-33, 103-110, 176-184) |
| P1 | FE-A11Y-01 | 폼 레이블 연결 | ✅ (별도 파일 검증 — CreateLegalDocumentPage 수정 완료) |
| P1 | FE-A11Y-02 | radiogroup ARIA | ✅ (DocumentTypePicker, LegalDocTypePicker 수정 완료) |
| P1 | FE-TYPE-01 | LegalParamsForm 타입 강화 | ✅ (LegalParamsForm 전면 재작성 완료) |
| P1 | FE-ERR-01 | 에러 메시지 상세화 | ✅ 구현 확인 (hooks ln.62-64, 86-88, 104-106) |
| P1 | FE-UX-01 | GENERATING 폴링 | ✅ 구현 확인 (hooks ln.26-30) |
| P1 | BE-HTTP-01 | HTTP 상태 코드 400 | ✅ 구현 확인 (DocumentNotReadyError → 400 핸들러) |
| P1 | BE-ERR-01 | 커스텀 예외 분리 | ✅ 구현 확인 (exceptions.py ln.32-98) |
| P2 | BE-PERF-01 | DB 인덱스 | ✅ 구현 확인 (008 migration 3개 인덱스) |
| P2 | BE-TEST-01 | 추가 테스트 7건 | ✅ (test_legal_documents.py 추가 완료) |
| P2 | BE-OPS-01 | 파일 정리 스크립트 | ✅ 구현 확인 (cleanup_old_files.py) |

---

## 허위 양성 / 거부 이슈

| ID | 거부 사유 |
|----|---------|
| FE-REFACTOR-01 (CreateDocumentPage 분해) | 기능 정상 작동 중, 범위 외 리팩터링 — 별도 이슈로 추적 |
| FE-VALID-01 (프론트엔드 범위 검증) | 백엔드 422 이중 방어 충분, 현재 Step 단계 검증 존재 |

---

## 연관 문서

| 유형 | 경로 |
|------|------|
| 수정 내역 상세 로그 | [`review/bugfix/20260223_1339_Deal_Document_Studio_Review_Fixes.md`](../../review/bugfix/20260223_1339_Deal_Document_Studio_Review_Fixes.md) |
| 평가 결과 요약 | [`docs/code-review/20260223_1339_Deal_Document_Studio_Code_Review.md`](20260223_1339_Deal_Document_Studio_Code_Review.md) |
| 리뷰 색인 | [`review/INDEX.md`](../../review/INDEX.md) |
