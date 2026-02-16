# AMIC x PETRA Platform - Claude Code Rules

## Project Overview
AMIC x PETRA Platform — 통합 금융 분석 프론트엔드.
3개 모듈: Auto FDD (실사 자동화), KIIS (투자정보), IM Generator (투자제안서).
React 19 SPA, 모듈별 FastAPI 백엔드 연동.

## Tech Stack
- Language: TypeScript 5.7+ (strict mode)
- Framework: React 19, React Router 7
- Build: Vite 6
- Data Fetching: TanStack React Query v5, Axios
- Styling: Tailwind CSS 3 (custom `amic` theme)
- Charts: Recharts 3
- UI: Custom component library (`src/components/ui/`)
- Icons: Lucide React
- Notifications: Sonner
- Linting: ESLint 9 (flat config) + Prettier 3

## Project Structure
- `src/modules/fdd/` — FDD module (**fully implemented, reference**)
- `src/modules/kiis/` — KIIS module (stub, Phase 2)
- `src/modules/im/` — IM module (stub, Phase 3)
- `src/components/ui/` — Shared UI: Badge, Breadcrumbs, Button, Card, DataTable, EmptyState, Input, KpiCard, LiveRegion, Modal, SectionHeader, Select, Skeleton, Spinner
- `src/components/layout/` — AppShell, Sidebar, ModuleSwitcher
- `src/components/charts/` — Recharts wrappers
- `src/components/auth/` — AuthContext, AuthProvider
- `src/api/client.ts` — API client factory (`createApiClient(baseURL)`)
- `src/api/{fdd,kiis,im}Client.ts` — Per-module API instances
- `src/hooks/useAuth.ts` — Auth hook (JWT, token refresh)
- `src/types/auth.ts` — Auth types
- `src/lib/` — Utilities (cn, format, statusVariant)

## API Proxy (Vite)
- `/api/fdd` → `localhost:8000/api/v1` (FDD backend)
- `/api/kiis` → `localhost:8001/api/v1` (KIIS backend)
- `/api/im` → `localhost:8002/api/v1` (IM backend)

## Code Style
- Functional components only (no class components)
- Named exports for components/types; default export for route components
- Custom hooks: `use{Resource}` pattern with TanStack React Query
- Type imports: `import type { ... }` (isolatedModules)
- Path alias: `@/` maps to `src/`
- Tailwind classes only (no inline styles, no CSS modules)
- Brand colors: use `amic-*`, `accent`, `positive`, `negative`, `caution` tokens

## Commands
- `npm run dev` — Dev server (port 5173)
- `npm run build` — Production build (`tsc -b && vite build`)
- `npm run lint` — ESLint (`--max-warnings 0`)
- `npm run lint:fix` — ESLint auto-fix
- `npm run format` — Prettier format
- `npm run format:check` — Prettier check

## IMPORTANT Rules
- IMPORTANT: Follow FDD module patterns for all new module development
- IMPORTANT: Never edit `.env`, `package-lock.json`, or `node_modules/`
- IMPORTANT: All API hooks must use `createApiClient` factory, not raw axios
- IMPORTANT: Query keys must be descriptive arrays: `["resource", id, ...params]`
- IMPORTANT: Use `isPending` (not `isLoading`) for mutation loading state (TanStack Query v5)
- IMPORTANT: Every new component must be accessible (ARIA labels, keyboard nav)
- IMPORTANT: Run `npm run build` before committing to catch type errors
- IMPORTANT: New shared UI components must be barrel-exported from `components/ui/index.ts`
- IMPORTANT: Module files stay in `src/modules/{module}/` — never in shared dirs

## Module Development Pattern (from FDD)
```
src/modules/{name}/
  {Name}Routes.tsx          # Route definitions (default export)
  pages/                    # Page components (default export)
  components/               # Module-specific components
  hooks/                    # TanStack Query hooks (use{Resource})
  types/                    # TypeScript interfaces and union types
```

## API Hook Pattern (from FDD — `src/modules/fdd/hooks/useDeals.ts`)
```typescript
export function use{Resource}s() {
  return useQuery<{Resource}[]>({
    queryKey: ["{resource}s"],
    queryFn: async () => {
      const { data } = await {mod}Api.get("/{resource}s");
      return data;
    },
  });
}

export function useCreate{Resource}() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {Resource}Create) => {
      const { data } = await {mod}Api.post("/{resource}s", body);
      return data as {Resource};
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["{resource}s"] }),
  });
}
```

## Agent Orchestration

### 코드 리뷰 에이전트 (Verified Claim Protocol 적용)
- @code-reviewer: 프론트엔드 코드 리뷰 (패턴, 상태관리, 에러처리, a11y, TypeScript, 성능, UX)
- @api-auditor: FE-BE API 통합 리뷰 (프록시, 인증, 타입 일치, URL 경로)
- @security-auditor: 보안 리뷰 (인증, 입력검증, LLM 보안, CORS, 시크릿, 데이터보호)
- @test-auditor: 테스트 품질 리뷰 (유닛+E2E, Mock 정확성, 커버리지 갭)
- @perf-auditor: 성능 리뷰 (번들, 렌더링, 네트워크, CSS, Vite)
- @infra-auditor: 인프라 리뷰 (Docker, Nginx, CI/CD, 환경변수)
- @review-verifier: 코드 리뷰 검증 (5단계 판정, 허위 양성 6종 분류, 인라인 교차 검증)

### 기존 에이전트 (VCP 임베드됨)
- @type-checker: TypeScript 타입 안전성 검증
- @accessibility-auditor: WCAG 2.1 접근성 감사
- @test-runner: 테스트 실행 및 커버리지 분석

### 하위 호환 (deprecated → 포워드)
- @component-reviewer → @code-reviewer
- @api-integration-debugger → @api-auditor

## Skill References
- 새 모듈 페이지 → `new-module-page`
- 새 UI 컴포넌트 → `new-component`
- API 훅 생성 → `api-hook`
- 모듈 스캐폴딩 → `module-scaffold`
- API 디버깅 → `debug-api`
- 코드 리뷰 검증 → `verify-review` (`/verify-review`)
- 코드 리뷰 오케스트레이션 → `review-orchestrate` (내부 사용)

## Review Commands
- `/review [scope]` — 기본 코드 리뷰 (code-reviewer 단일)
- `/review-full [scope]` — 멀티 에이전트 전체 리뷰
- `/review-security [scope]` — 보안 집중 리뷰
- `/review-test [scope]` — 테스트 품질 리뷰
- `/review-perf [scope]` — 성능/번들 리뷰
- `/review-infra [scope]` — 인프라/배포 리뷰

## 작업 방식 규칙 — LLM 코드 리뷰 검증 필수

- IMPORTANT: 코드 리뷰 항목을 수정하기 전, 반드시 `/verify-review`로 소스 대조 검증을 수행
- IMPORTANT: 검증 없이 리뷰 이슈를 수정하는 것을 절대 금지 — 허위 양성 수정은 코드 품질을 오히려 저하시킴
- IMPORTANT: 코드 리뷰 작성 시에도 반드시 Read/Grep으로 실제 코드를 확인한 뒤 클레임할 것
- 주의 유형: "없다" 클레임(실제로는 존재), 코드 스니펫 환각(실제와 다른 코드 인용), 라인 번호 오류(±5 이상 이동)
- 허위 양성 판정 기준: 이미 구현됨(FP-IMPL), 코드 환각(FP-HALLUC), 라인 오류(FP-LINE), 로직 오해(FP-LOGIC), 컨텍스트 누락(FP-CTX), 심각도 과장(FP-SEV)
- 검증 결과 유효 이슈(정확 + 부분 정확)만 수정 대상으로 진행

## 작업 방식 규칙 — 컨텍스트 한계 관리
- IMPORTANT: 컨텍스트 윈도우가 부족해질 것으로 예상되면 즉시 작업을 중단
- 중단 시: 완료/미완료 목록, 컨텍스트 요약을 `CLAUDE.local.md`에 기록
- IMPORTANT: 컨텍스트 부족 상태에서 억지로 작업을 계속하는 것을 절대 금지

## Workflow
1. 새 기능: 계획 수립 (plan mode 또는 `/plan`)
2. 구현: FDD 패턴 참조, 타입 먼저 정의
3. 검증: `npm run lint && npm run build`
4. 커밋: feature branch, main 직접 커밋 금지

## When Compacting
컴팩팅 시 반드시 보존할 정보:
- 현재 작업 중인 모듈명과 파일 목록
- 실패한 lint/typecheck 내역
- 진행 중인 Phase (2=KIIS, 3=IM)
- 최근 변경한 파일 경로들
