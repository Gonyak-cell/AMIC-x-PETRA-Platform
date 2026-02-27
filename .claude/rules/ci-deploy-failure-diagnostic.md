# CI/Deploy 실패 진단 규칙

> **핵심**: CI/Deploy 실패 시 외부 설정을 의심하기 전에 **코드/설정 파일을 먼저 읽는다**.
> 에러 메시지에 반응적으로 대응하지 않고, 체계적으로 진단한다.

## 적용 시점

사용자가 다음을 보고할 때 **자동 적용**:
- GitHub Actions CI 실패
- Deploy 워크플로우 실패
- Docker 빌드 실패
- "Repository not found", "permission denied" 등 CI 인프라 에러

## 절대 금지

- 워크플로우 YAML 파일을 `Read`하지 않고 수정 제안
- 외부 설정(GitHub Settings, Secrets)만 의심하고 코드 확인 생략
- 에러 메시지 1개만 보고 "아마 ~일 것이다"로 수정 시도
- CI 로그를 확인하지 않고 추측 기반 수정

## 필수 절차

### Step 1: 로그 수집 (수정 전 필수)

```bash
# 실패한 CI run의 로그 확인
gh run view <run-id> --log-failed

# 실패한 Job 목록 확인
gh run view <run-id> --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
```

### Step 2: 관련 파일 Read (외부 설정 의심 전 필수)

**반드시 Read해야 할 파일**:
| 실패 위치 | 읽어야 할 파일 |
|----------|--------------|
| `actions/checkout` 실패 | `.github/workflows/{해당}.yml` — `permissions` 블록 확인 |
| `pip install` 실패 | `{모듈}/pyproject.toml` — build-system, dependencies 확인 |
| `ruff check` 실패 | `{모듈}/pyproject.toml` — ruff select/ignore 설정 확인 |
| `pytest` 실패 | `{모듈}/pyproject.toml` — addopts, 의존성 확인 |
| `tsc`/`eslint` 실패 | `amic-platform/tsconfig.json`, `.eslintrc.*` 확인 |
| `docker build` 실패 | `{모듈}/Dockerfile`, 빌드 스테이지 확인 |
| Deploy 실패 | `.github/workflows/deploy.yml` 확인 |

### Step 3: 로컬 재현

CI와 동일한 명령을 로컬에서 실행하여 재현 확인:
```bash
# 예: ruff 실패 시
cd deal-mgmt && python -m ruff check .

# 예: pip install 실패 시
cd fdd/backend && pip install -e ".[dev]"

# 예: TypeScript 실패 시
cd amic-platform && npx tsc --noEmit
```

### Step 4: 카테고리별 진단

| 에러 카테고리 | 키워드 | 진단 방향 |
|-------------|--------|----------|
| **의존성 설치** | `pip install`, `npm ci`, `ModuleNotFoundError` | pyproject.toml, package.json 구조 확인 |
| **린트** | `ruff check`, `eslint`, `--max-warnings` | 로컬에서 동일 명령 실행, select/ignore 설정 비교 |
| **테스트** | `pytest`, `FAILED`, `unrecognized arguments` | addopts, 플러그인 설치 여부, 환경변수 확인 |
| **빌드** | `tsc`, `vite build`, `docker build` | 타입 에러, 누락 파일, Dockerfile 스테이지 확인 |
| **권한** | `Repository not found`, `403 Forbidden` | workflow YAML의 `permissions` 블록 확인 (job-level 우선) |
| **배포** | `SSH timeout`, `health check failed` | deploy.yml 로직, 서버 상태 확인 |

### Step 5: 수정 후 검증

1. 로컬에서 동일 명령이 통과하는지 확인
2. 커밋 & 푸시
3. `gh run list --limit 1` → CI 결과 추적
4. CI Gate success 확인까지 완료

## "외부 설정만 의심" 방지 체크리스트

CI 에러가 발생했을 때, 아래를 **순서대로** 확인한다:

1. ✅ `gh run view --log-failed`로 정확한 에러 메시지 확인했는가?
2. ✅ 관련 워크플로우 YAML 파일을 `Read`로 읽었는가?
3. ✅ 관련 설정 파일(pyproject.toml, tsconfig.json 등)을 `Read`로 읽었는가?
4. ✅ 로컬에서 동일 명령을 실행하여 재현했는가?

**위 4개를 모두 확인하기 전에 "GitHub Settings를 변경하세요"라고 제안하지 않는다.**

## 관련 규칙

- `.claude/rules/ci-regression-prevention.md` — CI 회귀 방지 (사전 차단)
- `.claude/rules/bugfix-root-cause-verification.md` — 버그 수정 근본 원인 확정
- `.claude/rules/production-error-diagnostic.md` — 프로덕션 에러 진단
