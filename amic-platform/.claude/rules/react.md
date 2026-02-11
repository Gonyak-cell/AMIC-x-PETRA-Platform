# React Rules

## Component Patterns
- Functional components only. Never use class components.
- Default export for page components (one per file).
- Named exports for reusable components and hooks.
- Component file naming: PascalCase (e.g., `DealListPage.tsx`).

## State Management
- Server state: TanStack React Query v5 (`useQuery`, `useMutation`).
- Local UI state: `useState` / `useReducer`.
- No Redux, Zustand, or Jotai unless explicitly requested.

## React 19 Specifics
- Use `React.lazy()` for module-level code splitting (see `App.tsx`).
- Wrap lazy routes in `<Suspense fallback={...}>`.
- Use `useMemo` / `useCallback` only for expensive computations or stable refs.

## Hooks Rules
- Custom hooks must start with `use`.
- Keep hooks in the module's `hooks/` directory.
- One hook file per resource (e.g., `useDeals.ts` for deal CRUD).
- Always pass `enabled: !!id` when query depends on a parameter.
- TanStack Query v5: mutations use `isPending`, NOT `isLoading`.

## JSX Conventions
- Self-closing tags for components without children: `<Component />`.
- Fragments (`<>...</>`) over wrapper `<div>` when no className needed.
- Event handlers: `handle{Action}` naming (e.g., `handleSubmit`, `handleRowClick`).
- Conditional rendering: `&&` for simple, ternary for if/else, early return for complex.

## Imports
- Path alias: `@/` for all src imports.
- UI components: import from `@/components/ui` barrel.
- Icons: import individually from `lucide-react`.
- Module-internal imports: relative paths within the module.
