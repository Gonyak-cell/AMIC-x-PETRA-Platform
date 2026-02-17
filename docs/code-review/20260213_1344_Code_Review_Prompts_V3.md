# AMIC x PETRA Platform — 코드 리뷰 프롬프트 V3 (세부 영역별)

> 생성일: 2026-02-13 13:44
> 용도: 할루시네이션을 최소화한 세부 영역별 코드 리뷰 프롬프트 40개
> 이전 버전: V1 (`20260213_0906`, 5세션), V2 (`20260213_1231`, 8세션)
> 핵심 개선: 프롬프트당 **최대 10~15개 파일** → LLM이 모든 파일을 실제로 읽을 수 있는 범위
> 참조: `docs/20260213_1253_Verified_Code_Review.md` (검증된 이슈 및 허위 발견 목록)

---

## 사용법

1. 각 프롬프트를 **코드 블록 안의 텍스트**를 복사하여 새 세션에 붙여넣기
2. **실행 우선순위**: Phase 1(Critical) → Phase 2(Module) → Phase 3(Infra) → Phase 4(Foundation)
3. 리뷰 완료 후 `/verify-review` 스킬로 결과 검증
4. 한 세션에서 **하나의 프롬프트만** 실행 (컨텍스트 오염 방지)

---

## 실행 우선순위

### Phase 1: Critical Path (10개)

A1, A2, B2, B5, D1, E1, E2, E4, F1, F5

### Phase 2: Module Completion (15개)

B1, B3, B4, B6, B7, B8, C1, C2, C3, C4, C5, C6, D2, D3, F2

### Phase 3: Infrastructure & Quality (10개)

G1, G2, G3, G4, H1, H2, H3, I1, I2, F3

### Phase 4: Foundations (5개)

A3, A4, A5, A6, A7, F4

---

# 카테고리 A: 프론트엔드 공통 인프라 (7개)

---

## A1. API Client & 네트워크 레이어

```
아래 파일들의 API 클라이언트 및 네트워크 레이어를 코드 리뷰해줘.
프롬프트당 최대 15개 파일만 다루므로, 모든 파일을 반드시 Read 도구로 읽은 후 리뷰해.

## 리뷰 대상 파일

1. amic-platform/src/api/client.ts
2. amic-platform/src/api/fddClient.ts
3. amic-platform/src/api/kiisClient.ts
4. amic-platform/src/api/imClient.ts
5. amic-platform/src/lib/token-storage.ts
6. amic-platform/src/lib/auth-events.ts
7. amic-platform/vite.config.ts (프록시 설정 섹션)

## 점검 항목

1. **토큰 리프레시 로직**: client.ts의 401 인터셉터에서 리프레시 실패 시 무한 루프 가능성
2. **FDD 하드코딩**: client.ts:49-52에 토큰 리프레시가 FDD 엔드포인트에 하드코딩 (기존 이슈 Platform M1)
3. **순환 의존**: client.ts ↔ useAuth.ts 간 순환 참조 여부 (token-storage.ts로 해소했는지)
4. **프록시 경로**: vite.config.ts의 `/api/fdd` → `:8000/api/v1` 매핑이 각 모듈 클라이언트 baseURL과 일치하는지
5. **에러 처리**: 401, 403, 404, 500 각각에 대한 인터셉터 동작
6. **요청 취소**: AbortController 또는 React Query signal 사용 여부
7. **auth-events.ts**: 크로스탭 로그아웃 이벤트 처리 (BroadcastChannel or storage event)

## 안티할루시네이션 규칙

🚫 파일을 읽지 않고 코드 패턴을 추정하지 마라
🚫 "일반적으로 axios 인터셉터는..." 같은 표현을 근거로 사용하지 마라
✅ 언급하는 모든 파일을 Read 도구로 반드시 읽어라
✅ 정확한 줄 번호를 인용하라 (예: client.ts:42-48)
✅ 3~10줄의 실제 코드를 붙여넣어라

## 기존 허위 발견 경고

- ❌ "순환 의존이 존재한다" → token-storage.ts로 이미 해소되었을 수 있음. 실제 import 경로를 확인하라
- ❌ Platform C1 "로그아웃 시 캐시 미삭제" → useAuth.ts에서 queryClient.clear()가 호출됨을 확인하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** — 정확한 위치
2. **실제 코드** — 3~10줄 붙여넣기
3. **문제** — 구체적 설명
4. **심각도** — 🔴 Critical / 🟠 Major / 🟡 Moderate / 🔵 Minor
5. **수정안** — 코드 제안
6. **검증** — ☐ Read로 확인 / ☐ 크로스 레퍼런스 확인
```

---

## A2. 인증 플로우

```
아래 파일들의 인증(Authentication) 플로우를 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/hooks/useAuth.ts
2. amic-platform/src/components/auth/AuthProvider.tsx
3. amic-platform/src/components/auth/ProtectedRoute.tsx
4. amic-platform/src/components/auth/AuthContext.ts
5. amic-platform/src/types/auth.ts
6. amic-platform/src/lib/storage.ts

## 점검 항목

1. **logout 캐시 정리**: logout 함수에서 `queryClient.clear()` 호출 여부 — 반드시 Read로 확인
2. **AuthProvider 초기화**: 마운트 시 토큰 검증 타이밍, 로딩 상태 관리
3. **토큰 만료**: 만료된 토큰 감지 및 자동 리프레시 / 리다이렉트 로직
4. **ProtectedRoute**: 인증되지 않은 상태에서의 리다이렉트, returnUrl 보존
5. **Race condition**: 동시 API 호출 시 토큰 리프레시 중복 요청 방지
6. **AuthContext 타입**: User, AuthState 타입 정의 완전성
7. **storage.ts**: localStorage 접근 시 예외 처리 (private browsing, quota exceeded)

## 안티할루시네이션 규칙

🚫 파일을 읽지 않고 코드 패턴을 추정하지 마라
🚫 "보통 AuthProvider는..." 같은 일반론을 근거로 사용하지 마라
✅ 모든 파일을 Read 도구로 읽어라
✅ 정확한 줄 번호와 실제 코드를 인용하라

## 기존 허위 발견 경고

- ❌ Platform C1 "로그아웃 시 queryClient.clear() 미호출" → 이전 리뷰의 허위 발견. useAuth.ts를 직접 읽어서 확인하라
- ❌ "storage.ts가 단순 wrapper" → 실제 에러 핸들링이 있는지 확인하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** (3~10줄) 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## A3. UI 컴포넌트 — 기초 (Batch 1)

```
아래 UI 기초 컴포넌트들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/components/ui/Button.tsx
2. amic-platform/src/components/ui/Input.tsx
3. amic-platform/src/components/ui/Select.tsx
4. amic-platform/src/components/ui/Badge.tsx
5. amic-platform/src/components/ui/Card.tsx
6. amic-platform/src/components/ui/Modal.tsx
7. amic-platform/src/lib/cn.ts
8. amic-platform/src/components/ui/index.ts

## 점검 항목

1. **cn() 유틸리티**: twMerge + clsx 사용 여부 확인 (이전 리뷰에서 "단순 join"으로 오인)
2. **Badge variants**: `success | warning | error | info | neutral` 정확한 variant 확인
3. **Card**: onClick prop 존재 여부 (API 문서상 없음 — 래핑 필요)
4. **Modal**: focus trap 구현, ESC 키 닫기, aria-modal 설정
5. **Button**: disabled 상태에서 이벤트 전파, loading 상태 처리
6. **Input**: ref forwarding, 에러 상태 표시
7. **Select**: 접근성 (aria-label, keyboard navigation)
8. **Barrel export**: index.ts의 export 누락 여부

## 안티할루시네이션 규칙

🚫 cn.ts를 읽지 않고 "단순 join"이라고 주장하지 마라 — 반드시 Read로 확인
🚫 "일반적으로 Modal은 focus trap이 필요하다"만으로 이슈를 만들지 마라 — 실제 구현 확인
✅ 모든 파일을 Read 도구로 읽어라
✅ Props 타입 정의를 직접 확인하고 인용하라

## 기존 허위 발견 경고

- ❌ Platform C2 "cn() 단순 filter(Boolean).join" → 실제로는 twMerge + clsx 사용. cn.ts를 읽어서 확인하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## A4. UI 컴포넌트 — 데이터 표시 (Batch 2)

```
아래 데이터 표시용 UI 컴포넌트들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/components/ui/DataTable.tsx
2. amic-platform/src/components/ui/KpiCard.tsx
3. amic-platform/src/components/ui/EmptyState.tsx
4. amic-platform/src/components/ui/Pagination.tsx
5. amic-platform/src/components/ui/Skeleton.tsx
6. amic-platform/src/components/ui/Spinner.tsx
7. amic-platform/src/components/ui/LiveRegion.tsx

## 점검 항목

1. **DataTable**:
   - `keyField` prop이 REQUIRED인지 확인
   - `Column.key`가 `string` 타입인지 (NOT `keyof T`)
   - `onSelectAll` prop 존재 여부 (문서상 없음)
   - 대량 데이터(1000+행) 시 가상화 여부
   - 정렬/필터 상태 관리
2. **KpiCard**:
   - variants: `default | positive | negative | caution` (Badge와 다름!)
   - 숫자 포맷팅
3. **Pagination**: 사용처 일관성 (FDD: 없음, KIIS: 6곳, IM: 직접구현)
4. **Skeleton/Spinner**: 로딩 상태 접근성 (aria-busy, role="status")
5. **LiveRegion**: 스크린 리더 공지 (aria-live="polite" vs "assertive")

## 안티할루시네이션 규칙

🚫 DataTable Props를 추측하지 마라 — 실제 타입 정의를 읽어라
🚫 KpiCard variants를 Badge variants와 혼동하지 마라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## A5. 레이아웃 & 네비게이션

```
아래 레이아웃 및 네비게이션 관련 파일들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/components/layout/AppShell.tsx
2. amic-platform/src/components/layout/Sidebar.tsx
3. amic-platform/src/components/layout/PageHeader.tsx
4. amic-platform/src/components/layout/HealthIndicator.tsx
5. amic-platform/src/components/layout/ModuleSwitcher.tsx
6. amic-platform/src/main.tsx
7. amic-platform/src/App.tsx

## 점검 항목

1. **AppShell**: Sidebar 토글 상태, 모바일 반응형 breakpoint
2. **Sidebar**: 현재 경로 하이라이트, 모듈별 메뉴 그룹핑
3. **HealthIndicator**: 폴링 간격, 컴포넌트 언마운트 후 setState 방지 (cleanup)
4. **ModuleSwitcher**: 모듈 전환 시 React Query 캐시 동작
5. **main.tsx**: React.StrictMode, QueryClientProvider 설정, 에러 바운더리
6. **App.tsx**: React.lazy 동적 import, Suspense fallback, 라우트 구조

## 안티할루시네이션 규칙

🚫 "HealthIndicator에 cleanup이 없다"고 가정하지 마라 — useEffect return문을 확인하라
🚫 React.lazy import 패턴을 추측하지 마라 — 실제 코드를 읽어라
✅ 모든 파일을 Read 도구로 읽어라
✅ useEffect의 cleanup 함수를 정확히 인용하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## A6. 글로벌 검색 & 커맨드 팔레트

```
아래 글로벌 검색 관련 파일들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/hooks/useGlobalSearch.ts
2. amic-platform/src/components/search/CommandPalette.tsx
3. amic-platform/src/types/search.ts

참고: SearchResults 컴포넌트는 별도 파일 없이 CommandPalette.tsx 내부에 구현되어 있을 수 있음.

## 점검 항목

1. **IM 폴백**: IM 검색이 전체 문서를 로드하는 비효율 (기존 이슈 Platform M2)
2. **디바운스**: 검색 입력 디바운싱 구현 (setTimeout vs useDeferredValue)
3. **Ctrl+K 단축키**: focus trap, 열림/닫힘 상태 관리, ESC 키 처리
4. **모듈별 라우팅**: 검색 결과 클릭 시 올바른 모듈 경로로 네비게이션
5. **빈 상태/로딩 상태**: 검색 중 스피너, 결과 없음 UI
6. **접근성**: aria-role="dialog", aria-label, keyboard navigation

## 안티할루시네이션 규칙

🚫 파일을 읽지 않고 "디바운스가 없다"고 주장하지 마라
✅ 모든 파일을 Read 도구로 읽어라
✅ useGlobalSearch.ts의 실제 검색 로직을 인용하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## A7. 유틸리티 & 테스트 인프라

```
아래 유틸리티 함수와 테스트 인프라 파일들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/lib/format.ts
2. amic-platform/src/lib/statusVariant.ts
3. amic-platform/src/lib/sentry.ts
4. amic-platform/src/lib/ics.ts
5. amic-platform/src/test/setup.ts
6. amic-platform/src/test/test-utils.tsx
7. amic-platform/src/test/mocks/handlers.ts
8. amic-platform/src/test/mocks/data.ts

## 점검 항목

1. **format.ts**: 통화 포맷(KRW, USD), 날짜 포맷, 숫자 축약, `ZERO_DECIMAL_CURRENCIES` Set
2. **statusVariant.ts**: 상태→Badge variant 매핑 정확성
3. **sentry.ts**: 프로덕션만 활성화, dsn 설정, 에러 필터링
4. **ics.ts**: iCalendar 표준 준수, 타임존 처리
5. **setup.ts**: jsdom 환경, `HTMLDialogElement.showModal()` 폴리필, MSW lifecycle
6. **test-utils.tsx**: `renderWithProviders()` — QueryClient 설정, MemoryRouter, AuthContext mock
7. **handlers.ts**: MSW 핸들러 — 페이로드 검증 여부 (FDD #8.4), 응답 타입 일치
8. **data.ts**: Mock 데이터 — 실제 API 응답 스키마와 일치하는지

## 안티할루시네이션 규칙

🚫 format.ts의 구현을 추측하지 마라 — 실제 함수 시그니처와 로직을 읽어라
🚫 MSW 핸들러가 "잘못되었다"고 주장하기 전에 실제 API 경로와 대조하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 B: FDD 모듈 프론트엔드 (8개)

---

## B1. FDD 훅 — Deal 관리

```
FDD 모듈의 Deal 관리 관련 훅들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/hooks/useDeals.ts
2. amic-platform/src/modules/fdd/hooks/useUploads.ts
3. amic-platform/src/modules/fdd/hooks/useDefinitions.ts
4. amic-platform/src/modules/fdd/hooks/__tests__/useDeals.test.tsx

## 점검 항목

1. **쿼리키 프리픽스**: 모든 쿼리키가 `["fdd", ...]`로 시작하는지 (Session 3 수정사항)
2. **useDeals**: CRUD 뮤테이션 onSuccess에서 올바른 쿼리 무효화
3. **useUploads**: 파일 업로드 progress 콜백, 대용량 파일 에러 처리
4. **useDefinitions**: staleTime 설정, 정의 데이터 캐싱 전략
5. **테스트 품질**: useDeals.test.tsx — 성공/실패 케이스, waitFor 사용, MSW 핸들러 매칭

## 크로스 레퍼런스

- BE: `Auto FDD/backend/app/api/deals.py` — 엔드포인트 경로와 FE 호출 경로 일치 여부
- BE: `Auto FDD/backend/app/schemas/deal.py` — 응답 스키마와 FE 타입 일치 여부

## 안티할루시네이션 규칙

🚫 "쿼리키에 fdd 프리픽스가 없다"고 주장하기 전에 실제 코드를 확인하라 (Session 3에서 수정됨)
✅ 모든 파일을 Read 도구로 읽어라
✅ 쿼리키 배열을 정확히 인용하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## B2. FDD 훅 — 계산 엔진 (QoE/NWC/Debt)

```
FDD 모듈의 계산 엔진 관련 훅과 타입을 코드 리뷰해줘.
FE 타입과 BE 스키마 간 불일치를 특히 주의 깊게 점검해.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/hooks/useQoE.ts
2. amic-platform/src/modules/fdd/hooks/useNWC.ts
3. amic-platform/src/modules/fdd/hooks/useDebt.ts
4. amic-platform/src/modules/fdd/types/qoe.ts
5. amic-platform/src/modules/fdd/types/nwc.ts
6. amic-platform/src/modules/fdd/types/debt.ts

## 점검 항목

1. **쿼리키 프리픽스**: `["fdd", "qoe"]`, `["fdd", "nwc"]`, `["fdd", "debt"]` 형태 확인
2. **category_breakdown 타이핑**: `Record<string, unknown>` 느슨한 타입 (기존 이슈 F3)
3. **뮤테이션 캐시 무효화**: 계산 결과 저장 후 관련 쿼리 무효화
4. **에러 처리**: 계산 API 실패 시 사용자 피드백
5. **빈 ID 처리**: dealId가 빈 문자열일 때 쿼리 실행 방지 (enabled 조건)

## 크로스 레퍼런스 (BE 스키마 대조)

아래 BE 파일도 함께 읽어서 FE 타입과 대조하라:
- `Auto FDD/backend/app/schemas/qoe.py` ↔ `qoe.ts`
- `Auto FDD/backend/app/schemas/nwc.py` ↔ `nwc.ts`
- `Auto FDD/backend/app/schemas/debt.py` ↔ `debt.ts`

필드명, 타입, optional/required 차이를 보고하라.

## 안티할루시네이션 규칙

🚫 BE 스키마를 추측하지 마라 — 반드시 양쪽 파일을 모두 읽어서 대조하라
🚫 "타입이 일치하지 않을 것 같다"는 추측 금지
✅ 모든 FE 타입 파일과 BE 스키마 파일을 Read 도구로 읽어라
✅ 불일치 발견 시 양쪽 코드를 모두 인용하라

## 출력 형식

각 발견사항마다:
1. **FE 파일:줄번호** + **BE 파일:줄번호** 2. **양쪽 코드** 3. **불일치 내용** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## B3. FDD 훅 — 보조 기능

```
FDD 모듈의 보조 기능 훅들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/hooks/useMapping.ts
2. amic-platform/src/modules/fdd/hooks/useIssues.ts
3. amic-platform/src/modules/fdd/hooks/useReportVersions.ts
4. amic-platform/src/modules/fdd/hooks/useVdr.ts

## 점검 항목

1. **useMapping**: tie-out 무효화 수정 확인 (Session 3), staleTime 1시간 for 표준 항목
2. **useIssues**: 쿼리키 `["fdd", "issues"]`, resolved_by 폴백 값
3. **useReportVersions**: 버전 목록 정렬, 다운로드 URL 생성
4. **useVdr**: 폴더 트리 재귀 데이터 구조, 깊이 제한, expand/collapse 상태

## 안티할루시네이션 규칙

🚫 Session 3 수정사항을 무시하지 마라 — useMapping의 tie-out 무효화가 수정되었을 수 있음
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## B4. FDD 페이지 — Deal Setup

```
FDD 모듈의 Deal 설정 관련 페이지와 컴포넌트를 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/pages/DealListPage.tsx
2. amic-platform/src/modules/fdd/pages/DealSetupWizardPage.tsx
3. amic-platform/src/modules/fdd/components/deal/DealSetupWizard.tsx
4. amic-platform/src/modules/fdd/components/deal/ScopeSelector.tsx
5. amic-platform/src/modules/fdd/pages/__tests__/DealListPage.test.tsx

## 점검 항목

1. **DealListPage**: 인더스트리 컬럼 표시, 필터링/정렬, DataTable 사용 패턴
2. **DealSetupWizard**: 멀티스텝 위자드 — 단계 간 상태 보존, 뒤로 가기 시 데이터 유지
3. **인더스트리 셀렉트**: FDD_INDUSTRY_OPTIONS 6개 옵션 사용, 기본값 처리
4. **ScopeSelector**: 분석 범위 선택 UI, validation
5. **로딩/에러/빈 상태**: 각 상태별 적절한 UI 표시
6. **테스트**: DealListPage.test.tsx — 커버리지, MSW 핸들러 매칭

## 안티할루시네이션 규칙

🚫 DealSetupWizard의 단계 수를 추측하지 마라 — 실제 코드를 읽어라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## B5. FDD 페이지 — QoE/NWC/Debt 계산

```
FDD 모듈의 계산 결과 페이지들을 코드 리뷰해줘. 계산 정확성이 핵심이므로 특히 주의 깊게 리뷰해.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/pages/QoEPage.tsx
2. amic-platform/src/modules/fdd/pages/NWCPage.tsx
3. amic-platform/src/modules/fdd/pages/NetDebtPage.tsx

## 점검 항목

1. **approved_by 폴백**: `approved_by: "unknown"` 하드코딩 대신 현재 사용자 정보 사용 여부
2. **빈 ID early return**: dealId가 없을 때 뮤테이션 훅에 빈 문자열 전달 (기존 이슈 F2)
3. **에러 메시지**: 한국어/영어 혼용 여부
4. **NWC classOrder**: 표시 순서 상수 정의 (Session 3 추가)
5. **숫자 포맷팅**: formatCurrency, formatNumber 사용 일관성
6. **로딩 상태**: 계산 진행 중 스피너/프로그레스 표시

## 안티할루시네이션 규칙

🚫 "approved_by가 누락되었다"고 주장하기 전에 실제 mutation payload를 확인하라
🚫 Session 3에서 수정된 사항을 무시하지 마라
✅ 각 페이지를 Read 도구로 읽어라
✅ 뮤테이션 호출부의 실제 코드를 인용하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## B6. FDD 페이지 — 보조 페이지

```
FDD 모듈의 보조 기능 페이지들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/pages/DefinitionPage.tsx
2. amic-platform/src/modules/fdd/pages/MappingPage.tsx
3. amic-platform/src/modules/fdd/pages/UploadPage.tsx
4. amic-platform/src/modules/fdd/pages/IssuesPage.tsx

## 점검 항목

1. **DefinitionPage**: approved_by 수정 확인 (Session 3)
2. **MappingPage**: 2곳의 approved_by 수정 확인, tie-out 표시
3. **UploadPage**: 파일 업로드 — 드래그앤드롭, 파일 크기 제한, 진행률 표시
4. **IssuesPage**: 필터 객체 매 렌더마다 재생성 (기존 이슈 FDD #5.1) — useMemo 적용 여부
5. **공통**: 로딩/에러/빈 상태 처리, Breadcrumbs 사용

## 안티할루시네이션 규칙

🚫 Session 3 수정사항(approved_by)이 반영되었는지 반드시 직접 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## B7. FDD 페이지 — Report & VDR

```
FDD 모듈의 리포트 및 VDR(Virtual Data Room) 관련 파일들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/pages/ReportPage.tsx
2. amic-platform/src/modules/fdd/pages/VdrPage.tsx
3. amic-platform/src/modules/fdd/components/report/ReportVersionCard.tsx
4. amic-platform/src/modules/fdd/components/report/ReportVersionList.tsx
5. amic-platform/src/modules/fdd/components/vdr/VdrFolderTree.tsx
6. amic-platform/src/modules/fdd/components/vdr/VdrFolderItem.tsx

## 점검 항목

1. **ReportVersionCard**: API 경로 수정 확인 (Session 2 M-1), DOCX 형식 지원 (Session 2 M-5)
2. **ReportVersionList**: 버전 목록 정렬 (최신순), 다운로드 트리거
3. **VdrFolderTree**: 재귀 컴포넌트 성능, React key 할당, 깊이 제한
4. **VdrFolderItem**: 파일/폴더 아이콘, 클릭 동작 (폴더 확장 vs 파일 다운로드)
5. **ReportPage**: 리포트 생성/다운로드 플로우

## 안티할루시네이션 규칙

🚫 Session 2 수정사항(API 경로, DOCX 형식)이 반영되었는지 직접 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## B8. FDD 타입 & 크로스모듈 통합

```
FDD 모듈의 타입 정의와 크로스모듈 통합 지점을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/types/industry.ts
2. amic-platform/src/modules/fdd/types/deal.ts
3. amic-platform/src/modules/fdd/types/report-version.ts
4. amic-platform/src/modules/fdd/constants.ts
5. amic-platform/src/modules/fdd/FddRoutes.tsx

## 점검 항목

1. **industry.ts**: IndustryId 타입 (9값: general, healthcare, tech_saas, manufacturing, logistics, financial_services, ...), FDD_INDUSTRY_OPTIONS 배열
2. **deal.ts**: Deal 인터페이스의 industry 필드 — IndustryId 타입 사용 여부
3. **report-version.ts**: 타입 정의 완전성, BE 스키마와의 일치
4. **constants.ts**: 하드코딩된 상수값, 매직 넘버
5. **FddRoutes.tsx**: React.lazy 사용 여부, 라우트 구조

## 크로스 레퍼런스

- IM 모듈의 `document.ts`에서 IndustryId를 re-export하는지 확인
- BE `Auto FDD/backend/app/industry/models.py`의 IndustryType과 FE IndustryId 값 일치 확인

## 안티할루시네이션 규칙

🚫 IndustryId 값을 추측하지 마라 — industry.ts를 직접 읽어라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 C: KIIS 모듈 프론트엔드 (6개)

---

## C1. KIIS 훅 — 코어 데이터

```
KIIS 모듈의 코어 데이터 훅들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/kiis/hooks/useCompanies.ts
2. amic-platform/src/modules/kiis/hooks/useDashboard.ts
3. amic-platform/src/modules/kiis/hooks/useSearch.ts
4. amic-platform/src/modules/kiis/hooks/__tests__/useSearch.test.tsx
5. amic-platform/src/modules/kiis/types/company.ts

## 점검 항목

1. **corpCode URL 삽입**: useCompanies에서 corpCode가 URL 경로에 직접 삽입되는지, 포맷 검증(`/^\d{8}$/`) 여부 (기존 이슈 K2)
2. **검색 디바운스**: useSearch에서 입력 디바운싱 구현
3. **쿼리키**: `["kiis", "companies"]`, `["kiis", "dashboard"]` 등 일관성
4. **테스트 품질**: useSearch.test.tsx — 디바운스 테스트, 에러 케이스
5. **company.ts 타입**: BE 스키마와의 일치

## 크로스 레퍼런스

- BE: `KIIS/app/routers/company.py` — 엔드포인트 경로
- BE: `KIIS/app/schemas/company.py` — 응답 스키마

## 안티할루시네이션 규칙

🚫 corpCode 검증이 "없다"고 주장하기 전에 실제 코드를 읽어라
🚫 "KIIS 검색이 느리다"는 주관적 판단 금지 — 구체적 코드 문제만 지적하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## C2. KIIS 훅 — 금융 데이터

```
KIIS 모듈의 금융 데이터 관련 훅들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/kiis/hooks/useFunds.ts
2. amic-platform/src/modules/kiis/hooks/useReits.ts
3. amic-platform/src/modules/kiis/hooks/useManagers.ts
4. amic-platform/src/modules/kiis/hooks/usePortfolio.ts
5. amic-platform/src/modules/kiis/hooks/useDeals.ts

## 점검 항목

1. **쿼리키 충돌**: useFundManagers vs useManagers 쿼리키 충돌 가능성 (Session 3 #1)
2. **usePortfolio corpCode 검증**: corpCode URL 삽입 시 포맷 검증 (K2 연장)
3. **useReits**: REIT 목록/상세 쿼리, 페이지네이션
4. **useDeals**: deal sourcing 쿼리, 필터 파라미터
5. **공통 패턴**: enabled 조건, staleTime, 에러 처리 일관성

## 안티할루시네이션 규칙

🚫 쿼리키 충돌을 가정하지 마라 — 실제 키 배열을 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## C3. KIIS 훅 — 뉴스 & 워치리스트

```
KIIS 모듈의 뉴스, 워치리스트, 제재, 공시 관련 훅들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/kiis/hooks/useNews.ts
2. amic-platform/src/modules/kiis/hooks/useWatchlist.ts
3. amic-platform/src/modules/kiis/hooks/useSanctions.ts
4. amic-platform/src/modules/kiis/hooks/useDisclosures.ts
5. amic-platform/src/modules/kiis/hooks/__tests__/useWatchlist.test.tsx

## 점검 항목

1. **useWatchlist**: invalidateQueries 범위 (기존 이슈 K12) — 추가/삭제 후 워치리스트 + 관련 쿼리 무효화
2. **useNews**: 뉴스 크롤 트리거, 센티먼트 분석 결과 포함 여부
3. **useSanctions**: 제재 검색, 필터링, 페이지네이션
4. **useDisclosures**: corpCode URL 삽입 검증 (K2 계열)
5. **테스트 품질**: useWatchlist.test.tsx — 추가/삭제 뮤테이션, 캐시 무효화 검증

## 안티할루시네이션 규칙

🚫 "invalidateQueries 범위가 잘못되었다"고 주장하기 전에 실제 onSuccess 콜백을 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## C4. KIIS 페이지 — 대시보드 & 기업 상세

```
KIIS 모듈의 대시보드와 기업 상세 페이지를 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/kiis/pages/DashboardPage.tsx
2. amic-platform/src/modules/kiis/pages/CompanyDetailPage.tsx
3. amic-platform/src/modules/kiis/components/CompanyFinancials.tsx
4. amic-platform/src/modules/kiis/components/SentimentIndicator.tsx
5. amic-platform/src/modules/kiis/types/dashboard.ts

## 점검 항목

1. **DashboardPage React key**: 동적 리스트에서 React key 생성 방식 (기존 이슈 K6)
2. **CompanyDetailPage 5-쿼리 워터폴**: 5개 독립 쿼리가 순차적으로 실행되는지 병렬인지 (기존 이슈 KIIS #3.6)
3. **corpCode non-null**: URL 파라미터에서 받는 corpCode가 null일 때 처리
4. **CompanyFinancials**: 재무 데이터 테이블 렌더링, 숫자 포맷팅
5. **SentimentIndicator**: 센티먼트 점수→시각적 표시 매핑, 접근성

## 안티할루시네이션 규칙

🚫 "5개 쿼리가 워터폴이다"고 추측하지 마라 — React Query는 기본적으로 병렬 실행. enabled 체이닝 여부를 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## C5. KIIS 페이지 — 리스트 페이지들

```
KIIS 모듈의 리스트 페이지들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/kiis/pages/CompanyListPage.tsx
2. amic-platform/src/modules/kiis/pages/NewsListPage.tsx
3. amic-platform/src/modules/kiis/pages/WatchlistPage.tsx
4. amic-platform/src/modules/kiis/pages/FundListPage.tsx
5. amic-platform/src/modules/kiis/pages/ReitListPage.tsx

## 점검 항목

1. **NewsListPage aria-label**: 100자 이상 과잉 aria-label (기존 이슈 K8)
2. **NewsListPage 크롤 메시지**: 크롤 트리거 후 사용자 피드백 (K10)
3. **Pagination 일관성**: 5개 페이지 모두 동일한 Pagination 컴포넌트 사용하는지
4. **DataTable 메모이제이션**: columns 배열 useMemo 적용 여부 (기존 이슈 KIIS #3.12)
5. **검색/필터**: 각 페이지의 검색, 필터, 정렬 구현 패턴

## 안티할루시네이션 규칙

🚫 "Pagination이 없다"고 주장하기 전에 실제 코드를 확인하라 — KIIS는 6곳에서 사용
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## C6. KIIS 라우트 & 번들 최적화

```
KIIS 모듈의 라우팅, 상수, 타입 구조를 코드 리뷰해줘. 번들 크기 최적화가 핵심.

## 리뷰 대상 파일

1. amic-platform/src/modules/kiis/KiisRoutes.tsx
2. amic-platform/src/modules/kiis/constants/variants.ts
3. amic-platform/src/modules/kiis/types/company.ts (헤더만)
4. amic-platform/src/modules/kiis/types/fund.ts (헤더만)
5. amic-platform/src/modules/kiis/types/reit.ts (헤더만)
6. amic-platform/src/modules/kiis/types/news.ts (헤더만)
7. amic-platform/src/modules/kiis/types/watchlist.ts (헤더만)

## 점검 항목

1. **18페이지 정적 임포트** [P0]: KiisRoutes.tsx에서 18개 페이지를 모두 정적 import 하는지, React.lazy 사용 여부
   - FDD는 React.lazy 사용, IM도 React.lazy 사용 — KIIS만 정적이면 번들 크기 이슈
2. **variants.ts**: 상태→스타일 매핑 상수, Badge/KpiCard variant 혼동 없는지
3. **타입 일관성**: 14개 타입 파일의 네이밍 컨벤션, export 패턴

## 안티할루시네이션 규칙

🚫 "React.lazy를 사용하고 있다"고 주장하기 전에 import 문을 확인하라
🚫 타입 파일 14개를 전부 읽을 필요 없음 — 헤더(export interface/type)만 확인
✅ KiisRoutes.tsx를 반드시 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 D: IM 모듈 프론트엔드 (3개)

---

## D1. IM 훅 & API

```
IM 모듈의 훅과 타입을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/im/hooks/useDocuments.ts
2. amic-platform/src/modules/im/hooks/useCompanies.ts
3. amic-platform/src/modules/im/hooks/__tests__/useDocuments.test.tsx
4. amic-platform/src/modules/im/hooks/__tests__/useCompanies.test.tsx
5. amic-platform/src/modules/im/types/document.ts
6. amic-platform/src/modules/im/types/company.ts

## 점검 항목

1. **blob URL revoke 타이밍**: 문서 다운로드 시 blob URL을 즉시 revoke하는지 (기존 이슈 P2)
2. **Company.industry 타입**: `string | null` vs `IndustryId` — industry.ts에서 re-export하는지 (기존 이슈 P3)
3. **문서 상태 폴링**: 생성 중인 문서의 상태를 refetchInterval로 폴링하는지
4. **쿼리키**: `["im", "documents"]`, `["im", "companies"]` 일관성
5. **테스트 품질**: 성공/실패 케이스, 뮤테이션 테스트

## 크로스 레퍼런스

- BE: `IM Module/auto-im-generator/src/api/routes/documents.py` — 엔드포인트 경로
- BE: `IM Module/auto-im-generator/src/api/schemas/documents.py` — 응답 스키마

## 안티할루시네이션 규칙

🚫 IM #1 "ProgressTracker always Stage 0"은 이전 리뷰의 허위 발견 — 재보고하지 마라
🚫 IM #2 "corp_code just length check"도 허위 발견 — 실제로 정규식 검증 사용
✅ 모든 파일을 Read 도구로 읽어라
✅ blob URL 처리 코드를 정확히 인용하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## D2. IM 페이지 & 컴포넌트

```
IM 모듈의 페이지와 컴포넌트를 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/im/pages/CreateDocumentPage.tsx
2. amic-platform/src/modules/im/pages/DocumentDetailPage.tsx
3. amic-platform/src/modules/im/pages/DocumentListPage.tsx
4. amic-platform/src/modules/im/components/ProgressTracker.tsx
5. amic-platform/src/modules/im/components/DocumentStatusBadge.tsx
6. amic-platform/src/modules/im/components/ImErrorBoundary.tsx

## 점검 항목

1. **CreateDocumentPage useEffect cleanup**: 언마운트 후 상태 업데이트 방지 (기존 이슈 P1)
2. **ProgressTracker NaN**: 진행률 계산에서 NaN 발생 가능성 (P4)
3. **ProgressTracker 실패 단계**: getFailedStageIndex() 구현 확인 — "항상 Stage 0"은 허위 발견
4. **DocumentStatusBadge**: Badge variants 매핑 정확성 (`success | warning | error | info | neutral`)
5. **ImErrorBoundary**: 에러 복구 UI, retry 버튼
6. **DocumentDetailPage**: 문서 상세 렌더링, 섹션별 내용 표시

## 안티할루시네이션 규칙

🚫 "ProgressTracker가 항상 Stage 0을 표시한다"는 이전 리뷰의 허위 발견 — 재보고 금지
🚫 "CreateDocumentPage에 cleanup이 없다"고 가정하지 마라 — useEffect return문을 확인하라
✅ 모든 파일을 Read 도구로 읽어라
✅ ProgressTracker.tsx의 getFailedStageIndex() 함수를 직접 읽어 확인하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## D3. IM ↔ FDD 크로스모듈 통합

```
IM과 FDD 모듈 간 통합 지점을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/types/industry.ts
2. amic-platform/src/modules/im/types/document.ts
3. amic-platform/src/modules/fdd/types/deal.ts
4. amic-platform/src/modules/im/ImRoutes.tsx

## 크로스 레퍼런스 (BE)

아래 BE 파일도 읽어서 FE와 대조하라:
- Auto FDD/backend/app/api/deals.py (deal summary endpoint — GET /deals/{id}/summary)
- Auto FDD/backend/app/industry/models.py (IndustryType enum)

## 점검 항목

1. **IndustryId 경로**: industry.ts에서 정의 → IM document.ts에서 re-export → FDD deal.ts에서 사용
2. **FDD deal summary API**: GET /deals/{id}/summary가 QoE+NWC+Debt를 3개 별도 쿼리로 조회하는지 (기존 이슈 F1 — 비효율)
3. **IndustryType 값 일치**: BE Python enum vs FE TypeScript union 값 대조
4. **ImRoutes.tsx**: 라우트 구조, React.lazy 사용 여부

## 안티할루시네이션 규칙

🚫 IndustryId 값 목록을 추측하지 마라 — industry.ts를 직접 읽어라
🚫 BE API 경로를 추측하지 마라 — deals.py를 직접 읽어라
✅ FE + BE 양쪽 파일을 모두 Read 도구로 읽어라
✅ 불일치 발견 시 양쪽 코드를 모두 인용하라

## 출력 형식

각 발견사항마다:
1. **FE 파일:줄번호** + **BE 파일:줄번호** 2. **양쪽 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 E: 백엔드 보안 & 인증 (4개)

---

## E1. FDD 백엔드 인증

```
FDD 백엔드의 인증 및 보안 설정을 코드 리뷰해줘.
이전 리뷰에서 여러 허위 발견이 있었으므로 특히 주의 깊게 실제 코드를 확인하라.

## 리뷰 대상 파일

1. Auto FDD/backend/app/auth/token.py
2. Auto FDD/backend/app/auth/password.py
3. Auto FDD/backend/app/auth/dependencies.py
4. Auto FDD/backend/app/config.py
5. Auto FDD/backend/app/main.py (CORS 설정 섹션)

## 점검 항목

1. **비밀번호 해싱**: password.py에서 bcrypt 사용 확인 — 이전 리뷰에서 PBKDF2로 잘못 보고됨
2. **auth_enabled 기본값**: config.py에서 auth_enabled 기본값이 True인지 확인 — 이전 리뷰에서 False로 잘못 보고됨
3. **JWT_SECRET 프로덕션 가드**: config.py:40-48에서 프로덕션 환경 시 RuntimeError 발생시키는 로직
4. **CORS 설정**: main.py에서 명시적 origin 리스트 사용 확인 — 이전 리뷰에서 와일드카드로 잘못 보고됨
5. **JWT 토큰**: 만료 시간 설정, refresh 토큰 구현
6. **의존성 주입**: dependencies.py의 현재 사용자 추출 로직

## 안티할루시네이션 규칙 (매우 중요!)

이전 리뷰에서 아래 항목이 모두 허위 발견으로 확인됨. 반드시 직접 확인하고 재보고하지 마라:
- ❌ FDD #1.2 "PBKDF2 사용" → 실제: bcrypt 사용 (password.py 확인)
- ❌ FDD #1.3 "auth_enabled 기본값 False" → 실제: True (config.py 확인)
- ❌ FDD #1.5 "CORS 와일드카드" → 실제: 명시적 origin 리스트 (main.py 확인)
- ❌ FDD #1.4 "setattr 취약점" → 실제: _UPDATABLE_FIELDS 화이트리스트 있음 (deals.py:106-118 확인)

✅ password.py의 해싱 함수를 직접 읽어서 bcrypt 라이브러리 import를 확인하라
✅ config.py의 auth_enabled 필드 정의를 직접 읽어서 기본값을 확인하라
✅ main.py의 CORSMiddleware 설정을 직접 읽어서 allow_origins를 확인하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** (3~10줄) 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**

추가로, 위 4개 허위 발견 항목에 대해 "✅ 확인 완료: [실제 상태]"를 반드시 명시하라.
```

---

## E2. KIIS 백엔드 보안 설정

```
KIIS 백엔드의 보안 설정을 코드 리뷰해줘.
K1(JWT_SECRET 빈 기본값)이 유일한 CRITICAL 이슈로 확인됨 — 이 부분을 최우선 확인하라.

## 리뷰 대상 파일

1. KIIS/app/core/config.py
2. KIIS/app/core/security.py
3. KIIS/app/core/dependencies.py
4. KIIS/app/middleware/rate_limit.py
5. KIIS/app/routers/auth.py

## 점검 항목

1. **K1 CRITICAL**: config.py에서 SECRET_KEY, JWT_SECRET 기본값이 빈 문자열("")인지 확인
   — 프로덕션 환경 시 시작 검증(RuntimeError) 존재 여부
2. **K3**: DART_API_KEY 등 필수 외부 API 키의 시작 시 검증 존재 여부
3. **비밀번호 해싱**: security.py에서 사용하는 해싱 알고리즘 (bcrypt? passlib?)
4. **Rate limiting**: rate_limit.py — 구현 방식 (Redis-backed? in-memory?), 제한 값
5. **인증 라우터**: auth.py — 로그인/토큰 발급/리프레시 플로우

## 안티할루시네이션 규칙

🚫 config.py를 읽지 않고 "SECRET_KEY가 안전하다"고 주장하지 마라
✅ config.py의 Settings 클래스를 직접 읽어 기본값을 확인하라
✅ security.py의 패스워드 해싱 코드를 직접 확인하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** (3~10줄) 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## E3. IM 백엔드 인증 & API 키

```
IM 백엔드의 인증 및 API 키 관리를 코드 리뷰해줘.

## 리뷰 대상 파일

1. IM Module/auto-im-generator/src/api/security/auth.py
2. IM Module/auto-im-generator/src/api/security/api_keys.py
3. IM Module/auto-im-generator/src/api/security/password.py
4. IM Module/auto-im-generator/src/api/routes/auth.py
5. IM Module/auto-im-generator/src/api/routes/api_keys.py
6. IM Module/auto-im-generator/src/api/services/auth_service.py
7. IM Module/auto-im-generator/src/api/services/api_key_service.py

## 점검 항목

1. **API 키 저장**: 평문 vs 해시(bcrypt/SHA256) — 평문이면 CRITICAL
2. **JWT vs API 키**: 두 인증 방식의 사용 구분, 우선순위
3. **토큰 만료**: JWT 만료 시간, 리프레시 토큰 구현
4. **비밀번호 해싱**: 해싱 알고리즘 확인
5. **미들웨어**: CORS, rate limiting 설정

## 안티할루시네이션 규칙

🚫 파일 경로를 추측하지 마라 — Glob으로 먼저 확인
✅ 실제 존재하는 파일만 리뷰하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## E4. LLM 프롬프트 인젝션 & 가드레일

```
FDD와 IM 백엔드의 LLM 통합에서 프롬프트 인젝션 위험과 가드레일을 코드 리뷰해줘.
이 영역은 이전 리뷰에서 거의 다루지 않았으므로 새로운 시각으로 접근하라.

## 리뷰 대상 파일

### FDD Backend
1. Auto FDD/backend/app/agents/guardrails.py
2. Auto FDD/backend/app/agents/coa_mapper.py
3. Auto FDD/backend/app/agents/qoe_analyzer.py
4. Auto FDD/backend/app/services/report/narrative_generator.py
5. Auto FDD/backend/app/services/llm/routing/model_router.py

### IM Backend
6. IM Module/auto-im-generator/src/narrative_generator/engine/orchestrator.py
7. IM Module/auto-im-generator/src/narrative_generator/fact_checker/validator.py
8. IM Module/auto-im-generator/src/narrative_generator/engine/model_router.py

## 점검 항목

1. **사용자 입력 → LLM 프롬프트**: project_name, industry, company_name, account_names 등 사용자 입력이 LLM 프롬프트에 직접 삽입되는지
2. **시스템/유저 프롬프트 분리**: system prompt와 user data가 명확히 분리되어 있는지
3. **guardrails.py**: validate_narrative_claims() — 바이패스 가능한 조건이 있는지
4. **fact_checker.py**: 팩트 체킹 로직의 강건성
5. **프롬프트 템플릿**: f-string으로 사용자 입력을 직접 삽입하는 패턴 (위험)
6. **LLM 응답 파싱**: JSON/구조화된 출력 파싱 실패 시 에러 처리
7. **토큰 제한**: max_tokens 설정, 비용 제어

## 안티할루시네이션 규칙

🚫 "프롬프트 인젝션 취약점이 있을 것 같다"는 추측 금지 — 실제 프롬프트 구성 코드를 읽어라
🚫 LLM 호출 패턴을 추측하지 마라 — 실제 API 호출 코드를 확인하라
✅ 프롬프트 템플릿 코드를 직접 읽어서 사용자 입력 삽입 지점을 확인하라
✅ 위험한 패턴과 안전한 패턴을 구분하여 보고하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** (프롬프트 구성 부분) 3. **위험도 분석** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 F: 백엔드 아키텍처 & 데이터 무결성 (5개)

---

## F1. FDD 계산 엔진

```
FDD 백엔드의 계산 엔진(QoE, NWC, Debt)을 코드 리뷰해줘.
금융 계산의 정확성이 핵심이므로 특히 주의 깊게 리뷰하라.

## 리뷰 대상 파일

1. Auto FDD/backend/app/engines/qoe_engine.py
2. Auto FDD/backend/app/engines/nwc_engine.py
3. Auto FDD/backend/app/engines/debt_engine.py
4. Auto FDD/backend/app/engines/delta_engine.py
5. Auto FDD/backend/app/engines/consolidation_engine.py
6. Auto FDD/backend/app/engines/anomaly_engine.py

## 점검 항목

1. **Decimal 정밀도**: float 대신 Decimal 사용 여부, 반올림 모드 (ROUND_HALF_UP)
2. **N+1 쿼리**: qoe_service에서 _get_line_items_map() 또는 유사 함수의 DB 쿼리 패턴 (기존 이슈 FDD #2.1)
3. **인더스트리 컨텍스트 주입**: 엔진에 industry_context 파라미터 전달 정확성
4. **부동소수점 비교**: delta 계산에서 정밀도 문제
5. **0으로 나누기**: 비율 계산에서 ZeroDivisionError 방지
6. **단위 변환**: 환율, 통화 단위 처리

## 안티할루시네이션 규칙

🚫 "float를 사용하고 있다"고 주장하기 전에 실제 계산 코드를 읽어라
🚫 엔진 구조를 추측하지 마라 — 실제 클래스/함수 시그니처를 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## F2. FDD DB & 트랜잭션

```
FDD 백엔드의 데이터베이스 모델, 트랜잭션 관리, 마이그레이션을 코드 리뷰해줘.

## 리뷰 대상 파일

1. Auto FDD/backend/app/database.py
2. Auto FDD/backend/app/models/deal.py
3. Auto FDD/backend/app/models/qoe.py
4. Auto FDD/backend/app/api/deals.py (특히 setattr 관련 코드)
5. Auto FDD/backend/app/api/qoe.py

## 점검 항목

1. **FK 인덱스**: 외래키에 인덱스가 있는지 (기존 이슈 FDD #2.2)
2. **동시성 race condition**: 동시 계산 요청 시 SELECT FOR UPDATE 사용 여부 (FDD #2.4)
3. **setattr() 화이트리스트**: deals.py의 PATCH 엔드포인트에서 _UPDATABLE_FIELDS 화이트리스트 확인
   — 이전 리뷰에서 "취약하다"고 허위 보고됨
4. **커넥션 풀**: database.py의 pool_size, max_overflow 설정
5. **세션 관리**: 트랜잭션 커밋/롤백 패턴, 예외 시 롤백

## 안티할루시네이션 규칙

🚫 FDD #1.4 "setattr 취약점"은 허위 발견 — _UPDATABLE_FIELDS 화이트리스트가 있음. 재보고 금지
🚫 deals.py를 읽지 않고 "setattr이 위험하다"고 주장하지 마라
✅ deals.py:106-118 (또는 유사 범위)에서 _UPDATABLE_FIELDS를 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## F3. KIIS 외부 API 통합

```
KIIS 백엔드의 외부 API 통합(DART, KOFIA)과 스케줄러를 코드 리뷰해줘.

## 리뷰 대상 파일

1. KIIS/app/services/dart_service.py
2. KIIS/app/services/kofia_service.py
3. KIIS/app/tasks/scheduler.py
4. KIIS/app/tasks/dart_sync.py
5. KIIS/app/core/database.py
6. KIIS/app/services/reputation_service.py

## 점검 항목

1. **DART XML/ZIP 파싱**: 파싱 에러 처리, 잘못된 XML 대응
2. **중복 공시 감지**: 동일 공시를 중복 저장하지 않는 로직
3. **스케줄러 에러 핸들링**: scheduler.py에서 작업 실패 시 재시도, 로깅 (기존 이슈 KIIS #2.10)
4. **외부 API 타임아웃**: DART/KOFIA API 호출 시 timeout 설정
5. **데이터베이스 세션**: autocommit 제거 확인 (KIIS #2.2), reputation_service double-commit (KIIS #2.3)

## 안티할루시네이션 규칙

🚫 DART API 응답 형식을 추측하지 마라 — 실제 파싱 코드를 읽어라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## F4. KIIS ElasticSearch & Redis

```
KIIS 백엔드의 ElasticSearch와 Redis 설정 및 사용 패턴을 코드 리뷰해줘.

## 리뷰 대상 파일

1. KIIS/app/core/elasticsearch.py
2. KIIS/app/core/redis.py
3. KIIS/app/services/search_service.py
4. KIIS/app/services/nlp_service.py

## 점검 항목

1. **Nori 분석기**: 한국어 형태소 분석기 설정 여부
2. **배치 reindex**: 대량 문서 재인덱싱 시 배치 처리 (기존 이슈 KIIS #2.6)
3. **와일드카드 검색**: 필드 지정 없는 와일드카드 검색 (기존 이슈 KIIS #2.4) — 성능 영향
4. **Redis**: AOF 퍼시스턴스, maxmemory-policy 설정
5. **Redis 캐시**: TTL 전략, 캐시 무효화 패턴
6. **ES 인덱스 매핑**: 필드 타입 정의, 한국어 분석기 매핑

## 안티할루시네이션 규칙

🚫 ElasticSearch 설정을 추측하지 마라 — 실제 인덱스 매핑 코드를 읽어라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## F5. IM 문서 생성 파이프라인

```
IM 백엔드의 문서 생성 파이프라인(DART → 분석 → 내러티브 → 렌더링)을 코드 리뷰해줘.

## 리뷰 대상 파일

1. IM Module/auto-im-generator/src/api/services/document_service.py
2. IM Module/auto-im-generator/src/narrative_generator/engine/orchestrator.py
3. IM Module/auto-im-generator/src/data_ingestor/pipeline.py
4. IM Module/auto-im-generator/src/api/db/session.py
5. IM Module/auto-im-generator/src/narrative_generator/engine/model_router.py
6. IM Module/auto-im-generator/src/api/tasks/generate_im.py
7. IM Module/auto-im-generator/src/api/tasks/fetch_company.py

## 점검 항목

1. **파이프라인 실패 복구**: 5단계 중 중간 단계 실패 시 복구 전략 (Celery chord?)
2. **중복 corp_code 방지**: 동일 corp_code로 동시에 문서 생성 요청 시 처리
3. **비동기 세션 에러**: AsyncSession에서 에러 발생 시 롤백
4. **문서 상태 전이**: PENDING → IN_PROGRESS → COMPLETED / FAILED 상태 머신 정확성
5. **멀티모델 라우팅**: model_router의 OpenAI/Claude/Gemini 라우팅 맵
6. **토큰 예산**: token_budget 관리, 비용 제어

## 안티할루시네이션 규칙

🚫 파이프라인 아키텍처를 추측하지 마라 — 실제 코드를 읽어라
🚫 Celery 사용 여부를 가정하지 마라 — import문을 확인하라
✅ 모든 파일을 Glob으로 찾은 후 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 G: 테스팅 (4개)

---

## G1. 유닛 테스트 — 훅

```
프론트엔드 훅 유닛 테스트의 품질을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/hooks/__tests__/useAuth.test.tsx
2. amic-platform/src/modules/fdd/hooks/__tests__/useDeals.test.tsx
3. amic-platform/src/modules/kiis/hooks/__tests__/useSearch.test.tsx
4. amic-platform/src/modules/kiis/hooks/__tests__/useWatchlist.test.tsx
5. amic-platform/src/modules/im/hooks/__tests__/useDocuments.test.tsx
6. amic-platform/src/test/mocks/handlers.ts
7. amic-platform/src/test/mocks/data.ts

## 점검 항목

1. **MSW 핸들러 페이로드 검증**: handlers.ts에서 요청 body를 검증하는지 (FDD #8.4)
2. **MSW 응답 타입 일치**: data.ts의 mock 데이터가 실제 API 응답 스키마와 일치하는지 (FDD #8.5)
3. **비동기 테스트**: waitFor vs findBy 적절한 사용
4. **에러 시나리오**: 네트워크 에러, 401, 404 등 실패 케이스 테스트
5. **뮤테이션 테스트**: create/update/delete 후 캐시 무효화 검증
6. **테스트 격리**: 테스트 간 상태 공유 없음 확인

## 안티할루시네이션 규칙

🚫 "테스트가 부족하다"는 주관적 판단 금지 — 구체적으로 어떤 시나리오가 누락인지 지적하라
✅ 모든 파일을 Read 도구로 읽어라
✅ 실제 테스트 코드를 인용하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## G2. 유닛 테스트 — 페이지 & 컴포넌트

```
프론트엔드 페이지 및 컴포넌트 유닛 테스트의 품질을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/pages/__tests__/DealListPage.test.tsx
2. amic-platform/src/pages/__tests__/DashboardPage.test.tsx
3. amic-platform/src/modules/im/components/__tests__/ImErrorBoundary.test.tsx
4. amic-platform/src/test/setup.ts
5. amic-platform/src/test/test-utils.tsx

## 점검 항목

1. **renderWithProviders**: QueryClient 설정 (retry: false, staleTime 등)
2. **jsdom 폴리필**: HTMLDialogElement.showModal() 폴리필 정확성
3. **matchMedia mock**: 반응형 테스트 지원
4. **MSW 라이프사이클**: beforeAll/afterEach/afterAll 설정
5. **Assertion 품질**: 스냅샷 테스트 vs 구체적 assertion
6. **테스트 간 cleanup**: unmount, queryClient.clear()

## 안티할루시네이션 규칙

🚫 setup.ts의 폴리필이 "불완전하다"고 주장하기 전에 실제 코드를 확인하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## G3. E2E 테스트 인프라

```
E2E 테스트(Playwright) 인프라 파일들을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/playwright.config.ts
2. amic-platform/e2e/fixtures/test-base.ts
3. amic-platform/e2e/fixtures/api-mocks.ts
4. amic-platform/e2e/fixtures/console-monitor.ts
5. amic-platform/e2e/fixtures/auth.fixture.ts (존재하면)

## 점검 항목

1. **serviceWorkers: "block"**: chromium-mocked 프로젝트에서 설정 확인 — MSW가 page.route()를 차단하는 CRITICAL 이슈
2. **Auth 토큰 키**: localStorage에 `autofdd_access_token` 사용 (NOT `access_token`)
3. **API mock 패턴**: api-mocks.ts의 page.route() 패턴이 실제 API 경로와 일치하는지
4. **Mock 데이터 날짜**: 분석 페이지 기본 timeRange "30d" — mock 데이터 날짜가 범위 내인지
5. **Console monitor**: 에러 수집 임계값, false positive 필터링

## 안티할루시네이션 규칙

🚫 Playwright 설정을 추측하지 마라 — playwright.config.ts를 직접 읽어라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## G4. E2E 테스트 케이스

```
E2E 테스트 케이스의 품질을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/e2e/tests/fdd-deep.spec.ts
2. amic-platform/e2e/tests/kiis-dashboard-deep.spec.ts
3. amic-platform/e2e/tests/im-deep.spec.ts
4. amic-platform/e2e/tests/search-deep.spec.ts
5. amic-platform/e2e/tests/dashboard-deep.spec.ts

## 점검 항목

1. **로케이터 안정성**: getByRole vs CSS 셀렉터 (FDD #8.9) — CSS 셀렉터보다 시맨틱 로케이터 선호
2. **Mock 응답 스키마**: page.route() 응답 데이터가 실제 BE 스키마와 일치하는지
3. **커버리지 갭**: Deal 생성 플로우, IM 문서 생성 플로우 등 핵심 시나리오 누락 여부
4. **테스트 격리**: 테스트 간 상태 의존성 없음 확인
5. **타임아웃**: waitForResponse, waitForSelector 타임아웃 적절성
6. **에러 케이스**: API 실패 시나리오 테스트 여부

## 안티할루시네이션 규칙

🚫 "테스트가 불충분하다"는 막연한 주장 금지 — 구체적 누락 시나리오를 지적하라
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 H: 인프라 & 배포 (3개)

---

## H1. Docker & Compose

```
Docker 설정과 Compose 파일을 코드 리뷰해줘.

## 리뷰 대상 파일

먼저 아래 경로에서 Docker 관련 파일을 Glob으로 찾아라:
- `**/docker-compose*.yml`
- `**/Dockerfile*`

예상 파일:
1. docker-compose.yml
2. docker-compose.prod.yml (존재하면)
3. amic-platform/Dockerfile
4. amic-platform/Dockerfile.dev (존재하면)

## 점검 항목

1. **healthcheck**: 각 서비스의 health check 설정, depends_on 의존성
2. **볼륨 퍼시스턴스**: dev vs prod 볼륨 설정 차이
3. **리소스 제한**: prod에서 mem_limit, cpus 설정 여부
4. **Redis**: AOF 퍼시스턴스, maxmemory-policy 설정
5. **멀티스테이지 빌드**: Dockerfile에서 빌드/런타임 분리
6. **환경변수**: .env 파일 참조, 프로덕션 시크릿 관리

## 안티할루시네이션 규칙

🚫 Docker 파일이 존재하지 않을 수 있음 — 먼저 Glob으로 확인하라
✅ 실제 존재하는 파일만 리뷰하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## H2. Nginx 설정

```
Nginx 설정 파일들을 코드 리뷰해줘.

## 리뷰 대상 파일

먼저 아래 경로에서 Nginx 관련 파일을 Glob으로 찾아라:
- `**/nginx*.conf`
- `**/nginx/**`

예상 파일:
1. nginx/prod.conf
2. nginx/dev.conf (존재하면)
3. amic-platform/nginx.conf (존재하면)

## 점검 항목

1. **API 프록시 rewrite**: `/api/fdd/*` → `/api/v1/*` rewrite 정확성 — vite.config.ts 프록시와 일치
2. **보안 헤더**: X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security, CSP
3. **CSP 정책**: Sentry 도메인 허용, 인라인 스크립트 제한
4. **client_max_body_size**: 파일 업로드 제한 (100M? 적절한지)
5. **proxy_read_timeout**: LLM API 호출용 충분한 타임아웃 (300s?)
6. **SSL/TLS**: TLS 1.2+ 강제, 안전한 cipher suite
7. **Health check**: 내부 전용 (127.0.0.1) 접근 제한

## 안티할루시네이션 규칙

🚫 Nginx 파일이 존재하지 않을 수 있음 — 먼저 Glob으로 확인하라
✅ 실제 존재하는 파일만 리뷰하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## H3. CI/CD & 환경변수

```
CI/CD 파이프라인과 환경변수 설정을 코드 리뷰해줘.

## 리뷰 대상 파일

먼저 아래 경로에서 파일을 Glob으로 찾아라:
- `.github/workflows/*.yml`
- `.env*`

예상 파일:
1. .github/workflows/ci.yml
2. .github/workflows/deploy.yml (존재하면)
3. .env.production.example

## 점검 항목

1. **CI 단계**: lint → typecheck → test → build → e2e 순서 확인
2. **E2E 범위**: chromium-mocked만 실행하는지 — 충분한지
3. **Sentry 소스맵**: AUTH_TOKEN이 GitHub Secrets에 있는지
4. **배포 전략**: health check 후 rollback 전략
5. **환경변수 검증**: 필수 환경변수 누락 시 시작 실패 처리
6. **.env.production.example**: 실제 필요한 모든 변수가 나열되어 있는지

## 안티할루시네이션 규칙

🚫 CI/CD 파일이 존재하지 않을 수 있음 — 먼저 Glob으로 확인하라
✅ 실제 존재하는 파일만 리뷰하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 카테고리 I: 성능 & 최적화 (2개)

---

## I1. 번들 분석

```
프론트엔드 번들 크기와 코드 스플리팅을 코드 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/vite.config.ts
2. amic-platform/package.json
3. amic-platform/src/modules/kiis/KiisRoutes.tsx
4. amic-platform/src/modules/fdd/FddRoutes.tsx
5. amic-platform/src/modules/im/ImRoutes.tsx

## 점검 항목

1. **KIIS 18페이지 정적 임포트** [P0]: KiisRoutes.tsx에서 React.lazy 미사용 시 번들에 전부 포함
   - 비교: FddRoutes.tsx와 ImRoutes.tsx는 React.lazy 사용하는지
2. **코드 스플리팅**: Vite의 manualChunks 설정 여부
3. **React Query devtools**: 프로덕션 빌드에서 제외되는지
4. **트리 셰이킹**: 미사용 export가 빌드에 포함되는지
5. **라이브러리 중복**: recharts 등 큰 라이브러리의 중복 번들링
6. **package.json**: 불필요한 dependencies (react-joyride 등 — React 19 비호환)

실제로 `npm run build`를 실행하여 dist/ 크기를 확인하면 더 좋음.

## 안티할루시네이션 규칙

🚫 "React.lazy를 사용하고 있다"고 주장하기 전에 import문을 확인하라
🚫 번들 크기를 추측하지 마라 — 코드만 리뷰하라
✅ KiisRoutes.tsx의 import문을 직접 읽어 정적/동적 여부를 확인하라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

## I2. 런타임 성능

```
프론트엔드 런타임 성능 관련 코드를 리뷰해줘.

## 리뷰 대상 파일

1. amic-platform/src/modules/fdd/pages/IssuesPage.tsx
2. amic-platform/src/modules/kiis/pages/CompanyDetailPage.tsx
3. amic-platform/src/components/ui/DataTable.tsx
4. amic-platform/src/lib/cn.ts
5. amic-platform/src/modules/kiis/pages/NewsListPage.tsx

## 점검 항목

1. **IssuesPage 필터 객체**: 매 렌더마다 새 객체 생성 (FDD #5.1) — useMemo 적용 여부
2. **CompanyDetailPage 5-쿼리**: 5개 useQuery가 병렬 실행되는지, enabled 체이닝으로 순차화되는지
3. **DataTable**: 1000+ 행 가상화 (react-window/tanstack-virtual), 열 메모이제이션
4. **cn() 호출 빈도**: 매 렌더 시 호출되는 cn()의 성능 영향 (twMerge 캐싱)
5. **인라인 객체/함수**: onClick={() => fn(id)} 패턴으로 인한 불필요 리렌더
6. **React Query 설정**: staleTime, refetchOnWindowFocus 전역 설정

## 안티할루시네이션 규칙

🚫 "성능이 나쁘다"는 주관적 판단 금지 — 구체적 코드 패턴과 영향을 설명하라
🚫 cn()이 "느리다"고 주장하기 전에 실제 구현을 확인하라 — twMerge는 내부 캐싱을 함
✅ 모든 파일을 Read 도구로 읽어라

## 출력 형식

각 발견사항마다:
1. **파일:줄번호** 2. **실제 코드** 3. **문제** 4. **심각도** 5. **수정안** 6. **검증 체크리스트**
```

---

# 부록: 공통 안티할루시네이션 가이드

모든 프롬프트 실행 시 아래 규칙을 반드시 준수하라.

## 금지 표현

- "일반적으로 ~는 ~하다" → 실제 코드를 인용하라
- "이 파일에는 아마 ~가 있을 것이다" → Read로 확인하라
- "비슷한 프로젝트에서 ~했다" → 이 프로젝트의 코드만 참조하라
- "~가 없는 것 같다" → 정확히 어떤 줄에서 확인했는지 명시하라

## 필수 증거

모든 발견사항에 반드시 포함:
1. **파일 경로 + 줄번호** (예: `src/hooks/useAuth.ts:45-52`)
2. **실제 코드 스니펫** (3~10줄)
3. **Read 도구 사용 확인** (파일을 읽었다는 것을 명시)

## 기존 허위 발견 목록 (재보고 금지)

아래 항목은 `docs/20260213_1253_Verified_Code_Review.md`에서 허위 발견으로 확정됨:

| ID | 허위 주장 | 실제 |
|----|-----------|------|
| FDD #1.2 | PBKDF2 사용 | bcrypt 사용 (password.py) |
| FDD #1.3 | auth_enabled 기본값 False | 기본값 True (config.py) |
| FDD #1.4 | setattr 취약점 | _UPDATABLE_FIELDS 화이트리스트 존재 (deals.py) |
| FDD #1.5 | CORS 와일드카드 | 명시적 origin 리스트 (main.py) |
| Platform C1 | 로그아웃 시 캐시 미삭제 | queryClient.clear() 호출함 (useAuth.ts) |
| Platform C2 | cn() 단순 join | twMerge + clsx 사용 (cn.ts) |
| IM #1 | ProgressTracker 항상 Stage 0 | getFailedStageIndex() 구현됨 |
| IM #2 | corp_code 길이만 체크 | 정규식 `/^\d{8}$/` 검증 사용 |
