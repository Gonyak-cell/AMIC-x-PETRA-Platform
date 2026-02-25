# M&A 파이프라인 탭 제거 — 코드 리뷰 & 정합성 수정

> 2026-02-25 16:49 작성

## 작업 요약

M&A 딜 워크스페이스에서 4개 탭을 파이프라인 탭 바에서 제거:
- `risks`, `compliance`, `notes-approvals` → 사이드바 Tools에서 접근
- `ai-quality` (Ralph Loop) → 향후 DD/Checklist 탭에 인라인 통합 예정

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/modules/ma/constants.ts:546-548` | `ALWAYS_VISIBLE_TABS`: `["overview", "risks", "compliance", "notes-approvals", "ai-quality"]` → `["overview"]` |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:530-547` | `allTabs` 배열에서 4개 항목 제거 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:216` | `VALID_TABS`에서 `ai-quality` 제거 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:556-561` | `SIDEBAR_ONLY_TABS` 추가 + `safeActiveTab` 로직 수정 |

## 리뷰 결과

### PASS

| 항목 | 파일:라인 | 검증 결과 |
|------|----------|----------|
| `ALWAYS_VISIBLE_TABS` 정리 | constants.ts:546-548 | `["overview"]`만 남김 ✓ |
| `PHASE_VISIBLE_TABS` 무결성 | constants.ts:550-558 | 7개 phase 모두 정상, 제거된 탭 미참조 ✓ |
| `PHASE_TAB_MAP` 무결성 | constants.ts:535-543 | 제거된 탭으로 매핑하는 phase 없음 ✓ |
| `allTabs` 배열 정리 | TransactionWorkspacePage.tsx:530-547 | 4개 항목 제거 완료 ✓ |
| 타입 안전성 | constants.ts `as const` | 타입 제약 깨짐 없음 ✓ |
| Hook/import 정합성 | TransactionWorkspacePage.tsx:67-70 | content 블록에서 여전히 사용 중, 불필요 import 없음 ✓ |
| 사이드바 유지 | Sidebar.tsx:136-143 | `MA_TOOLS_NAV`에 risks/compliance/notes-approvals 정상 유지 ✓ |
| tsc --noEmit | — | 에러 없음 ✓ |
| vite build | — | 빌드 성공 ✓ |

### FAIL → 수정 완료

| 항목 | 문제 | 수정 |
|------|------|------|
| **사이드바 경로 단절 (P0)** | 사이드바 "리스크/컴플라이언스/노트·승인" 클릭 시 `safeActiveTab` 폴백으로 overview 표시됨 | `SIDEBAR_ONLY_TABS` 상수 추가, `safeActiveTab` 조건에 포함 |
| **ai-quality URL 접근** | 사이드바/탭 모두 없지만 URL 직접 접근 가능 | `VALID_TABS`에서 제거하여 overview로 폴백 |

### 버그 원인 추적 (사이드바 경로 단절)

```
사이드바 클릭 → URL /ma/transactions/:id/risks
  → VALID_TABS.includes("risks") = true → activeTab = "risks"
  → visibleTabIds = PHASE_VISIBLE_TABS[phase] (risks 미포함)
  → safeActiveTab: "risks" not in visibleTabIds → "overview" 폴백 ← 버그!
```

수정 후:
```
  → safeActiveTab: "risks" in SIDEBAR_ONLY_TABS → "risks" 허용 ← 정상
```

## 남아있는 코드 (의도적 유지)

| 코드 | 위치 | 이유 |
|------|------|------|
| risks content 블록 | TransactionWorkspacePage.tsx:2419-2566 | 사이드바에서 접근 |
| compliance content 블록 | TransactionWorkspacePage.tsx:2569-2702 | 사이드바에서 접근 |
| notes-approvals content 블록 | TransactionWorkspacePage.tsx:3004+ | 사이드바에서 접근 |
| ai-quality content 블록 | TransactionWorkspacePage.tsx:2855-2939 | 향후 DD/Checklist 인라인 통합 시 재활용 (현재 unreachable) |
| 관련 hooks (useRisks, useCompliance 등) | TransactionWorkspacePage.tsx:67-70 | content 블록에서 사용 |
