# AMIC x PETRA Platform — 추가 코드 리뷰 프롬프트 V2

> 생성일: 2026-02-13 12:31
> 용도: 기존 10개 리뷰 문서 분석 후, 미리뷰 영역을 커버하는 심화 프롬프트
> 기존 문서: `20260213_0906_Code_Review_Prompts.md` (Session 1~5)
> 이 문서: Session 6~13 (기존 Session 5 크로스모듈은 업데이트 버전으로 재작성)

---

## 기존 리뷰 커버리지 요약

| 문서 | 범위 | 이슈 수 |
|------|------|---------|
| `0833_FDD_Code_Review` | FDD FE+BE 전체 | 41건 |
| `0927_FDD_Code_Review_Session2` | FDD FE 심층 (기존 제외) | 19건 (3 FP 정정) |
| `1228_FDD_Code_Review_Session3` | FDD 수정 검증 + 추가 | 10건 수정 + N1~N8 |
| `0836_KIIS_Code_Review` | KIIS FE+BE 전체 | 28건 |
| `0926_KIIS_Code_Review_Session3` | KIIS FE 심층 (기존 제외) | 15건 |
| `1659_IM_FE_BE_Mismatch_Audit` | IM FE↔BE 필드 대조 | 7건 (전부 수정) |
| `1003_IM_Module_Code_Review` | IM FE+BE 리뷰 | 8건 |
| `0957_Platform_Code_Review` | Platform 공통 레이어 | 25건 (3 FP 제거) |
| `1222_Platform_Code_Review_Supplement` | Platform 보충 | 15건 |

**합계: ~168건 이슈 (FP 제거 후)**

---

## 미리뷰 영역 (Gap Analysis)

| # | 영역 | 미리뷰 사유 |
|---|------|------------|
| 1 | 크로스 모듈 통합 | Session 5 프롬프트만 작성, 미실행 |
| 2 | 백엔드 보안 통합 | 표면적 지적만 (JWT, PBKDF2), 심층 미검토 |
| 3 | 백엔드 아키텍처 심층 | FE-BE 타입 비교 관점에서만 다뤄짐 |
| 4 | FE 유닛 테스트 품질 | "테스트 부족" 지적만, 기존 테스트 품질 미리뷰 |
| 5 | E2E 테스트 품질 | 38개 deep test 코드 자체 미리뷰 |
| 6 | 인프라/배포 | Docker 14서비스, nginx 4conf, CI/CD 2workflow 전혀 미리뷰 |
| 7 | 성능/번들 | 코드 스플리팅, 번들, Tailwind purge 미리뷰 |
| 8 | 누적 수정사항 검증 | Session 2-3 수정 ~30건의 일관성 미검증 |

---

## 세션 6: 크로스 모듈 통합 리뷰 (업데이트)

```
개별 모듈 리뷰가 완료되었어. 이제 크로스 모듈 관점에서 통합 리뷰해줘.
기존 리뷰에서 발견된 이슈를 바탕으로, 모듈 간 영향을 분석하는 게 핵심이야.

## 필수 사전 읽기 (기존 리뷰 문서)

아래 문서들을 먼저 읽고, 이미 발견된 이슈를 이해한 상태에서 리뷰해줘:
- docs/20260213_0957_Platform_Code_Review.md (Platform 25건)
- docs/20260213_1222_Platform_Code_Review_Supplement.md (Platform 보충 15건)
- docs/20260213_1228_FDD_Code_Review_Session3.md (FDD 최종 상태)
- docs/20260213_0926_KIIS_Code_Review_Session3.md (KIIS 최종 상태)
- docs/20260213_1003_IM_Module_Code_Review.md (IM 최종 상태)

## 리뷰 대상

### 모듈 간 공유 지점
- src/api/client.ts — 3개 모듈 공통 API 팩토리
- src/api/client.ts:49-52 — 토큰 리프레시 FDD 하드코딩 (Platform M1)
- src/types/industry.ts — FDD ↔ IM 공유 IndustryId 타입
- src/hooks/useAuth.ts — 인증 훅 + 토큰 관리
- src/lib/token-storage.ts — 토큰 저장소 (순환 의존 해소용 신규 파일)
- src/lib/auth-events.ts — 강제 로그아웃 이벤트
- src/components/auth/ — AuthProvider, ProtectedRoute
- vite.config.ts — 프록시 설정 (/api/fdd, /api/kiis, /api/im)

### 모듈별 라우팅
- src/main.tsx — 앱 진입점
- src/modules/fdd/FddRoutes.tsx
- src/modules/kiis/KiisRoutes.tsx — ⚠️ Lazy loading 미적용 (기존 이슈)
- src/modules/im/ImRoutes.tsx

### 모듈별 API 클라이언트
- src/api/client.ts (default export = fddApi)
- 각 모듈의 훅에서 api import 방식 비교

## 점검 관점

1. **인증 흐름 일관성**
   - Platform C1: logout 시 queryClient.clear() 적용 여부 → 3개 모듈 캐시 모두 클리어되는지
   - Platform M1: 토큰 리프레시가 FDD 하드코딩 → FDD 다운 시 KIIS/IM 영향
   - Platform M9: window.location.href 대신 auth-events 적용 여부
   - Platform M13: client.ts ↔ useAuth.ts 순환 의존성 → token-storage.ts 분리 적용 여부
   - 3개 백엔드의 JWT 시크릿 동일 여부 (FDD JWT_SECRET vs KIIS SECRET_KEY vs IM SECRET_KEY)

2. **React Query 키 충돌**
   - FDD: `["fdd", "deals", ...]` (Session 3에서 접두사 추가됨)
   - KIIS: `["kiis", "companies", ...]` (원래부터 접두사 있음)
   - IM: `["im-documents", ...]` vs `["im-companies", ...]`
   - 3개 모듈 간 쿼리 키 네이밍 규칙이 일관적인지
   - KIIS Session 3 #1: useFundManagers 쿼리키가 useManagers와 충돌하는 이슈 수정 여부

3. **공유 UI 컴포넌트 사용 일관성**
   - 3개 모듈에서 Badge, DataTable, KpiCard 사용 시 variant 값 일관성
   - KIIS Session 1 #3.5: variant 맵 중복 → constants/variants.ts 추출 여부
   - Pagination 컴포넌트 사용: FDD(미사용), KIIS(6곳 중복), IM(직접 구현) → 통합 여부

4. **에러 처리 패턴**
   - Platform M10: QueryClient 전역 onError 핸들러 적용 여부
   - 3개 모듈의 mutation onError 패턴이 동일한지
   - toast 사용 패턴: sonner? 직접 구현? import 경로?

5. **코드 스플리팅**
   - FddRoutes: React.lazy 사용 여부
   - KiisRoutes: 18개 페이지 정적 import (기존 이슈)
   - ImRoutes: React.lazy 사용 여부
   - 공유 라이브러리(recharts 등) 중복 번들링 여부

6. **타입 공유**
   - IndustryId: src/types/industry.ts → FDD deal.ts + IM document.ts 양쪽 import 정확성
   - Paginated 응답 타입: 3개 모듈이 각각 정의 vs 공통 타입 사용
   - 에러 응답 타입: 통일된 ErrorResponse 타입 존재 여부

## 출력 형식

이슈를 크로스 모듈 관점에서 분류:
- **영향 범위**: 어떤 모듈들이 영향받는지 (FDD+IM, FDD+KIIS, 전체 등)
- **심각도**: Critical / Major / Minor
- **관련 기존 이슈**: 해당하면 기존 리뷰 문서의 이슈 ID 참조
- **문제**: 구체적 설명
- **수정안**: 어디서 무엇을 변경해야 하는지

리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 7: 백엔드 보안 통합 리뷰

```
3개 백엔드(FDD, KIIS, IM)의 보안을 통합 관점에서 심층 리뷰해줘.
기존 리뷰에서 표면적으로만 지적된 보안 이슈들의 실제 영향을 분석하고,
아직 발견되지 않은 보안 취약점을 찾는 게 목표야.

## 기존 보안 이슈 (확인 필요)

기존 리뷰에서 지적된 보안 이슈들이 수정되었는지 먼저 확인:
- FDD #1.1: JWT Secret 하드코딩 (`Auto FDD/backend/app/config.py:12`)
- FDD #1.2: PBKDF2 100K iterations → bcrypt/argon2 전환
- FDD #1.3: auth_enabled 기본 False → True 변경
- FDD #1.4: setattr() 취약점
- FDD #1.5: CORS 과도한 허용
- KIIS #2.1: SECRET_KEY 하드코딩 기본값
- KIIS #2.5: 인증 없는 엔드포인트

## 리뷰 대상

### FDD 인증/권한
- Auto FDD/backend/app/auth/token.py — JWT 생성/검증
- Auto FDD/backend/app/auth/password.py — 비밀번호 해싱
- Auto FDD/backend/app/auth/rbac.py — 역할 기반 접근 제어
- Auto FDD/backend/app/auth/dependencies.py — 인증 미들웨어
- Auto FDD/backend/app/services/auth_service.py — 인증 서비스

### KIIS 인증/보안
- KIIS/app/core/config.py — 시크릿 설정
- KIIS/app/core/security.py — 보안 헤더
- KIIS/app/middleware/rate_limit.py — 레이트 리미팅
- KIIS/app/routers/ — 각 라우터의 인증 Depends 적용 여부

### IM 인증/보안
- IM Module/auto-im-generator/src/api/security/auth.py — 인증
- IM Module/auto-im-generator/src/api/security/api_keys.py — API 키 관리
- IM Module/auto-im-generator/src/api/middleware/ — 미들웨어

### 환경설정
- .env.example — 개발용 시크릿 기본값
- .env.production.example — 프로덕션 시크릿 목록

## 점검 관점

1. **인증 아키텍처**
   - 3개 백엔드의 JWT 시크릿이 동일한지, 분리되어야 하는지
   - 토큰 리프레시 메커니즘: FDD만 /auth/refresh 제공 → KIIS/IM은?
   - 토큰 블랙리스트(revocation) 구현: 메모리? Redis? DB? 재시작 시 유지?
   - 토큰 만료 시간 설정: access token / refresh token 각각
   - API 키 인증 (IM): 키가 DB에 평문 저장되는지, 해싱되는지

2. **LLM 프롬프트 인젝션**
   - FDD `app/services/llm/client.py` — 시스템 프롬프트와 사용자 데이터 결합 방식
   - FDD `app/agents/guardrails.py` — LLM 출력 검증 로직의 우회 가능성
   - IM 문서 생성 — 사용자 입력(project_name, industry)이 LLM 프롬프트에 삽입되는지
   - 프롬프트에 사용자 제어 가능한 필드가 직접 삽입되면 jailbreak 위험

3. **입력 검증**
   - FDD `app/api/deals.py:87-101` — setattr() 취약점 수정 여부
   - KIIS `app/services/search_service.py:56` — ES wildcard 필드 사용
   - 파일 업로드: 확장자 검증, 파일 크기 제한, MIME 타입 확인
   - SQL 인젝션: SQLAlchemy ORM 사용하더라도 raw query 있는지
   - Path traversal: VDR, 파일 다운로드 경로에 `../` 주입 가능성

4. **CORS & 네트워크**
   - 3개 백엔드의 CORS 설정 비교 (origins, methods, headers)
   - nginx prod.conf의 보안 헤더: HSTS, CSP, X-Frame-Options
   - 내부 서비스 간 통신: Docker 네트워크 내 인증 여부

5. **시크릿 관리**
   - .env 파일이 .gitignore에 포함되는지
   - .env.example에 실제 시크릿이 남아있지 않은지
   - Docker 환경변수 전달 시 시크릿 노출 경로
   - Sentry DSN, API 키 등이 프론트엔드 번들에 포함되는지

6. **데이터 보호**
   - 민감 데이터(재무 정보, 기업 데이터) 암호화 at rest/in transit
   - 로그에 민감 정보(토큰, 비밀번호, 재무 수치) 기록 여부
   - FDD masking engine: PII 마스킹 정확성
   - 삭제된 데이터의 완전 제거 여부 (soft delete → 실제 데이터 남아있음)

## 출력 형식

각 이슈:
- **백엔드**: FDD / KIIS / IM / 전체
- **심각도**: Critical / High / Medium
- **카테고리**: 인증 | 인가 | 입력검증 | 데이터보호 | 설정 | LLM보안
- **문제**: 구체적 설명 + 공격 시나리오
- **수정안**: 코드 변경 제안

리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 8: 백엔드 아키텍처 심층 리뷰

```
3개 백엔드의 아키텍처와 비즈니스 로직을 심층 리뷰해줘.
기존 리뷰는 FE-BE 타입 비교 관점이었고, 이번에는 백엔드 자체의
DB 설계, 서비스 레이어, 외부 API 연동, 비동기 처리에 집중해.

## 리뷰 대상

### FDD — 계산 엔진 & 데이터 무결성
- Auto FDD/backend/app/services/qoe/qoe_service.py — QoE 계산 서비스
- Auto FDD/backend/app/engines/qoe_engine.py — QoE 엔진
- Auto FDD/backend/app/services/nwc/ — NWC 서비스
- Auto FDD/backend/app/engines/nwc_engine.py — NWC 엔진
- Auto FDD/backend/app/services/debt/ — Debt 서비스
- Auto FDD/backend/app/engines/debt_engine.py — Debt 엔진
- Auto FDD/backend/app/engines/delta_engine.py — 변경 감지
- Auto FDD/backend/app/services/consolidation/ — 연결 재무제표 통합
- Auto FDD/backend/app/database.py — DB 연결 설정
- Auto FDD/backend/app/models/ — ORM 모델 전체
- Auto FDD/backend/alembic/versions/ — 마이그레이션 히스토리

### FDD — Job 오케스트레이션
- Auto FDD/backend/app/services/jobs/orchestrator.py — 작업 상태 머신
- Auto FDD/backend/app/services/report/ — 리포트 생성 파이프라인
- Auto FDD/backend/app/services/narrative/ — 내러티브 생성

### KIIS — 외부 API 연동 & 검색
- KIIS/app/services/dart_service.py — DART API 통합
- KIIS/app/services/kofia_service.py — KOFIA 데이터
- KIIS/app/services/search_service.py — ElasticSearch 검색
- KIIS/app/core/elasticsearch.py — ES 클라이언트 설정
- KIIS/app/core/redis.py — Redis 클라이언트
- KIIS/app/core/database.py — DB 풀 설정
- KIIS/app/tasks/scheduler.py — APScheduler 작업
- KIIS/app/tasks/dart_sync.py — DART 동기화
- KIIS/app/services/reputation_service.py — 평판 점수 (이중 커밋 이슈)

### IM — 문서 생성 파이프라인
- IM Module/auto-im-generator/src/api/tasks/generate_im.py — Celery 파이프라인
- IM Module/auto-im-generator/src/api/tasks/fetch_company.py — 기업 데이터 수집
- IM Module/auto-im-generator/src/api/tasks/narrative.py — 내러티브 생성 태스크
- IM Module/auto-im-generator/src/api/services/document_service.py — 문서 CRUD
- IM Module/auto-im-generator/src/api/db/session.py — 비동기 DB 세션
- IM Module/auto-im-generator/src/data_ingestor/pipeline.py — 데이터 인제스트
- IM Module/auto-im-generator/src/api/services/webhook_service.py — 웹훅

## 점검 관점

1. **DB 설계 & 트랜잭션**
   - FDD: FK 인덱스 추가 여부 (기존 이슈 #2.2)
   - FDD: 동시 계산 요청 Race Condition (기존 이슈 #2.4) — SELECT FOR UPDATE 적용 여부
   - KIIS: get_db() 자동 커밋 제거 여부 (기존 이슈 #2.2)
   - KIIS: reputation_service 이중 커밋 수정 여부 (기존 이슈 #2.3)
   - FDD database.py: pool_size, pool_recycle, pool_pre_ping 설정 여부
   - KIIS database.py: pool_max_overflow=20 적절성, pool_timeout 설정
   - IM session.py: 비동기 세션 에러 복구 패턴

2. **계산 엔진 정확성 (FDD)**
   - Decimal 연산: 명시적 반올림 모드 (ROUND_HALF_UP 등) 사용 여부
   - QoE 엔진: N+1 쿼리 (기존 이슈 #2.1) — _get_line_items_map() 수정 여부
   - NWC 엔진: classification별 정렬이 display_order와 충돌하는 경우 처리
   - Debt 엔진: 통화 단위 변환 정확성
   - Industry context 주입: 유효하지 않은 industry_id 전달 시 동작
   - Delta engine: 변경 감지 시 부동소수점 비교 정밀도

3. **비동기 처리 & 작업 큐**
   - FDD Job Orchestrator: 데드락 감지, 타임아웃 강제, 재시도 전략
   - KIIS Scheduler: 개별 작업 에러 핸들링 (기존 이슈 #2.10)
   - IM Celery 파이프라인: 5단계 chord에서 중간 단계 실패 시 복구
   - IM Celery: 직렬화 방식 (pickle → JSON 권장), 워커 동시성 설정
   - IM fetch_company 태스크: 동일 corp_code 중복 요청 방지

4. **외부 API 연동 (KIIS)**
   - DART API: XML/ZIP 파싱 에러 핸들링, 응답 스키마 검증
   - DART sync: 중복 공시 감지, 증분 동기화 전략
   - KOFIA: 펀드 데이터 불완전 시 graceful degradation
   - Rate limiting: 토큰 버킷 구현 정확성, 버스트 트래픽 대응
   - HTTP 클라이언트: 타임아웃, 재시도, 지수 백오프

5. **ElasticSearch (KIIS)**
   - 인덱스 매핑 정의: 필드 타입, analyzer 설정
   - Nori tokenizer: 불용어, 동의어, 한국어 형태소 분석 설정
   - Reindex: 전체 테이블 로드 (기존 이슈 #2.6) — 배치 처리 적용 여부
   - 와일드카드 필드 검색 (기존 이슈 #2.4) — 명시적 필드 지정 여부

6. **에러 처리 & 로깅**
   - FDD: Unhandled Exception 로깅 (기존 이슈 #2.7) — logger.error 추가 여부
   - FDD: 에러 응답 형식 통일 (기존 이슈 #2.3) — FDDError 일관 사용 여부
   - KIIS: 스케줄러 작업 내부 try/except 보장
   - IM: Celery 태스크 실패 시 상태 전이 (FAILED 상태로 정확히 마킹)
   - 구조화된 로깅(JSON 포맷) 사용 여부
   - 분산 트레이싱(OpenTelemetry) 적용 여부

## 출력 형식

각 이슈:
- **백엔드**: FDD / KIIS / IM
- **심각도**: Critical / High / Medium / Low
- **카테고리**: DB설계 | 트랜잭션 | 계산정확성 | 비동기처리 | 외부API | 검색 | 에러처리
- **파일**: 경로:라인번호
- **문제**: 구체적 설명 + 잠재적 영향
- **수정안**: 코드 변경 제안

기존 이슈 참조:
- docs/20260213_0833_FDD_Code_Review.md
- docs/20260213_0836_KIIS_Code_Review.md
기존 이슈는 수정 여부만 확인하고, 새로운 이슈를 중심으로 보고해줘.
리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 9: FE 유닛 테스트 품질 리뷰

```
프론트엔드 기존 유닛 테스트의 품질을 리뷰하고,
테스트 커버리지 확대를 위한 구체적 테스트 케이스를 제안해줘.

## 현황

### 기존 테스트 (11 파일, ~85 케이스)
- src/hooks/__tests__/useAuth.test.tsx — 11 cases
- src/lib/__tests__/format.test.ts — 36 cases
- src/modules/fdd/hooks/__tests__/useDeals.test.tsx — 8 cases
- src/modules/fdd/pages/__tests__/DealListPage.test.tsx — 5 cases
- src/modules/kiis/hooks/__tests__/useCompanies.test.tsx — 4+ cases
- src/modules/kiis/hooks/__tests__/useSearch.test.tsx
- src/modules/kiis/hooks/__tests__/useWatchlist.test.tsx
- src/modules/im/hooks/__tests__/useDocuments.test.tsx — 8 cases
- src/modules/im/hooks/__tests__/useCompanies.test.tsx
- src/modules/im/components/__tests__/ImErrorBoundary.test.tsx — 3+ cases
- src/pages/__tests__/DashboardPage.test.tsx — 7+ cases

### 테스트 인프라
- src/test/setup.ts — Vitest/jsdom 전역 설정, MSW 라이프사이클
- src/test/test-utils.tsx — renderWithProviders() (QueryClient + Router + Auth)
- src/test/mocks/server.ts — MSW 서버 인스턴스
- src/test/mocks/handlers.ts — API 핸들러 (FDD, KIIS, IM)
- src/test/mocks/data.ts — Mock 데이터

### 미테스트 (우선순위순)
**Hooks (21개 미테스트):**
- FDD: useQoE, useNWC, useDebt, useUploads, useMapping, useIssues, useVdr, useReportVersions, useDefinitions
- KIIS: useNews, useSanctions, useFunds, useReits, useManagers, usePortfolio, useDeals, useDisclosures, useAnalysis
- Shared: useGlobalSearch, useNotifications, useAnalytics

**Pages (29개 미테스트):**
- FDD: QoEPage, NWCPage, NetDebtPage, MappingPage, UploadPage, DefinitionPage, ReportPage, VdrPage, WorkflowOverviewPage, IssuesPage, DealSetupWizardPage
- KIIS: 전체 18개 페이지 (0개 테스트)
- IM: DocumentListPage, CreateDocumentPage, DocumentDetailPage, TemplatesPage

**UI 컴포넌트 (전체 미테스트):**
- Badge, Button, Card, DataTable, Input, Modal, Select, KpiCard, EmptyState, Skeleton, Spinner, Pagination, Breadcrumbs, LiveRegion, SectionHeader

## 리뷰 & 작업

### Part 1: 기존 테스트 품질 리뷰

아래 파일들을 읽고 품질을 평가해줘:

1. **src/test/mocks/handlers.ts**
   - MSW 핸들러가 실제 백엔드 응답 구조와 일치하는지
   - FDD 기존 이슈 #8.4: POST /api/fdd/deals에 payload 검증 없음
   - FDD 기존 이슈 #8.5: mockDealSummary 수치 필드가 string 타입
   - 에러 응답(401, 404, 500) 시뮬레이션 존재 여부

2. **src/test/mocks/data.ts**
   - 타입 안전성: mock 객체가 TypeScript 타입과 일치하는지
   - 엣지 케이스: null/undefined/빈 배열 데이터 커버리지
   - 날짜 형식: ISO-8601 문자열 사용 여부

3. **src/test/test-utils.tsx**
   - renderWithProviders: AuthContext 커스터마이징 유연성
   - QueryClient 설정: retry=false, cacheTime 등 테스트 적합성

4. **각 테스트 파일**
   - 비동기 쿼리 대기: waitFor / findBy 패턴 올바른 사용
   - cleanup: 각 테스트 간 상태 격리
   - assertion 품질: 의미 있는 검증인지, 단순 스냅샷인지
   - 에러 시나리오 테스트 존재 여부
   - mutation 테스트: onSuccess 캐시 무효화 검증 여부

### Part 2: 우선순위 높은 테스트 케이스 제안

아래 기준으로 추가해야 할 테스트 케이스를 구체적으로 제안해줘:

1. **useGlobalSearch** (Platform M2 이슈 관련)
   - IM fallback이 전체 문서 로드하는 경우 테스트
   - 디바운스 동작 테스트
   - 빈 검색어 처리

2. **useNotifications** (Platform M4, M8 이슈 관련)
   - endpointAvailable 상태 변경 테스트
   - 404/405 에러 시 graceful degradation

3. **useQoE / useNWC / useDebt** (FDD 핵심 훅)
   - calculate mutation 호출 + 캐시 무효화
   - approve workflow
   - 에러 응답 처리

4. **CreateDocumentPage** (IM 핵심 플로우)
   - corp_code 검증 (숫자 8자리)
   - 기업 검색 → 선택 → industry 자동 매핑
   - CUSTOM 모드 섹션 선택
   - 중복 제출 방지

## 출력 형식

### Part 1 — 기존 테스트 품질
각 이슈:
- **파일**: 테스트 파일 경로:라인
- **심각도**: Critical / Major / Minor
- **카테고리**: 타입불일치 | 검증부족 | 패턴오류 | 커버리지갭
- **문제**: 설명
- **수정안**: 코드 변경 또는 추가 테스트 케이스

### Part 2 — 추가 테스트 제안
훅/페이지별로:
- **대상**: 훅/페이지/컴포넌트 이름
- **우선순위**: P0 / P1 / P2
- **테스트 케이스 목록**: describe/it 형태로 구체적 나열
- **MSW 핸들러 추가 필요 여부**

리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 10: E2E 테스트 품질 리뷰

```
Playwright E2E 테스트의 품질을 리뷰하고, 커버리지 갭을 분석해줘.

## 현황

### 테스트 구조
- 프로젝트: setup, chromium, firefox, chromium-mocked
- chromium-mocked: *-deep.spec.ts 파일만 실행, MSW 서비스워커 차단
- API 모킹: page.route()로 백엔드 응답 인터셉트
- Auth: localStorage에 autofdd_access_token 직접 설정

### 기존 Deep Tests (10 파일)
- e2e/tests/browser-health-deep.spec.ts
- e2e/tests/dashboard-deep.spec.ts
- e2e/tests/search-deep.spec.ts
- e2e/tests/analytics-deep.spec.ts
- e2e/tests/fdd-deep.spec.ts
- e2e/tests/kiis-deep.spec.ts
- e2e/tests/kiis-dashboard-deep.spec.ts
- e2e/tests/kiis-news-deep.spec.ts
- e2e/tests/kiis-watchlist-deep.spec.ts
- e2e/tests/im-deep.spec.ts

### Fixtures & Page Objects
- e2e/fixtures/test-base.ts, api-mocks.ts, console-monitor.ts
- e2e/pages/ — 11개 page object 파일

### 기존 이슈
- FDD #8.9: DOM 구조 의존적 locator 사용 → 불안정
- FDD #8.3: E2E 워크플로우 테스트 부재 (딜 생성 → 리포트)
- KIIS #5: DashboardPage, NewsListPage, WatchlistPage 등 미구현
- MEMORY.md: analytics 기본 timeRange "30d" → mock 날짜 범위 주의
- MEMORY.md: serviceWorkers: "block" 필수 (MSW 차단)

## 리뷰 대상

### Part 1: 테스트 인프라 리뷰

1. **playwright.config.ts**
   - 프로젝트 설정 적절성
   - 타임아웃, 재시도, 워커 설정
   - baseURL과 webServer 설정

2. **e2e/fixtures/api-mocks.ts**
   - Mock 데이터가 백엔드 실제 응답과 일치하는지
   - API 경로 패턴 (/api/fdd/*, /api/kiis/*, /api/im/*) 정확성
   - 에러 응답 모킹 존재 여부

3. **e2e/fixtures/test-base.ts**
   - 인증 토큰 설정 방식
   - 테스트 간 격리

4. **e2e/fixtures/console-monitor.ts**
   - 콘솔 에러 감지 로직

### Part 2: 개별 테스트 품질 리뷰

각 deep spec 파일을 읽고 평가:
- Locator 안정성: getByRole, getByText vs CSS selector/XPath
- Assertion 의미: 실제 비즈니스 로직을 검증하는지
- API mock 정확성: 응답 구조가 백엔드 스키마와 일치하는지
- 날짜 범위: analytics "30d" 기본값 고려
- 에러 시나리오: API 실패 시 UI 동작 테스트 존재 여부
- 경쟁 조건: waitForResponse, waitForSelector 적절한 사용

### Part 3: 커버리지 갭 분석

모듈별 E2E 커버리지:

**FDD (5개 케이스만):**
- ✅ Deal 목록 (fdd-deep.spec.ts)
- ❌ Deal 생성 위자드
- ❌ 파일 업로드
- ❌ QoE/NWC/Debt 계산
- ❌ 리포트 생성/다운로드
- ❌ VDR 폴더 관리

**KIIS (4개 + α):**
- ✅ Company 테이블 (kiis-deep.spec.ts)
- ✅ Dashboard KPI (kiis-dashboard-deep.spec.ts)
- ✅ News 목록 (kiis-news-deep.spec.ts)
- ✅ Watchlist (kiis-watchlist-deep.spec.ts)
- ❌ Fund/REIT 상세
- ❌ Manager 프로필
- ❌ Entity Resolution
- ❌ Sanction 검색

**IM:**
- ✅ 문서 목록 (im-deep.spec.ts)
- ❌ 문서 생성 플로우
- ❌ 문서 상세 + 진행률 폴링
- ❌ 다운로드

## 출력 형식

### Part 1-2: 테스트 품질
- **파일**: spec 파일 경로:라인
- **심각도**: Critical / Major / Minor
- **카테고리**: 불안정 | Mock불일치 | 검증부족 | 패턴오류
- **문제**: 설명
- **수정안**: 코드 변경 제안

### Part 3: 추가 E2E 제안
모듈별:
- **시나리오**: 사용자 흐름 설명
- **우선순위**: P0 / P1 / P2
- **Mock 필요 API**: 어떤 엔드포인트를 모킹해야 하는지
- **검증 포인트**: 무엇을 assert해야 하는지

리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 11: 인프라/배포 리뷰

```
Docker, nginx, CI/CD, 환경설정을 리뷰해줘.
이 영역은 기존 리뷰에서 전혀 다뤄지지 않았어.

## 리뷰 대상

### Docker Compose
- docker-compose.yml — 개발 환경 (14 서비스)
- docker-compose.prod.yml — 프로덕션 오버라이드
- docker-compose.ssl.yml — SSL/HTTPS 오버레이

### Dockerfile
- amic-platform/Dockerfile — 프로덕션 멀티스테이지 빌드 (Node → nginx)
- amic-platform/Dockerfile.dev — 개발용 (hot reload)

### Nginx
- nginx/dev.conf — 개발 리버스 프록시
- nginx/prod.conf — 프로덕션 HTTPS + 보안 헤더
- nginx/prod-nossl.conf — HTTP 전용 프로덕션
- amic-platform/nginx.conf — SPA 라우팅 (컨테이너 내부)

### CI/CD
- .github/workflows/ci.yml — 빌드/테스트 파이프라인
- .github/workflows/deploy.yml — 배포 워크플로우

### 환경 설정
- .env.example — 개발 환경 변수
- .env.production.example — 프로덕션 환경 변수
- amic-platform/.dockerignore

## 점검 관점

1. **Docker Compose 설계**
   - 서비스 간 의존성 순서: depends_on + healthcheck 설정 적절성
   - 볼륨 마운트: 데이터 영속성, 개발-프로덕션 차이
   - 네트워크: amic-network 브릿지 내 서비스 접근 제어
   - 리소스 제한(prod): 메모리/CPU limits 적절성
   - DB 초기화: PostgreSQL 초기 스키마/마이그레이션 자동화
   - Redis 설정: AOF 영속성, maxmemory-policy (LRU vs noeviction)
   - Celery: concurrency, time limits, 데드 레터 큐
   - ElasticSearch: 메모리 설정, 인덱스 자동 생성

2. **Nginx 설정**
   - API 프록시: /api/{mod}/* → /api/v1/* 리라이팅 정확성
   - WebSocket 지원: Upgrade 헤더 처리 (HMR용)
   - 파일 업로드: client_max_body_size 100M 적절성
   - 타임아웃: 300s proxy_read_timeout (LLM 호출 고려)
   - 보안 헤더(prod): HSTS, CSP, X-Frame-Options, X-Content-Type-Options
   - CSP 정책: Sentry 도메인 허용이 올바른지, 나머지 제한 적절한지
   - gzip: 압축 대상 MIME 타입, 최소 크기(1000 bytes) 적절성
   - SSL: TLS 1.2/1.3, cipher suite, session 설정
   - Health check: /health/{fdd,kiis,im} 내부 전용(127.0.0.1) 제한 여부
   - 정적 파일 캐싱: 30일 + immutable — 캐시 무효화 전략 (파일명 해시)

3. **CI/CD 파이프라인**
   - ci.yml 단계: lint → typecheck → test + build(병렬) → e2e
   - 캐싱: npm cache 효과, node_modules 캐싱 여부
   - Sentry 소스맵: SENTRY_AUTH_TOKEN이 GitHub Secrets에 있는지
   - E2E: chromium-mocked만 CI에서 실행 — 충분한지
   - 아티팩트: coverage-report(14d), dist(7d) — 보존 기간 적절성
   - deploy.yml: SSH 키 관리, 무중단 배포 전략 (rolling vs blue-green)
   - deploy.yml: health check 실패 시 롤백 전략 존재 여부
   - 동시성 설정: CI cancel-in-progress vs Deploy no-cancel

4. **환경 변수**
   - 필수 변수 누락 시 시작 실패하는지 (validation)
   - 개발/프로덕션 기본값 차이: 보안 시크릿이 dev 기본값으로 폴백 가능한지
   - CORS_ORIGINS: 프로덕션에서 와일드카드(*) 사용 여부
   - DB 비밀번호: 복잡도 요구사항
   - Sentry: DSN이 프론트엔드 번들에 포함되는 건 정상이지만, AUTH_TOKEN은 빌드 타임만

5. **보안**
   - Docker 이미지 버전: node:22-alpine, nginx:1.25-alpine 최신 패치 여부
   - 컨테이너 사용자: root 실행 여부 (non-root 권장)
   - .dockerignore: .env, node_modules, .git 제외 확인
   - 빌드 아규먼트로 시크릿 노출 여부
   - 프로덕션 빌드에 devDependencies 포함 여부

## 출력 형식

각 이슈:
- **파일**: 경로:라인번호
- **심각도**: Critical / High / Medium / Low
- **카테고리**: Docker | Nginx | CI/CD | 환경설정 | 보안
- **문제**: 구체적 설명
- **수정안**: 설정 변경 제안

리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 12: 성능/번들 최적화 리뷰

```
프론트엔드 성능과 번들 최적화 상태를 리뷰해줘.

## 리뷰 대상

### 빌드 설정
- amic-platform/vite.config.ts
- amic-platform/tailwind.config.js
- amic-platform/tsconfig.app.json
- amic-platform/package.json (dependencies)

### 라우팅 & 코드 스플리팅
- src/main.tsx — 앱 진입점
- src/modules/fdd/FddRoutes.tsx
- src/modules/kiis/KiisRoutes.tsx — ⚠️ 18개 페이지 정적 import
- src/modules/im/ImRoutes.tsx

### 성능 관련 기존 이슈
- FDD #5.1: IssuesPage 필터 객체 매 렌더 재생성 → useMemo 필요
- FDD #5.3: Optimistic Updates 미적용 (느린 네트워크 UX)
- KIIS #3.6: CompanyDetailPage 5개 독립 쿼리 → UI 깜빡임
- KIIS #3.12: DataTable 컬럼 정의 미메모화
- KIIS #3.13: KiisRoutes 18개 정적 import → 번들 크기
- Platform C2: cn() tailwind-merge 미사용

### 무거운 라이브러리
- recharts — 차트 (FDD + KIIS + Analytics)
- @tanstack/react-query — 서버 상태 관리
- axios — HTTP 클라이언트
- sonner — 토스트

## 점검 관점

1. **번들 분석**
   - `npm run build` 실행 후 dist/ 크기 확인
   - vite build 로그에서 청크별 크기 확인
   - 모듈별 코드 스플리팅 정상 동작 여부:
     - FDD 페이지 → 별도 청크?
     - KIIS 18개 페이지 → 단일 청크? (정적 import면 전부 포함)
     - IM 페이지 → 별도 청크?
   - 공유 라이브러리(recharts) 중복 번들링 여부
   - React Query devtools 프로덕션 빌드에서 제외 여부
   - tree shaking: 미사용 export가 번들에 포함되는지

2. **런타임 렌더링 성능**
   - 불필요한 리렌더링 원인:
     - 인라인 객체/배열 props (매 렌더 새 참조)
     - useMemo/useCallback 적용 필요한 곳
     - Context 값 변경 시 전체 트리 리렌더 여부
   - 무거운 컴포넌트:
     - DataTable: 대량 데이터(1000+행) 가상화 여부
     - 차트 컴포넌트: SVG 렌더링 최적화
     - CompanyDetailPage: 5개 쿼리 워터폴
   - React Query 설정:
     - staleTime: 30초 적절한지 (너무 짧으면 불필요한 refetch)
     - refetchOnWindowFocus: 기본 true → 자주 탭 전환 시 과도한 요청

3. **네트워크 최적화**
   - API 호출 패턴: 동일 데이터 중복 요청 여부
   - 프리페칭: 다음 페이지 데이터 미리 로드 (목록 → 상세)
   - 이미지/정적 자산: lazy loading, WebP 변환
   - gzip/brotli: nginx 압축 대상 MIME 타입
   - HTTP 캐싱 헤더: Cache-Control, ETag 설정

4. **CSS 최적화**
   - Tailwind purge: 미사용 클래스 제거 동작 확인
   - 커스텀 CSS 크기: tailwind.config.js에 정의된 확장 항목 수
   - 동적 클래스명: cn() 내부의 조건부 클래스가 purge에서 제외되지 않는지
   - @font-face: 폰트 로딩 전략 (swap, block, optional)
   - 폰트 파일 크기: Space Grotesk, SUITE Variable, IBM Plex Mono

5. **Vite 최적화**
   - 소스맵: 프로덕션 빌드에서 활성화 여부 (Sentry용이면 hidden-source-map 권장)
   - 청크 분할 전략: manualChunks 설정 여부
   - 의존성 최적화: optimizeDeps 설정
   - CSS 코드 분할: cssCodeSplit 기본값 확인

## 실행 명령

아래 명령어를 실행하여 실제 번들 상태를 확인해줘:
1. `cd amic-platform && npm run build` — 빌드 크기 확인
2. `npx vite-bundle-visualizer` (설치 필요 시) — 번들 시각화

## 출력 형식

각 이슈:
- **파일**: 경로:라인번호
- **심각도**: Critical / Major / Minor
- **카테고리**: 번들 | 렌더링 | 네트워크 | CSS | Vite설정
- **문제**: 구체적 설명 + 수치 (번들 크기, 리렌더 횟수 등)
- **수정안**: 코드 변경 제안

리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 13: 누적 수정사항 검증

```
Session 2-3에서 적용된 코드 수정사항들의 일관성을 검증하고,
수정으로 인한 새로운 이슈가 없는지 확인해줘.

## 검증 대상

### FDD Session 3 수정 (docs/20260213_1228_FDD_Code_Review_Session3.md)

#### Batch 1: approved_by 통일
- src/modules/fdd/pages/DefinitionPage.tsx — `approved_by: "unknown"` 확인
- src/modules/fdd/pages/QoEPage.tsx — `approved_by: "unknown"` 확인
- src/modules/fdd/pages/NetDebtPage.tsx — `approved_by: "unknown"` 확인
- src/modules/fdd/pages/MappingPage.tsx — 2곳 `approved_by: "unknown"` 확인
- src/modules/fdd/pages/IssuesPage.tsx — `resolved_by: user?.email ?? "unknown"` 확인
→ **검증**: 5개 파일 모두 동일한 fallback 패턴인지, useAuth import 있는지

#### Batch 2: Query Key 접두사
- src/modules/fdd/hooks/useDeals.ts — `["fdd", "deals"]`
- src/modules/fdd/hooks/useQoE.ts — `["fdd", "qoe"]`
- src/modules/fdd/hooks/useNWC.ts — `["fdd", "nwc"]`
- src/modules/fdd/hooks/useDebt.ts — `["fdd", "debt"]`
- src/modules/fdd/hooks/useMapping.ts — `["fdd", "mappings"]`, `["fdd", "tie-out"]`, `["fdd", "standard-items"]`
- src/modules/fdd/hooks/useIssues.ts — `["fdd", "issues"]`
- src/modules/fdd/hooks/useUploads.ts — `["fdd", "uploads"]`
- src/modules/fdd/hooks/useReportVersions.ts — `["fdd", "report-versions"]`
- src/modules/fdd/hooks/useVdr.ts — `["fdd", "vdr-status"]`
- src/modules/fdd/hooks/__tests__/useDeals.test.tsx — 테스트의 queryKey도 업데이트
→ **검증**: 모든 invalidateQueries 호출도 새 키를 사용하는지

#### Batch 3: 기타 수정
- src/modules/fdd/hooks/useMapping.ts — useApproveMapping에 tie-out invalidation 추가
- src/modules/fdd/hooks/useMapping.ts — useStandardLineItems에 staleTime 1시간 추가
- src/modules/fdd/hooks/useDefinitions.ts — 신규 파일 (DefinitionPage에서 추출)
- src/modules/fdd/pages/QoEPage.tsx, NWCPage.tsx, NetDebtPage.tsx — 빈 ID early return
- src/modules/fdd/pages/NWCPage.tsx — classOrder 상수화
- 3개 파일 에러 메시지 영어 통일
- src/lib/format.ts — ZERO_DECIMAL_CURRENCIES Set (KRW, JPY, VND, IDR, HUF)

### FDD Session 2 확인 수정 (미수정 deferred 포함)

Session 2에서 지적되었으나 Session 3에서 "confirmed fixed"로 처리된 항목:
- M-7: KRW 하드코딩 → `deal?.base_currency ?? "KRW"` (4 pages)
- C-1: NWC_METHOD_OPTIONS → BE PegMethod 일치
- M-1: ReportVersionCard → `/api/fdd/deals/...`
- M-3: useFinalizeReportVersion → `{ version, notes? }` body
- M-5: ReportPage → DOCX format 추가
→ **검증**: 이 수정들이 실제 코드에 반영되어 있는지 재확인

### Session 2 Deferred (BE 협의 필요)
- m-5: debt_like/cash_like UI — BE 스키마 확정 대기
- m-6/m-7: Snapshot Select 드롭다운 — BE API 필요
- m-2: useUpdateNWCLineItem 빈 nwcId 방어
→ **검증**: 이 항목들이 여전히 미수정인지 확인

### Platform 수정 확인
기존 Platform 이슈들의 코드 반영 여부:
- C1: logout 시 queryClient.clear() — src/hooks/useAuth.ts
- C2: cn()에 tailwind-merge — src/lib/cn.ts
- M13: token-storage.ts 분리 — src/lib/token-storage.ts 존재 여부
- M9: auth-events.ts — src/lib/auth-events.ts 존재 여부

## 실행 명령

아래 명령어로 빌드/테스트 정상 여부 확인:
1. `cd amic-platform && npx tsc --noEmit` — TypeScript 컴파일 에러
2. `cd amic-platform && npm run test` — 유닛 테스트 전체 통과
3. `cd amic-platform && npm run build` — Vite 빌드 성공
4. `cd amic-platform && npm run lint` — ESLint 경고 0

## 출력 형식

| 항목 | 파일 | 기대 상태 | 실제 상태 | 비고 |
|------|------|----------|----------|------|
| 예시 | useDeals.ts | queryKey ["fdd","deals"] | ✅ 일치 | invalidate도 일치 |
| 예시 | useAuth.ts | queryClient.clear() | ❌ 미적용 | C1 미수정 |

수정이 불완전하거나 새로운 이슈가 발견되면:
- **원본 이슈**: Session/ID
- **현재 상태**: 수정됨 / 부분수정 / 미수정 / 새 이슈 유발
- **문제**: 구체적 설명
- **수정안**: 추가 변경 필요 사항

리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 사용 가이드

| 세션 | 범위 | 난이도 | 선행 조건 |
|------|------|--------|----------|
| 6 | 크로스 모듈 통합 | 중 | 세션 1-4 문서 필수 |
| 7 | 백엔드 보안 통합 | 상 | 독립 실행 가능 |
| 8 | 백엔드 아키텍처 심층 | 상 | 독립 실행 가능 |
| 9 | FE 유닛 테스트 품질 | 중 | 독립 실행 가능 |
| 10 | E2E 테스트 품질 | 중 | 독립 실행 가능 |
| 11 | 인프라/배포 | 중 | 독립 실행 가능 |
| 12 | 성능/번들 | 중 | 빌드 실행 필요 |
| 13 | 누적 수정 검증 | 하 | 세션 2-3 문서 필수 |

### 권장 실행 순서

1. **세션 13** (누적 검증) — 기존 수정 상태 파악
2. **세션 7** (보안) — 가장 높은 리스크
3. **세션 8** (백엔드 아키텍처) — DB/계산 엔진 정확성
4. **세션 6** (크로스 모듈) — 모듈 간 통합 이슈
5. **세션 11** (인프라) — 배포 안정성
6. **세션 9** (FE 테스트) → **세션 10** (E2E 테스트) — 테스트 품질
7. **세션 12** (성능) — 최적화
