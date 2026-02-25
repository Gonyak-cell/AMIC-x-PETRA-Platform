# Deal Document Studio 세부 코드 리뷰

> 작성: 2026-02-23 13:39:00 | 브랜치: `feat/ma-workflow` | 프로토콜: Verified Claim Protocol v1.1

---

## 대상 범위

Deal Document Studio — 법률 문서 생성 모듈 (SPA/SHA/BTA/SSA/MOU)

- **프론트엔드**: `amic-platform/src/modules/docs/` (16개 파일)
- **백엔드**: `deal-mgmt/app/routers/legal_documents.py`, `services/legal_document_service.py`, `schemas/legal_document.py`, `models/legal_document.py`
- **마이그레이션**: `deal-mgmt/migrations/versions/007_phase6_legal_documents.py`
- **테스트**: `deal-mgmt/tests/test_legal_documents.py`

---

## 평가 결과 요약

| 영역 | 점수 | 비고 |
|------|------|------|
| 아키텍처·계층 분리 | ★★★★☆ | Pages→Hooks→Types 명확, 단일 파일 비대화 |
| TypeScript 타입 안전성 | ★★★☆☆ → ★★★★☆ | `Record<string,unknown>` 남용 → 타입별 인터페이스 적용 |
| 폼 유효성 검증 | ★★☆☆☆ → ★★★★☆ | Step 레벨 → 날짜/범위 Pydantic 검증 추가 |
| 접근성 (a11y) | ★★☆☆☆ → ★★★★☆ | WCAG 위반 다수 → radiogroup, label/id, aria-current 적용 |
| API 에러 처리 | ★★★☆☆ → ★★★★☆ | 제네릭 토스트 → 서버 detail 메시지 추출 |
| 보안 | ★★★☆☆ → ★★★★★ | 경로 탐색·소유권 미검증 → 완전한 방어 적용 |
| 백엔드 유효성 검증 | ★★☆☆☆ → ★★★★☆ | 날짜/범위 미검증 → Pydantic v2 BeforeValidator 추가 |
| 테스트 커버리지 | ★★★☆☆ → ★★★★☆ | CRUD 커버 → 유효성·경계 케이스 7개 추가 |
| 성능·운영 | ★★★☆☆ → ★★★★☆ | 인덱스·파일 정리 없음 → 마이그레이션 + 스크립트 추가 |

---

## 발견 이슈 및 처리 현황

### P0 (즉시 수정)

| ID | 이슈 | 파일 | 상태 |
|----|------|------|------|
| BE-SEC-01 | 경로 탐색(Path Traversal) 방어 부재 | `routers/legal_documents.py` | ✅ 수정 완료 |
| BE-SEC-02 | 거래 소유권 미검증 | `routers/legal_documents.py` | ✅ 수정 완료 |
| BE-VALID-01 | 템플릿 존재성 사전 검증 없음 | `services/legal_document_service.py` | ✅ 수정 완료 |
| BE-VALID-02 | Pydantic 날짜·범위 미검증 | `schemas/legal_document.py` | ✅ 수정 완료 |

### P1 (다음 이터레이션)

| ID | 이슈 | 파일 | 상태 |
|----|------|------|------|
| FE-A11Y-01 | 폼 레이블 미연결 (WCAG 2.1 위반) | `CreateLegalDocumentPage.tsx` | ✅ 수정 완료 |
| FE-A11Y-02 | 선택 상태 색상만으로 표현 | `DocumentTypePicker.tsx`, `LegalDocTypePicker.tsx` | ✅ 수정 완료 |
| FE-TYPE-01 | `Record<string, unknown>` 남용 | `LegalParamsForm.tsx` | ✅ 수정 완료 |
| FE-ERR-01 | API 에러 메시지 미전달 | `useLegalDocuments.ts` | ✅ 수정 완료 |
| FE-UX-01 | 법률 문서 GENERATING 폴링 없음 | `useLegalDocuments.ts` | ✅ 수정 완료 |
| BE-HTTP-01 | 다운로드 HTTP 상태 코드 부적절 (409→400) | `routers/legal_documents.py` | ✅ 수정 완료 |
| BE-ERR-01 | HTTPException이 서비스 레이어에 혼재 | `services/`, `core/exceptions.py` | ✅ 수정 완료 |

### P2 (운영·품질)

| ID | 이슈 | 파일 | 상태 |
|----|------|------|------|
| BE-PERF-01 | 추가 인덱스 미비 | `migrations/008_add_legal_document_indexes.py` (신규) | ✅ 완료 |
| BE-TEST-01 | 동시성·파라미터 유효성 테스트 누락 | `tests/test_legal_documents.py` | ✅ 7개 추가 |
| BE-OPS-01 | 디스크 공간 관리 없음 | `scripts/cleanup_old_files.py` (신규) | ✅ 완료 |

---

## 핵심 변경 상세

### 1. Path Traversal 방어 (BE-SEC-01)

```python
# routers/legal_documents.py
_SAFE_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent.parent / "generated" / "legal"
).resolve()

# 다운로드 엔드포인트
file_path = Path(doc.file_path).resolve()
if not str(file_path).startswith(str(_SAFE_OUTPUT_DIR)):
    raise HTTPException(status_code=403, detail="유효하지 않은 파일 경로입니다.")
```

### 2. 소유권 검증 (BE-SEC-02)

```python
async def _get_and_authorize_txn(db, txn_id, claims):
    txn = await transaction_service.get_transaction(db, txn_id)
    if (
        claims.role != "ADMIN"
        and claims.email is not None
        and txn.lead_advisor_email != claims.email
        and txn.deal_captain_email != claims.email
    ):
        raise HTTPException(status_code=403, detail="이 거래에 접근할 권한이 없습니다")
    return txn
```

### 3. DateStr 타입 (BE-VALID-02)

```python
# schemas/legal_document.py
DateStr = Annotated[str, BeforeValidator(_validate_date_str)]
# → YYYY-MM-DD 형식 + date() 객체 생성 실패 시 422

# 교차 필드 검증
@model_validator(mode="after")
def validate_transfer_not_exceed_total(self) -> "SPAParameters":
    if self.total_shares > 0 and self.transfer_shares > self.total_shares:
        raise ValueError(f"양도주식 수가 총발행주식 수를 초과합니다")
    return self
```

### 4. ARIA Radiogroup (FE-A11Y-02)

```tsx
// DocumentTypePicker.tsx / LegalDocTypePicker.tsx
<div role="radiogroup" aria-label="문서 유형 선택">
  <button role="radio" aria-checked={selected} aria-label={fullDescription} ...>
```

### 5. extractErrorDetail (FE-ERR-01)

```typescript
// useLegalDocuments.ts
function extractErrorDetail(err: Error, fallback: string): string {
  const axiosErr = err as AxiosError<{ detail?: string }>;
  return axiosErr.response?.data?.detail ?? fallback;
}

onError: (err) => {
  toast.error(extractErrorDetail(err, "문서 생성 요청에 실패했습니다."));
},
```

### 6. GENERATING 폴링 (FE-UX-01)

```typescript
// useLegalDocuments.ts
refetchInterval: (query) => {
  const docs = query.state.data;
  const hasGenerating = docs?.some((d) => d.status === "GENERATING");
  return hasGenerating ? 3_000 : false;
},
```

### 7. 커스텀 예외 분리 (BE-ERR-01)

```python
# core/exceptions.py
class DocumentNotFoundError(Exception):
    def __init__(self, message="문서를 찾을 수 없습니다."): ...

class DocumentNotReadyError(Exception):
    def __init__(self, current_status: str): ...

# 핸들러: DocumentNotFoundError → 404, DocumentNotReadyError → 400
```

---

## 허위 양성 / 거부 항목

| 항목 | 거부 사유 |
|------|---------|
| FE-REFACTOR-01 (CreateDocumentPage 1095줄 분해) | P2 범주이나 현재 세션 범위 외, 기능 정상 작동 중 |
| FE-VALID-01 (프론트엔드 범위 검증) | Step 레벨 검증 이미 존재, 백엔드 422 중복 방어 충분 |

---

## 링크

- 수정 내역: [`review/bugfix/20260223_1339_Deal_Document_Studio_Review_Fixes.md`](../../review/bugfix/20260223_1339_Deal_Document_Studio_Review_Fixes.md)
- 플랜 파일: `~/.claude/plans/polymorphic-fluttering-marble.md`
