# RFI 모듈 코드 리뷰 프롬프트

> **목적**: 구현 완료된 RFI 모듈(백엔드 11파일 + 프론트엔드 6파일)에 대한 꼼꼼한 코드 리뷰 프롬프트 작성
> **작성일**: 2026-02-25 21:23:00
> **형식**: 기존 `docs/code-review/20260213_0908_Code_Review_Prompts.md` V1/V2 패턴 준수

---

## 실행 방법

1. 새 세션 열고 **세션 A** 프롬프트 복사 붙여넣기 → 백엔드 리뷰 실행
2. 또 다른 새 세션에서 **세션 B** 프롬프트 복사 붙여넣기 → 프론트엔드 리뷰 실행
3. 각 리포트를 `docs/code-review/` 폴더에 저장
4. 발견된 이슈 중 Critical/Major를 우선 수정
5. 수정 내역을 `review/` 폴더에 문서화

---

## 세션 A: RFI 백엔드 심층 코드 리뷰

```
RFI (Request for Information) 모듈 백엔드 구현을 꼼꼼하게 코드 리뷰해줘.
모든 파일을 반드시 Read 도구로 읽은 후 리뷰해.

## 배경

RFI 모듈은 M&A 거래에서 바이어/셀러 간 정보 요청을 관리하는 시스템이다.
라운드 단위(rfis) — 개별 질문/응답(rfi_items) — 체크리스트 매핑(rfi_checklist_mappings) 3계층 구조.
DD 체크리스트 미완료 항목에서 자동 생성 + Excel 가져오기/내보내기 + 응답률 기반 상태 자동 전환 로직 포함.

## 리뷰 대상 파일 (11개)

### 모델
1. deal-mgmt/app/models/rfi.py — RFI 라운드 모델
2. deal-mgmt/app/models/rfi_item.py — RFI 질문/응답 아이템 모델
3. deal-mgmt/app/models/rfi_checklist_mapping.py — 체크리스트 매핑 모델
4. deal-mgmt/app/models/enums.py — RFI 관련 5개 Enum (620~667행 부근)

### 스키마
5. deal-mgmt/app/schemas/rfi.py — Pydantic 스키마 15개

### 라우터
6. deal-mgmt/app/routers/rfi.py — 18개 엔드포인트

### 서비스
7. deal-mgmt/app/services/rfi_service.py — 핵심 CRUD + 워크플로우 (19개 함수)
8. deal-mgmt/app/services/rfi_sync_service.py — 체크리스트 동기화 서비스

### Excel
9. deal-mgmt/app/excel/rfi_excel.py — Excel 내보내기/가져오기

### 마이그레이션
10. deal-mgmt/migrations/versions/021_rfi_request_for_information.py — 3 테이블 스키마

### 테스트
11. deal-mgmt/tests/test_rfi.py — 25개 테스트 케이스

## 점검 관점 (8가지)

### 1. 보안 · 권한 검증
- rfi.py 라우터에서 모든 엔드포인트가 `get_jwt_claims` 또는 `require_write_access()`를 올바르게 사용하는지
- respond_to_item 엔드포인트가 `get_jwt_claims`만 사용 — 클라이언트 포탈 사용자가 응답하는 경우인지, 아니면 `require_write_access`가 적절한지 판단
- check_client_deal_access 호출 패턴: create_rfi에서는 호출 안 함 → 다른 CRUD 엔드포인트와 권한 처리 일관성 확인
- Excel import에서 업로드된 파일의 확장자/MIME 타입 검증 여부 (악의적 파일 업로드 방어)
- get_item_mappings에서 `_get_rfi_item` 호출 시 private 함수(`_` prefix) 직접 호출 → 라우터에서 private 함수 접근이 적절한지
- Excel export의 파일명에 사용자 입력(`rfi.title`) 포함 → Content-Disposition 헤더 인젝션 가능성

### 2. 데이터 무결성 · 타입 일관성
- rfi.py 모델 due_date가 `String(10)` → 날짜 검증 없음. 스키마에서도 `max_length=10`만 검증 → "1234567890" 같은 잘못된 입력 허용 여부
- RFIExtendDeadlineInput의 `min_length=10, max_length=10` — 날짜 포맷 검증이 없음. Legal Document 스키마의 `DateStr = Annotated[str, BeforeValidator]` 패턴과 비교
- response_documents가 `JSONB` → 스키마에서 `list[dict]`로만 정의 → 내부 dict의 구조가 미정의. 악의적 대용량 JSON 방어 없음
- vdr_document_ids도 `JSONB` → 스키마에서 `list | None`만 정의 → 구조 미정의
- rfi.py 모델 sent_at, closed_at의 Mapped 타입이 `str | None`이지만 실제로는 DateTime 컬럼 → 타입 힌트 불일치

### 3. 워크플로우 · 상태 전환 로직
- _auto_transition_rfi_status: `CLARIFICATION_NEEDED` 상태 아이템이 responded_items 카운트에 포함되는지 확인 → FULLY_RESPONDED 전환이 차단/허용되는 조건 분석
- send_rfi: DRAFT→SENT만 허용하지만, close_rfi는 CLOSED 상태만 차단하고 DRAFT→CLOSED도 허용 → 의도인지 검증
- respond_to_item: 이미 RESPONDED/ACCEPTED 상태인 아이템에 재응답 가능 여부 (상태 체크 없음)
- review_item: RESPONDED 상태가 아닌 아이템도 리뷰 가능 → PENDING 아이템 직접 ACCEPTED 가능
- 비정규화 카운트(total_items, responded_items, accepted_items)와 실제 items 간 정합성 보장 메커니즘

### 4. SQL 쿼리 · 성능 · 인덱스
- list_rfis에 페이지네이션(limit/offset) 없음 → 대량 RFI 시 성능 문제
- list_rfi_items에도 페이지네이션 없음
- get_rfi_summary: 거래 전체 RFI 아이템을 메모리에 로딩 후 Python에서 집계 → 아이템 수 증가 시 O(N) 메모리. SQL GROUP BY 활용 가능 여부
- _update_rfi_counts: 매 아이템 추가/수정/삭제 시 모든 아이템 재조회 → RFI당 아이템이 많을 때 성능
- batch_add_items: N개 아이템 개별 `db.add()` 후 N번 `db.refresh()` → `add_all()` + 단일 refresh로 최적화 가능
- 마이그레이션에서 `(rfi_id, question_number)` 복합 유니크 제약 없음 → 동일 rfi_id 내 question_number 중복 가능
- dd_checklists.py 라우터(참조 패턴)와 비교하여 쿼리 패턴 일관성

### 5. Excel 가져오기/내보내기 품질
- import_rfi_from_excel: 헤더 감지 조건이 `matched >= 2` → 데이터 행을 헤더로 오인할 가능성
- HEADER_MAPPING: "description"이 "question"에 매핑됨 → 일부 Excel에서 Description 컬럼이 질문 상세에 해당할 수 있음
- import에서 new_item 생성 시 question_number 충돌 가능
- export 시 openpyxl import가 함수 내부에서 발생 → 의존성 누락 시 런타임 에러
- import에서 에러 리스트(errors)가 빈 리스트로만 반환 → try/except에서 행별 에러를 수집하지 않음
- import에서 파일 크기 제한 없음 → 대용량 Excel로 서버 메모리 공격 가능

### 6. 테스트 커버리지 · 품질
- 25개 테스트가 기본 CRUD와 워크플로우를 커버하지만, 아래 경계 케이스 테스트 누락:
  - 동시 응답 (같은 아이템에 동시에 두 사용자가 응답)
  - Excel import/export 기능 테스트 없음 (openpyxl 의존)
  - sync_to_checklists 엔드포인트 테스트 없음
  - 404 이외의 에러 케이스 (422 유효성 검증 실패, 잘못된 enum 값)
  - CLOSED 상태 RFI에 대한 아이템 추가/응답 시도
  - due_date 형식 검증 테스트
  - question 빈 문자열 등 Pydantic 검증 테스트
- conftest.py의 test fixture 공유 패턴 확인 (기존 test_dd_checklists.py와 비교)

### 7. 에러 처리 · Audit 추적
- HTTPException이 서비스 레이어에 직접 존재 → 기존 패턴(core/exceptions.py의 커스텀 예외)과 비교
- audit_service.record() 호출 일관성: respond_to_item에서 response 내용 자름 → 감사 추적 완전성
- rfi_sync_service.py: synced_count > 0일 때만 commit → synced_count == 0이어도 이전 변경사항이 커밋되지 않는 것이 안전한지
- extend_deadline: 기존 마감일보다 이전 날짜로 연장 가능 (날짜 비교 없음)

### 8. DD 자동 생성 · 동기화 로직
- generate_from_dd_checklist의 ws_category_map 하드코딩 — DDChecklistWorkstream enum 변경 시 깨짐 위험
- `dd.workstream.value.split("_")[0]` → workstream 값이 예상 형식이 아닐 때 매핑 실패 (조용히 GENERAL로 폴백)
- sync_accepted_to_checklists: DD만 구현, IM/FDD는 스텁 → 매핑은 생성되지만 동기화는 작동하지 않는 상태
- 자동 생성 시 RFIChecklistMapping 레코드가 생성되지 않음 → source_ref_id만 설정되고 매핑 테이블은 비어 있음

## 참조 패턴 (비교 대상)
- deal-mgmt/app/routers/dd_checklists.py — 가장 유사한 라우터 구조
- deal-mgmt/app/services/transaction_service.py — audit 연동 패턴
- deal-mgmt/app/schemas/legal_document.py — DateStr 타입 검증 패턴
- deal-mgmt/app/core/exceptions.py — 커스텀 예외 클래스 패턴

## 안티할루시네이션 규칙

🚫 파일을 읽지 않고 코드 패턴을 추정하지 마라
🚫 "일반적으로 FastAPI는..." 같은 표현을 근거로 사용하지 마라
✅ 언급하는 모든 파일을 Read 도구로 반드시 읽어라
✅ 정확한 줄 번호를 인용하라 (예: rfi_service.py:538-547)
✅ 3~10줄의 실제 코드를 붙여넣어라
✅ 기존 패턴(dd_checklists.py, transaction_service.py)과 비교 시 해당 파일도 Read로 읽어라

## 기존 허위 발견 경고

- ❌ "HTTPException을 서비스에서 사용하면 안 된다" → 이 프로젝트에서는 서비스 레이어에 HTTPException 사용이 일반적 패턴. core/exceptions.py와의 일관성만 확인하라
- ❌ "audit 로깅이 누락됐다" → audit_service.record()가 대부분의 CRUD에 호출됨을 먼저 확인하라
- ❌ "enum 비교가 잘못됐다" → StrEnum이므로 문자열 비교가 작동함을 먼저 확인하라

## 출력 형식

각 발견사항마다:
1. **ID** — BE-{카테고리}-{번호} (예: BE-SEC-01, BE-PERF-02)
2. **파일:줄번호** — 정확한 위치
3. **실제 코드** — 3~10줄 붙여넣기
4. **문제** — 구체적 설명
5. **심각도** — 🔴 Critical / 🟠 Major / 🟡 Moderate / 🔵 Minor
6. **신뢰도** — HIGH (90%+) / MEDIUM (60-89%) / LOW (<60%)
7. **수정안** — 코드 제안
8. **검증** — ☐ Read로 확인 / ☐ 참조 패턴 비교 확인

발견사항은 심각도 순으로 정렬하라.
리포트를 `docs/code-review/` 폴더에 타임스탬프 파일명으로 저장해줘.
리포트 말미에 검증 투명성(거부된 가설 수/사유)을 기재하라.
```

---

## 세션 B: RFI 프론트엔드 + FE↔BE 정합성 코드 리뷰

```
RFI (Request for Information) 모듈 프론트엔드 구현 및 프론트엔드↔백엔드 정합성을 코드 리뷰해줘.
모든 파일을 반드시 Read 도구로 읽은 후 리뷰해.

## 배경

RFI 모듈은 M&A 거래 워크스페이스 내 "RFI" 탭으로 제공되는 정보 요청 관리 UI이다.
패널(목록+KPI) → 상세(카테고리별 그룹, 필터, 인라인 응답/검토) 구조.
React Query 18개 훅, 4개 컴포넌트, 20+ TypeScript 인터페이스로 구성.

## 리뷰 대상 파일

### 프론트엔드 — 타입
1. amic-platform/src/modules/ma/types/rfi.ts — 20+ TypeScript 인터페이스

### 프론트엔드 — 훅
2. amic-platform/src/modules/ma/hooks/useRFI.ts — 18개 React Query 훅

### 프론트엔드 — 컴포넌트
3. amic-platform/src/modules/ma/components/rfi/RFIPanel.tsx — 메인 패널
4. amic-platform/src/modules/ma/components/rfi/RFICreateModal.tsx — 생성 모달
5. amic-platform/src/modules/ma/components/rfi/RFIDetailView.tsx — 상세 뷰
6. amic-platform/src/modules/ma/components/rfi/RFIItemRow.tsx — 아이템 행

### 프론트엔드 — 수정된 기존 파일
7. amic-platform/src/modules/ma/constants.ts — RFI 상수 + PHASE_VISIBLE_TABS 업데이트
8. amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx — RFI 탭 추가 부분만

### 백엔드 참조 (FE↔BE 정합성 검증용)
9. deal-mgmt/app/schemas/rfi.py — Pydantic 스키마
10. deal-mgmt/app/models/enums.py — RFI Enum 정의 (620~667행)

## 점검 관점 (7가지)

### 1. TypeScript 타입 ↔ Pydantic 스키마 정합성

**반드시 rfi.ts와 schemas/rfi.py를 모두 Read한 후 필드별로 1:1 대조하라.**

- RFIItem.response_documents: TS에서 `Record<string, unknown>[] | null` vs BE에서 `list[dict] | None` → 호환 여부
- RFIItem.vdr_document_ids: TS에서 `string[] | null` vs BE에서 `list | None` → BE의 타입이 더 느슨
- RFIOut vs RFI 인터페이스: BE의 uuid.UUID가 FE에서 string으로 올바르게 매핑되는지 (모든 UUID 필드)
- RFIOut.sent_at / closed_at: BE에서 `datetime | None`, FE에서 `string | null` → ISO 8601 직렬화 확인
- RFICreate: BE에서 `round_number: int = 1` (필수, 기본값) vs FE에서 `round_number?: number` (선택) → 호환성
- RFIItemCreate: 모든 필드의 required/optional 상태가 FE↔BE 일치하는지

### 2. React Query 훅 품질 · 캐시 무효화

- useRFIs의 queryKey에 `{ status, roundNumber }`가 객체로 포함 → 같은 txnId에 대해 다른 필터 조합이 별도 캐시 → 의도적인지, stale data 위험
- useRespondRFIItem과 useReviewRFIItem이 `selectedRFIId ?? ""`로 초기화 → rfiId가 빈 문자열일 때 mutation이 잘못된 URL로 호출 가능
- 모든 mutation의 onError가 제네릭 토스트만 표시 → 서버 detail 메시지 미전달
- useExportRFI: mutation 내부에서 Blob 다운로드 + DOM 조작 → URL.revokeObjectURL 타이밍이 click() 직후라 브라우저에 따라 다운로드 실패 가능
- invalidateQueries 범위: `rfiKeys(txnId)` 전체를 무효화 → 세밀한 무효화 vs 전체 무효화 트레이드오프
- useMutation의 `data as RFI` 타입 단언 → axios response가 실제로 해당 타입인지 런타임 검증 없음

### 3. 접근성 (WCAG 2.1)

- RFIPanel의 상태 필터 버튼들: `<button>` 사용은 OK이나 `role="radiogroup"` + `aria-checked` 없음 → 스크린리더가 선택 상태 인식 불가
- RFIDetailView의 3중 필터(분류/상태/우선순위)도 동일 접근성 문제
- RFICreateModal의 폼 필드: `<label>` + `<input>`이 id/htmlFor로 연결되지 않음 → 레이블 클릭 시 포커스 불가
- RFIItemRow의 질문 텍스트가 `<button>`으로 작동하지만 `aria-expanded` 미설정 → 펼침/접힘 상태 미전달
- RFIDetailView의 KpiCard: 시각적 색상(positive/negative)만으로 의미 전달 → 색맹 사용자 대응
- RFIPanel의 RFI 카드: `onClick`으로 전체 Card 클릭 가능하지만 키보드(Enter/Space) 지원 여부

### 4. 상태 관리 · 컴포넌트 설계

- STATUS_LABELS, STATUS_VARIANT, CATEGORY_LABELS, PRIORITY_LABELS가 RFIPanel, RFIDetailView, RFIItemRow 3곳에 중복 정의 → constants.ts에 이미 일부 정의됨(RFI_STATUS_OPTIONS 등). 중복 제거 가능 여부
- RFIPanel에서 respondItem/reviewItem mutation이 `selectedRFIId ?? ""`로 생성 → selectedRFIId가 null이면 빈 문자열 rfiId로 생성됨. 불필요한 mutation 인스턴스 생성 여부
- RFICreateModal의 `useState<RFICreate>` 초기값에 빈 문자열이 포함 → 닫을 때 폼 초기화에서 `description`, `recipient_name` 등이 초기화되지 않음 (title과 round_number만)
- RFIDetailView가 300줄 이상 → 필터 바, 헤더, 그룹 렌더링 등을 서브컴포넌트로 분리 가능 여부

### 5. 에러 처리 · 로딩 상태 · 빈 상태

- RFIDetailView: isLoading 시 Spinner, 데이터 없으면 텍스트 → error 상태 처리 없음 (useRFI hook의 isError)
- RFIPanel: isLoading 분기만 있고 error 상태 분기 없음
- useExportRFI에서 서버 에러 시 Blob이 아닌 JSON 에러 응답을 받을 수 있음 → Blob으로 파싱 실패 가능
- generateFromDD 버튼이 로딩 중에도 다른 버튼 클릭 가능 → 중복 요청 방어
- RFICreateModal의 handleSubmit에서 form.title.trim() 외 다른 필드 유효성 미검증 (이메일 형식, 날짜 형식)

### 6. UX 패턴 · 기존 컴포넌트 일관성

**참조**: amic-platform/src/modules/ma/hooks/useDDChecklist.ts, amic-platform/src/modules/ma/components/vdr/VdrTab.tsx

- useDDChecklist 훅의 에러 처리 패턴과 useRFI 훅의 패턴 비교
- VdrTab의 패널 구조와 RFIPanel의 구조 비교 (일관된 레이아웃 패턴인지)
- InlineSelect 컴포넌트가 다른 MA 탭에서 사용되는데 RFI 필터에서는 수동 버튼 구현 → 필터 UI 일관성
- 진행률 바 컴포넌트: RFIPanel과 RFIDetailView에서 인라인 div로 구현 → 기존 공유 컴포넌트가 있는지 확인
- Excel Import 훅이 useRFI.ts에 없음 (useExportRFI만 있음) → 프론트엔드에서 Import UI가 구현되었는지 확인 (백엔드에는 import 엔드포인트 존재)
- constants.ts의 PHASE_VISIBLE_TABS에서 RFI가 PREPARATION, MARKETING, BIDDING_DD에만 포함 → NEGOTIATION, SIGNING, CLOSING 단계에서도 RFI 접근이 필요한지 (비즈니스 로직 검토)

### 7. 성능 · 리렌더링

- RFIPanel에서 useRespondRFIItem과 useReviewRFIItem이 `selectedRFIId` 변경마다 새로 생성 → 이전 mutation 상태가 리셋되지 않을 수 있음
- RFIDetailView의 filteredItems와 groupedItems: useMemo 사용은 적절하나, rfi?.items가 selectin으로 관계 로딩되어 매 쿼리마다 새 배열 참조 → useMemo 종속성이 자주 변경될 수 있음
- RFIItemRow가 개별 상태(expanded, responseText, reviewComment) 보유 → 부모 리렌더링 시 모든 Row가 리렌더링되는지 (React.memo 필요 여부)
- categories useMemo가 rfi.items를 매번 Set으로 변환 → 캐시 효과 검증

## 안티할루시네이션 규칙

🚫 파일을 읽지 않고 코드 패턴을 추정하지 마라
🚫 "React에서 일반적으로..." 같은 표현을 근거로 사용하지 마라
✅ 언급하는 모든 파일을 Read 도구로 반드시 읽어라
✅ FE↔BE 정합성은 양쪽 파일을 모두 Read한 후 비교하라
✅ 정확한 줄 번호를 인용하라 (예: RFIPanel.tsx:42-73)
✅ 참조 패턴(useDDChecklist.ts, VdrTab.tsx)도 Read하여 비교하라

## 기존 허위 발견 경고

- ❌ "invalidateQueries가 너무 광범위하다" → 이 프로젝트에서는 rfiKeys(txnId) 수준의 무효화가 일반적 패턴. useDDChecklist도 동일 패턴인지 먼저 확인하라
- ❌ "as 타입 단언이 위험하다" → 이 프로젝트에서는 API 응답에 대한 타입 단언이 일반적. 실제 런타임 타입 불일치가 발생하는 경우만 보고하라
- ❌ "Record<string, unknown>은 안전하지 않다" → response_documents의 경우 백엔드에서도 구조가 미정의이므로 FE에서 unknown이 적절할 수 있음. 양쪽 모두 확인 후 판단하라

## 출력 형식

각 발견사항마다:
1. **ID** — FE-{카테고리}-{번호} (예: FE-A11Y-01, FE-TYPE-02)
2. **파일:줄번호** — 정확한 위치
3. **실제 코드** — 3~10줄 붙여넣기
4. **문제** — 구체적 설명
5. **심각도** — 🔴 Critical / 🟠 Major / 🟡 Moderate / 🔵 Minor
6. **신뢰도** — HIGH (90%+) / MEDIUM (60-89%) / LOW (<60%)
7. **수정안** — 코드 제안
8. **검증** — ☐ Read로 확인 / ☐ 참조 패턴 비교 확인 / ☐ BE 스키마 비교 확인

발견사항은 심각도 순으로 정렬하라.
리포트를 `docs/code-review/` 폴더에 타임스탬프 파일명으로 저장해줘.
리포트 말미에 검증 투명성(거부된 가설 수/사유)을 기재하라.
```
