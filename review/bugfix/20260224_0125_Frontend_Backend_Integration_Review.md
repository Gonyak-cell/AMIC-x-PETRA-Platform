# 프론트엔드-백엔드 전체 연동 검증 리뷰

**날짜**: 2026-02-24 01:25:00
**범위**: amic-platform (프론트엔드) ↔ 4개 백엔드 (FDD, KIIS, IM, MA)
**검증 대상**: 67개 훅, 385+ 엔드포인트, 50+ 페이지

---

## 검증 결과 요약

| 검증 항목 | 결과 | 상세 |
|-----------|------|------|
| Phase 0: API 경로 교차 검증 | **7건 발견, 5건 수정** | BUG-1~5 수정, BUG-6~7 안전 처리 |
| Phase 1: TS ↔ Pydantic 타입 대조 | **런타임 에러 0건** | UUID/datetime 차이는 JSON 직렬화로 자동 변환 |
| Phase 2: tsc --noEmit | **에러 0건** | |
| Phase 2: vite build | **성공 (8.11s)** | |

---

## 발견된 버그 및 수정 내역

### BUG-1 (P0) — useAnalytics.ts FDD deals 응답 파싱 오류

- **파일**: `amic-platform/src/hooks/useAnalytics.ts:145, 232`
- **문제**: `api.get<Deal[]>("/deals")` — 배열을 기대하지만 FDD 백엔드는 `{items, total, skip, limit}` 객체 반환
- **결과**: `filterByDate(data, cutoff)` → 객체에 `.filter()` 호출 → **런타임 TypeError**
- **영향**: Analytics 페이지(`/analytics`) 전체 로딩 실패
- **수정**: `Array.isArray(data) ? data : data.items` 패턴 적용

### BUG-2 (P1) — FDD /auth/change-password 엔드포인트 누락

- **파일**: `fdd/backend/app/api/auth.py` (신규 추가)
- **문제**: 프론트엔드 `useProfile.ts`에서 `POST /auth/change-password` 호출하지만 백엔드에 없음
- **영향**: 비밀번호 변경 기능 불가 (설정 > 프로필 페이지)
- **수정**: `auth.py`에 `/change-password` POST 엔드포인트 추가

### BUG-3 (P1) — useGlobalSearch.ts FDD deals 응답 + 검색 파라미터 불일치

- **파일**: `amic-platform/src/hooks/useGlobalSearch.ts`
- **문제1**: BUG-1과 동일한 응답 형태 불일치
- **문제2**: FDD 백엔드가 `search` 쿼리 파라미터를 지원하지 않음
- **영향**: 글로벌 검색 시 FDD 딜 검색 실패
- **수정**: 응답 형태 수정 + 클라이언트 사이드 필터링 적용

### BUG-4 (P2) — useCompanies.ts KIIS 평판 API 경로 불일치

- **파일**: `amic-platform/src/modules/kiis/hooks/useCompanies.ts:96`
- **문제**: 프론트가 `/qualitative` 경로 호출, 백엔드는 Session 33에서 `/themes`로 변경됨
- **영향**: 정성적 평판 분석 데이터 로딩 실패
- **수정**: 경로를 `/themes`로 변경

### BUG-5 (P2) — KIIS /deals/tendency-summary 엔드포인트 미구현

- **파일**:
  - `kiis/app/schemas/deal.py` (스키마 추가)
  - `kiis/app/services/deal_service.py` (서비스 메서드 추가)
  - `kiis/app/routers/deals.py` (라우터 엔드포인트 추가)
- **문제**: 프론트 `useTendencySummary` 훅이 호출하는 엔드포인트가 백엔드에 없음
- **영향**: GP/Fund 상세 페이지 투자성향 탭 데이터 로딩 실패
- **수정**: 기존 `aggregate_by_sector/stage` 서비스를 재활용하여 `/tendency-summary` 엔드포인트 구현

### BUG-6 (P3) — useComments.ts /comments 미구현 (안전 처리)

- **파일**: `amic-platform/src/hooks/useComments.ts`
- **문제**: `/comments` 엔드포인트가 어떤 백엔드에도 없음
- **영향**: 에러 핸들링으로 빈 배열 반환, 페이지 크래시 없음
- **조치**: 향후 구현 시 백엔드 추가 필요 (현재는 안전)

### BUG-7 (P3) — useCalendar.ts KIIS /deals 목록 쿼리 미구현 (안전 처리)

- **문제**: KIIS 딜 목록 전체 조회 API 없음 (by-company/by-fund만 존재)
- **영향**: 캘린더 뷰에서 KIIS 딜 표시 불가, 빈 배열 반환
- **조치**: 향후 필요 시 백엔드 추가 (현재는 안전)

---

## 수정된 파일 목록

| 파일 | 변경 유형 | 관련 버그 |
|------|----------|----------|
| `amic-platform/src/hooks/useAnalytics.ts` | 수정 | BUG-1 |
| `amic-platform/src/hooks/useGlobalSearch.ts` | 수정 | BUG-3 |
| `amic-platform/src/modules/kiis/hooks/useCompanies.ts` | 수정 | BUG-4 |
| `fdd/backend/app/api/auth.py` | 수정 | BUG-2 |
| `kiis/app/schemas/deal.py` | 수정 | BUG-5 |
| `kiis/app/services/deal_service.py` | 수정 | BUG-5 |
| `kiis/app/routers/deals.py` | 수정 | BUG-5 |

---

## Phase 1: 타입 대조 결과 (참고)

6개 엔티티 (Deal, Transaction, Document, LegalDocument, LDDReport, MarketingMaterial) 대조 완료.
- UUID vs string, datetime vs string 차이는 JSON 직렬화로 자동 변환 → **런타임 에러 없음**
- Transaction에 `notes` 필드 TS 미반영 (P3, 기능 부족)
- MarketingMaterialCreate에 Ralph Loop 3 필드 TS 미반영 (P3, 기본값 사용)
