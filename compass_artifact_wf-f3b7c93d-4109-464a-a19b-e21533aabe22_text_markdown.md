# 풀스택 모노레포 CI/CD 품질 게이트 완벽 구축 가이드

**FastAPI + React/TypeScript 모노레포에서 GitHub Actions 기반 pre-deploy 품질 게이트를 구축하려면, 린팅→테스트→보안 스캔→Docker 빌드→배포의 5단계 파이프라인을 설계하고 각 단계를 PR 머지의 필수 통과 조건으로 설정해야 한다.** 이 가이드는 2025년 기준 최신 도구 체인(Ruff, Vitest, Playwright, Trivy, buildx)과 Azure App Service 배포 슬롯 전략까지 포함하는 종합 구현 레퍼런스다. 모든 YAML 예시는 실전 복사-붙여넣기 수준으로 제공하며, 각 도구의 선택 근거와 주의사항을 함께 다룬다.

---

## 전체 파이프라인 아키텍처 흐름

파이프라인은 아래 흐름으로 구성된다. PR 단계에서는 Phase 1~4가 병렬·순차 혼합으로 실행되며, `main` 브랜치 머지 후에만 Phase 5(배포)가 트리거된다.

```
PR 생성/업데이트
  │
  ├─ Phase 0: 변경 감지 (dorny/paths-filter)
  │    ├─ backend/** 변경? → backend jobs 활성화
  │    └─ frontend/** 변경? → frontend jobs 활성화
  │
  ├─ Phase 1: 린팅 & 포맷팅 (병렬)          ─┐
  │    ├─ Backend: Ruff lint + Ruff format + mypy  │
  │    └─ Frontend: ESLint + Prettier + tsc        │
  │                                                 │
  ├─ Phase 2: 유닛 테스트 + 커버리지 (병렬)    ├─ 모두 병렬 실행
  │    ├─ Backend: pytest + coverage ≥80%          │
  │    └─ Frontend: Vitest + coverage ≥80%         │
  │                                                 │
  ├─ Phase 3: 보안 스캔 (병렬)                ─┘
  │    ├─ SAST: Semgrep + Bandit
  │    ├─ SCA: Trivy FS + pip-audit + npm audit
  │    └─ Secrets: Gitleaks
  │
  ├─ Phase 4: Docker 빌드 검증 (Phase 1-3 이후)
  │    ├─ 멀티스테이지 빌드 (--load, push 안 함)
  │    ├─ Trivy 이미지 스캔
  │    └─ 빌드 성공 + 취약점 없음 확인
  │
  ├─ ci-gate (필수 status check)
  │    └─ 모든 Phase 결과 집계 → 하나라도 실패 시 PR 머지 차단
  │
  └─ main 머지 후 (push 이벤트)
       │
       Phase 5: 배포
       ├─ ACR에 이미지 push
       ├─ Staging 슬롯 배포
       ├─ 헬스 체크
       ├─ Production 스왑 (수동 승인)
       └─ 실패 시 자동 롤백
```

---

## 1. 린팅과 포맷팅: Ruff가 모든 것을 대체한다

2025년 Python 린팅의 표준은 **Ruff** 단일 도구다. Rust로 작성되어 기존 도구 대비 **10~200배 빠르며**, Flake8, Black, isort, pyupgrade, autoflake을 모두 대체한다. FastAPI, pandas, pydantic 등 주요 프로젝트가 이미 Ruff로 마이그레이션했다. **Black과 isort는 더 이상 별도로 설치할 필요가 없으며**, mypy만 타입 체킹 전용으로 유지하면 된다.

**Python 백엔드 `pyproject.toml` 핵심 설정:**

```toml
[tool.ruff]
line-length = 88
target-version = "py312"
src = ["backend/app", "backend/tests"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "B", "UP", "N", "S",
    "A", "C4", "DTZ", "T20", "SIM", "RUF",
]
ignore = ["E501", "B008"]  # B008: FastAPI Depends() 허용

[tool.ruff.lint.flake8-bugbear]
extend-immutable-calls = [
    "fastapi.Depends", "fastapi.Query", "fastapi.Path",
    "fastapi.Body", "fastapi.Header"
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**/*.py" = ["S101"]  # assert 허용

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

프론트엔드는 **ESLint v9+ flat config**(`eslint.config.js`)가 새로운 표준이다. `.eslintrc` 포맷은 공식 폐기되었다. Biome(Rust 기반 ESLint+Prettier 대체제)도 React/TS 프로젝트에서 프로덕션 수준으로 성숙했지만, 플러그인 생태계의 깊이에서 ESLint가 아직 우위에 있다.

```js
// eslint.config.js (ESLint v9+ flat config)
import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import prettierRecommended from "eslint-plugin-prettier/recommended";

export default defineConfig([
  { ignores: ["dist/", "coverage/"] },
  ...tseslint.configs.recommendedTypeChecked,
  {
    files: ["**/*.{tsx,jsx}"],
    plugins: { react, "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react/react-in-jsx-scope": "off",
    },
  },
  prettierRecommended, // 반드시 마지막
]);
```

**Pre-commit hooks + CI 조합 패턴**은 "로컬에서 빠르게 잡고, CI에서 엄격하게 강제"가 핵심이다. 로컬 훅은 staged 파일만 검사해 빠른 피드백을 주고, CI는 전체 파일을 검사하는 hard gate 역할을 한다. Python 측은 `pre-commit` 프레임워크로 Ruff + mypy를, 프론트엔드 측은 Husky + lint-staged로 ESLint + Prettier를 실행한다.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        files: ^backend/
        additional_dependencies: [pydantic, fastapi]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.22.1
    hooks:
      - id: gitleaks
```

**GitHub Actions 린트 워크플로우:**

```yaml
# .github/workflows/lint.yml
name: Lint & Type Check
on:
  pull_request:
    branches: [main]
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check . --output-format=github
      - run: ruff format --check .

  backend-typecheck:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: mypy app/ --config-file pyproject.toml

  frontend-lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22", cache: "npm", cache-dependency-path: "frontend/package-lock.json" }
      - run: npm ci
      - run: npx eslint . --max-warnings 0
      - run: npx prettier --check "src/**/*.{ts,tsx,js,jsx,json,css,md}"
      - run: npx tsc --noEmit
```

> **팁:** Ruff의 `--output-format=github` 플래그를 사용하면 린트 오류가 GitHub PR의 파일 diff에 인라인 어노테이션으로 표시된다. `ruff check`와 `ruff format`은 별도 단계로 분리해야 어디서 실패했는지 명확하다.

---

## 2. 유닛 테스트와 커버리지 임계값으로 품질을 강제한다

### FastAPI 백엔드 테스트 패턴

FastAPI 공식 문서는 **`httpx.AsyncClient` + `ASGITransport`** 조합을 비동기 테스트의 표준으로 권장한다. `pytest-asyncio`의 `asyncio_mode = "auto"` 설정을 사용하면 매 테스트마다 `@pytest.mark.asyncio`를 붙일 필요가 없다.

```python
# tests/conftest.py
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.db import Base, get_db

TEST_DB_URL = "postgresql+asyncpg://test:test@localhost:5432/test_db"
engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

외부 API 모킹에는 **`respx`**(httpx 네이티브 모킹 라이브러리)를, 일반 함수 모킹에는 `unittest.mock.patch`를 사용한다. **커버리지 임계값 80%**를 `--cov-fail-under=80`으로 설정하면, 커버리지 미달 시 CI가 자동으로 실패한다.

### React/TypeScript 테스트: Vitest가 2025년 표준

**Vitest는 Vite + React + TypeScript 프로젝트의 확실한 표준**이다. Jest 대비 실제 벤치마크에서 **10배 빠르며**(~50개 컴포넌트 테스트 기준 1.8초 vs 18.7초), 네이티브 ESM/TypeScript 지원으로 별도의 ts-jest나 Babel이 불필요하다. API 모킹에는 **MSW(Mock Service Worker) v2**가 산업 표준이다.

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'lcov'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
});
```

**커버리지 리포팅**은 Codecov의 **flags** 기능으로 백엔드와 프론트엔드를 별도 추적하면서 통합 뷰를 제공받을 수 있다. `codecov.yml`에서 `after_n_builds: 2`로 설정하면 두 job 모두 업로드 완료 후에 PR 코멘트가 생성된다.

```yaml
# GitHub Actions - 테스트 job 발췌
backend-tests:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
      env: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: test_db }
      ports: ["5432:5432"]
      options: >-
        --health-cmd pg_isready --health-interval 10s
        --health-timeout 5s --health-retries 5
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
    - run: pytest --cov=app --cov-report=xml --cov-fail-under=80 -v
      working-directory: backend
      env:
        DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
    - uses: codecov/codecov-action@v5
      with: { files: backend/coverage.xml, flags: backend }

frontend-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: "22", cache: "npm", cache-dependency-path: "frontend/package-lock.json" }
    - run: npm ci
      working-directory: frontend
    - run: npx vitest run --coverage
      working-directory: frontend
    - uses: codecov/codecov-action@v5
      with: { files: frontend/coverage/lcov.info, flags: frontend }
```

---

## 3. E2E 테스트: Playwright + Docker Compose가 정답이다

2025년 기준 **Playwright가 새 프로젝트의 확실한 선택**이다. 2024년 6월 npm 주간 다운로드에서 Cypress를 최초 추월했고, 그 이후 격차가 벌어지고 있다. 핵심 장점은 **무료 병렬 실행(sharding)**, Chromium·Firefox·WebKit 3대 브라우저 네이티브 지원, `codegen`(녹화→테스트 코드 생성), Trace Viewer(타임라인+DOM 스냅샷+네트워크 로그)다. Cypress Cloud의 병렬 실행은 유료(Team $799/년~)인 반면 Playwright의 모든 기능은 무료다.

풀스택 E2E 패턴은 **`docker-compose.ci.yml`로 전체 스택(PostgreSQL + FastAPI + React)을 띄운 뒤, 호스트에서 Playwright를 실행**하는 것이 가장 안정적이다.

```yaml
# docker-compose.ci.yml
services:
  db:
    image: postgres:16
    environment: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: app_test }
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d app_test"]
      interval: 5s
      retries: 20

  backend:
    build: { context: ./backend }
    environment:
      DATABASE_URL: postgresql://test:test@db:5432/app_test
      ENVIRONMENT: testing
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 5s
      retries: 30

  frontend:
    build:
      context: ./frontend
      args: { VITE_API_URL: "http://localhost:8000" }
    ports: ["5173:80"]
    depends_on:
      backend: { condition: service_healthy }
```

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on:
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Start services
        run: docker compose -f docker-compose.ci.yml up -d --build

      - name: Wait for backend
        run: |
          for i in $(seq 1 60); do
            curl -sf http://localhost:8000/health > /dev/null 2>&1 && exit 0
            sleep 3
          done
          docker compose -f docker-compose.ci.yml logs backend
          exit 1

      - name: Seed database
        run: |
          docker compose -f docker-compose.ci.yml exec -T backend alembic upgrade head
          docker compose -f docker-compose.ci.yml exec -T backend python -m app.initial_data

      - uses: actions/setup-node@v4
        with: { node-version: "lts/*" }
      - run: npm ci
        working-directory: frontend
      - run: npx playwright install --with-deps chromium
        working-directory: frontend

      - name: Run E2E tests
        working-directory: frontend
        run: npx playwright test
        env: { BASE_URL: "http://localhost:5173" }

      - uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 14

      - name: Collect logs on failure
        if: failure()
        run: |
          mkdir -p logs
          docker compose -f docker-compose.ci.yml logs > logs/all.log 2>&1
      - uses: actions/upload-artifact@v5
        if: failure()
        with: { name: container-logs, path: logs/ }

      - if: always()
        run: docker compose -f docker-compose.ci.yml down -v
```

**Playwright 설정 핵심:**

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'tests/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
});
```

> **팁:** CI에서는 `workers: 1`로 안정성을 확보하되, **matrix + `--shard`**로 여러 머신에 분산하면 전체 실행 시간을 크게 단축할 수 있다. 아티팩트는 `if: ${{ !cancelled() }}`로 실패 시에도 반드시 업로드해야 디버깅이 가능하다.

---

## 4. 보안 스캔은 PR 시점에 빠르게, 스케줄로 깊게

### SAST 도구 조합 전략

| 도구 | 용도 | 속도 | PR 시점 | 스케줄 |
|------|------|------|---------|--------|
| **Semgrep** | Python + TS 멀티언어 SAST | ~12초/500K LoC | ✅ (블로킹) | – |
| **Bandit** | Python 전용 심층 검사 | ~28초/500K LoC | ✅ (경고만) | – |
| **CodeQL** | 크로스파일 데이터플로우 분석 | 수 분 | – | ✅ (주 1회) |

**Semgrep이 PR 단계의 핵심 SAST**다. `--config auto`로 Python과 TypeScript를 동시에 커버하며, SARIF 출력으로 GitHub Security 탭에 통합된다. Bandit은 Python 전용 AST 분석으로 Semgrep이 놓치는 Python 관용구를 잡아낸다. CodeQL은 느리지만 복잡한 크로스파일 취약점 발견에 강력하므로 주 1회 스케줄 실행이 적절하다.

### SCA + Docker 이미지 스캔 + 시크릿 탐지

```yaml
# .github/workflows/security.yml (핵심 발췌)
jobs:
  semgrep:
    runs-on: ubuntu-latest
    container: { image: semgrep/semgrep }
    steps:
      - uses: actions/checkout@v4
      - run: semgrep scan --config auto --config p/security-audit --sarif -o semgrep.sarif
      - uses: github/codeql-action/upload-sarif@v4
        with: { sarif_file: semgrep.sarif }
        if: always()

  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pip-audit && pip install -r backend/requirements.txt
      - run: pip-audit --strict -f json -o pip-audit.json || true
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: cd frontend && npm ci && npm audit --audit-level=high || true
      - uses: aquasecurity/trivy-action@0.33.1
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          format: 'sarif'
          output: 'trivy-fs.sarif'
      - uses: github/codeql-action/upload-sarif@v4
        with: { sarif_file: trivy-fs.sarif }

  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
```

**Dependabot 설정**(`.github/dependabot.yml`)에서는 `pip`, `npm`, `docker`, `github-actions` 4개 생태계를 주간 스캔하고, `groups`로 minor/patch 업데이트를 묶어 PR 노이즈를 줄이는 것이 핵심이다.

**Docker 이미지 스캔**은 ACR push 전에 Trivy로 CRITICAL/HIGH 취약점을 차단한다. `exit-code: '1'`로 발견 시 파이프라인을 실패시키고, 별도 단계에서 SARIF를 GitHub Security 탭에 업로드한다. `ignore-unfixed: true`로 수정 불가능한 취약점의 노이즈를 제거한다.

> **팁:** 오탐 관리가 중요하다. Semgrep은 `# nosemgrep: rule-id`, Bandit은 `# nosec B602`, Trivy는 `.trivyignore` 파일로 관리한다. 시크릿 탐지(Gitleaks)는 `fetch-depth: 0`(전체 히스토리)이 필수다.

---

## 5. Docker 빌드 검증과 레이어 캐싱 전략

### 멀티스테이지 빌드 패턴

**FastAPI Dockerfile** (핵심):
```dockerfile
FROM python:3.13-slim AS deps-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-slim AS production
RUN groupadd -r api && useradd -r -g api api
WORKDIR /app
COPY --from=deps-builder /install /usr/local
COPY ./app ./app
USER api
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8000/health || exit 1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**React Dockerfile** (핵심):
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --frozen-lockfile
COPY . .
RUN npm run build

FROM nginx:stable-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### CI에서 빌드 검증 (push 없이)

**`docker/build-push-action`의 `load: true` 옵션**이 핵심이다. 이미지를 로컬 Docker 데몬에 로드하되 레지스트리에 push하지 않는다. 로드된 이미지로 smoke test를 실행한 후, main 브랜치에서만 push한다.

```yaml
- uses: docker/setup-buildx-action@v3

- uses: docker/build-push-action@v6
  with:
    context: ./backend
    load: true          # 로컬 로드만
    push: false
    tags: myapp-backend:test
    cache-from: type=gha
    cache-to: type=gha,mode=max

- name: Smoke test
  run: |
    docker run --rm -d -p 8000:8000 --name test myapp-backend:test
    sleep 5
    curl -f http://localhost:8000/health || exit 1
    docker stop test
```

**레이어 캐싱**은 `type=gha` (GitHub Actions 캐시 백엔드)가 가장 간편하다. 10GB 제한 내에서 자동 관리되며, `mode=max`로 모든 중간 레이어를 캐싱한다. 여러 서비스를 빌드하는 모노레포에서는 `scope` 파라미터로 캐시 충돌을 방지한다.

---

## 6. 모노레포 GitHub Actions 워크플로우 설계의 핵심 패턴

### Path filter로 불필요한 실행을 차단한다

`dorny/paths-filter@v3`로 변경된 디렉터리를 감지하고, 관련 없는 job은 건너뛴다. **모노레포에서 가장 중요한 패턴**이다.

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    permissions: { pull-requests: read }
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'shared/**'
            frontend:
              - 'frontend/**'
              - 'shared/**'

  backend-lint:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    # ...
```

### ci-gate 패턴으로 branch protection 문제를 해결한다

조건부 job이 건너뛰어지면 GitHub는 해당 status check를 "pending"으로 표시해 PR 머지를 영원히 차단하는 문제가 있다. **해결책은 항상 실행되는 gate job 하나를 만들어 이것만 required status check로 설정하는 것이다.**

```yaml
  ci-gate:
    if: always()
    needs: [backend-lint, frontend-lint, backend-tests, frontend-tests, security]
    runs-on: ubuntu-latest
    steps:
      - run: |
          results=("${{ needs.backend-lint.result }}" "${{ needs.frontend-lint.result }}" \
                   "${{ needs.backend-tests.result }}" "${{ needs.frontend-tests.result }}" \
                   "${{ needs.security.result }}")
          for r in "${results[@]}"; do
            if [[ "$r" == "failure" ]]; then
              echo "❌ Quality gate failed"
              exit 1
            fi
          done
          echo "✅ All quality gates passed"
```

Branch Protection 설정에서 `ci-gate`만 required check로 지정하면, 조건부로 건너뛴 job은 "skipped"로 처리되어 머지를 차단하지 않는다.

### Reusable workflow로 DRY한 파이프라인을 만든다

Docker 빌드처럼 백엔드/프론트엔드에서 반복되는 로직은 `workflow_call`로 재사용 워크플로우로 추출한다.

```yaml
# .github/workflows/docker-build.yml
on:
  workflow_call:
    inputs:
      context: { required: true, type: string }
      image-name: { required: true, type: string }

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: ${{ inputs.context }}
          load: true
          push: false
          tags: ${{ inputs.image-name }}:${{ github.sha }}
          cache-from: type=gha,scope=${{ inputs.image-name }}
          cache-to: type=gha,mode=max,scope=${{ inputs.image-name }}
```

호출 측에서는 `uses: ./.github/workflows/docker-build.yml`로 간결하게 사용한다. `secrets: inherit`로 시크릿을 자동 전달할 수 있다.

### Concurrency 그룹으로 리소스를 절약한다

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.ref }}
  cancel-in-progress: true  # 테스트 job은 이전 실행 취소
```

**배포 job에는 `cancel-in-progress: false`를 사용해야 한다.** 진행 중인 배포를 절대 취소해서는 안 된다.

---

## 7. Azure App Service 배포: OIDC + 슬롯 스왑 전략

### OIDC 인증이 2025년 표준이다

장기 보관 시크릿 대신 **OIDC 페더레이션 자격 증명**을 사용하면 GitHub가 워크플로우 실행마다 단기 토큰을 발급하고, Azure가 이를 검증해 접근을 허가한다. **비밀번호 로테이션이 불필요하다.**

설정 순서: Azure AD 앱 등록 → 서비스 주체 생성 → 역할 할당(Contributor + AcrPush) → 페더레이션 자격 증명 생성(`subject` 필드에 `repo:OWNER/REPO:ref:refs/heads/main` 또는 `repo:OWNER/REPO:environment:production` 지정).

```yaml
permissions:
  id-token: write   # OIDC에 필수
  contents: read

steps:
  - uses: azure/login@v2
    with:
      client-id: ${{ secrets.AZURE_CLIENT_ID }}
      tenant-id: ${{ secrets.AZURE_TENANT_ID }}
      subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

  - name: Login to ACR
    run: az acr login --name ${{ env.ACR_NAME }}
```

### 배포 슬롯 + 스왑 + 롤백 전체 흐름

품질 게이트를 모두 통과한 후의 배포 워크플로우는 5단계로 구성된다:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure
on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

env:
  AZURE_WEBAPP_NAME: my-app
  ACR_NAME: myregistry
  IMAGE_NAME: myapp
  RESOURCE_GROUP: my-rg

jobs:
  # 1. ACR에 이미지 Push
  build-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: az acr login --name ${{ env.ACR_NAME }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      # Trivy 이미지 스캔 (push 후 최종 검증)
      - uses: aquasecurity/trivy-action@0.33.1
        with:
          image-ref: '${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'

  # 2. Staging 슬롯 배포
  deploy-staging:
    needs: build-push
    runs-on: ubuntu-latest
    environment: { name: staging, url: 'https://${{ env.AZURE_WEBAPP_NAME }}-staging.azurewebsites.net' }
    steps:
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ env.AZURE_WEBAPP_NAME }}
          slot-name: staging
          images: '${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}'

  # 3. 헬스 체크
  health-check:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
      - run: sleep 30
      - run: |
          for i in $(seq 1 10); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
              "https://${{ env.AZURE_WEBAPP_NAME }}-staging.azurewebsites.net/health" --max-time 10)
            [ "$STATUS" = "200" ] && echo "✅ Healthy" && exit 0
            echo "Attempt $i: $STATUS"
            sleep 15
          done
          exit 1

  # 4. Production 스왑 (수동 승인 필요)
  swap-production:
    needs: health-check
    runs-on: ubuntu-latest
    environment: { name: production, url: 'https://${{ env.AZURE_WEBAPP_NAME }}.azurewebsites.net' }
    concurrency: { group: deploy-production, cancel-in-progress: false }
    steps:
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - uses: azure/cli@v2
        with:
          inlineScript: |
            az webapp deployment slot swap \
              --resource-group ${{ env.RESOURCE_GROUP }} \
              --name ${{ env.AZURE_WEBAPP_NAME }} \
              --slot staging --target-slot production
      - name: Production 헬스 체크
        run: |
          for i in $(seq 1 5); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
              "https://${{ env.AZURE_WEBAPP_NAME }}.azurewebsites.net/health" --max-time 10)
            [ "$STATUS" = "200" ] && exit 0
            sleep 10
          done
          exit 1

  # 5. 롤백 (스왑 실패 시)
  rollback:
    needs: swap-production
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - uses: azure/cli@v2
        with:
          inlineScript: |
            az webapp deployment slot swap \
              --resource-group ${{ env.RESOURCE_GROUP }} \
              --name ${{ env.AZURE_WEBAPP_NAME }} \
              --slot staging --target-slot production
```

**롤백 원리가 우아하다.** 스왑 후에는 이전 프로덕션 코드가 staging 슬롯에 남아 있으므로, 다시 한 번 swap하면 즉시 이전 버전으로 복원된다. GitHub Environments의 `production` 환경에 **required reviewers**를 설정하면 swap 전 수동 승인이 필수가 된다.

> **팁:** 이미지 태그는 항상 `${{ github.sha }}`를 사용해 추적성을 확보한다. `latest` 태그는 프로덕션에서 절대 사용하지 않는다. 페더레이션 자격 증명은 브랜치/환경별로 별도 생성해 최소 권한 원칙을 지킨다.

---

## 결론: 실전 적용 시 기억할 핵심 원칙

이 가이드의 전체 파이프라인을 한 번에 구현하려 하지 말고, **Phase 1(린팅) → Phase 2(유닛 테스트) → ci-gate → 배포** 순서로 점진적으로 추가하는 것이 현실적이다. 보안 스캔과 E2E 테스트는 기본 파이프라인이 안정된 후에 레이어링한다.

**2025년 도구 선택의 핵심 결론:** Python 린팅은 Ruff 단독(+mypy), 프론트엔드 테스트는 Vitest, E2E는 Playwright, 보안 스캔의 주력은 Semgrep + Trivy, Docker 캐싱은 buildx + GHA cache, Azure 인증은 OIDC가 각 영역의 확정적 승자다. 도구 간 중복을 최소화하되, 보안 계층만은 의도적으로 중첩(defense-in-depth)시키는 것이 올바른 전략이다.

가장 흔한 실수는 **ci-gate 패턴 미적용으로 path filter가 건너뛴 job이 PR 머지를 영원히 차단하는 것**, 그리고 **배포 concurrency 그룹에 `cancel-in-progress: true`를 설정해 진행 중인 배포가 취소되는 것**이다. 이 두 가지만 피해도 모노레포 CI/CD의 가장 고통스러운 문제를 선제적으로 방지할 수 있다.