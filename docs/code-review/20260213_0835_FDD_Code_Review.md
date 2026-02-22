# FDD 모듈 전체 코드 리뷰

> 리뷰 일시: 2026-02-13 08:33
> 범위: Frontend (`amic-platform/src/modules/fdd/`) + Backend (`Auto FDD/backend/`) + Tests & Integration

---

## 요약 (Executive Summary)

| 영역 | Critical | High | Medium | Low | 합계 |
|------|----------|------|--------|-----|------|
| **Backend 보안** | 3 | 2 | 3 | - | 8 |
| **Backend API/DB** | 1 | 1 | 5 | 1 | 8 |
| **Backend LLM** | - | - | 2 | - | 2 |
| **Frontend 타입안전성** | - | 2 | 2 | - | 4 |
| **Frontend 성능** | - | - | 3 | - | 3 |
| **Frontend 에러처리** | - | 2 | 2 | - | 4 |
| **Frontend 접근성** | - | - | 3 | - | 3 |
| **테스트 커버리지** | 3 | 3 | 3 | - | 9 |
| **합계** | **7** | **10** | **23** | **1** | **41** |

---

## 1. Backend — 보안 (CRITICAL)

### 1.1 JWT Secret 하드코딩 🔴
- **파일**: `Auto FDD/backend/app/config.py:12`
- `jwt_secret: str = "dev-secret-change-in-production-!!"`
- 환경변수 미설정 시 이 약한 시크릿으로 폴백 → 토큰 위조 가능
- **수정**: 프로덕션에서 env var 미설정 시 에러 발생시키기, 최소 32자 강제

### 1.2 취약한 비밀번호 해싱 🔴
- **파일**: `app/auth/password.py:7-11`
- PBKDF2 100,000 iterations — 현재 권장치 600,000+ 미달
- `key.hex() == key_hex` 비교 → 타이밍 공격에 취약 (`hmac.compare_digest()` 미사용)
- **수정**: `bcrypt` 또는 `argon2-cffi` 라이브러리로 교체

### 1.3 인증 기본 비활성화 + Dev User가 ADMIN 🔴
- **파일**: `app/auth/dependencies.py:38-55`, `app/config.py:11`
- `auth_enabled: bool = False` 기본값 → 모든 요청이 ADMIN 권한으로 처리
- 감사 추적 불가 (모든 기록이 "system@autofdd.dev"로 남음)
- **수정**: 프로덕션 기본값 `True`, 비활성화 시 WARNING 로그

### 1.4 Deal Update에서 setattr() 취약점 🔴 HIGH
- **파일**: `app/api/deals.py:87-101`
- `setattr(deal, key, value)` — 사용자 입력 key로 임의 속성 설정 가능
- `created_by`, `created_at` 등 보호 필드 덮어쓰기 위험
- **수정**: 명시적 필드 할당으로 교체

### 1.5 CORS 과도한 허용 🟠
- **파일**: `app/main.py:48-54`
- `allow_methods=["*"]`, `allow_headers=["*"]` + `allow_credentials=True`
- **수정**: 명시적 메서드/헤더 목록으로 제한

---

## 2. Backend — API/DB 설계

### 2.1 N+1 쿼리 문제 🔴 HIGH
- **파일**: `app/services/qoe/qoe_service.py:55-73`
- `_get_line_items_map()` — 전체 5000+ 항목 로드 (50개 매핑에 대해)
- **수정**: `WHERE code IN (...)` 필터링 추가

### 2.2 FK 컬럼 인덱스 누락 🟠
- `deal_definition.deal_id`, `deal_snapshot.deal_id`, `qoe_calculation.deal_id` 등
- FK는 SQLAlchemy에서 자동 인덱싱 안 됨 → full table scan 위험
- **수정**: Alembic 마이그레이션으로 인덱스 추가

### 2.3 일관성 없는 에러 응답 🟠
- `HTTPException`과 `FDDError` 혼용
- RFC 7807 형식의 `FDDError` 정의되어 있으나 다수 엔드포인트에서 미사용
- **수정**: 모든 엔드포인트에서 `FDDError` 사용으로 통일

### 2.4 동시 계산 요청 Race Condition 🟠
- QoE/NWC/Debt calculate 엔드포인트에 동시 요청 방지 없음
- **수정**: `SELECT ... FOR UPDATE` 락 추가

### 2.5 DB 커넥션 풀 미설정 🟠
- **파일**: `app/database.py:6`
- `pool_size`, `pool_recycle`, `pool_pre_ping` 모두 기본값
- **수정**: 명시적 풀 설정 추가

### 2.6 Rate Limiting 없음 🟠
- 계산 엔드포인트 등 비용이 큰 API에 제한 없음
- **수정**: `slowapi` 미들웨어 추가

### 2.7 Unhandled Exception 로깅 누락 🟠
- **파일**: `app/core/exceptions.py:114-127`
- 500 에러 발생 시 스택트레이스 미기록
- **수정**: `logger.error(exc, exc_info=True)` 추가

### 2.8 Upload 상태 관리 트랜잭션 문제 🟠
- **파일**: `app/api/uploads.py:233-246`
- 검증 실패 시 `VALIDATING` 상태에 고착 가능 (rollback 없음)

---

## 3. Backend — LLM 통합

### 3.1 LLM Router 실패 시 Silent Fallthrough 🟠
- **파일**: `app/services/llm/routing/model_router.py:206-241`
- Router 실패 → `raw_response = None` → `AgentResponse.success = True` + 빈 결과 반환 가능
- **수정**: `raw_response is None` 시 명시적 실패 응답 반환

### 3.2 Guardrails에서 파싱 실패 무시 🟠
- **파일**: `app/agents/guardrails.py:236-273`
- Decimal 파싱 실패 시 `continue`만 실행, 로깅 없음
- **수정**: `logger.warning()` 추가

---

## 4. Frontend — 타입 안전성

### 4.1 ReportPage에서 타입 없는 API 클라이언트 사용 🔴 HIGH
- **파일**: `src/modules/fdd/pages/ReportPage.tsx:12`
- `import api from "@/api/client"` — 타입 없는 bare `api` import
- 다른 파일들은 `fddApi` 사용 → 여기만 불일치
- **수정**: `fddApi`로 교체

### 4.2 validation_summary 타입 캐스팅 🔴 HIGH
- **파일**: `src/modules/fdd/pages/UploadPage.tsx:285-292`
- `upload.validation_summary as Record<string, number>` — 런타임 검증 없이 캐스팅
- **수정**: `ValidationSummary` 인터페이스 정의 후 타입 가드 적용

### 4.3 에러 객체 타입 미지정 🟠
- **파일**: QoEPage.tsx:407, MappingPage.tsx:498
- `error.message` 접근 시 타입 가드 없음
- **수정**: `instanceof Error` 체크 또는 `error?.message` 패턴 통일

### 4.4 NWC 훅 파라미터명 백엔드 불일치 가능 🟠
- **파일**: `src/modules/fdd/hooks/useNWC.ts:25-28`
- `custom_peg_value` — 백엔드에서 `custom_value`일 수 있음
- **수정**: 백엔드 OpenAPI 스펙과 대조 검증 필요

---

## 5. Frontend — 성능

### 5.1 필터 객체 매 렌더 재생성 🟠
- **파일**: `src/modules/fdd/pages/IssuesPage.tsx:256-260`
- 인라인 필터 객체 → 매 렌더마다 새 참조 → useIssues 캐시 미스
- **수정**: `useMemo`로 필터 객체 메모이제이션

### 5.2 NWCPage 정렬 배열 재생성 🟠
- **파일**: `src/modules/fdd/pages/NWCPage.tsx:117-118`
- `[...items].sort(...)` — 매 렌더마다 새 배열 생성
- **수정**: `useMemo`로 정렬 결과 캐싱

### 5.3 Optimistic Updates 미적용 🟠
- 모든 mutation 훅 (`useNWC`, `useQoE`, `useDebt`)에서 `onMutate` 없음
- 느린 네트워크에서 UI 지연 발생

---

## 6. Frontend — 에러 처리

### 6.1 DealSetupWizard 날짜 검증 누락 🔴 HIGH
- **파일**: `src/modules/fdd/components/deal/DealSetupWizard.tsx:75-99`
- `period_end < period_start` 클라이언트 검증 없음
- 잘못된 날짜 범위가 백엔드로 전송될 수 있음

### 6.2 에러 복구 경로 없음 🔴 HIGH
- **파일**: NetDebtPage.tsx:313-325
- 계산 실패 시 토스트만 표시, 폼/상태 리셋 없음
- 사용자가 무효 상태에 갇힘

### 6.3 WorkflowOverviewPage 에러 바운더리 없음 🟠
- `deal.current_phase ?? "MOU"` — deal이 null이면 무반환
- **수정**: 에러 바운더리 또는 로딩/에러 상태 처리

### 6.4 중복 상수 정의 🟠
- `DEAL_TYPE_OPTIONS`가 DealListPage.tsx와 DealSetupWizard.tsx 양쪽에 정의
- **수정**: `fdd/constants.ts`로 추출

---

## 7. Frontend — 접근성

### 7.1 UploadPage 키보드 지원 부족 🟠
- 파일 input `className="hidden"` → `sr-only`로 교체 필요

### 7.2 ARIA 라벨 누락 🟠
- DefinitionPage TagInput의 제거 버튼에 `aria-label` 없음

### 7.3 색상 대비 부족 가능 🟠
- IssuesPage.tsx:140 — `text-text-secondary` 배경 위 텍스트 대비 검증 필요

---

## 8. 테스트 커버리지

### 8.1 FDD 훅 테스트 전무 🔴 CRITICAL
- `useQoE`, `useNWC`, `useDebt`, `useUploads`, `useMapping`, `useIssues`, `useVdr`, `useReportVersions` — **8개 훅 모두 미테스트**
- 유일한 FDD 훅 테스트: `useDeals.test.tsx`

### 8.2 FDD 페이지 테스트 대부분 누락 🔴 CRITICAL
- 테스트 있음: `DealListPage.test.tsx`, `DashboardPage.test.tsx`
- 미테스트: QoEPage, NWCPage, NetDebtPage, MappingPage, UploadPage, DefinitionPage, ReportPage, VdrPage, WorkflowOverviewPage, IssuesPage, DealSetupWizardPage (**11개 페이지**)

### 8.3 E2E 워크플로우 테스트 부재 🔴 CRITICAL
- `fdd-deep.spec.ts` — Deal 목록 5개 케이스만 존재
- 딜 생성, 파일 업로드, QoE/NWC/Debt 계산, 리포트 생성 E2E 없음

### 8.4 MSW 핸들러 요청 검증 없음 🔴 HIGH
- POST `/api/fdd/deals` — 어떤 payload든 수락, `DealCreate` 스키마 검증 없음

### 8.5 Mock 데이터 타입 불일치 🔴 HIGH
- `mockDealSummary`의 수치 필드가 `string` — 백엔드는 `number` 반환 가능
- E2E mock의 `sections` 배열이 `SectionId` union 타입과 불일치

### 8.6 API Client 토큰 리프레시 미테스트 🔴 HIGH
- `client.ts:50-54` — `/api/fdd/auth/refresh` 하드코딩, KIIS/IM 모듈에서의 동작 미검증

### 8.7 백엔드 Python 테스트 미확인 🟠
- `Auto FDD/backend/` 내 테스트 파일 존재 여부 불명확

### 8.8 Cross-Module Industry 검증 없음 🟠
- `FDD_INDUSTRY_IDS`가 `INDUSTRY_LIST` 부분집합인지 테스트 없음
- IM Document의 nullable `industry`와 FDD의 non-null `industry` 호환성 미검증

### 8.9 E2E KPI 어설션 불안정 🟠
- DOM 구조 의존적 locator (`page.getByText("Total Deals").locator("../..")`) 사용 → 불안정

---

## 긍정적 평가 (What's Working Well)

- ✅ 모듈 구조가 깔끔하고 일관적 (`pages/hooks/types/components`)
- ✅ TanStack Query 캐시 키 패턴이 체계적
- ✅ Decimal-as-string 패턴으로 정밀도 보존 (프론트엔드)
- ✅ Industry Registry 패턴으로 확장 가능한 업종 지원
- ✅ Multi-Model LLM 라우팅 아키텍처 잘 설계됨
- ✅ Mutation 후 캐시 무효화 일관적으로 적용
- ✅ 로딩/빈 상태 처리 잘 되어 있음
- ✅ Tailwind 스타일링 일관성 높음

---

## 수정 우선순위

### P0 — 프로덕션 배포 전 필수
1. JWT Secret 하드코딩 제거 (보안)
2. 비밀번호 해싱 bcrypt 전환 (보안)
3. 인증 기본 활성화 (보안)
4. setattr() 취약점 수정 (보안)
5. CORS 허용 범위 축소 (보안)

### P1 — 이번 스프린트
6. FK 인덱스 추가 (성능)
7. N+1 쿼리 수정 (성능)
8. ReportPage API 클라이언트 수정 (타입안전)
9. 날짜 검증 추가 (에러처리)
10. 에러 응답 형식 통일 (API)

### P2 — 다음 스프린트
11. useQoE/useNWC/useDebt 단위 테스트 추가
12. 핵심 페이지 테스트 추가 (QoEPage, NWCPage)
13. 필터 객체 메모이제이션 (성능)
14. 접근성 개선 (ARIA, 키보드)
15. Mock 데이터 타입 정합성 수정

### P3 — 백로그
16. E2E 워크플로우 테스트 확대
17. Optimistic Updates 적용
18. Rate Limiting 추가
19. Soft Delete 구현
20. 토큰 리프레시 엔드포인트 구현
