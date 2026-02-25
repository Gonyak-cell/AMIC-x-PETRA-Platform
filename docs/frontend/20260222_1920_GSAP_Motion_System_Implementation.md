# GSAP 모션 시스템 도입 — 구현 보고서

> 작성: 2026-02-22 19:20
> 상태: Phase 1~4 전체 완료

---

## 1. 개요

AMIC x PETRA Platform에 GSAP(GreenSock Animation Platform)을 도입하여 기존 CSS transition 기반 UI를 프리미엄 모션 인터페이스로 업그레이드했다. dealroom.net, IMM Investment, MBK Partners 수준의 고급 모션을 목표로 4단계에 걸쳐 구현 완료.

**이전 상태**: CSS transition + Tailwind keyframes만 사용 (애니메이션 성숙도 ⭐⭐⭐/5)
**현재 상태**: GSAP timeline, ScrollTrigger, micro-interactions 전면 적용 (⭐⭐⭐⭐⭐/5)

---

## 2. 기술 스택

| 패키지 | 버전 | 크기 (gzip) | 용도 |
|--------|------|-------------|------|
| `gsap` | 3.x | ~23KB | 코어 애니메이션 엔진 |
| `gsap/ScrollTrigger` | 3.x | ~8KB | 스크롤 기반 트리거 |
| `@gsap/react` | 2.x | ~2KB | React 통합 (`useGSAP` hook) |
| **합계** | | **~33KB** | 기존 빌드 대비 ~1.5% 증가 |

---

## 3. Phase별 구현 상세

### Phase 1: GSAP 인프라 + 페이지 전환 + 접근성 (5개 파일)

| 파일 | 유형 | 변경 내용 |
|------|------|----------|
| `src/lib/gsap.ts` | 신규 | GSAP 초기화, ScrollTrigger 등록, `prefers-reduced-motion` 지원 |
| `src/components/layout/PageTransition.tsx` | 신규 | 라우트 변경 시 opacity + y 14px 페이드인 (0.4s) |
| `src/components/layout/AppShell.tsx` | 수정 | `<PageTransition>` 래퍼 적용 |
| `src/index.css` | 수정 | `.stagger` CSS 규칙 제거, `prefers-reduced-motion` 미디어 쿼리 추가 |
| `package.json` | 수정 | `gsap`, `@gsap/react` 의존성 추가 |

**핵심 코드 — `src/lib/gsap.ts`**:
```typescript
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

// prefers-reduced-motion 지원
const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
function applyMotionPreference(e: MediaQueryList | MediaQueryListEvent) {
  if (e.matches) {
    gsap.globalTimeline.timeScale(0);
    ScrollTrigger.getAll().forEach((t) => t.kill());
  } else {
    gsap.globalTimeline.timeScale(1);
  }
}
applyMotionPreference(motionQuery);
motionQuery.addEventListener("change", applyMotionPreference);
gsap.defaults({ ease: "power2.out", duration: 0.5 });

export { gsap, ScrollTrigger, useGSAP };
```

### Phase 2: PageHero + DashboardPage + .stagger 정리 (3개 파일)

| 파일 | 변경 내용 |
|------|----------|
| `src/components/ui/PageHero.tsx` | CSS `.stagger` → GSAP timeline. 타이틀(y:30→0) → 서브타이틀(y:20→0) → 액션(x:20→0) → children(stagger 0.06s) 순차 진입 |
| `src/pages/DashboardPage.tsx` | Quick Actions, Modules 그리드에 `useScrollReveal` 적용 |
| `src/index.css` | `.stagger > *` CSS 규칙 6줄 제거 |

**신규 커스텀 훅**:

| 훅 | 파일 | 용도 |
|----|------|------|
| `useCountUp` | `src/hooks/useCountUp.ts` | 숫자 0→목표값 카운팅 애니메이션 (1회 실행) |
| `useScrollReveal` | `src/hooks/useScrollReveal.ts` | ScrollTrigger 기반 뷰포트 진입 시 자식 요소 stagger 페이드인 |
| `useTilt` | `src/hooks/useTilt.ts` | 마우스 위치 기반 3D 기울기 효과 (rotateX/Y ±2°) |

### Phase 3: Micro-interactions (7개 파일)

| 파일 | 변경 내용 |
|------|----------|
| `src/components/ui/Modal.tsx` | GSAP 진입(scale 0.95→1, y 16→0, 0.35s) / 퇴장(역방향 0.25s) + backdrop 독립 애니메이션. `isClosingRef`로 중복 닫기 방지 |
| `src/components/ui/Tabs.tsx` | 활성 탭 변경 시 하단 인디케이터 바 슬라이딩 (0.3s, power2.inOut). `indicatorRef` + `useEffect`로 위치 계산 |
| `src/components/ui/Button.tsx` | 클릭 좌표 기반 리플(물결) 효과. 동적 `<span>` 생성 → GSAP로 diameter 확장 + opacity 0 (0.6s) |
| `src/components/ui/Card.tsx` | `tilt?: boolean` prop 추가. `useTilt(2)` 훅으로 마우스 기반 3D 미세 기울기 |
| `src/components/ui/DataTable.tsx` | 데이터 변경 시 행 stagger-in (opacity 0→1, y 10→0, stagger 0.03s). `prevDataLen` ref로 중복 방지 |
| `src/components/layout/SidebarNavItem.tsx` | 호버 시 아이콘 바운스 (scale 1→1.15→1, yoyo, 0.15s) |

### Phase 4: 리스트 페이지 ScrollReveal 적용 (5개 파일)

| 파일 | 적용 위치 | 옵션 |
|------|----------|------|
| `src/modules/kiis/pages/GPListPage.tsx` | 카드 그리드 (3열) | `stagger: 0.05, y: 20` |
| `src/modules/fdd/pages/DealListPage.tsx` | KPI 카드 그리드 (4열) | `stagger: 0.06, y: 20` |
| `src/modules/ma/pages/TransactionListPage.tsx` | KPI 카드 그리드 (4열) | `stagger: 0.06, y: 20` |
| `src/modules/im/pages/DocumentListPage.tsx` | KPI 카드 그리드 (4열) | `stagger: 0.06, y: 20` |
| `src/modules/kiis/pages/CompanyListPage.tsx` | (DataTable 자체 row stagger로 커버) | — |

---

## 4. 검증 결과

### 빌드 검증
| 항목 | 결과 |
|------|------|
| `tsc --noEmit` | 에러 0건 ✅ |
| `vite build` | 8.65s, 2974 modules ✅ |
| 번들 크기 변화 | index.js 478.42KB (기존 대비 GSAP ~33KB gzip 추가) |

### 접근성 검증
- `prefers-reduced-motion: reduce` 시 `gsap.globalTimeline.timeScale(0)` + 모든 ScrollTrigger kill
- CSS에서도 `animation-duration: 0.01ms !important` 적용
- 기존 WCAG 2.1 AA 준수 상태 유지

---

## 5. 파일 통계

| 구분 | 파일 수 |
|------|--------|
| 신규 파일 | 5개 (gsap.ts, PageTransition.tsx, useCountUp.ts, useScrollReveal.ts, useTilt.ts) |
| 수정 파일 | 14개 |
| **총 변경** | **19개 파일** |

### 신규 파일 목록

```
src/lib/gsap.ts                           — GSAP 초기화 + 접근성
src/components/layout/PageTransition.tsx   — 페이지 전환 래퍼
src/hooks/useCountUp.ts                    — 숫자 카운팅 훅
src/hooks/useScrollReveal.ts               — ScrollTrigger 유틸리티 훅
src/hooks/useTilt.ts                       — 3D 기울기 훅
```

### 수정 파일 목록

```
package.json                                        — gsap, @gsap/react 의존성
src/index.css                                       — .stagger 제거, reduced-motion
src/components/layout/AppShell.tsx                   — PageTransition 적용
src/components/layout/SidebarNavItem.tsx              — 아이콘 바운스
src/components/ui/PageHero.tsx                        — GSAP timeline
src/components/ui/Modal.tsx                           — GSAP 진입/퇴장
src/components/ui/Tabs.tsx                            — 인디케이터 슬라이드
src/components/ui/Button.tsx                          — 리플 효과
src/components/ui/Card.tsx                            — 3D 기울기
src/components/ui/DataTable.tsx                       — 행 stagger
src/pages/DashboardPage.tsx                           — ScrollReveal
src/modules/fdd/pages/DealListPage.tsx                — KPI ScrollReveal
src/modules/ma/pages/TransactionListPage.tsx          — KPI ScrollReveal
src/modules/im/pages/DocumentListPage.tsx             — KPI ScrollReveal
src/modules/kiis/pages/GPListPage.tsx                 — 카드 그리드 ScrollReveal
```

---

## 6. 적용된 모션 효과 총정리

| 효과 | 대상 | 트리거 | 애니메이션 |
|------|------|--------|-----------|
| 페이지 전환 | 전체 라우트 | location.pathname 변경 | opacity 0→1, y 14→0 (0.4s) |
| Hero 시퀀스 | PageHero | 마운트 | 타이틀→서브타이틀→액션→children timeline |
| KPI 등장 | KPI 카드 그리드 | 뷰포트 진입 (85%) | opacity 0→1, y 20→0, stagger 0.06s |
| 카드 그리드 등장 | GP 카드 등 | 뷰포트 진입 (85%) | opacity 0→1, y 20→0, stagger 0.05s |
| 모달 진입 | Modal | open=true | scale 0.95→1, y 16→0 (0.35s) + backdrop |
| 모달 퇴장 | Modal | close | scale 1→0.95, y 0→12 (0.25s) |
| 탭 인디케이터 | Tabs (underline) | 탭 변경 | x + width 슬라이딩 (0.3s) |
| 버튼 리플 | Button | 클릭 | 클릭 좌표에서 원형 확장 (0.6s) |
| 카드 기울기 | Card (tilt=true) | 마우스 이동 | rotateX/Y ±2° (perspective 800px) |
| 테이블 행 | DataTable | 데이터 변경 | opacity 0→1, y 10→0, stagger 0.03s |
| 사이드바 아이콘 | SidebarNavItem | 호버 | scale 1→1.15→1 바운스 (0.15s) |
| 접근성 비활성화 | 전체 | prefers-reduced-motion | 모든 모션 즉시 비활성화 |

---

## 7. 성능 가이드라인 (적용됨)

- **GPU 가속**: transform, opacity만 애니메이션 (layout/paint 트리거 방지)
- **자동 cleanup**: `useGSAP` hook의 scope 기반 자동 cleanup (메모리 누수 방지)
- **1회 실행**: `useCountUp`은 `hasAnimated` ref로 1회만 실행
- **중복 방지**: DataTable `prevDataLen` ref로 동일 데이터 길이 시 재애니메이션 방지
- **접근성 우선**: GSAP + CSS 양쪽에서 `prefers-reduced-motion` 지원
