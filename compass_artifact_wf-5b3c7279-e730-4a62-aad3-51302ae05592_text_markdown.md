# The complete pre-push quality gate for FastAPI + React TypeScript

**Ruff, pyright, Vitest, and an AI reviewer—wired into a single GitHub Actions workflow—can give a greenfield fullstack project an enterprise-grade quality gate that runs in under four minutes.** This guide provides the exact tools, configurations, and workflow YAML to set up linting, type checking, test automation, and LLM-powered code review from scratch. Every recommendation reflects the 2025–2026 tooling landscape, where Rust-based tools have displaced legacy Python linters, ESLint 9's flat config has stabilized, and commercial AI review services have matured into production-ready offerings.

---

## 1. Linting and formatting: Ruff dominates Python, ESLint 9 leads TypeScript

### Python: one tool replaces five

**Ruff is the undisputed standard for Python linting and formatting in 2025.** Written in Rust by Astral (the team behind `uv`), it replaces flake8, black, isort, pyupgrade, and bandit in a single binary. FastAPI, Django, pandas, and Pydantic all use Ruff in their own CI. Performance tells the story:

| Tool | Time on ~200K LOC | Relative speed |
|------|-------------------|---------------|
| **Ruff** | 0.2–0.4s | 1× (baseline) |
| Flake8 | ~20s | ~100× slower |
| Pylint | ~2.5 min | ~400× slower |

`ruff format` achieves **>99.9% line-level compatibility with Black** at 30× the speed. There is no reason to use Black for new projects. Ruff ships **900+ built-in rules** from 50+ flake8 plugins plus ~209 Pylint rules, eliminating the need for separate plugin packages.

A production-ready `pyproject.toml` for FastAPI requires special attention to Pydantic and FastAPI's dependency injection patterns:

```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "B", "C4", "UP", "ARG",
    "SIM", "TCH", "S", "RUF", "ASYNC", "N", "PT",
]
ignore = ["B008"]  # Allow function calls in defaults (FastAPI Depends())

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ARG"]

[tool.ruff.lint.flake8-bugbear]
extend-immutable-calls = [
    "fastapi.Depends", "fastapi.Query", "fastapi.Path",
    "fastapi.Body", "fastapi.Header", "fastapi.Security",
]

[tool.ruff.lint.flake8-type-checking]
runtime-evaluated-base-classes = [
    "pydantic.BaseModel", "sqlalchemy.orm.DeclarativeBase",
]
```

The `B008` ignore and `extend-immutable-calls` configuration are **critical for FastAPI projects**—without them, Ruff incorrectly flags `Depends()`, `Query()`, and other dependency injection calls as bugs.

### TypeScript: ESLint 9 flat config with Prettier

For React TypeScript, **ESLint 9 + Prettier remains the safer choice** over Biome. While Biome is 10–25× faster and requires only one package, it still lacks `eslint-plugin-jsx-a11y` for accessibility, has incomplete type-aware linting, and misses several React-specific rules.

| Dimension | ESLint + Prettier | Biome |
|-----------|-------------------|-------|
| Speed (500 files) | 15–30s | 2–3s |
| Dependencies | 8–12 packages | 1 package |
| React ecosystem coverage | Full (hooks, a11y, JSX) | ~85% |
| Type-aware linting | Full | Partial (since v2.0) |
| Plugin ecosystem | Massive, 12+ years | GritQL plugins, growing |
| **Verdict** | **Recommended for full React TS** | Great for simpler projects |

ESLint 9.18+ supports native TypeScript config files (`eslint.config.ts`) and the new `defineConfig()` API. A production flat config:

```typescript
// eslint.config.mjs
import eslint from '@eslint/js';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import prettierConfig from 'eslint-config-prettier';

export default defineConfig(
  { ignores: ['dist/', 'build/', 'coverage/'] },
  eslint.configs.recommended,
  tseslint.configs.recommended,
  reactPlugin.configs.flat.recommended,
  reactPlugin.configs.flat['jsx-runtime'],
  reactHooks.configs.flat.recommended,
  prettierConfig,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-floating-promises': 'error',
      'react/prop-types': 'off',
    },
  },
);
```

### Full-repo linting is fast enough—skip "changed files only" complexity

With Ruff completing a full backend lint in under 1 second and ESLint with caching finishing in seconds, **lint the full project within each job**. The only filtering worth doing is at the job level—skip the entire backend lint job when only frontend files changed—using `dorny/paths-filter`. Changed-files-only linting adds complexity and can miss cross-file issues.

---

## 2. Type checking: pyright for speed, mypy for authority

### Python: the two-checker landscape

**Pytype was deprecated in August 2025** (Google's announcement cites inability to keep pace with modern typing PEPs). Two emerging Rust-based checkers—**ty** (Astral) and **pyrefly** (Meta)—are in alpha and not production-ready. For CI today, the choice is between mypy and pyright.

| Dimension | mypy | pyright |
|-----------|------|---------|
| Speed | Baseline | **3–5× faster** |
| Pydantic v2 support | Official `pydantic.mypy` plugin | Native via PEP 681 (no plugin) |
| Strictness control | ~15 granular flags | 4 levels: off/basic/standard/strict |
| Untyped code handling | Skips unannotated functions by default | Checks everything, infers return types |
| Editor integration | Good (plugins) | **Excellent** (powers VS Code Pylance) |
| Plugin system | Yes (Pydantic, Django, SQLAlchemy) | No |
| Community adoption | ~73% of typed Python projects | Rapidly growing |

Both work well with Pydantic v2 and FastAPI. The practical recommendation: **use pyright as your primary checker** (fast, zero-config Pydantic support, matches VS Code behavior) and optionally add mypy as a secondary gate if you need its plugin ecosystem.

One critical pitfall applies to both: **FastAPI's `Depends()` erases return types.** Always use the `Annotated` pattern:

```python
from typing import Annotated
from fastapi import Depends

DBDep = Annotated[AsyncSession, Depends(get_db)]

@app.get("/")
async def root(db: DBDep):  # Type preserved for both mypy and pyright
    ...
```

### TypeScript: strict mode from day one

Use `tsc --noEmit` with these settings enabled from the start—retrofitting strictness later is painful:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/tsbuildinfo",
    "noEmit": true
  }
}
```

`strict: true` enables 8 strictness flags at once. **`noUncheckedIndexedAccess`** (not included in `strict`) adds `| undefined` to array and object indexing—it catches real bugs and is highly recommended. `skipLibCheck: true` is essential for CI performance, skipping `.d.ts` file checking.

### Caching matters for type checkers

Cache mypy's `.mypy_cache` directory between CI runs (cuts check time from minutes to seconds on medium codebases). For TypeScript, cache the `.tsbuildinfo` file with `incremental: true`. Pyright is fast enough that caching is less critical.

---

## 3. Test automation: async pytest fixtures and Vitest

### FastAPI testing: httpx AsyncClient is the standard

The 2025 pattern uses `httpx.AsyncClient` with `ASGITransport` for native async testing. The older `TestClient` (from Starlette) runs async code synchronously and breaks with complex async workflows:

```python
# tests/conftest.py
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.main import app
from app.db import get_session

@pytest_asyncio.fixture(scope="function")
async def async_db(async_db_engine):
    session_factory = async_sessionmaker(bind=async_db_engine, class_=AsyncSession)
    async with session_factory() as session:
        await session.begin()
        yield session
        await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def client(async_db):
    app.dependency_overrides[get_session] = lambda: async_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

Configure pytest-asyncio in **auto mode** to avoid decorating every test:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-v --cov=app --cov-report=xml --cov-fail-under=80 --timeout=30 -n auto"
```

For database tests, **testcontainers-python** spins up a real PostgreSQL container (GitHub Actions runners include Docker), giving integration-test fidelity without SQLite compatibility issues. For unit tests, the transaction rollback pattern provides speed with isolation.

### React testing: Vitest has won

**Vitest is the standard for React projects using Vite.** Benchmarks consistently show **4–10× faster execution than Jest**, with native ESM and TypeScript support that eliminates the Babel/ts-jest configuration pain. The API is ~95% Jest-compatible, making migration trivial. The only reason to stay on Jest is React Native or a large legacy Jest infrastructure.

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/testing/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'lcov'],
      thresholds: { lines: 80, branches: 80, functions: 80, statements: 80 },
    },
  },
});
```

Use **MSW (Mock Service Worker) v2** for API mocking—it intercepts at the network level, works in both browser and Node, and avoids brittle `fetch` mocking.

### Coverage enforcement

**80% coverage** across lines, branches, and functions is the widely accepted industry threshold (Google's internal guidance calls 60% acceptable, 75% commendable, 90% exemplary). Enforce this in CI:

- **Python:** `pytest --cov-fail-under=80` fails the pipeline if coverage drops below threshold
- **Vitest:** The `thresholds` configuration in `vitest.config.ts` exits with error code on violation
- **PR reporting:** Use `MishaKav/pytest-coverage-comment` for Python and `davelosert/vitest-coverage-report-action` for Vitest to post coverage summaries as PR comments

### Parallel execution

Use `pytest-xdist` (`-n auto`) for Python and Vitest's native worker threads for TypeScript. For large test suites, both support sharding across GitHub Actions matrix jobs: `pytest --splits 4 --group ${{ matrix.group }}` or `vitest run --shard=${{ matrix.shard }}/4`.

---

## 4. LLM-powered code review: three tiers of investment

### Commercial tools comparison

The AI code review market matured significantly in 2025. Amazon CodeGuru was **deprecated in November 2025**. The viable options:

| | CodeRabbit | Copilot Code Review | Qodo PR-Agent | Custom (Claude API) |
|---|---|---|---|---|
| **Cost (10 devs/mo)** | $240–300 | $190–390 (bundled) | Free (OSS) | $15–45 API only |
| **Setup** | 2-click GitHub app | Built into GitHub | GitHub Action | Medium (custom code) |
| **Review quality** | High (46% bug detection) | Moderate | High (best F1 score) | Model-dependent |
| **Customizability** | High (YAML + NL rules) | Low | High (BYO model) | Full control |
| **Self-host option** | Enterprise only | No | Yes (Docker) | Yes (Ollama/vLLM) |
| **Security** | SOC 2 Type II, zero retention | SOC 2 via Microsoft | Zero retention | Provider-dependent |

**CodeRabbit** ($24/dev/month) is the market leader with the deepest feature set—AST-based analysis combined with LLM reasoning, agentic workflows, and a learning system. **Qodo's PR-Agent** is the best open-source option, self-hostable with your own API keys. **GitHub Copilot Code Review** has the lowest friction (already included in Copilot plans) but delivers shallower analysis.

### Custom integration with Claude

Anthropic provides an official GitHub Action (`anthropics/claude-code-action`) that's production-ready:

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on:
  pull_request:
  issue_comment:
    types: [created]

jobs:
  claude-review:
    if: github.event_name == 'pull_request' ||
        contains(github.event.comment.body, '@claude')
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

This supports `@claude` mentions in PR comments, respects a `CLAUDE.md` project guidelines file, and intelligently switches between review and Q&A modes. For a team of 10 developers making ~5 PRs/day each, **Claude Sonnet costs roughly $15–45/month**—an order of magnitude cheaper than commercial tools.

### Prompting best practices for automated review

When building custom LLM review (or configuring tools like PR-Agent), structure your system prompt to mirror your code review checklist: define the reviewer persona, specify priority categories (critical/warning/suggestion), instruct it to output structured JSON for parsing, and explicitly tell it to skip bikeshedding. For large PRs exceeding context limits, chunk by file, review each independently, then generate an overall summary. Always exclude lock files, generated code, and `.d.ts` declarations via file filters.

**Always make AI review non-blocking**—post as PR comments, not required status checks. Use `continue-on-error: true` in the workflow so API outages never block merges.

---

## 5. The complete pipeline: one workflow, parallel jobs, under four minutes

### Architecture: single workflow with path-filtered parallel jobs

The critical architectural insight is using **one workflow file with `dorny/paths-filter`** rather than separate workflow files with `on.paths` triggers. Separate workflows create the notorious "required but skipped" problem—a skipped workflow's status check stays "Pending" forever, blocking PR merges. A single workflow that always triggers, with jobs conditionally skipped via `if:`, reports skipped jobs as passing.

The **`re-actors/alls-green` quality gate pattern** ties it together: a single `quality-gate` job that depends on all other jobs, accepts skipped jobs as passing, and serves as the only required branch protection check.

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write

jobs:
  # ── Change Detection ──────────────────────────────────
  detect-changes:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
      ci: ${{ steps.filter.outputs.ci }}
    steps:
      - uses: actions/checkout@v4
        if: github.event_name == 'push'
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'shared/**'
              - 'pyproject.toml'
            frontend:
              - 'frontend/**'
              - 'shared/**'
              - 'package.json'
              - 'tsconfig*.json'
            ci:
              - '.github/**'

  # ── Backend: Lint ─────────────────────────────────────
  backend-lint:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true' || needs.detect-changes.outputs.ci == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }
      - uses: astral-sh/setup-uv@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: uv sync --dev
      - run: uv run ruff check . --output-format=github
      - run: uv run ruff format --check .

  # ── Backend: Type Check ───────────────────────────────
  backend-typecheck:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true' || needs.detect-changes.outputs.ci == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }
      - uses: astral-sh/setup-uv@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: uv sync --dev
      - uses: actions/cache@v4
        with:
          path: backend/.mypy_cache
          key: mypy-${{ hashFiles('backend/**/*.py') }}
          restore-keys: mypy-
      - run: uv run mypy app/ --show-error-codes --pretty

  # ── Backend: Test ─────────────────────────────────────
  backend-test:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true' || needs.detect-changes.outputs.ci == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }
      - uses: astral-sh/setup-uv@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: uv sync --dev
      - run: uv run pytest --cov=app --cov-report=xml --cov-fail-under=80 -n auto --timeout=60
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/testdb

  # ── Frontend: Lint ────────────────────────────────────
  frontend-lint:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true' || needs.detect-changes.outputs.ci == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx eslint . --max-warnings=0
      - run: npx prettier --check .

  # ── Frontend: Type Check ──────────────────────────────
  frontend-typecheck:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true' || needs.detect-changes.outputs.ci == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx tsc --noEmit --pretty

  # ── Frontend: Test ────────────────────────────────────
  frontend-test:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true' || needs.detect-changes.outputs.ci == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx vitest run --coverage

  # ── AI Code Review (PRs only, non-blocking) ──────────
  ai-review:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}

  # ── Quality Gate (the ONLY required status check) ─────
  quality-gate:
    if: always()
    needs:
      - backend-lint
      - backend-typecheck
      - backend-test
      - frontend-lint
      - frontend-typecheck
      - frontend-test
    runs-on: ubuntu-latest
    steps:
      - uses: re-actors/alls-green@release/v1
        with:
          allowed-skips: >-
            backend-lint, backend-typecheck, backend-test,
            frontend-lint, frontend-typecheck, frontend-test
          jobs: ${{ toJSON(needs) }}
```

### Why this architecture works

The `concurrency` block with `cancel-in-progress: true` automatically cancels stale runs when new commits are pushed, saving CI minutes. `fetch-depth: 1` (shallow clone) saves 5–30 seconds per job. All six check jobs run **in parallel** after the 5-second change detection step, and each completes in **60–120 seconds** with caching. Total wall-clock time is typically **2–4 minutes**.

The AI review job runs independently and is deliberately excluded from the quality gate—it's advisory only. Store `ANTHROPIC_API_KEY` in GitHub repository secrets (Settings → Secrets → Actions). For AWS-hosted teams, use OIDC with Bedrock to avoid static API keys entirely.

### Branch protection: one required check

In repository Settings → Branches → Protection rules for `main`:

- Require pull request before merging (1+ approval)
- Require status checks to pass: add **`quality-gate`** as the only required check
- Require conversation resolution before merging
- Optionally enable merge queue (valuable for teams with 10+ active contributors)

The `quality-gate` job passes when all jobs pass or are legitimately skipped via path filtering. It fails if any job fails. This solves the "required but skipped" problem that plagues multi-workflow monorepo setups.

---

## Conclusion: the recommended tool stack

The full quality gate for a FastAPI + React TypeScript monorepo in 2025–2026 distills to a surprisingly small set of tools. **Ruff** (lint + format + import sort) replaces five Python tools in one sub-second binary. **Pyright** or **mypy** with the `Annotated` pattern handles Python type safety with Pydantic v2. **ESLint 9 flat config + Prettier** covers TypeScript with full React ecosystem support. **Vitest** has replaced Jest as the default for Vite-based React testing. And **Anthropic's claude-code-action** provides production-ready AI review at a fraction of the cost of commercial alternatives.

The most impactful architectural decisions are not tool choices but pipeline design: a single workflow file with `dorny/paths-filter` for change detection, all jobs running in parallel, `re-actors/alls-green` as a unified quality gate, and aggressive caching throughout. This pattern achieves sub-4-minute feedback loops while correctly handling the monorepo path-filtering edge cases that trip up most teams. Start with this workflow as-is, adjust coverage thresholds and linting rules to match your team's standards, and iterate from there.