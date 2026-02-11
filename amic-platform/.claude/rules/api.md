# API Integration Rules

## Client Architecture
- Factory: `createApiClient(baseURL)` in `src/api/client.ts`.
- Per-module clients: `fddApi` (`/api/fdd`), `kiisApi` (`/api/kiis`), `imApi` (`/api/im`).
- All clients include JWT auth interceptors and auto-refresh on 401.
- Never import raw `axios` in module code — always use module client.

## Vite Proxy
- Dev proxy rewrites: `/api/{mod}` → `localhost:{port}/api/v1`.
- FDD: port 8000, KIIS: port 8001, IM: port 8002.
- All backends are FastAPI with `/api/v1` prefix.

## TanStack React Query Patterns
- Query keys: descriptive arrays `["resource", parentId, childId]`.
- `queryFn`: async arrow, destructure `{ data }` from axios response.
- `enabled`: use `!!id` guard when key depends on a parameter.
- Mutations: always `invalidateQueries` on success for affected keys.
- Error handling: use `onError` callback with `toast.error()` from sonner.
- Success feedback: use `toast.success()` from sonner.

## Query Key Conventions
```
["deals"]                      - all deals
["deals", dealId]              - single deal
["deals", dealId, "uploads"]   - nested resource
```

## Error Handling
- API errors: axios interceptor handles 401 (auto-refresh).
- Network errors: show toast, do not crash the UI.
- Loading states: use `isLoading` for queries, `isPending` for mutations.
- Empty states: use `<EmptyState>` component when data array is empty.

## Authentication Flow
- Login: POST `/auth/login` → store tokens in localStorage.
- Token refresh: automatic via response interceptor (deduplicated).
- Logout: clear tokens, redirect to `/login`.
- Protected routes: `useAuth()` hook from `@/hooks/useAuth.ts`.
