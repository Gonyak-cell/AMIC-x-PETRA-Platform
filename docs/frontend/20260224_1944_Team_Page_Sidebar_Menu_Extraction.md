# Our Team 섹션 → 사이드바 독립 메뉴 분리

> 작성: 2026-02-24 19:44

## 개요

대시보드(`/`) 하단의 "OUR TEAM" 섹션을 제거하고, 사이드바의 독립 메뉴(`/team`)로 분리.

## 변경 내역

### 신규 파일

| 파일 | 설명 |
|------|------|
| `src/pages/team/TeamPage.tsx` | 독립 팀 페이지 — PageHero(compact) + Card + 6명 프로필 그리드 |

### 수정 파일

| 파일 | 변경 |
|------|------|
| `src/App.tsx` | `TeamPage` lazy import + `/team/*` Route 추가 |
| `src/components/layout/Sidebar.tsx` | Home/Calendar/Exports 아래에 `Team` SidebarNavItem 추가 (`Users` 아이콘) |
| `src/pages/DashboardPage.tsx` | `TEAM_MEMBERS` 배열 + Our Team 섹션 + `Users`/`getMemberPhoto` import 제거 |

## 팀원 데이터 (업데이트)

| 이름 | 직함 |
|------|------|
| 김양태 | 대표 / 회계사 |
| 임영훈 | 변호사 |
| 박병준 | 변호사 |
| 조우상 | 이사 |
| 윤태리 | 실장 |
| 서지원 | 변호사 |

## 기술 상세

- `TeamPage`는 기존 대시보드 카드 로직 기반, 독립 페이지에 맞게 레이아웃 확장
  - 그리드: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
  - 사진 크기: `w-14 h-14` (대시보드 `w-11 h-11` 대비 확대)
  - `useScrollReveal` GSAP 애니메이션 적용
- 사이드바 메뉴: 공통 상단 링크 (Home, Calendar, Exports, **Team**) 레벨에 배치
- 사진 시스템: `getMemberPhoto()` (`src/lib/member-photos.ts`) 재사용

## 검증

- TypeScript `tsc --noEmit` 통과
- Vite 빌드 성공 (8.05s)
