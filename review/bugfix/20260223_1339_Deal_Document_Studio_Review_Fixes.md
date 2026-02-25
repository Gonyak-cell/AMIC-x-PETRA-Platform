# Deal Document Studio 코드 리뷰 수정 내역

> 작성: 2026-02-23 13:39:00 | 브랜치: `feat/ma-workflow`

---

## 수정 범위 요약

Deal Document Studio 모듈(법률 문서 생성 SPA/SHA/BTA/SSA/MOU) 전체 코드 리뷰 후 **15개 이슈 수정 완료**.

| 우선순위 | 수정 건수 | 상태 |
|---------|---------|------|
| P0 보안·안정성 | 4건 | ✅ 완료 |
| P1 기능·접근성 | 7건 | ✅ 완료 |
| P2 운영·품질 | 4건 | ✅ 완료 |

---

## P0 — 보안·안정성 수정

### BE-SEC-01: 경로 탐색(Path Traversal) 방어 추가 ✅

- **파일**: [deal-mgmt/app/routers/legal_documents.py](../../deal-mgmt/app/routers/legal_documents.py)
- **수정 내용**: `_SAFE_OUTPUT_DIR` 상수 추가, 다운로드 엔드포인트에서 `Path(doc.file_path).resolve()`가 안전 디렉터리 내에 있는지 검증
- **Before**: `return FileResponse(path=doc.file_path, ...)` — DB 경로를 직접 사용
- **After**: `file_path.resolve()`와 `_SAFE_OUTPUT_DIR`을 비교, 외부 경로면 403 반환

### BE-SEC-02: 거래 소유권 검증 추가 ✅

- **파일**: [deal-mgmt/app/routers/legal_documents.py](../../deal-mgmt/app/routers/legal_documents.py)
- **수정 내용**: `_get_and_authorize_txn()` 헬퍼 함수 추가
  - ADMIN 역할은 모든 거래에 접근 가능
  - 그 외는 `lead_advisor_email` 또는 `deal_captain_email` 일치 시만 접근 허용
- **Before**: 거래 ID 존재 여부만 확인, 요청자 검증 없음
- **After**: 모든 엔드포인트에서 소유권 확인 후 403 반환

### BE-VALID-01: 템플릿 존재성 사전 검증 ✅

- **파일**: [deal-mgmt/app/services/legal_document_service.py](../../deal-mgmt/app/services/legal_document_service.py)
- **수정 내용**: `generate_document()`에서 렌더링 스레드 시작 전 `template_path.exists()` 체크 추가
- **Before**: 없는 템플릿으로 `asyncio.to_thread` 실행 → 스레드 내부에서 FileNotFoundError 발생
- **After**: 조기 실패 (`status=FAILED`, 친화적 오류 메시지 포함)

### BE-VALID-02: Pydantic 파라미터 유효성 검증 강화 ✅

- **파일**: [deal-mgmt/app/schemas/legal_document.py](../../deal-mgmt/app/schemas/legal_document.py)
- **수정 내용**:
  - `DateStr = Annotated[str, BeforeValidator(_validate_date_str)]` — YYYY-MM-DD 형식 + 실제 날짜 유효성 검증
  - 모든 수치 필드에 `ge=0` 제약 추가
  - `SPAParameters`: `transfer_shares ≤ total_shares` 교차 필드 검증
  - `SSAParameters`: `post_money_valuation ≥ pre_money_valuation` 교차 필드 검증
  - `SHAParameters.board_seats_total: int = Field(3, ge=1)` — 0 의석 방지

---

## P1 — 기능·접근성 수정

### FE-A11Y-01: 폼 레이블 연결 (WCAG 2.1 준수) ✅

- **파일**: [amic-platform/src/modules/docs/pages/CreateLegalDocumentPage.tsx](../../amic-platform/src/modules/docs/pages/CreateLegalDocumentPage.tsx)
- **수정 내용**:
  - `StepIndicator`: `<ol role="list" aria-label="...">` + 각 단계에 `aria-current="step"` 속성
  - 문서 제목 input: `<label htmlFor="legal-doc-title">` + `<input id="legal-doc-title" required aria-required="true">`

### FE-A11Y-02: 문서 유형 선택기 ARIA 속성 ✅

- **파일**: [amic-platform/src/modules/docs/components/DocumentTypePicker.tsx](../../amic-platform/src/modules/docs/components/DocumentTypePicker.tsx), [LegalDocTypePicker.tsx](../../amic-platform/src/modules/docs/components/LegalDocTypePicker.tsx)
- **수정 내용**: 컨테이너에 `role="radiogroup"`, 각 버튼에 `role="radio"` + `aria-checked={isSelected}` + `aria-label={설명}` 추가
- **Before**: 색상만으로 선택 상태 표현 → 스크린리더 접근 불가
- **After**: 라디오 그룹 패턴으로 키보드·스크린리더 완전 지원

### FE-TYPE-01: LegalParamsForm 타입 강화 ✅

- **파일**: [amic-platform/src/modules/docs/components/LegalParamsForm.tsx](../../amic-platform/src/modules/docs/components/LegalParamsForm.tsx)
- **수정 내용**: `Record<string, unknown>` → `Partial<SPAParameters>` 등 타입별 인터페이스 사용
  - `LabeledInput`, `LabeledTextarea` 컴포넌트 — `htmlFor`/`id` 자동 생성
  - 각 서브폼(`SPAForm`, `SHAForm`, `BTAForm`, `SSAForm`, `MOUForm`)이 타입 안전한 `Partial<T>` 파라미터 사용
  - `fieldset`/`legend`로 체크박스 그룹 묶기
  - 배열 항목에 `aria-label={n번째 항목}`, 삭제 버튼에 `aria-label="삭제"` 추가

### FE-ERR-01: API 에러 메시지 상세 전달 ✅

- **파일**: [amic-platform/src/modules/docs/hooks/useLegalDocuments.ts](../../amic-platform/src/modules/docs/hooks/useLegalDocuments.ts)
- **수정 내용**: `extractErrorDetail(err, fallback)` 헬퍼 추가, 3개 mutation `onError` 핸들러에 적용
- **Before**: `() => toast.error("문서 생성 요청에 실패했습니다.")` — 제네릭 메시지
- **After**: `(err) => toast.error(extractErrorDetail(err, fallback))` — 서버 `detail` 메시지 우선 표시

### FE-UX-01: GENERATING 상태 폴링 ✅

- **파일**: [amic-platform/src/modules/docs/hooks/useLegalDocuments.ts](../../amic-platform/src/modules/docs/hooks/useLegalDocuments.ts)
- **수정 내용**: `useLegalDocuments`에 `refetchInterval` 추가
  - `GENERATING` 상태 문서가 있을 때 3초마다 자동 재조회
  - `GENERATING` 문서가 없으면 폴링 중단

### BE-HTTP-01: 다운로드 엔드포인트 HTTP 상태 코드 수정 ✅

- **파일**: [deal-mgmt/app/routers/legal_documents.py](../../deal-mgmt/app/routers/legal_documents.py)
- **수정 내용**: 문서 미준비 시 `409 CONFLICT` → `400 BAD REQUEST`로 변경 (커스텀 예외 핸들러 경유)
- **근거**: 409는 "현재 리소스 상태와 충돌"이지만, "아직 준비 안 됨"은 의미적으로 400이 적합

### BE-ERR-01: 서비스 레이어 커스텀 예외 분리 ✅

- **파일**: [deal-mgmt/app/core/exceptions.py](../../deal-mgmt/app/core/exceptions.py), [legal_document_service.py](../../deal-mgmt/app/services/legal_document_service.py), [legal_documents.py](../../deal-mgmt/app/routers/legal_documents.py)
- **수정 내용**:
  - `DocumentNotFoundError`, `DocumentNotReadyError` 커스텀 예외 추가
  - 핸들러 등록: `DocumentNotFoundError → 404`, `DocumentNotReadyError → 400`
  - 서비스 레이어에서 `from fastapi import HTTPException` 로컬 임포트 제거
  - 라우터의 다운로드 엔드포인트에서 `DocumentNotReadyError` 사용

---

## P2 — 운영·품질 수정

### BE-PERF-01: DB 인덱스 마이그레이션 추가 ✅

- **파일**: [deal-mgmt/migrations/versions/008_add_legal_document_indexes.py](../../deal-mgmt/migrations/versions/008_add_legal_document_indexes.py) (신규)
- **추가 인덱스**:
  - `ix_legal_documents_status`: 상태별 필터링 최적화
  - `ix_legal_documents_created_at`: 최신순 정렬 최적화 (DESC)
  - `ix_legal_documents_txn_status`: 거래별 상태 복합 인덱스 (폴링 쿼리 최적화)

### BE-TEST-01: 추가 테스트 케이스 ✅

- **파일**: [deal-mgmt/tests/test_legal_documents.py](../../deal-mgmt/tests/test_legal_documents.py)
- **추가 테스트**:
  - `test_create_document_invalid_date_format` — 슬래시 구분자(2026/03/15) → 422
  - `test_create_document_invalid_date_value` — 존재하지 않는 날짜(2026-13-45) → 422
  - `test_create_document_negative_shares` — 음수 주식 수 → 422
  - `test_create_document_transfer_exceeds_total_shares` — 양도 > 총발행 → 422
  - `test_create_document_ssa_post_money_less_than_pre_money` — Post < Pre → 422
  - `test_download_failed_document_returns_400` — FAILED 다운로드 → 400 (409 아님)
  - `test_document_not_found_returns_404` — 커스텀 예외 형식 검증
  - 기존 `test_download_not_ready_document`: `409` → `400` 기대값 수정

### BE-OPS-01: 파일 정리 스크립트 ✅

- **파일**: [deal-mgmt/scripts/cleanup_old_files.py](../../deal-mgmt/scripts/cleanup_old_files.py) (신규)
- **기능**:
  - 30일(기본) 초과 `.docx` 파일 자동 삭제
  - `--dry-run` 옵션으로 삭제 전 미리보기
  - `--days N` 옵션으로 보존 기간 조정
  - 프로젝트 루트 외부 경로 삭제 방지 (안전 경로 검증)
  - 통계 출력: 검사/삭제 건수, 회수 공간

---

## 수정된 파일 목록

**백엔드**:
- `deal-mgmt/app/routers/legal_documents.py` ← 경로 방어, 소유권, HTTP 상태, 커스텀 예외
- `deal-mgmt/app/services/legal_document_service.py` ← 템플릿 검증, HTTPException 제거
- `deal-mgmt/app/schemas/legal_document.py` ← DateStr, 범위 검증, 교차 필드 검증
- `deal-mgmt/app/core/exceptions.py` ← DocumentNotFoundError, DocumentNotReadyError 추가
- `deal-mgmt/tests/test_legal_documents.py` ← 기존 수정 + 7개 테스트 추가
- `deal-mgmt/migrations/versions/008_add_legal_document_indexes.py` ← 신규

**프론트엔드**:
- `amic-platform/src/modules/docs/hooks/useLegalDocuments.ts` ← 에러 상세화, GENERATING 폴링
- `amic-platform/src/modules/docs/components/LegalParamsForm.tsx` ← 타입 강화, a11y
- `amic-platform/src/modules/docs/components/DocumentTypePicker.tsx` ← ARIA radiogroup
- `amic-platform/src/modules/docs/components/LegalDocTypePicker.tsx` ← ARIA radiogroup
- `amic-platform/src/modules/docs/pages/CreateLegalDocumentPage.tsx` ← StepIndicator a11y, label 연결

**스크립트**:
- `deal-mgmt/scripts/cleanup_old_files.py` ← 신규
