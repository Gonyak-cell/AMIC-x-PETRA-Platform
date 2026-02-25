# RFI 모듈 코드 리뷰 수정 보고서

> **작성일**: 2026-02-25 22:04
> **기반 문서**:
> - `docs/code-review/20260225_2136_RFI_Module_Backend_Code_Review.md` (26건)
> - `docs/code-review/20260225_2136_RFI_Module_Frontend_Code_Review.md` (23건)
> **결과**: 백엔드 34/34 테스트 통과 | 프론트엔드 tsc 0 errors + vite build OK

---

## 1. 백엔드 수정 (20건 적용 / 6건 보류)

### Critical (2/2 적용)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| BE-SEC-01 | Content-Disposition 헤더 인젝션 | `routers/rfi.py` | `re.sub` + RFC 5987 `filename*=UTF-8''` 인코딩 |
| BE-SEC-02 | Excel 업로드 검증 미흡 | `routers/rfi.py` | 확장자(.xlsx/.xls) + 10MB 크기 제한, `content: bytes` 전달 |

### Major (9/10 적용)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| BE-DATA-01 | due_date `str` → `DateStr` | `schemas/rfi.py` | 5개 스키마 필드 `DateStr` 타입 전환 |
| BE-DATA-02 | DateTime 컬럼 Mapped 타입 | `models/rfi.py`, `rfi_item.py`, `rfi_checklist_mapping.py` | `Mapped[str\|None]` → `Mapped[datetime\|None]` |
| BE-DATA-03 | response_documents 타입 | `models/rfi_item.py` | `Mapped[dict\|None]` → `Mapped[list\|None]` |
| BE-DATA-05 | RFIUpdate에 status 필드 | `schemas/rfi.py` | `status` 필드 제거 (상태 전이는 전용 엔드포인트만) |
| BE-WF-01 | close_rfi 상태 가드 | `services/rfi_service.py` | DRAFT/CLOSED/CANCELLED → CLOSED 차단 |
| BE-WF-02 | respond 재응답 차단 | `services/rfi_service.py` | ACCEPTED/NOT_APPLICABLE 상태 아이템 재응답 차단 |
| BE-WF-03 | review 상태 가드 | `services/rfi_service.py` | RESPONDED/CLARIFICATION_NEEDED만 리뷰 허용 |
| BE-WF-05 | extend_deadline 과거 날짜 | `services/rfi_service.py` | 과거 날짜 + 현재 마감일 이전 날짜 차단 |
| BE-SYNC-01 | DD 자동생성 매핑 누락 | `services/rfi_service.py` | `RFIChecklistMapping` 레코드 동시 생성 |
| ~~BE-PERF-02~~ | ~~Summary SQL GROUP BY~~ | — | **보류** (MEDIUM 신뢰도, 선택적 최적화) |

### Moderate (7/10 적용)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| BE-PERF-01 | 페이지네이션 미적용 | `routers/rfi.py`, `services/rfi_service.py` | `limit`/`offset` Query 파라미터 추가 |
| BE-PERF-03 | batch_add N회 refresh | `services/rfi_service.py` | 단일 IN 쿼리로 대체 |
| BE-EXCEL-01 | 헤더 탐지 오인식 | `excel/rfi_excel.py` | `has_question` 플래그 + `matched >= 2` 조건 |
| BE-EXCEL-02 | 행 레벨 에러 수집 | `excel/rfi_excel.py` | try/except + `errors.append(f"행 {row_idx}: ...")` |
| BE-SEC-03 | 프라이빗 함수 호출 | `routers/rfi.py`, `services/rfi_service.py` | `get_item_mappings()` 퍼블릭 함수 추가 |
| BE-TEST-03 | respond 권한 체크 | `routers/rfi.py` | `check_client_deal_access` 호출 추가 |
| BE-AUDIT-01 | 응답 절삭 100자 | `services/rfi_service.py` | 500자로 확장 |

| 보류 ID | 사유 |
|---------|------|
| BE-PERF-02 | MEDIUM 신뢰도, 선택적 최적화 |
| BE-WF-04 | 테스트만 추가 (기존 코드 정상) |
| BE-SYNC-02 | Minor, ws_category_map 매핑 현재 운영에 충분 |

### Minor (2/4 적용)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| BE-DATA-04 | question_number 유니크 | `migrations/versions/022_rfi_question_number_unique.py` | `(rfi_id, question_number)` 복합 유니크 제약 |
| BE-SYNC-03 | commit 누락 | `services/rfi_sync_service.py` | `synced_count == 0`일 때도 commit 실행 |

### 테스트 추가 (12건 신규)

```
test_close_rfi_from_draft_fails          (BE-WF-01)
test_respond_to_accepted_item_fails      (BE-WF-02)
test_review_pending_item_fails           (BE-WF-03)
test_clarification_rerespond_flow        (BE-WF-04)
test_extend_deadline_past_date_fails     (BE-WF-05)
test_extend_deadline_earlier_than_current_fails (BE-WF-05)
test_create_rfi_invalid_date_fails       (BE-DATA-01)
test_update_rfi_status_field_ignored     (BE-DATA-05)
test_import_invalid_extension_fails      (BE-SEC-02)
test_batch_add_items                     (기존 보강)
test_excel_export_import_roundtrip       (기존 보강)
test_auto_generate_from_dd              (기존 보강)
```

**결과**: `34 passed` (전체 통과)

---

## 2. 프론트엔드 수정 (13건 적용)

### Hook 개선 (3건)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| FE-HOOK-01 | revokeObjectURL 즉시 호출 | `hooks/useRFI.ts` | `setTimeout(() => URL.revokeObjectURL(url), 5000)` |
| FE-HOOK-04 | 에러 메시지 제네릭 | `hooks/useRFI.ts` | `extractErrorDetail()` 헬퍼 + 15개 mutation 적용 |
| FE-UX-02 | useImportRFI 훅 분리 | `hooks/useRFI.ts` | `useImportRFI()` 전용 훅 추가 |

### 에러 처리 (2건)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| FE-ERR-01 | isError 미처리 | `components/rfi/RFIDetailView.tsx` | `if (isError) return <에러 UI>` 추가 |
| FE-ERR-02 | isError 미처리 | `components/rfi/RFIPanel.tsx` | `if (isError) return <에러 UI>` 추가 |

### 디자인 일관성 (2건)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| FE-DESIGN-01 | 레이블 하드코딩 | `constants.ts` + 4개 컴포넌트 | 4개 공유 LABELS Record 추출 |
| FE-DESIGN-02 | INITIAL_FORM 불완전 | `components/rfi/RFICreateModal.tsx` | 누락 필드 전체 초기화 |

### 접근성 (3건)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| FE-A11Y-01 | radiogroup 미적용 | `RFIDetailView.tsx`, `RFIPanel.tsx` | `role="radiogroup"` + `aria-checked` |
| FE-A11Y-02 | htmlFor/id 미연결 | `RFICreateModal.tsx` | 7개 필드 `htmlFor`/`id` 페어링 |
| FE-A11Y-03 | aria-expanded 미적용 | `RFIItemRow.tsx` | 토글 버튼 `aria-expanded` 추가 |

### 타입 정합성 (1건)

| ID | 제목 | 파일 | 수정 내용 |
|----|------|------|-----------|
| FE-TYPE-02 | vdr_document_ids 타입 | `schemas/rfi.py` + `models/rfi_item.py` | `list[str] \| None` 통일 |

**검증**: `tsc --noEmit` 0 errors | `vite build` 13.56s OK

---

## 3. 수정 파일 목록

### 백엔드 (8파일 + 마이그레이션 1 + 테스트 1)

| 파일 | 수정 유형 |
|------|-----------|
| `deal-mgmt/app/routers/rfi.py` | SEC-01, SEC-02, SEC-03, TEST-03, PERF-01 |
| `deal-mgmt/app/services/rfi_service.py` | WF-01~03, WF-05, SYNC-01, PERF-01, PERF-03, AUDIT-01, SEC-03 |
| `deal-mgmt/app/schemas/rfi.py` | DATA-01, DATA-05, TYPE-02 |
| `deal-mgmt/app/models/rfi.py` | DATA-02 |
| `deal-mgmt/app/models/rfi_item.py` | DATA-02, DATA-03, TYPE-02 |
| `deal-mgmt/app/models/rfi_checklist_mapping.py` | DATA-02 |
| `deal-mgmt/app/excel/rfi_excel.py` | EXCEL-01, EXCEL-02, SEC-02 |
| `deal-mgmt/app/services/rfi_sync_service.py` | SYNC-03 |
| `deal-mgmt/migrations/versions/022_rfi_question_number_unique.py` | DATA-04 (신규) |
| `deal-mgmt/tests/test_rfi.py` | 12개 테스트 추가 |

### 프론트엔드 (6파일)

| 파일 | 수정 유형 |
|------|-----------|
| `amic-platform/src/modules/ma/hooks/useRFI.ts` | HOOK-01, HOOK-04, UX-02 |
| `amic-platform/src/modules/ma/components/rfi/RFIPanel.tsx` | ERR-02, DESIGN-01, A11Y-01 |
| `amic-platform/src/modules/ma/components/rfi/RFIDetailView.tsx` | ERR-01, DESIGN-01, A11Y-01 |
| `amic-platform/src/modules/ma/components/rfi/RFICreateModal.tsx` | DESIGN-02, A11Y-02 |
| `amic-platform/src/modules/ma/components/rfi/RFIItemRow.tsx` | DESIGN-01, A11Y-03 |
| `amic-platform/src/modules/ma/constants.ts` | DESIGN-01 (4개 LABELS Record) |
