# TypeScript Rules

## Strict Mode
- `strict: true` is enabled. Never use `any` unless absolutely unavoidable.
- `noUnusedLocals: true` and `noUnusedParameters: true` are enforced.
- Use `unknown` instead of `any` for truly unknown types.

## Type Definitions
- Prefer `interface` for object shapes (extensible).
- Use `type` for unions, intersections, and mapped types.
- Status/enum values: union literal types (`type Status = "DRAFT" | "ACTIVE"`), NOT TypeScript enums.
- Module types live in `src/modules/{mod}/types/`.
- Shared types live in `src/types/`.

## Type Imports
- Always use `import type { ... }` for type-only imports.
- Required by `isolatedModules: true`.

## Generics
- TanStack Query: always specify response type: `useQuery<Deal[]>(...)`.
- Axios responses: cast after destructure: `const { data } = ...; return data as Deal`.
- Mutation functions: type the body parameter explicitly.

## Patterns from FDD
- API response types: match backend Pydantic models exactly.
- Optional fields in Create types: use `?` suffix (e.g., `client_name?: string`).
- Null vs undefined: API returns `null` (use `| null`), optional props use `?`.

## Naming
- Interfaces: PascalCase, no `I` prefix (e.g., `Deal`, not `IDeal`).
- Type aliases: PascalCase (e.g., `DealStatus`).
- Constants: UPPER_SNAKE_CASE for enums/options arrays.
- Files: camelCase for hooks/utils, PascalCase for components.
