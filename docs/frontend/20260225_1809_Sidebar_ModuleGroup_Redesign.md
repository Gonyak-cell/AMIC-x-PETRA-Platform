# 사이드바 ModuleSwitcher → ModuleGroup 리디자인

> 작성: 2026-02-25 18:09

## 변경 요약

ModuleSwitcher 드롭다운을 제거하고, 4개 모듈(M&A Deals, VDR, Deal Doc Studio, KIIS)을 사이드바에 직접 노출. 각 모듈의 하위 메뉴는 독립적으로 접기/펼치기 가능.

## 변경 파일

| 파일 | 작업 | 설명 |
|------|------|------|
| `amic-platform/src/components/layout/SidebarModuleGroup.tsx` | **신규** | 모듈 헤더 + 접기/펼치기 래퍼 컴포넌트 |
| `amic-platform/src/components/layout/Sidebar.tsx` | **수정** | ModuleSwitcher 제거, SidebarModuleGroup 4개 적용 |
| `amic-platform/src/components/layout/SidebarNavItem.tsx` | **수정** | SidebarSection에 `className` prop 추가 |
| `amic-platform/src/components/layout/ModuleSwitcher.tsx` | **삭제** | 더 이상 미사용 |
| `amic-platform/src/components/layout/index.ts` | **수정** | barrel export 갱신 (ModuleSwitcher → SidebarModuleGroup) |

## SidebarModuleGroup 컴포넌트 설계

### Props
```typescript
interface SidebarModuleGroupProps {
  id: string;                   // "ma" | "vdr" | "docs" | "kiis"
  label: string;                // "M&A Deals"
  icon: LucideIcon;             // Handshake
  basePath: string;             // "/ma/transactions"
  isActive: boolean;            // 현재 pathname이 이 모듈 소속인지
  storageKey: string;           // localStorage 키: "module-ma"
  defaultOpen?: boolean;        // 기본 열림 (기본값: false)
  children: React.ReactNode;    // 하위 메뉴
  onNavItemClick?: () => void;  // 모바일 자동 닫기 콜백
}
```

### 핵심 동작
- **클릭 → 토글 + 이동**: 접힌 상태에서 클릭 → 펼치면서 `navigate(basePath)` 수행. 이미 펼친 상태면 접기만.
- **독립 토글**: 아코디언 아님. 여러 모듈을 동시에 펼칠 수 있음.
- **자동 펼침**: 활성 모듈이 되면 `useEffect`로 자동 펼침.
- **상태 보존**: localStorage (`sidebar-module-{id}`) 기반 열림/닫힘 상태 보존.

### 스타일링
- 모듈 헤더: `px-3 py-2.5 rounded-lg text-sm font-semibold`
- 활성 모듈: `bg-white/[0.08] text-white` + 좌측 accent 바 (3px, green glow)
- 비활성: `text-white/60 hover:bg-white/[0.06]`
- 하위 메뉴: `ml-2 pl-3 border-l border-white/[0.08]` (좌측 연결선)
- 트랜지션: `duration-500 ease-in-out` (0.5초)
- 접기: `max-h-0 opacity-0` / 펼치기: `max-h-[2000px] opacity-100`
- GSAP 아이콘 hover 애니메이션 (기존 SidebarNavItem 패턴 재사용)

### 상태 관리 구조
```
SidebarModuleGroup (storageKey: "module-kiis")     → 1차 토글
  └── SidebarSection (storageKey: "kiis-research")  → 2차 토글
  └── SidebarSection (storageKey: "kiis-pipeline")  → 2차 토글
  └── SidebarSection (storageKey: "kiis-portfolio") → 2차 토글
```

## Sidebar.tsx 주요 변경

1. `ModuleSwitcher` import → `SidebarModuleGroup` import
2. ModuleSwitcher 렌더링 영역 제거 (기존 line 259-264)
3. Portal Nav과 모듈 영역 사이에 그래디언트 구분선 추가
4. 배타적 조건 렌더링(`{isKiis && ...}`) → 4개 모듈 동시 렌더링 (`SidebarModuleGroup` 래핑)
5. 모듈 그룹 내부 `SidebarSection`에 `className="mt-3"` 적용 (간격 축소)
6. `FileStack` Lucide 아이콘 import 추가 (Deal Doc Studio 모듈 아이콘)

## 엣지 케이스 처리

| 케이스 | 처리 |
|--------|------|
| CLIENT 역할 | M&A만 표시 (기존 `!isClient` 조건 유지) |
| M&A 워크스페이스 | 그룹 내 Workspace/Workflow/Tools 조건부 활성화 유지 |
| FDD 딜 워크스페이스 | Docs 그룹 내 FDD 섹션 조건부 표시 유지 |
| 4개 모듈 동시 펼침 | `overflow-y-auto`로 스크롤 |
| 모바일 | 기존 슬라이드 드로어 방식 유지 |

## 검증 결과

- `npx tsc --noEmit` — 통과
- `npx vite build` — 12.37초, 성공
