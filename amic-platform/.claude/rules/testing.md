# Testing Rules

## Framework (To Be Set Up)
- Unit/Integration: Vitest (Vite-native)
- Component Testing: React Testing Library (@testing-library/react)
- API Mocking: MSW (Mock Service Worker)
- E2E (future): Playwright

## Test File Conventions
- Co-locate tests: `src/modules/{mod}/__tests__/` or `*.test.ts(x)` next to source.
- Hook tests: `useDeals.test.ts` testing each exported hook.
- Component tests: `DealListPage.test.tsx` testing render + interactions.
- Utility tests: `format.test.ts` for pure function tests.

## Testing Patterns
- Arrange-Act-Assert structure.
- Mock API responses with MSW handlers matching Vite proxy paths.
- Use `renderHook()` from `@testing-library/react` for custom hook tests.
- Wrap renders in `QueryClientProvider` for TanStack Query hooks.
- Test loading, success, error, and empty states for data-fetching components.

## What to Test
- All custom hooks: query returns, mutation side effects, cache invalidation.
- Page components: renders without crash, displays data, handles interactions.
- Utility functions: all edge cases (null, undefined, empty string, NaN).
- UI components: accessibility (role, aria-label), keyboard interactions.

## What NOT to Test
- Third-party library internals (TanStack Query, React Router).
- Tailwind CSS class names.
- Implementation details (internal state, private methods).

## Commands (once set up)
- `npm run test` — Run all tests
- `npm run test:watch` — Watch mode
- `npm run test:coverage` — Coverage report
