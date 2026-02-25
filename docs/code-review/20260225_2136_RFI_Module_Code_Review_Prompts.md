# RFI 모듈 코드 리뷰 프롬프트

**작성일**: 2026-02-25 21:36
**목적**: RFI 모듈(백엔드 11파일 + 프론트엔드 6파일) 심층 코드 리뷰
**형식**: docs/code-review/20260213_0908_Code_Review_Prompts.md V1/V2 패턴 준수

---

## 실행 결과

| 세션 | 리뷰 대상 | 발견사항 | 리포트 |
|------|-----------|----------|--------|
| A (백엔드) | 11개 파일 | 🔴2 🟠7 🟡13 🔵4 = 26개 | `20260225_2136_RFI_Module_Backend_Code_Review.md` |
| B (프론트엔드) | 6+개 파일 | 🟠1 🟡12 🔵10 = 23개 | `20260225_2136_RFI_Module_Frontend_Code_Review.md` |

---

## 세션 A: RFI 백엔드 심층 코드 리뷰

### 리뷰 대상 (11개)

| # | 파일 | 역할 |
|---|------|------|
| 1 | `deal-mgmt/app/models/rfi.py` | RFI 라운드 모델 |
| 2 | `deal-mgmt/app/models/rfi_item.py` | RFI 질문/응답 모델 |
| 3 | `deal-mgmt/app/models/rfi_checklist_mapping.py` | 체크리스트 매핑 모델 |
| 4 | `deal-mgmt/app/models/enums.py` (620~667행) | RFI 관련 5개 Enum |
| 5 | `deal-mgmt/app/schemas/rfi.py` | Pydantic 스키마 15개 |
| 6 | `deal-mgmt/app/routers/rfi.py` | 18개 엔드포인트 |
| 7 | `deal-mgmt/app/services/rfi_service.py` | 핵심 CRUD + 워크플로우 19개 함수 |
| 8 | `deal-mgmt/app/services/rfi_sync_service.py` | 체크리스트 동기화 |
| 9 | `deal-mgmt/app/excel/rfi_excel.py` | Excel 내보내기/가져오기 |
| 10 | `deal-mgmt/migrations/versions/021_rfi_request_for_information.py` | 3 테이블 스키마 |
| 11 | `deal-mgmt/tests/test_rfi.py` | 25개 테스트 케이스 |

### 점검 관점 (8가지)
1. 보안 · 권한 검증
2. 데이터 무결성 · 타입 일관성
3. 워크플로우 · 상태 전환 로직
4. SQL 쿼리 · 성능 · 인덱스
5. Excel 가져오기/내보내기 품질
6. 테스트 커버리지 · 품질
7. 에러 처리 · Audit 추적
8. DD 자동 생성 · 동기화 로직

### 참조 패턴
- `deal-mgmt/app/routers/dd_checklists.py`
- `deal-mgmt/app/services/transaction_service.py`
- `deal-mgmt/app/schemas/legal_document.py`
- `deal-mgmt/app/core/exceptions.py`

---

## 세션 B: RFI 프론트엔드 + FE↔BE 정합성 코드 리뷰

### 리뷰 대상 (6+개)

| # | 파일 | 역할 |
|---|------|------|
| 1 | `amic-platform/src/modules/ma/types/rfi.ts` | 20+ TypeScript 인터페이스 |
| 2 | `amic-platform/src/modules/ma/hooks/useRFI.ts` | 18개 React Query 훅 |
| 3 | `amic-platform/src/modules/ma/components/rfi/RFIPanel.tsx` | 메인 패널 |
| 4 | `amic-platform/src/modules/ma/components/rfi/RFICreateModal.tsx` | 생성 모달 |
| 5 | `amic-platform/src/modules/ma/components/rfi/RFIDetailView.tsx` | 상세 뷰 |
| 6 | `amic-platform/src/modules/ma/components/rfi/RFIItemRow.tsx` | 아이템 행 |
| 7 | `amic-platform/src/modules/ma/constants.ts` (수정부분) | RFI 상수 |
| 8 | `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` (수정부분) | RFI 탭 |

### 점검 관점 (7가지)
1. TypeScript 타입 ↔ Pydantic 스키마 정합성
2. React Query 훅 품질 · 캐시 무효화
3. 접근성 (WCAG 2.1)
4. 상태 관리 · 컴포넌트 설계
5. 에러 처리 · 로딩 상태 · 빈 상태
6. UX 패턴 · 기존 컴포넌트 일관성
7. 성능 · 리렌더링

### 참조 패턴
- `amic-platform/src/modules/ma/hooks/useDDChecklist.ts`
- `deal-mgmt/app/schemas/rfi.py` (BE 정합성 검증)
- `deal-mgmt/app/models/enums.py` (BE 정합성 검증)

---

## 수정 우선순위 종합

### 즉시 수정 (Critical/Major)
| ID | 심각도 | 요약 |
|---|---|---|
| BE-SEC-01 | 🔴 Critical | Content-Disposition 헤더 인젝션 |
| BE-SEC-02 | 🔴 Critical | Excel import 파일 검증 부재 |
| BE-DATA-05 | 🟠 Major | RFIUpdate에서 status 직접 변경 → 워크플로우 우회 |
| BE-WF-02 | 🟠 Major | ACCEPTED 아이템 재응답 가능 |
| BE-WF-03 | 🟠 Major | PENDING 아이템 직접 ACCEPTED 가능 |
| BE-SYNC-01 | 🟠 Major | DD 자동생성 시 매핑 미생성 |
| BE-DATA-01 | 🟠 Major | due_date DateStr 미사용 |
| BE-DATA-02 | 🟠 Major | DateTime 컬럼 타입 힌트 str |
| BE-WF-01 | 🟠 Major | DRAFT→CLOSED 직접 전환 |
| FE-HOOK-01 | 🟠 Major | revokeObjectURL 즉시 호출 |

### 단기 수정 (Moderate 상위)
| ID | 요약 |
|---|---|
| FE-HOOK-04 | 서버 에러 detail 미전달 |
| FE-ERR-01/02 | isError 미처리 |
| FE-DESIGN-02 | 폼 불완전 초기화 |
| FE-UX-02 | Excel Import UI 미구현 |
| BE-TEST-03 | respond_to_item deal-level 접근 제어 |
