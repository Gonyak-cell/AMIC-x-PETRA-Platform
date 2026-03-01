---
name: ci-diagnostic
description: CI/Deploy 실패 시 체계적 진단. 로그 수집 → 파일 확인 → 로컬 재현 → 수정 → 검증.
user-invokable: true
---

# CI/Deploy 실패 진단

> **핵심**: CI 실패 시 외부 설정을 의심하기 전에 **코드/설정 파일을 먼저 읽는다**.

## 적용 시점

GitHub Actions CI 실패, Deploy 워크플로우 실패, Docker 빌드 실패 보고 시.

## Step 1: 로그 수집

```bash
gh run view <run-id> --log-failed
gh run view <run-id> --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
```

## Step 2: 관련 파일 Read

| 실패 위치 | 읽어야 할 파일 |
|----------|--------------|
| `actions/checkout` | `.github/workflows/{해당}.yml` — `permissions` 블록 |
| `pip install` | `{모듈}/pyproject.toml` — dependencies |
| `ruff check` | `{모듈}/pyproject.toml` — ruff select/ignore |
| `pytest` | `{모듈}/pyproject.toml` — addopts |
| `tsc`/`eslint` | `amic-platform/tsconfig.json`, `.eslintrc.*` |
| `docker build` | `{모듈}/Dockerfile` |
| Deploy | `.github/workflows/deploy.yml` |

## Step 3: 로컬 재현

```bash
cd deal-mgmt && python -m ruff check .     # ruff 실패 시
cd amic-platform && npx tsc --noEmit        # TypeScript 실패 시
```

## Step 4: 카테고리별 진단

| 카테고리 | 진단 방향 |
|---------|----------|
| 의존성 설치 | pyproject.toml, package.json 구조 |
| 린트 | 로컬 동일 명령 실행, select/ignore 비교 |
| 테스트 | addopts, 플러그인, 환경변수 |
| 빌드 | 타입 에러, Dockerfile 스테이지 |
| 권한 | workflow YAML `permissions` 블록 (job-level 우선) |

## Step 5: 수정 후 검증

1. 로컬 동일 명령 통과 확인
2. 커밋 & 푸시
3. `gh run list --limit 1` → CI 결과 추적

## 외부 설정 의심 전 필수 체크

1. ✅ `gh run view --log-failed` 확인?
2. ✅ 워크플로우 YAML `Read`?
3. ✅ 설정 파일 `Read`?
4. ✅ 로컬 재현?

**4개 모두 확인 전 "GitHub Settings 변경하세요" 제안 금지.**

## ci-regression-prevention Guards (요약)

- **Guard 1**: `deploy.yml` — `permissions: checks: read` 보존 필수
- **Guard 2**: SQLAlchemy — `Uuid` + `JSON().with_variant(JSONB, "postgresql")` 사용
- **Guard 3**: Python stdlib import — `json.dumps()` → `import json`, `os.path.*` → `import os`, `re.match()` → `import re` 필수. ruff F821.
- **Guard 4**: 미사용 변수 — `except Exception as exc:` → `exc` 사용하거나 `except Exception:`으로 변경. ruff F841.
- **Guard 5**: TypeScript 타입 파일 함께 커밋
- **Guard 6**: hatchling + `packages = ["app"]`
- **Guard 7**: `[project.optional-dependencies]` 사용 (`[dependency-groups]` 금지)
- **Guard 8**: job-level permissions에 `contents: read` 포함

## 참조

- `.claude/rules/ci-regression-prevention.md` — 사전 차단 규칙
- `.claude/rules/bugfix-root-cause-verification.md` — 원인 확정 게이트
