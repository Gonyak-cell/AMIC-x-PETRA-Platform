# 코드 리뷰 리포트: FE 모듈 레이어 — Chunk 7

- 라운드: 1
- 모듈: Chunk 7 FE 모듈 레이어
- 배치: 1~4 통합
- 시작: 2026-03-05 03:50
- 종료: 2026-03-05 04:01

## 배치 1: tsc + eslint

- tsc --noEmit: 0건 (Chunk 6과 공유 실행)
- eslint --max-warnings 0: 0건 (Chunk 6과 공유 실행)
- 코드 수정: 0건

## 배치 2~4: 통합 리뷰 (읽기 전용)

22개 파일 상세 읽기 + 390개 파일 패턴 스캔.

### 모듈별 통계

| 모듈 | 파일 수 | 총 줄수 | 최대 파일 (줄) |
|------|------:|-------:|----------------|
| MA | 167 | ~30,029 | TransactionWorkspacePage.tsx (1,371) |
| KIIS | 92 | ~12,524 | gpMockData.ts (1,392) |
| FDD | 51 | ~8,411 | ReportPage.tsx (679) |
| Docs | 48 | ~11,200 | AnalysisReviewPanel.tsx (1,102) |
| IM | 28 | ~4,800 | CreateDocumentPage.tsx (699) |
| VDR | 4 | ~226 | VdrOverviewPage.tsx (185) |
| 합계 | 390 | ~68,430 | |

### 발견된 이슈

| # | 심각도 | 관점 | 모듈 | 파일 | 이슈 |
|---|--------|------|------|-----|-----|
| 1 | Critical | 아키텍처 | MA | TransactionWorkspacePage.tsx (1,371줄) | God 컴포넌트 — ~20개 훅, 인라인 편집, 파이프라인 플로우, 탭 관리 모두 단일 파일 |
| 2 | High | 아키텍처 | MA→Docs | TransactionWorkspacePage.tsx:65 | useLegalDocuments 크로스 모듈 import |
| 3 | High | 아키텍처 | MA→Docs | DDReportSection, QualityTab, ContractsTab | MA→Docs 9개 크로스 모듈 import |
| 4 | High | 아키텍처 | MA→FDD | FDDReportsTab.tsx:14-15 | FDD hooks/types 직접 import |
| 5 | High | 아키텍처 | Docs→MA | StudioHomePage, CreateLDDReportPage 등 | Docs→MA 5개 import — MA↔Docs 양방향 의존성 |
| 6 | High | 아키텍처 | Docs→FDD | useFDDDocuments.ts, DDReportListPage | Docs→FDD 타입 import |
| 7 | High | 아키텍처 | IM→MA | CreateFromVdrPage, useVdrDocumentSelector | IM→MA hooks/types import |
| 8 | High | 아키텍처 | VDR→MA | VdrOverviewPage.tsx:20 | PHASE_CONFIG import |
| 9 | High | 보안 | Docs | AnalysisReviewPanel.tsx:713 | 인라인 HTML 삽입 — 자체 sanitizer (DOMPurify 미사용) |
| 10 | Medium | 성능 | KIIS | GPListPage.tsx:254-261 | Debounce 버그: useCallback 내 setTimeout cleanup 미호출 |
| 11 | Medium | 타입 안전성 | FDD | ReportPage.tsx:441,443,448 | score as number 3회 — 런타임 검증 없음 |
| 12 | Medium | 타입 안전성 | Docs | QualityDashboard.tsx:138 | score as number 동일 패턴 |
| 13 | Medium | 타입 안전성 | 전체 | 149건 | return data as Type API 캐스트 — 런타임 검증 없음 |
| 14 | Medium | 코드 품질 | FDD | hooks/*.ts (11개) | 31개 console.error — Sentry 미사용 |
| 15 | Medium | UX | MA | 12개 탭/컴포넌트 | 13개 confirm() 네이티브 다이얼로그 |
| 16 | Medium | UX | Docs | 2개 파일 | 2개 confirm() 추가 |
| 17 | Medium | 코드 품질 | 다수 | 5개 파일 | 5개 eslint-disable exhaustive-deps |
| 18 | Medium | 데이터/성능 | KIIS | gpMockData.ts (1,392줄) | 하드코딩 목 데이터 — 번들 + 민감 데이터 |
| 19 | Medium | 성능 | FDD | FddRoutes.tsx:4 | DealListPage eager import |
| 20 | Medium | 성능 | Docs | DocsRoutes.tsx:5-6 | 2개 페이지 eager import |
| 21 | Medium | 성능 | IM | ImRoutes.tsx:5 | DocumentListPage eager import |
| 22 | Medium | 타입 안전성 | Docs | AnalysisReviewPanel.tsx | 15개 e.target.value as Type select 캐스트 |
| 23 | Medium | 타입 안전성 | Docs | LegalParamsForm.tsx:146-147 | API 프로퍼티 런타임 검증 없이 cast |
| 24 | Low | 아키텍처 | KIIS | KiisRoutes.tsx | Error boundary 누락 |
| 25 | Low | 아키텍처 | FDD | FddRoutes.tsx | Error boundary 누락 |
| 26 | Low | 아키텍처 | VDR | VdrRoutes.tsx | Error boundary + catch-all route 누락 |
| 27 | Low | 코드 품질 | KIIS | useGPResearch.ts:21 | TODO: 미완성 API 연동 |
| 28 | Info | 디자인 | VDR | VdrOverviewPage.tsx:71-128 | Tailwind raw 색상 — 시맨틱 토큰 미적용 |

### 크로스 모듈 의존성 맵

| Source | Target | Import 수 |
|--------|--------|--------:|
| MA | Docs | 9 |
| Docs | MA | 5 |
| IM | MA | 4 |
| Docs | FDD | 3 |
| MA | FDD | 2 |
| VDR | MA | 1 |
| KIIS | (없음) | 0 — 완전 격리 |
| FDD | (없음) | 0 — 완전 격리 |

### 패턴 스캔 요약

| 패턴 | 건수 |
|------|------|
| any 타입 | 0 (390 파일) |
| @ts-ignore / @ts-expect-error | 0 |
| 인라인 HTML 삽입 | 1 (sanitized) |
| console.log/error/warn | 37 (FDD: 31) |
| confirm() 네이티브 | 15 (MA: 13) |
| return data as Type | 149 |
| 크로스 모듈 import | 22줄 / 5 쌍 |

### 양호한 패턴

- any 타입 0건 / @ts-ignore 0건 — 390개 파일 ~68,430줄 전체 타입 엄격성
- React Query 일관 패턴 (계층적 쿼리 키, invalidation)
- React.lazy() + Suspense 코드 스플리팅 (일부 예외)
- MA, IM, Docs Error Boundary 구현
- Docs 접근성 우수 (htmlFor/id, aria-*, role=group)
- IM 입력 검증 (regex, 파일 타입/크기 제한)
- KIIS, FDD 완전 모듈 격리
- 디자인 시스템 시맨틱 토큰 일관 사용 (VDR 제외)

## 검증 결과

- tsc --noEmit: 0건
- eslint --max-warnings 0: 0건

## 에러 카운트

| 심각도 | 건수 |
|--------|------|
| Critical | 1건 (God 컴포넌트) |
| High | 8건 (크로스 모듈 7건 + 인라인 HTML 1건) |
| Medium | 14건 |
| Low | 3건 |
| Info | 1건 |
| 합계 | 27건 (코드 수정 0건 — 읽기 전용 관찰) |

## 충족 관점 체크리스트

- [x] 9. 린트/포맷 (tsc 0건, eslint 0건)
- [x] 6. 타입 안전성 (any 0건, unsafe cast 관찰)
- [x] 1. 보안 (인라인 HTML 1건 관찰 — sanitizer 사용)
- [x] 2. 성능 (lazy loading, debounce 버그 관찰)
- [x] 3. 아키텍처 (크로스 모듈 22줄, God 컴포넌트)
- [x] 4. 예외처리 (Error Boundary 3/6 모듈)
- [x] 11. 테스트 (관찰)
- [x] 13. 코드 품질 (console.error 37건, confirm 15건)
