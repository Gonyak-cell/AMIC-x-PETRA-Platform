# MA 사이드바 팀 탭 삭제 및 타임라인 네비게이션 수정

> 작성: 2026-02-25 17:26

## 요약

MA 딜 워크스페이스 사이드바 TOOLS 섹션에서 불필요한 "팀" 탭을 삭제하고, "타임라인" 탭 클릭 시 네비게이션이 작동하지 않는 문제를 수정함.

## 변경 사항

### 1. "팀" 탭 삭제

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/components/layout/Sidebar.tsx:138` | `MA_TOOLS_NAV` 배열에서 `{ to: "team", label: "팀", icon: Users }` 항목 제거 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:218` | `VALID_TABS` 배열에서 `"team"` 제거 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:536` | `allTabs` 배열에서 `{ id: "team", label: "팀", ... }` 항목 제거 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:963-1028` | `safeActiveTab === "team"` 렌더링 블록 전체 삭제 (워킹그룹 Card + DealClientManager) |
| `amic-platform/src/modules/ma/constants.ts:551` | `PHASE_VISIBLE_TABS.ENGAGEMENT`에서 `"team"` 제거 |

### 2. "타임라인" 네비게이션 수정

**근본 원인**: `SIDEBAR_ONLY_TABS`에 `"timeline"`이 누락되어 있어서, CLOSING 단계가 아닌 다른 단계에서 사이드바의 타임라인을 클릭하면 `safeActiveTab` 계산 시 `visibleTabIds.includes("timeline")`이 false가 되어 폴백됨.

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:560` | `SIDEBAR_ONLY_TABS`에 `"timeline"` 추가 → 모든 단계에서 사이드바 접근 가능 |
| `amic-platform/src/modules/ma/constants.ts:556` | `PHASE_VISIBLE_TABS.CLOSING`에서 `"timeline"` 제거 → 파이프라인 탭 바 중복 표시 방지 |

## 검증

- `npx tsc --noEmit` — 통과
- `npx vite build` — 12.40s 빌드 성공
