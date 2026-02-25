# RFI 모듈 프론트엔드 코드 리뷰 리포트

**리뷰 대상**: RFI 모듈 프론트엔드 (타입, 훅, 컴포넌트 4개) + 백엔드 정합성
**리뷰 일시**: 2026-02-25 21:36
**검증 방식**: 모든 파일을 Read/Grep 도구로 직접 읽은 후 비교

---

## 1. TypeScript 타입 ↔ Pydantic 스키마 정합성

### FE-TYPE-01: `RFIItemCreate.source_ref_id` 타입 불일치

- **파일:줄번호**: `amic-platform/src/modules/ma/types/rfi.ts:147` vs `deal-mgmt/app/schemas/rfi.py:86`
- **실제 코드 (FE)**: `source_ref_id?: string;`
- **실제 코드 (BE)**: `source_ref_id: uuid.UUID | None = None`
- **문제**: FE에서 `string`, BE에서 `uuid.UUID`. JSON 직렬화 시 호환되지만, FE에서 UUID 형식 검증 없음.
- **심각도**: 🔵 Minor
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인 / ☑ BE 스키마 비교 확인

---

### FE-TYPE-02: `vdr_document_ids` BE 타입이 `list | None`으로 느슨 + DB 모델 `Mapped[dict]` 불일치

- **파일:줄번호**: `amic-platform/src/modules/ma/types/rfi.ts:107` vs `deal-mgmt/app/schemas/rfi.py:154` vs `deal-mgmt/app/models/rfi_item.py:60`
- **실제 코드**:
  - FE: `vdr_document_ids: string[] | null;`
  - BE 스키마: `vdr_document_ids: list | None = None`
  - DB 모델: `vdr_document_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)`
- **문제**: DB 모델 `Mapped[dict | None]`이지만 실제로는 list를 저장. BE 스키마에서 요소 타입 미지정.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: BE 스키마 `list[str] | None`, DB 모델 `Mapped[list | None]`
- **검증**: ☑ Read로 확인 / ☑ BE 스키마 비교 확인 / ☑ DB 모델 비교 확인

---

### FE-TYPE-03: `response_documents` DB 모델 타입 힌트 불일치

- **파일:줄번호**: `deal-mgmt/app/models/rfi_item.py:37` vs `deal-mgmt/app/schemas/rfi.py:143` vs `amic-platform/src/modules/ma/types/rfi.ts:96`
- **문제**: DB 모델 `Mapped[dict | None]`(단일 dict)이지만 스키마는 `list[dict]`(리스트). FE `Record<string, unknown>[]`은 BE와 호환.
- **심각도**: 🔵 Minor
- **신뢰도**: HIGH (90%+)
- **수정안**: DB 모델 타입 힌트를 `Mapped[list | None]`으로 변경.
- **검증**: ☑ Read로 확인 / ☑ BE 스키마 비교 확인

---

## 2. React Query 훅 품질 · 캐시 무효화

### FE-HOOK-01: `useExportRFI`에서 `URL.revokeObjectURL`이 다운로드 시작 전 즉시 호출

- **파일:줄번호**: `amic-platform/src/modules/ma/hooks/useRFI.ts:356-373`
- **실제 코드**:
```typescript
const url = URL.createObjectURL(data);
const a = document.createElement("a");
a.href = url;
a.download = `RFI_${rfiId}.xlsx`;
a.click();
URL.revokeObjectURL(url);
```
- **문제**: `a.click()` 후 즉시 `URL.revokeObjectURL(url)` 실행. Firefox/Safari에서 다운로드 실패 가능.
- **심각도**: 🟠 Major
- **신뢰도**: HIGH (90%+)
- **수정안**: `setTimeout(() => URL.revokeObjectURL(url), 5000);`
- **검증**: ☑ Read로 확인

---

### FE-HOOK-02: `useExportRFI`에서 서버 에러 시 Blob 파싱 실패 가능

- **파일:줄번호**: `amic-platform/src/modules/ma/hooks/useRFI.ts:359-362`
- **문제**: `responseType: "blob"` 지정 → 서버 에러 JSON도 Blob으로 파싱. 200 + Content-Type JSON인 경우 문제.
- **심각도**: 🔵 Minor
- **신뢰도**: MEDIUM (60-89%)
- **수정안**: 다운로드 전 `data.type` 확인.
- **검증**: ☑ Read로 확인

---

### FE-HOOK-03: `useRespondRFIItem`/`useReviewRFIItem`의 빈 문자열 rfiId 초기화

- **파일:줄번호**: `amic-platform/src/modules/ma/components/rfi/RFIPanel.tsx:53-54`
- **실제 코드**:
```typescript
const respondItem = useRespondRFIItem(txnId, selectedRFIId ?? "");
const reviewItem = useReviewRFIItem(txnId, selectedRFIId ?? "");
```
- **문제**: `selectedRFIId`가 `null`이면 빈 문자열이 rfiId로 전달. 실제 호출은 selectedRFIId 존재 시에만 발생하므로 런타임 문제 없으나 불필요한 mutation 인스턴스 생성.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: mutation을 RFIDetailView 내부로 이동.
- **검증**: ☑ Read로 확인

---

### FE-HOOK-04: 모든 mutation `onError`가 서버 에러 detail 미전달

- **파일:줄번호**: `amic-platform/src/modules/ma/hooks/useRFI.ts` (전체, 18개 mutation)
- **실제 코드**: `onError: () => toast.error("RFI 생성에 실패했습니다.")`
- **문제**: 서버의 구체적 에러 메시지 미전달. useDDChecklist.ts도 동일 패턴이지만, 사용자가 실패 원인 파악 불가.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**:
```typescript
onError: (err: unknown) => {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  toast.error(detail || "RFI 생성에 실패했습니다.");
},
```
- **검증**: ☑ Read로 확인 / ☑ 참조 패턴 비교 확인

---

## 3. 접근성 (WCAG 2.1)

### FE-A11Y-01: 필터 버튼 그룹에 `role="radiogroup"` + `aria-checked` 부재

- **파일:줄번호**: `RFIPanel.tsx:132-155`; `RFIDetailView.tsx:245-304`
- **문제**: 단일 선택 필터 UI인데 `role="radiogroup"` / `aria-checked` 없음. 4곳.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**:
```tsx
<div role="radiogroup" aria-label="RFI 상태 필터">
  <button role="radio" aria-checked={statusFilter === opt.value}>
```
- **검증**: ☑ Read로 확인

---

### FE-A11Y-02: `RFICreateModal` 폼 필드에 label-input 연결 누락

- **파일:줄번호**: `RFICreateModal.tsx:48-121`
- **문제**: `<label>`에 `htmlFor` 없고 `<input>`에 `id` 없음. 7개 필드 모두 해당.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: `htmlFor`/`id` 쌍 추가.
- **검증**: ☑ Read로 확인

---

### FE-A11Y-03: `RFIItemRow` 질문 버튼에 `aria-expanded` 미설정

- **파일:줄번호**: `RFIItemRow.tsx:84-89`
- **문제**: 펼침/접힘 토글 버튼인데 `aria-expanded` 없음.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: `aria-expanded={expanded}` 추가.
- **검증**: ☑ Read로 확인

---

### FE-A11Y-04: KpiCard가 색상만으로 의미 전달

- **파일:줄번호**: `RFIPanel.tsx:86-102`; `RFIDetailView.tsx:219-236`
- **문제**: `variant` 색상만으로 positive/negative 구분. label 텍스트가 보조적으로 의미 전달.
- **심각도**: 🔵 Minor
- **신뢰도**: MEDIUM (60-89%)
- **검증**: ☑ Read로 확인

---

### FE-A11Y-05: RFI 카드 클릭 시 키보드 접근성

- **파일:줄번호**: `RFIPanel.tsx:189-228`
- **문제**: `Card`에 `onClick`만 있고, `<div>` 기반이면 키보드 접근성(tabIndex, onKeyDown) 부재.
- **심각도**: 🟡 Moderate
- **신뢰도**: MEDIUM (60-89%)
- **검증**: ☑ Read로 확인 (Card 내부 구현 미확인)

---

## 4. 상태 관리 · 컴포넌트 설계

### FE-DESIGN-01: STATUS_LABELS, CATEGORY_LABELS 등 3개 컴포넌트에 중복 정의

- **파일:줄번호**: `RFIPanel.tsx:20-36`, `RFIDetailView.tsx:20-53`, `RFIItemRow.tsx:5-50`
- **문제**: `constants.ts`에 이미 `RFI_STATUS_OPTIONS` 등 정의됨. 3곳에서 별도 `Record<>` 객체 중복 생성.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: `constants.ts`에 공용 LABELS 맵 정의 후 import.
- **검증**: ☑ Read로 확인 / ☑ constants.ts 참조 확인

---

### FE-DESIGN-02: `RFICreateModal` 성공 시 폼 불완전 초기화

- **파일:줄번호**: `RFICreateModal.tsx:37-42`
- **실제 코드**: `setForm({ title: "", round_number: 1 });`
- **문제**: `description`, `recipient_name`, `recipient_email` 등 6개 필드 미초기화. 모달 재열기 시 이전 값 잔존.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: `INITIAL_FORM` 상수로 전체 필드 초기화.
- **검증**: ☑ Read로 확인

---

### FE-DESIGN-03: `RFIDetailView`가 340행 — 서브컴포넌트 분리 가능

- **파일:줄번호**: `RFIDetailView.tsx` (전체 340행)
- **문제**: 5개 영역(헤더, 마감일 연장, KPI, 필터 바, 아이템 그룹)이 단일 컴포넌트.
- **심각도**: 🔵 Minor
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

## 5. 에러 처리 · 로딩 상태 · 빈 상태

### FE-ERR-01: `RFIDetailView`에서 `isError` 상태 미처리

- **파일:줄번호**: `RFIDetailView.tsx:64,107-108`
- **실제 코드**: `const { data: rfi, isLoading } = useRFI(txnId, rfiId);`
- **문제**: `isError` 구조 분해 안 함. 네트워크 에러 시 "RFI를 찾을 수 없습니다" 표시.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: `isError` 분기 추가하여 에러 메시지 표시.
- **검증**: ☑ Read로 확인

---

### FE-ERR-02: `RFIPanel`에서 `isError` 상태 미처리

- **파일:줄번호**: `RFIPanel.tsx:43-44,174`
- **문제**: FE-ERR-01과 동일. `isError` 처리 없음.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### FE-ERR-03: `generateFromDD` 버튼 이중 클릭 방어

- **파일:줄번호**: `RFIPanel.tsx:158-166`
- **문제**: `loading` prop 전달 중이나 Button 컴포넌트가 자동 disabled 처리하는지 미확인.
- **심각도**: 🔵 Minor
- **신뢰도**: LOW (<60%)
- **검증**: ☑ Read로 확인 (Button 내부 미확인)

---

## 6. UX 패턴 · 기존 컴포넌트 일관성

### FE-UX-01: 필터 UI에서 수동 버튼 구현 — InlineSelect 미사용

- **파일:줄번호**: `RFIPanel.tsx:132-155`; `RFIDetailView.tsx:245-304`
- **문제**: 다른 MA 탭에서 InlineSelect 사용하나, RFI는 수동 버튼. 칩 스타일은 의도적 디자인 선택 가능.
- **심각도**: 🔵 Minor
- **신뢰도**: MEDIUM (60-89%)
- **수정안**: 칩 필터를 공용 컴포넌트로 추출.
- **검증**: ☑ Read로 확인

---

### FE-UX-02: Excel Import UI 미구현 (BE 엔드포인트 존재)

- **파일:줄번호**: BE `routers/rfi.py:295-307`, FE `types/rfi.ts:199-203` (타입 정의됨), `useRFI.ts` (import 훅 없음)
- **문제**: BE에 import 엔드포인트 존재, FE 타입에 `RFIExcelImportResult` 정의됨, 그러나 훅/UI 없음. 기능 누락.
- **심각도**: 🟡 Moderate
- **신뢰도**: HIGH (90%+)
- **수정안**: `useImportRFI` 훅 + UI 버튼 추가.
- **검증**: ☑ Read로 확인 / ☑ BE 라우터 확인

---

### FE-UX-03: PHASE_VISIBLE_TABS에서 RFI가 NEGOTIATION 이후 미포함

- **파일:줄번호**: `constants.ts:598-606`
- **문제**: RFI가 PREPARATION, MARKETING, BIDDING_DD에만 포함. NEGOTIATION에서도 보충 RFI 필요 가능.
- **심각도**: 🔵 Minor
- **신뢰도**: MEDIUM (60-89%)
- **검증**: ☑ Read로 확인

---

## 7. 성능 · 리렌더링

### FE-PERF-01: mutation 훅이 `selectedRFIId` 변경마다 재생성

- **파일:줄번호**: `RFIPanel.tsx:53-54`
- **문제**: 실질적 문제 미미 — mutation이 목록 화면에서 호출되지 않음.
- **심각도**: 🔵 Minor
- **신뢰도**: HIGH (90%+)
- **검증**: ☑ Read로 확인

---

### FE-PERF-02: `RFIItemRow`에 `React.memo` 미적용

- **파일:줄번호**: `RFIItemRow.tsx:58`
- **문제**: 부모 리렌더링 시 모든 Row 리렌더링. `onRespond`/`onReview` 콜백도 매번 새로 생성.
- **심각도**: 🔵 Minor
- **신뢰도**: HIGH (90%+)
- **수정안**: `React.memo` + 부모에서 `useCallback` 적용.
- **검증**: ☑ Read로 확인

---

## 요약 표

| ID | 심각도 | 신뢰도 | 파일 | 문제 요약 |
|---|---|---|---|---|
| FE-HOOK-01 | 🟠 Major | HIGH | useRFI.ts:356 | revokeObjectURL 즉시 호출 → 다운로드 실패 가능 |
| FE-TYPE-02 | 🟡 Moderate | HIGH | rfi.ts:107 | vdr_document_ids BE 타입 느슨 + DB 모델 불일치 |
| FE-HOOK-03 | 🟡 Moderate | HIGH | RFIPanel.tsx:53 | 빈 문자열 rfiId로 mutation 생성 |
| FE-HOOK-04 | 🟡 Moderate | HIGH | useRFI.ts 전체 | 18개 mutation 서버 에러 detail 미전달 |
| FE-A11Y-01 | 🟡 Moderate | HIGH | RFIPanel/DetailView | 필터 버튼에 radiogroup/aria-checked 부재 |
| FE-A11Y-02 | 🟡 Moderate | HIGH | RFICreateModal.tsx | label-input 연결 누락 (7개 필드) |
| FE-A11Y-03 | 🟡 Moderate | HIGH | RFIItemRow.tsx:84 | aria-expanded 미설정 |
| FE-A11Y-05 | 🟡 Moderate | MEDIUM | RFIPanel.tsx:189 | Card 키보드 접근성 |
| FE-DESIGN-01 | 🟡 Moderate | HIGH | 3개 컴포넌트 | LABELS 상수 중복 정의 |
| FE-DESIGN-02 | 🟡 Moderate | HIGH | RFICreateModal.tsx:37 | 폼 불완전 초기화 |
| FE-ERR-01 | 🟡 Moderate | HIGH | RFIDetailView.tsx:64 | isError 미처리 |
| FE-ERR-02 | 🟡 Moderate | HIGH | RFIPanel.tsx:43 | isError 미처리 |
| FE-UX-02 | 🟡 Moderate | HIGH | useRFI.ts | Excel Import 훅/UI 미구현 |
| FE-TYPE-01 | 🔵 Minor | HIGH | rfi.ts:147 | source_ref_id UUID 형식 미검증 |
| FE-TYPE-03 | 🔵 Minor | HIGH | rfi_item.py:37 | DB 모델 Mapped[dict] → Mapped[list] |
| FE-HOOK-02 | 🔵 Minor | MEDIUM | useRFI.ts:359 | Blob export 서버 에러 시 파싱 문제 |
| FE-A11Y-04 | 🔵 Minor | MEDIUM | RFIPanel/DetailView | KpiCard 색상만으로 의미 전달 |
| FE-ERR-03 | 🔵 Minor | LOW | RFIPanel.tsx:158 | generateFromDD 이중 클릭 |
| FE-UX-01 | 🔵 Minor | MEDIUM | RFIPanel/DetailView | 수동 필터 버튼 vs InlineSelect |
| FE-UX-03 | 🔵 Minor | MEDIUM | constants.ts:598 | RFI NEGOTIATION 이후 미포함 |
| FE-DESIGN-03 | 🔵 Minor | HIGH | RFIDetailView.tsx | 340행 서브컴포넌트 분리 가능 |
| FE-PERF-01 | 🔵 Minor | HIGH | RFIPanel.tsx:53 | mutation selectedRFIId 변경마다 재생성 |
| FE-PERF-02 | 🔵 Minor | HIGH | RFIItemRow.tsx:58 | React.memo 미적용 |

---

## 통계

- **총 발견사항**: 23개 (정보 제공 1건 제외)
- 🟠 Major: 1개
- 🟡 Moderate: 12개
- 🔵 Minor: 10개

---

## 검증 투명성

### 거부된 가설: 5건

1. **"invalidateQueries가 rfiKeys(txnId) 전체를 무효화하므로 과도하다"** — 거부. useDDChecklist.ts도 동일 패턴. 프로젝트 전체의 일관된 패턴.

2. **"data as RFI 타입 단언이 위험하다"** — 거부. useDDChecklist.ts에서도 동일 패턴. 런타임 타입 불일치 사례 미확인.

3. **"Record<string, unknown>[]이 안전하지 않다"** — 거부. BE에서도 구조 미정의이므로 FE에서 unknown 적절.

4. **"useRFIs의 queryKey 객체 포함이 stale data 위험"** — 거부. React Query 깊은 비교로 처리. 다른 필터 조합은 의도적 별도 캐시.

5. **"categories useMemo Set 변환 비효율적"** — 거부. 수십~수백 건 수준에서 비용 무시 가능. useMemo 사용 적절.

---

## 우선 수정 권장 순서

1. **즉시 (Major)**: FE-HOOK-01 (revokeObjectURL 타이밍)
2. **단기 (Moderate 상위)**: FE-HOOK-04 (에러 detail 전달), FE-ERR-01/02 (isError 처리), FE-DESIGN-02 (폼 초기화), FE-UX-02 (Import UI)
3. **중기 (Moderate 접근성)**: FE-A11Y-01/02/03 (ARIA 속성), FE-DESIGN-01 (LABELS 중복)
4. **장기 (Minor)**: FE-PERF-02, FE-DESIGN-03, FE-UX-01
