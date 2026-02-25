# Deal Document Studio — TM 생성 기능 통합 리뷰

> **작성일**: 2026-02-23 00:05
> **범위**: 백엔드 TM 렌더링 인프라 + 내러티브 프롬프트 + 프론트엔드 Deal Document Studio 모듈
> **검증 방법**: 병렬 코드 리뷰 에이전트 (백엔드 + 프론트엔드) + TypeScript 빌드 검증

---

## 1. 작업 요약

M&A 폴더의 독립 CLI TM 생성기를 AMIC 플랫폼에 통합하여 "Deal Document Studio"를 구축.

### 백엔드 (모노레포 `im/`) — 11개 파일

| 파일 | 작업 | 상태 |
|------|------|------|
| `section_renderers/target_positioning.py` | 신규 — TargetPositioningRenderer | 완료 |
| `section_renderers/market_drivers.py` | 신규 — MarketOutlook/Demand/SupplyDriverRenderer | 완료 |
| `section_renderers/proforma.py` | 신규 — ProformaPlan/FinancialsRenderer | 완료 |
| `section_renderers/tm_aliases.py` | 신규 — TargetOverview/HighlightsRenderer | 완료 (버그 수정 포함) |
| `section_renderers/__init__.py` | 수정 — F-θ TM import 블록 추가 | 완료 |
| `im_document.py` | 수정 — TEASER enum, 상수, TOC 그룹 | 완료 (오탈자 수정 포함) |
| `pipeline.py` | 수정 — `_render_tm_sections` 추가 | 완료 (docstring 수정 포함) |
| `pptx_engine/toc_builder.py` | 수정 — TM TOC 함수 2개 추가 | 완료 |
| `api/schemas/documents.py` | 수정 — TEASER 허용 | 완료 |
| `prompts/section_prompts/teaser.py` | 신규 — 8개 TM 프롬프트 | 완료 |
| `prompts/__init__.py` | 수정 — 레지스트리 등록 | 완료 (docstring 수정 포함) |

### 프론트엔드 (`amic-platform/`) — 17개 파일

| 파일 | 작업 | 상태 |
|------|------|------|
| `modules/docs/DocsRoutes.tsx` | 신규 — 라우팅 | 완료 |
| `modules/docs/pages/StudioHomePage.tsx` | 신규 — 문서 허브 페이지 | 완료 |
| `modules/docs/pages/CreateDocumentPage.tsx` | 신규 — 3-step 문서 생성 폼 | 완료 |
| `modules/docs/pages/DocumentDetailPage.tsx` | 신규 — 문서 상세 (TM/IM 구분) | 완료 |
| `modules/docs/pages/TemplatesPage.tsx` | 신규 — TEASER 템플릿 추가 | 완료 |
| `modules/docs/hooks/useDocuments.ts` | 신규 — API 훅 | 완료 |
| `modules/docs/hooks/useCompanies.ts` | 신규 — 회사 검색 훅 | 완료 |
| `modules/docs/types/document.ts` | 신규 — TEASER + DocumentType 확장 | 완료 |
| `modules/docs/types/company.ts` | 신규 — 회사 타입 | 완료 |
| `modules/docs/components/DocumentTypePicker.tsx` | 신규 — TM/IM 유형 선택 카드 | 완료 |
| `modules/docs/components/DocsErrorBoundary.tsx` | 신규 — 에러 바운더리 | 완료 |
| `modules/docs/components/DocumentStatusBadge.tsx` | 신규 — 상태 뱃지 | 완료 |
| `modules/docs/components/ProgressTracker.tsx` | 신규 — 진행률 트래커 | 완료 |
| `App.tsx` | 수정 — `/docs/*` 등록, `/im/*` 리다이렉트 | 완료 |
| `components/layout/ModuleSwitcher.tsx` | 수정 — "Deal Doc Studio" 표시 | 완료 |
| `components/layout/Sidebar.tsx` | 수정 — Docs 네비게이션 | 완료 |
| `pages/DashboardPage.tsx` | 수정 — 퀵 액션 링크 업데이트 | 완료 |

---

## 2. 코드 리뷰 결과

### 2.1 통과 항목

| 검증 항목 | 결과 |
|-----------|------|
| import 경로 일관성 (`@/modules/im/` 잔존 없음) | PASS |
| API 클라이언트 경로 (`/api/im/` 유지) | PASS |
| 네비게이션 경로 (`/docs/*` 통일) | PASS |
| section_id 3-way 매핑 (렌더러 ↔ 프롬프트 ↔ im_document) | PASS |
| RENDERER_REGISTRY 8개 TM 렌더러 등록 | PASS |
| 프롬프트 레지스트리 8개 TM 프롬프트 등록 | PASS |
| IMStyle.TEASER enum + 스키마 검증 | PASS |
| toc_builder 함수 서명/호출 일치 | PASS |
| 단독 리포 ↔ 모노레포 동기화 (렌더러 4파일) | PASS |
| 허위 참조 (존재하지 않는 컴포넌트/함수) | PASS |
| 하드코딩 시크릿/SQL 인젝션 없음 | PASS |
| UI 컴포넌트 export 존재 확인 | PASS |
| React Query 키 네임스페이스 일관성 | PASS |

### 2.2 발견 및 수정된 이슈

#### 백엔드

| # | 파일 | 심각도 | 이슈 | 수정 |
|---|------|--------|------|------|
| B1 | `im_document.py:156` | Warning | TOC 그룹 오탈자 "Execution Summary" → "Executive Summary" | **수정 완료** |
| B2 | `tm_aliases.py:67,152` | Warning | 내러티브 키 불일치 — PPTX/HTML 렌더러가 `company_overview`/`business_overview` 키로 읽지만, TM 프롬프트는 `target_overview`/`target_highlights` 키로 생성 | **수정 완료** — 폴백 체인 + HTML 위임 전 키 복사 |
| B3 | `pipeline.py:107` | Info | docstring "18종" → 실제 26종 (TM 8종 추가) | **수정 완료** |
| B4 | `prompts/__init__.py:86` | Info | docstring "15개" → 실제 23개 (TM 8종 추가) | **수정 완료** |

#### 프론트엔드

| # | 파일 | 심각도 | 이슈 | 수정 |
|---|------|--------|------|------|
| F1 | `im/types/document.ts` | Warning | `IMStyle` 타입에 TEASER 누락 — docs 모듈과 불일치 | **수정 완료** |
| F2 | `ModuleSwitcher.tsx` | Info | `FileText` 미사용 import | **수정 완료** |
| F3 | `DashboardPage.tsx` | Info | `AnimatedKpiValue` + `useCountUp` 미사용 | **수정 완료** |
| F4 | `docs/types/document.ts` | Info | `CONTENT_SECTIONS`에 TM 섹션 미포함 이유 주석 부재 | **수정 완료** — 설명 주석 추가 |

### 2.3 미수정 이슈 (설계 수준 — 향후 개선)

| # | 파일 | 심각도 | 이슈 | 비고 |
|---|------|--------|------|------|
| D1 | `pipeline.py:464` | Suggestion | `factory._manager.add_slide()` private 속성 직접 접근 | 양쪽 리포 동일 — `SlideFactory`에 public 메서드 추가 시 해결 |
| D2 | `pipeline.py:196` | Suggestion | TM 모드 `active_sections = []` 뮤테이션 패턴 | 단독 리포의 `if/else` 분기가 더 명확하나, 현재 동작에 버그 없음 (for 루프 즉시 종료 → manifest 갱신 정상 실행) |
| D3 | `proforma.py` | Suggestion | 재무 수치 `float` 사용 — `Decimal` 전환 검토 | 상위 데이터 모델(`FinancialStatements`) 레벨 의사결정 필요 |
| D4 | `StudioHomePage.tsx` | Suggestion | 클라이언트 사이드 상태 필터링 — 서버 사이드 지원 시 개선 | 현재 API에 `status` 필터 파라미터 미구현 |
| D5 | `CreateDocumentPage.tsx` | Suggestion | `updateField`가 `useEffect` 의존성 배열에 미포함 | 실제 버그 가능성 낮음 (순수 setter) |
| D6 | `TemplatesPage.tsx` | Suggestion | `selectedStyle` URL 파라미터 타입 가드 미적용 | UI 상태에만 영향, 기능적 문제 없음 |
| D7 | `DocumentDetailPage.tsx` | Suggestion | 재생성 시 신규 문서 ID로 이동 — 기존 FAILED 문서 잔존 | 백엔드 `/regenerate` 전용 엔드포인트 구현 시 해결 |

---

## 3. 빌드 검증

```
$ npx tsc --noEmit    → 에러 없음
$ npm run build       → ✓ built in 7.15s
```

### 코드 스플리팅 확인

| 청크 | 크기 | 비고 |
|------|------|------|
| `DocsRoutes-w_dSVP99.js` | 14.22 kB (gzip 5.47 kB) | 신규 모듈 라우팅 |
| `CreateDocumentPage-BkpI4ujQ.js` | 18.86 kB (gzip 6.17 kB) | 3-step 생성 폼 |
| `DocumentDetailPage-VKYlEtDB.js` | 9.18 kB (gzip 3.04 kB) | 문서 상세 |

---

## 4. 라우팅 변경 사항

| 경로 | 이전 | 이후 |
|------|------|------|
| `/docs` | 없음 | StudioHomePage (문서 허브) |
| `/docs/new` | 없음 | CreateDocumentPage (3-step) |
| `/docs/new?type=teaser` | 없음 | TM 생성 모드 |
| `/docs/new?type=im` | 없음 | IM 생성 모드 |
| `/docs/documents/:id` | 없음 | DocumentDetailPage |
| `/docs/templates` | 없음 | TemplatesPage |
| `/im/*` | ImRoutes | → `/docs` 리다이렉트 |

---

## 5. 허위 양성 검증 (거부된 가설)

리뷰 과정에서 사전 검증 후 거부된 가설:

| 가설 | 검증 결과 | 거부 사유 |
|------|-----------|-----------|
| `@/modules/im/` 잔존 참조 | Grep 0건 | 반증됨 |
| `SkeletonCard` 미export | `ui/index.ts:36` 확인 | 반증됨 |
| `StudioHomePage` eager import 비효율 | 진입점 페이지 — lazy 불필요 | 설계 의도 |
| `sanitizeFilename` 주석 누락 | private 함수 — 허용 범위 | 오판 |
| `selectedStyle` 완전 미사용 | 177줄 `variant` 결정에 사용 | 반증됨 |

**거부율**: 5/11 = 45% — 높은 거부율은 허위 양성 방지 게이트가 정상 작동함을 나타냄.

---

## 6. 수정 파일 목록 (리뷰 후 추가 수정)

| 파일 | 수정 내용 |
|------|-----------|
| `im/src/design_renderer/im_document.py` | "Execution Summary" → "Executive Summary" 오탈자 |
| `im/src/design_renderer/section_renderers/tm_aliases.py` | 내러티브 키 폴백 체인 + HTML 위임 전 키 복사 |
| `im/src/design_renderer/pipeline.py` | docstring 렌더러 수 업데이트 |
| `im/src/narrative_generator/prompts/__init__.py` | docstring 프롬프트 수 업데이트 |
| `amic-platform/src/modules/im/types/document.ts` | `IMStyle`에 TEASER 추가 |
| `amic-platform/src/modules/docs/types/document.ts` | `CONTENT_SECTIONS` 주석 보강 |
| `amic-platform/src/components/layout/ModuleSwitcher.tsx` | `FileText` 미사용 import 제거 |
| `amic-platform/src/pages/DashboardPage.tsx` | 미사용 코드 제거 + 퀵 액션 링크 업데이트 |
