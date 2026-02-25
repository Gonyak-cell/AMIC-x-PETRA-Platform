# GSAP 모션 시스템 코드 리뷰

> 작성: 2026-02-23 09:34
> 대상: Session 32 GSAP 모션 시스템 전체 19개 파일
> 상태: **3건 수정 완료** (P0 1건, P1 1건, P2 1건) + 12건 허위 양성 필터링

---

## 리뷰 범위

Session 32에서 구현한 GSAP 모션 시스템 Phase 1~4 전체:
- 신규 5개 파일 (gsap.ts, PageTransition.tsx, useCountUp.ts, useScrollReveal.ts, useTilt.ts)
- 수정 14개 파일 (AppShell, PageHero, Modal, Tabs, Button, Card, DataTable, SidebarNavItem, DashboardPage, DealListPage, TransactionListPage, DocumentListPage, GPListPage, index.css)

---

## 발견된 실제 이슈 및 수정 내역

### Issue 1: [P0 Critical] gsap.ts timeScale(0) — 접근성 치명적 버그

**파일**: `src/lib/gsap.ts:13`
**문제**: `timeScale(0)` = 애니메이션 재생 속도 0배 = 영원히 시작 상태(opacity: 0)에 정지
**영향**: `prefers-reduced-motion: reduce` 사용자에게 전체 앱이 빈 화면으로 표시
**수정**: `timeScale(0)` → `timeScale(1000)` (1000배속 = 즉시 완료 → 최종 상태로 점프)
**상태**: ✅ 수정 완료

### Issue 2: [P1 High] GPListPage 조건부 ref — ScrollReveal 미동작

**파일**: `src/modules/kiis/pages/GPListPage.tsx:169-170`
**문제**: `gridRef`가 조건부 렌더링되는 div에만 연결. `isLoading=true`일 때 ref=null → `useGSAP` 실행 시 early return → 데이터 로드 후에도 재실행 안 됨
**수정**: `useScrollReveal` 훅에 `deps` 매개변수 추가 + GPListPage에서 `[isLoading, data?.items.length]` 전달
**상태**: ✅ 수정 완료

### Issue 3: [P2 Medium] useCountUp 데드 코드

**파일**: `src/hooks/useCountUp.ts`
**문제**: 31줄짜리 훅 정의만 있고 프로젝트 전체에서 import 0건. 추가로 `hasAnimated` ref 때문에 end 값 변경 시 재애니메이션 불가능한 버그도 내재
**수정**: 파일 삭제 (데드 코드 제거)
**상태**: ✅ 삭제 완료

### Issue 4: [P2 Low] DataTable data.length 비교 제한 (미수정)

**파일**: `src/components/ui/DataTable.tsx:69`
**문제**: `data.length === prevDataLen.current`이면 정렬/필터 후에도 행 애니메이션 스킵
**판정**: 의도된 설계 — 같은 개수 = 재애니메이션 불필요. 수정 불요.

---

## 허위 양성 필터링 (12건 기각)

| # | 에이전트 주장 | 판정 | 근거 |
|---|-------------|------|------|
| FP-1 | Modal timeline cleanup 없음 → 메모리 누수 | 허위 양성 | GSAP timeline은 완료 후 자동 GC |
| FP-2 | Button onClick 에러 시 ripple DOM 누수 | 허위 양성 | GSAP 애니메이션은 onClick과 독립 실행 |
| FP-3 | Button 빠른 연타 시 ripple 누적 | 허위 양성 | Material Design 리플은 의도적 복수 생성 |
| FP-4 | Card useTilt 항상 호출 → 낭비 | 허위 양성 | React Hooks 규칙상 조건부 호출 불가 |
| FP-5 | PageHero opacity:0 이중 설정 | 허위 양성 | FOUC 방지를 위한 의도적 설계 |
| FP-6 | PageTransition 동일 경로 애니메이션 없음 | 허위 양성 | 동일 페이지 전환 효과 불필요 |
| FP-7 | useTilt mousemove throttle 필요 | 허위 양성 | GSAP overwrite가 자체적으로 처리 |
| FP-8 | gsap.ts matchMedia 리스너 cleanup 없음 | 허위 양성 | SPA 모듈 레벨, 앱 수명 동안 유지 |
| FP-9 | DashboardPage KPI ScrollReveal 없음 | 허위 양성 | PageHero children timeline이 이미 처리 |
| FP-10 | SSR 호환성 (window.matchMedia) | 허위 양성 | Vite SPA 전용, SSR 미사용 |
| FP-11 | Modal Race Condition | 허위 양성 | isClosingRef가 정확히 방지 |
| FP-12 | useTilt ref.current 오버라이드 | 허위 양성 | e.currentTarget은 항상 올바른 요소 |

---

## 수정된 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `src/lib/gsap.ts` | `timeScale(0)` → `timeScale(1000)` |
| `src/hooks/useScrollReveal.ts` | `deps` 매개변수 추가 |
| `src/modules/kiis/pages/GPListPage.tsx` | `useScrollReveal` deps 전달 |
| `src/hooks/useCountUp.ts` | 삭제 |

---

## 빌드 검증

| 항목 | 결과 |
|------|------|
| `tsc --noEmit` | 에러 0건 ✅ |
| `vite build` | 7.50s 성공 ✅ |
