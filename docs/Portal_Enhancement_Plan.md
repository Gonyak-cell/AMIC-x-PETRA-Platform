# AMIC x PETRA Platform - Portal Enhancement Plan

> 최종 업데이트: 2026-02-11

## 1. Context

AMIC x PETRA Platform은 3개 모듈(Auto FDD, KIIS, IM Generator)을 통합하는 M&A 자문 포털이다.
M&A 자문사 실무자들은 동시에 3~10개 딜을 관리하며, FDD 분석 -> KIIS 리서치 -> IM 생성을 빈번히 오가므로,
**통합 포털 경험**이 생산성에 직접적으로 영향을 미친다.

### 구현 방향

- **Wave 1~3**: Frontend + Backend 함께 구현 (FDD 백엔드 기준)
- **Wave 4**: 미구현 (향후 진행)

---

## 2. 진행 현황 요약

| Wave | 범위 | 상태 | 비고 |
| --- | --- | --- | --- |
| **Wave 1** | Portal Foundation (P0) | **COMPLETE** | Dashboard, Admin, Settings |
| **Wave 2** | Productivity (P1 전반) | **COMPLETE** | Search, Favorites, Notifications |
| **Wave 3** | Compliance & Collaboration (P1 후반) | **COMPLETE** | Activity Log, Team Collaboration |
| **Wave 4** | Intelligence & Enhancement (P2) | **미구현** | Analytics, Help, Calendar 등 |
| 추가 | KIIS 모듈 전체 구현 | **COMPLETE** | 10 pages, 10 hooks, 10 types, 5 components |
| 추가 | IM 모듈 전체 구현 | **COMPLETE** | 4 pages, 2 hooks, 2 types, 3 components |

---

## 3. 기능 전체 목록 및 상태

| 우선순위 | 기능 | 복잡도 | 상태 | 주요 파일 |
| --- | --- | --- | --- | --- |
| **P0** | Portal Home Dashboard | M | **DONE** | `src/pages/DashboardPage.tsx` |
| **P0** | User Management (Admin) | M | **DONE** | `src/pages/admin/UserManagementPage.tsx` |
| **P1** | User Profile & Settings | S | **DONE** | `src/pages/settings/ProfilePage.tsx` |
| **P1** | Global Search (Ctrl+K) | M | **DONE** | `src/components/search/`, `src/hooks/useGlobalSearch.ts` |
| **P1** | Notification Center | L | **DONE** | `src/components/notifications/`, `src/hooks/useNotifications.ts` |
| **P1** | Activity Log / Audit Trail | L | **DONE** | `src/pages/admin/ActivityLogPage.tsx` |
| **P1** | Team Collaboration | L | **DONE** | `src/components/collaboration/`, `src/hooks/useComments.ts` |
| **P2** | Favorites / Recent Items | S | **DONE** | `src/components/SidebarFavorites.tsx`, `src/hooks/useFavorites.ts` |
| **P2** | Cross-Module Analytics | L | 미구현 | - |
| **P2** | Help Center / Onboarding | S | 미구현 | - |
| **P2** | Data Export Hub | M | 미구현 | - |
| **P2** | Calendar / Timeline | M | 미구현 | - |
| **P2** | External Integrations | L | 미구현 | - |

---

## 4. Wave 1: Portal Foundation (COMPLETE)

### 4.1 Portal Home Dashboard

**경로:** `/`

**구현 내용:**

- Cross-module KPI Row (4개 KpiCard): Active FDD Deals, Watchlist Alerts, IM In Progress, Draft Deals
- Quick Actions: New Deal, New IM, Search Company, Watchlist (4개 바로가기)
- Module Status: 3개 백엔드 health check (green/red dot, 60초 자동 갱신)
- Modules 카드: FDD, KIIS, IM 각 모듈 바로가기

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/pages/DashboardPage.tsx` | 메인 대시보드 페이지 |
| `src/hooks/useDashboard.ts` | `usePortalKpis()` - 3개 API 병렬 호출(useQueries), `useModuleHealth()` - health check |
| `src/types/dashboard.ts` | PortalKpis, QuickAction, ModuleHealth 타입 |

**수정된 파일:**

- `src/App.tsx` - `Navigate` 제거, `DashboardPage` lazy load로 교체
- `src/components/layout/Sidebar.tsx` - Home 링크 추가 (ModuleSwitcher 위)

**KPI 데이터 소스:**

- FDD: `GET /deals` -> `status === "ACTIVE"` 건수 집계
- KIIS: `GET /alerts/unread-count` -> watchlist 알림 수
- IM: `GET /documents` -> `status in [PENDING, COLLECTING, ANALYZING, GENERATING, RENDERING]` 건수

---

### 4.2 User Management (Admin Panel)

**경로:** `/admin/users`

**구현 내용:**

- User List: DataTable (이름, 이메일, 역할, 상태, 가입일, 편집 버튼)
- KPI Row: Total Users, Admins, Managers, Analysts & Viewers
- Create User Modal: 이메일, 이름, 비밀번호, 역할 선택
- Edit User Modal: 이름 수정, 역할 변경, 활성/비활성 토글(switch)
- Role-Permission Matrix: 4 roles x 11 permissions 시각화 테이블
- Access Guard: `user:manage` 권한 없으면 "Access Denied" 표시

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/pages/admin/UserManagementPage.tsx` | 관리 페이지 (DealListPage 패턴) |
| `src/pages/admin/AdminRoutes.tsx` | `/admin/users`, `/admin/activity` 라우팅 |
| `src/hooks/useUsers.ts` | useUsers(), useCreateUser(), useUpdateUser(), useDeactivateUser() |
| `src/types/admin.ts` | AdminUser, UserCreate, UserUpdate |

**Backend API (FDD 기존 API 활용):**

- `GET /api/v1/auth/users` - 사용자 목록
- `POST /api/v1/auth/users` - 사용자 생성
- `PUT /api/v1/auth/users/{user_id}` - 사용자 수정
- Deactivate: `PUT /auth/users/{id}` with `{ is_active: false }`

---

### 4.3 User Profile & Settings

**경로:** `/settings/profile`

**구현 내용:**

- Profile Section: 아바타(이니셜), 이름(수정 가능), 이메일(읽기전용), 역할 Badge, 가입일
- 비밀번호 변경: 현재 비밀번호 + 새 비밀번호 + 확인 (8자 이상 validation)
- Display Preferences: 기본 랜딩 페이지(Dashboard/FDD/KIIS/IM), 날짜 형식(short/long)
- Your Permissions: 현재 역할의 권한 목록 Badge 표시

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/pages/settings/ProfilePage.tsx` | 프로필 + 비밀번호 + 설정 통합 페이지 |
| `src/pages/settings/SettingsRoutes.tsx` | `/settings/profile` 라우팅 |
| `src/hooks/useProfile.ts` | useUpdateProfile(), useChangePassword() |
| `src/hooks/usePreferences.ts` | localStorage 기반 설정 관리 |
| `src/types/settings.ts` | UserPreferences, PasswordChangeRequest |
| `src/lib/storage.ts` | Typed localStorage 헬퍼 (prefix: `amic_`) |

**Sidebar 변경:**

- 유저 정보 영역을 `<button>` 으로 감싸서 클릭 시 `/settings/profile`로 이동

---

## 5. Wave 2: Productivity (COMPLETE)

### 5.1 Global Search (Ctrl+K)

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/components/search/` | CommandPalette, SearchResultGroup, SearchResultItem |
| `src/hooks/useGlobalSearch.ts` | 3개 모듈 병렬 검색 (300ms debounce) |
| `src/types/search.ts` | SearchResult 타입 |

**수정:** `src/components/layout/AppShell.tsx` - global Ctrl+K keydown listener

---

### 5.2 Favorites / Recent Items

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/components/SidebarFavorites.tsx` | 사이드바 즐겨찾기 + 최근 항목 섹션 |
| `src/components/FavoriteButton.tsx` | star/bookmark 토글 버튼 |
| `src/hooks/useFavorites.ts` | localStorage 기반 즐겨찾기 (toggle, isFavorite) |
| `src/hooks/useRecentItems.ts` | 최근 방문 항목 자동 추적 |
| `src/types/favorite.ts` | FavoriteItem, FavoriteType (deal, company, im-project) |

**Sidebar 통합:** Favorites/Recent 섹션이 모듈 네비게이션 아래에 항상 표시

---

### 5.3 Notification Center

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/components/notifications/` | NotificationBell, NotificationPanel, NotificationItem |
| `src/hooks/useNotifications.ts` | 알림 polling + mark as read |
| `src/types/notification.ts` | Notification, NotificationType |

---

## 6. Wave 3: Compliance & Collaboration (COMPLETE)

### 6.1 Activity Log / Audit Trail

**경로:** `/admin/activity`

**구현 내용:**

- KPI Cards: Total Activities, Today, Active Users, Export(CSV)
- Table/Timeline 뷰 토글
- Filter Bar: 사용자, 모듈, 액션 유형, 날짜 범위
- CSV Export: 클라이언트 사이드 CSV 생성 + 다운로드
- Pagination: Previous/Next 버튼
- Access Guard: `audit:view` 권한 필요

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/pages/admin/ActivityLogPage.tsx` | 감사 추적 메인 페이지 |
| `src/components/activity/ActivityFilterBar.tsx` | 필터 컨트롤 |
| `src/components/activity/ActivityTimeline.tsx` | 수직 타임라인 뷰 |
| `src/hooks/useActivityLog.ts` | paginated 조회 + export |
| `src/types/activity.ts` | ActivityLogItem, ActivityLogFilter, PaginatedActivityLog |

---

### 6.2 Team Collaboration

**구현 파일:**

| 파일 | 역할 |
| --- | --- |
| `src/components/collaboration/` | CommentThread, TeamAssignment, MentionInput 등 |
| `src/hooks/useComments.ts` | 댓글 CRUD |
| `src/hooks/useTeamMembers.ts` | 팀 멤버 관리 |
| `src/types/collaboration.ts` | Comment, TeamMember 등 |

---

## 7. 추가 구현: KIIS 모듈

**경로:** `/kiis/*`

**이전 상태:** stub 페이지만 존재
**현재 상태:** 전체 모듈 구현 완료

| 카테고리 | 파일 수 | 내용 |
| --- | --- | --- |
| Pages | 10 | Dashboard, CompanyList/Detail, FundList/Detail, ReitList/Detail, NewsList/Detail, DealSourcing, SanctionList, Watchlist |
| Hooks | 10 | useDashboard, useCompanies, useFunds, useReits, useNews, useDeals, useSanctions, useWatchlist, useSearch, useAnalysis |
| Types | 10 | company, fund, reit, news, deal, sanction, analysis, watchlist, dashboard, search |
| Components | 5 | SearchBar, ReputationBadge, SentimentIndicator, CompanyFinancials, DealTrendChart |

**라우팅:** `src/modules/kiis/KiisRoutes.tsx` (수정됨)

---

## 8. 추가 구현: IM 모듈

**경로:** `/im/*`

**이전 상태:** stub 페이지만 존재
**현재 상태:** 전체 모듈 구현 완료

| 카테고리 | 파일 수 | 내용 |
| --- | --- | --- |
| Pages | 4 | DocumentList, DocumentDetail, CreateDocument, Templates |
| Hooks | 2 | useDocuments, useCompanies |
| Types | 2 | document, company |
| Components | 3 | DocumentStatusBadge, ProgressTracker, ImErrorBoundary |

**라우팅:** `src/modules/im/ImRoutes.tsx` (수정됨)

---

## 9. 현재 아키텍처

### 9.1 라우팅 구조 (App.tsx)

```text
/                    -> DashboardPage (Portal Home)
/settings/profile    -> ProfilePage
/admin/users         -> UserManagementPage (user:manage 권한)
/admin/activity      -> ActivityLogPage (audit:view 권한)
/fdd/*               -> FddRoutes (14 pages)
/kiis/*              -> KiisRoutes (10 pages)
/im/*                -> ImRoutes (4 pages)
/login               -> LoginPage
```

### 9.2 사이드바 구조 (Sidebar.tsx)

```text
[AMIC x PETRA Platform]
-----
[Home]                              (항상 표시, "/" 링크)
-----
[Module Switcher: FDD / KIIS / IM]
[모듈별 내비게이션]
-----
[Favorites]                         (즐겨찾기 항목이 있을 때 표시)
[Recent]                            (최근 방문 항목이 있을 때 표시)
-----
[Admin]                             (user:manage 또는 audit:view 권한 시)
  - Users
  - Activity Log
-----
[User Info -> Settings]             (클릭 시 /settings/profile)
[Sign Out]
```

### 9.3 전체 파일 목록 (포털 기능)

```text
src/
  pages/
    DashboardPage.tsx
    admin/
      AdminRoutes.tsx
      UserManagementPage.tsx
      ActivityLogPage.tsx
    settings/
      SettingsRoutes.tsx
      ProfilePage.tsx
  components/
    DesktopHeader.tsx
    FavoriteButton.tsx
    SidebarFavorites.tsx
    search/                     (CommandPalette 등)
    notifications/              (NotificationBell 등)
    activity/
      ActivityFilterBar.tsx
      ActivityTimeline.tsx
    collaboration/              (CommentThread 등)
  hooks/
    useDashboard.ts
    useUsers.ts
    useProfile.ts
    usePreferences.ts
    useGlobalSearch.ts
    useNotifications.ts
    useActivityLog.ts
    useFavorites.ts
    useRecentItems.ts
    useComments.ts
    useTeamMembers.ts
  types/
    dashboard.ts
    admin.ts
    settings.ts
    search.ts
    notification.ts
    activity.ts
    favorite.ts
    collaboration.ts
  lib/
    storage.ts
```

---

## 10. 빌드 상태

- **TypeScript**: `tsc --noEmit` 통과 (에러 없음)
- **Git**: 모든 변경사항 unstaged (커밋 전)

---

## 11. Wave 4: 미구현 기능 (향후 계획)

### 11.1 Cross-Module Analytics

- 관리자용 실적 현황판 (`/analytics`)
- 모듈별 KPI 집계, 시계열 차트 (Recharts)
- FDD: 딜 수, 평균 사이클, 이슈 분포 / KIIS: 모니터링 기업 수, DART 처리량 / IM: 문서 생성 수
- 기존 FinancialBarChart, TrendLineChart 재사용

### 11.2 Help Center / Onboarding

- 첫 로그인 가이드 투어 (react-joyride 등)
- FDD/KIIS/IM 도메인 용어집 (QoE, NWC, DART, KOFIA 등)
- 키보드 단축키 레퍼런스 모달
- 릴리즈 변경사항

### 11.3 Calendar / Timeline

- 딜 마일스톤 캘린더 뷰 (`/calendar`)
- Deal의 reference_date, period_start, period_end 활용
- 월간 뷰 + 수평 Gantt 타임라인

### 11.4 Data Export Hub

- 모듈간 통합 내보내기 이력 (`/exports`)
- FDD Reports, KIIS Research, IM Documents 통합 관리
- 재다운로드, 배치 다운로드(ZIP)

### 11.5 External Integrations

- 이메일 SMTP 알림
- 캘린더 동기화 (.ics export)
- SSO/SAML 연동
- API Webhook

---

## 12. Backend 확인 필요 사항

FDD 백엔드에 다음 API가 추가되었는지 별도 확인 필요:

| API | 용도 | Frontend에서 호출하는 곳 |
| --- | --- | --- |
| `DELETE /api/v1/auth/users/{id}` | 사용자 비활성화 (soft delete) | `useDeactivateUser()` (현재 PUT으로 우회) |
| `PATCH /api/v1/auth/me` | 프로필 이름 수정 | `useUpdateProfile()` (현재 PUT /auth/users/{id}로 우회) |
| `POST /api/v1/auth/change-password` | 비밀번호 변경 | `useChangePassword()` |
| `GET /api/v1/health` | 백엔드 health check | `useModuleHealth()` |
| `GET /api/v1/audit/logs` | 감사 로그 조회 | `useActivityLog()` |
| `GET /api/v1/notifications` | 알림 조회 | `useNotifications()` |

> 현재 프론트엔드에서 일부 API는 기존 엔드포인트를 우회 사용 중 (예: deactivate를 PUT is_active=false로 처리).
> 백엔드에 전용 엔드포인트가 추가되면 프론트엔드 훅도 맞춰 업데이트 필요.
