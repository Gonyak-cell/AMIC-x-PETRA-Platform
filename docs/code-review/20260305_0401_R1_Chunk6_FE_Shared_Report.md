# 코드 리뷰 리포트: FE 공유 레이어 — Chunk 6

- 라운드: 1
- 모듈: Chunk 6 FE 공유 레이어
- 배치: 1~4 통합
- 시작: 2026-03-05 03:50
- 종료: 2026-03-05 04:01

## 배치 1: tsc + eslint

- tsc --noEmit: 0건
- eslint --max-warnings 0: 0건
- 코드 수정: 0건

## 배치 2~4: 통합 리뷰 (읽기 전용)

30개 파일 상세 읽기 + ~120개 파일 패턴 스캔.

### 발견된 이슈

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 |
|---|------|-----|------|-----|--------|
| 1 | 아키텍처 | hooks/useCalendar.ts | 5-6 | modules/ma/constants에서 PHASE_CONFIG import — 공유 훅이 모듈에 의존 | High |
| 2 | 아키텍처 | hooks/useGlobalSearch.ts | 8-9 | modules/fdd/types, modules/im/types에서 타입 import — 모듈 경계 위반 | High |
| 3 | 아키텍처 | hooks/useAnalytics.ts | 8-10 | modules/fdd, modules/im, modules/kiis에서 3개 모듈 타입 import | High |
| 4 | 타입 안전성 | main.tsx | 18 | Axios 에러 unsafe cast — axios.isAxiosError() 타입 가드 미사용 | Medium |
| 5 | 타입 안전성 | api/errors.ts | 11 | err as AxiosError unsafe cast — 타입 가드 없음 | Medium |
| 6 | 성능 | hooks/useGlobalSearch.ts | 71 | FDD 검색: 200건 전체 fetch 후 클라이언트 필터링 — 서버 사이드 검색 미사용 | Medium |
| 7 | 성능 | hooks/useAnalytics.ts | 395-446 | MA 시계열: 최대 1000건 10페이지 병렬 fetch — AbortController 없음 | Medium |
| 8 | 코드 품질 | hooks/useCalendar.ts | 23 | eslint-disable 미사용 파라미터 _filter — 미완성 필터링 기능 | Medium |
| 9 | 타입 안전성 | hooks/useGlobalSearch.ts | 104 | 인라인 unsafe cast (err as object) | Low |
| 10 | 타입 안전성 | hooks/useExports.ts | 26-27 | 동일 인라인 unsafe cast 패턴 | Low |
| 11 | 타입 안전성 | components/diagrams/ExcalidrawViewer.tsx | 39 | as unknown as ExcalidrawInitialDataState 이중 캐스트 | Low |
| 12 | 코드 품질 | types/auth.ts | 74-83 | Dead types: TokenResponse, RefreshRequest — 쿠키 인증 전환 후 미사용 | Low |
| 13 | 코드 품질 | components/layout/SidebarModuleGroup.tsx | 61 | eslint-disable exhaustive-deps — 의도적 생략이나 문서화 없음 | Low |
| 14 | 코드 품질 | components/ui/LiveRegion.tsx | 79 | eslint-disable 미사용 변수 — no-op 폴백에서 불필요 | Low |
| 15 | 성능 | components/ui/DataTable.tsx | 83-87 | GSAP 애니메이션이 매 데이터 변경 시 실행 — 대량 행에서 jank 가능 | Low |
| 16 | 데이터 무결성 | hooks/useNotifications.ts | 14-28 | 404/405 외 에러도 빈 배열 반환 — 500 에러 삼킴 | Low |
| 17 | 데이터 무결성 | hooks/useDashboard.ts | 38 | items: unknown[] — 타입 정보 손실 | Low |
| 18 | 코드 품질 | main.tsx | 49 | console.log 프로덕션 코드 (MSW 서비스 워커 정리) | Low |
| 19 | 코드 품질 | components/ui/DataTable.tsx | 1-373 | 373줄 컴포넌트, 헤더 렌더링 3회 중복 | Low |

### 양호한 패턴

- any 타입 0건, @ts-ignore 0건 — 전체 공유 레이어 타입 엄격성 유지
- 인라인 HTML 삽입 0건
- SentryErrorBoundary 루트 레벨 래핑
- 쿠키 기반 인증 + 동시 401 재시도 중복 방지 (api/client.ts)
- safe-parse.ts 방어적 API 응답 파싱
- 접근성: LiveRegion, skip-to-content, focus trap, aria 속성 일관
- 배럴 export + React Query 일관 패턴
- CSS 변수 기반 테마 시스템
- 한국어 로케일 포맷팅 (조/억/만 단위)

## 검증 결과

- tsc --noEmit: 0건
- eslint --max-warnings 0: 0건

## 에러 카운트

| 심각도 | 건수 |
|--------|------|
| High | 3건 (공유 훅 모듈 경계 위반) |
| Medium | 4건 (unsafe cast, 성능, eslint-disable) |
| Low | 12건 |
| 합계 | 19건 (코드 수정 0건 — 읽기 전용 관찰) |

## 충족 관점 체크리스트

- [x] 9. 린트/포맷 (tsc 0건, eslint 0건)
- [x] 6. 타입 안전성 (any 0건, unsafe cast 관찰)
- [x] 10. 의존성 (관찰)
- [x] 7. 데이터 무결성 (관찰)
- [x] 1. 보안 (인라인 HTML 삽입 0건)
- [x] 2. 성능 (클라이언트 필터링 관찰)
- [x] 3. 아키텍처 (모듈 경계 위반 3건)
- [x] 13. 코드 품질 (dead type, eslint-disable 관찰)
