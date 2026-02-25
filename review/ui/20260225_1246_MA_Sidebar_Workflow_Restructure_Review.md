# MA 사이드바 워크플로우 재구성 — 코드 리뷰

> 작성: 2026-02-25 12:46 | 대상 브랜치: `feat/ma-workflow`

## 변경 요약

MA 모듈 사이드바를 7단계 워크플로우에 맞게 재구성.

**변경 파일 2개**:
- `amic-platform/src/components/layout/SidebarNavItem.tsx` — `SidebarPhaseItem` 컴포넌트 신규 추가
- `amic-platform/src/components/layout/Sidebar.tsx` — MA 네비게이션 상수 교체 + 렌더링 재구성

**변경 전**:
```
WORKSPACE: Overview, 수임, 팀, 매수자, 타임라인
DUE DILIGENCE: DD/Checklist
```

**변경 후**:
```
WORKSPACE: Overview
WORKFLOW: ① 수임, ② 준비, ③ 마케팅, ④ 입찰/DD, ⑤ 협상, ⑥ Closing, ⑦ Post-Close
TOOLS: VDR, 팀, 타임라인, 리스크, 컴플라이언스, 노트/승인
```

---

## 검증 결과 (7항목)

### 1. PHASE_TAB_MAP 일치 — ✅

`MA_WORKFLOW_NAV.to` ↔ `constants.ts PHASE_TAB_MAP` 값을 1:1 교차 검증. 7개 모두 정확히 일치.

### 2. useTransaction 훅 안전성 — ✅

- 빈 문자열 전달 시 `enabled: !!txnId` → `false` → fetch 차단
- React Query 캐시 키 공유로 TransactionWorkspacePage와 중복 fetch 없음

### 3. Phase 상태 판정 로직 — ✅

- `currentPhaseIdx < 0` (데이터 미로딩) → 전체 "future" 처리 (올바른 방어)
- done/current/future 경계 조건 정확

### 4. CLIENT 역할 처리 — ✅

- `!isClient` 가드가 Workflow/Tools 섹션 전체 감싸고 있어 기존 동작 유지

### 5. 접근성 (a11y) — ✅

- `future`: `aria-disabled="true"`
- `current`: `aria-current="step"`
- `done`: NavLink (클릭 가능)

### 6. GSAP 통합 — ✅

- 기존 `SidebarNavItem` hover 애니메이션 패턴 동일 적용
- `future` 상태 조기 반환으로 불필요한 애니메이션 방지

### 7. TypeScript + Build — ✅

- `npx tsc --noEmit` 통과
- `npx vite build` 12.17s 성공

---

## 발견 및 수정된 이슈 (1건)

### BUG-001: `h-4.5 w-4.5` 무효 Tailwind 클래스 — ✅ 수정 완료

| 항목 | 내용 |
|------|------|
| **위치** | `SidebarNavItem.tsx` 라인 187, 202, 218 |
| **문제** | Tailwind 기본 spacing scale에 `4.5` 없음 → CSS 미생성 → 아이콘 크기 미적용 |
| **영향** | Lucide 기본 24x24로 렌더링, 의도(18px)보다 크게 표시 |
| **수정** | `h-4.5 w-4.5` → `h-[18px] w-[18px]` (3곳 모두) |
| **검증** | 수정 후 tsc 통과 |

---

## 허위 클레임 검증

| 클레임 | 검증 방법 | 결과 |
|--------|----------|------|
| "라우팅 변경 불필요" | `App.tsx` 라우트 구조 확인, `?viewPhase` 쿼리 파라미터 기존 패턴 | ✅ 사실 |
| "React Query 캐시 공유로 추가 fetch 없음" | `useTransaction` 쿼리 키 `["ma", "transactions", txnId]` 동일 | ✅ 사실 |
| "기존 PipelineFlow 컴포넌트 유지" | Sidebar 변경에 `TransactionWorkspacePage.tsx` 미수정 | ✅ 사실 |
| "CLIENT 역할 기존 동작 유지" | `!isClient` 가드 코드 직접 확인 | ✅ 사실 |
| "tsc + build 통과" | 실제 실행 결과 확인 | ✅ 사실 |

**허위 클레임: 0건**
