# MA 미팅 로그 — 코드 리뷰 수정 보고서

> 최종 업데이트: 2026-02-25 01:46:00

## 개요

MA 모듈 MARKETING/NEGOTIATION 단계의 미팅 로그 기능(Phase A~E) 구현 완료 후 코드 리뷰에서 발견된 **17개 이슈**를 전량 수정하고, 추가로 발견된 **~12개 빌드 에러**를 함께 해결한 보고서이다.

**최종 검증**: 백엔드 27/27 테스트 통과 (4.80s) + 프론트엔드 빌드 성공 (10.21s)

---

## 1. 수정 완료 이슈 목록

### 1.1 백엔드 Critical (2건)

| # | 파일 | 이슈 | 수정 내용 |
|---|------|------|----------|
| B-C1 | `deal-mgmt/app/routers/contract_markups.py` | `delete_markup()` — `check_client_deal_access()` 누락 (인증 우회 가능) | 핸들러 시작부에 `check_client_deal_access(txn_id, claims)` 추가 |
| B-C2 | `deal-mgmt/app/routers/contract_markups.py` | `upload_markup()` — 파일 크기 제한 없음 (무한 업로드 DoS) | 50MB 크기 제한 + 10종 확장자 허용 목록 (.docx, .doc, .pdf, .xlsx, .xls, .pptx, .ppt, .hwp, .hwpx, .txt) |

### 1.2 백엔드 Major (4건)

| # | 파일 | 이슈 | 수정 내용 |
|---|------|------|----------|
| B-M1 | `deal-mgmt/app/routers/contract_markups.py` | `version_number` 레이스 컨디션 — 동시 업로드 시 중복 번호 | `SELECT ... FOR UPDATE`로 Contract 행 잠금 후 MAX 조회 |
| B-M2 | `deal-mgmt/app/routers/meeting_logs.py` | 참석자/액션아이템 CRUD 6개 핸들러에 audit 로깅 없음 | 6개 핸들러 모두 `audit_service.record()` 추가 |
| B-M3 | `deal-mgmt/app/routers/negotiation_issues.py` | AI 제안 호출 audit 로깅 없음 | `audit_service.record(action="ai_suggest")` 추가 |
| B-M4 | `deal-mgmt/pyproject.toml` | `aiofiles` 의존성 미등록 | `[project.dependencies]`에 `aiofiles` 추가 |

### 1.3 백엔드 Moderate (4건)

| # | 파일 | 이슈 | 수정 내용 |
|---|------|------|----------|
| B-m1 | `deal-mgmt/app/routers/contract_markups.py` | `Path.is_relative_to()` Python 3.9+ 전용 | `try: resolve().relative_to() except ValueError: 403` 패턴으로 변경 |
| B-m2 | `deal-mgmt/app/routers/contract_markups.py` | `meeting_id` Form 파라미터 UUID 검증 없음 | `_parse_optional_uuid()` 헬퍼 함수 추가 |
| B-m3 | `deal-mgmt/app/schemas/meeting_log.py` | `provided_materials` JSONB 스키마 검증 없음 | `ProvidedMaterial` Pydantic 모델 추가, `list[dict]` → `list[ProvidedMaterial]` 변경 (3곳) |
| B-m4 | `deal-mgmt/app/routers/meeting_logs.py` | 참석자 추가 시 중복 검증 없음 | email 기준 중복 체크 추가 (409 Conflict) |

### 1.4 프론트엔드 Major (3건)

| # | 파일 | 이슈 | 수정 내용 |
|---|------|------|----------|
| F-M1 | `ContractMarkupTimeline.tsx` | 업로드 폼에 HTML `<input>` 사용 — 디자인 시스템 미사용 | `<Input>` 컴포넌트로 교체 |
| F-M2 | `MeetingLogsTab.tsx` | API 에러 상태(`isError`) 미처리 | `isError` 구조분해 + `EmptyState` 에러 UI 표시 |
| F-M3 | `MeetingLogForm.tsx` | `existing` prop 변경 시 폼 상태 미갱신 | `useEffect`로 `existing` 변경 감지 후 8개 필드 동기화 |

### 1.5 프론트엔드 Moderate (4건)

| # | 파일 | 이슈 | 수정 내용 |
|---|------|------|----------|
| F-m1 | `ActionItemList.tsx` | Enter 키 `e.preventDefault()` 없음 | `onKeyDown` 핸들러에 `e.preventDefault()` 추가 |
| F-m2 | `AttendeeList.tsx` | 참석자 추가 폼 모바일 과밀 | `flex-wrap` 추가 |
| F-m3 | `NegotiationIssuePanel.tsx` | `aiResult` prop 미사용 (`_aiResult`로 리네임만) | prop 자체 제거 (AI 결과는 issue 객체에 직접 저장) |
| F-m4 | `MeetingLogsTab.tsx` | `contractId` prop 선언되었으나 미사용 | prop 제거 |

---

## 2. 추가 빌드 에러 수정 (~12건)

리뷰 이슈 수정 과정에서 기존에 남아있던 빌드 에러들을 함께 해결했다.

| 파일 | 이슈 | 수정 |
|------|------|------|
| `InlineSelect.tsx` | `disabled` prop 미정의 (8곳에서 사용) | `disabled?: boolean` prop 추가 |
| `TransactionWorkspacePage.tsx` | DataTable render 콜백 타입 불일치 | value 기반 → row 기반 `(row: T, index: number)` 패턴으로 전환 |
| `TransactionWorkspacePage.tsx` | `rows=` → `data= keyField="id"` | DataTable API 맞춤 |
| `TransactionWorkspacePage.tsx` | Button `size="xs"` / `variant="outline"` 미존재 | `"sm"` / `"secondary"` 또는 `"ghost"`로 교체 |
| `TransactionWorkspacePage.tsx` | Card `action=` → `actions=` | prop명 수정 |
| `TransactionWorkspacePage.tsx` | svcGroups 유니온 타입 속성 접근 에러 | `SvcItem` 인터페이스 정의 |
| `VdrOverviewPage.tsx` | KpiCard `value` number → string 필요 | `String()` 래핑 |
| `VdrTab.tsx` | KpiCard `icon` JSX 엘리먼트 → 컴포넌트 참조 필요 | `<FolderTree />` → `FolderTree` |
| `CreateLegalDocumentPage.tsx` | 미사용 `Spinner` import | 제거 |
| `FDDReportsTab.tsx` | `target_company` → `target_company_name` | 존재하지 않는 속성 수정 |
| `useActivityLog.ts` | `size` 구조분해 누락 | `const { params, page, size }` 추가 |

---

## 3. 주요 코드 패턴

### 3.1 파일 업로드 보안 (B-C2)

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt", ".hwp", ".hwpx", ".txt"}

content = await file.read()
if len(content) > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다")
ext = Path(safe_filename).suffix.lower()
if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다")
```

### 3.2 비관적 잠금 (B-M1)

```python
lock_q = select(Contract).where(Contract.id == contract_id).with_for_update()
await db.execute(lock_q)
# 이후 MAX(version_number) 조회 → 동시 업로드 시 중복 번호 방지
```

### 3.3 경로 탐색 방어 (B-m1)

```python
try:
    file_path.resolve().relative_to(UPLOAD_DIR.resolve())
except ValueError:
    raise HTTPException(status_code=403, detail="잘못된 파일 경로입니다")
```

### 3.4 useEffect prop 동기화 (F-M3)

```tsx
useEffect(() => {
  setTitle(existing?.title ?? "");
  setMeetingDate(existing?.meeting_date ?? "");
  // ... 8개 필드 동기화
}, [existing]);
```

---

## 4. 변경 파일 목록

### 백엔드 (5개 파일)

| 파일 | 변경 |
|------|------|
| `deal-mgmt/app/routers/contract_markups.py` | B-C1, B-C2, B-M1, B-m1, B-m2 |
| `deal-mgmt/app/routers/meeting_logs.py` | B-M2, B-m4 |
| `deal-mgmt/app/routers/negotiation_issues.py` | B-M3 |
| `deal-mgmt/app/schemas/meeting_log.py` | B-m3 |
| `deal-mgmt/pyproject.toml` | B-M4 |

### 프론트엔드 (11개 파일)

| 파일 | 변경 |
|------|------|
| `amic-platform/src/modules/ma/components/meetings/ContractMarkupTimeline.tsx` | F-M1 |
| `amic-platform/src/modules/ma/components/meetings/MeetingLogsTab.tsx` | F-M2, F-m3, F-m4 |
| `amic-platform/src/modules/ma/components/meetings/MeetingLogForm.tsx` | F-M3 |
| `amic-platform/src/modules/ma/components/meetings/ActionItemList.tsx` | F-m1 |
| `amic-platform/src/modules/ma/components/meetings/AttendeeList.tsx` | F-m2 |
| `amic-platform/src/modules/ma/components/meetings/NegotiationIssuePanel.tsx` | F-m3 |
| `amic-platform/src/components/ui/InlineSelect.tsx` | disabled prop 추가 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` | 빌드 에러 ~6건 |
| `amic-platform/src/modules/vdr/pages/VdrOverviewPage.tsx` | KpiCard value 타입 |
| `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx` | KpiCard icon 타입 |
| `amic-platform/src/hooks/useActivityLog.ts` | size 구조분해 |

---

## 5. 검증 결과

```
# 백엔드 테스트
$ cd deal-mgmt && python -m pytest tests/test_meeting_logs.py tests/test_negotiation_issues.py tests/test_contract_markups.py -v
27 passed in 4.80s ✅

# 프론트엔드 빌드
$ cd amic-platform && npm run build
✓ built in 10.21s ✅
```
