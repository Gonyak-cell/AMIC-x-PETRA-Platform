# CI/Deploy 회귀 방지 규칙

> **핵심**: CI/Deploy 실패는 사전 차단 가능하다. 아래 체크리스트를 실수 발생 전에 적용한다.

## 적용 시점

다음 파일을 수정할 때 **자동 적용**:
- `.github/workflows/deploy.yml`
- `*/app/models/*.py` (SQLAlchemy 모델)
- `deal-mgmt/**/*.py`, `kiis/**/*.py`, `fdd/**/*.py`, `im/**/*.py` (Python 백엔드)

---

## 빠른 참조 (8개 Guard)

| Guard | 위반 시 에러 | 핵심 규칙 |
|-------|-----------|----------|
| 1 | deploy.yml 403 타임아웃 | `permissions: checks: read` + `contents: read` 보존 |
| 2 | SQLite CompileError | `Uuid` + `JSON().with_variant(JSONB, "postgresql")` 사용. JSONB/UUID 직접 금지 |
| 3 | ruff F821 | stdlib 사용 시 `import` 반드시 확인 (json, os, re 등) |
| 4 | ruff F841 | `except Exception as exc:` 캡처 후 `exc` 반드시 사용 또는 제거 |
| 5 | Docker 빌드 실패 | TypeScript 타입 파일 함께 커밋. `git status` 확인 |
| 6 | Multiple packages discovered | hatchling + `packages = ["app"]` 사용. setuptools 금지 |
| 7 | dev 의존성 미설치 | `[project.optional-dependencies]` 사용. `[dependency-groups]` 금지 |
| 8 | Repository not found | job-level `permissions`에 `contents: read` 반드시 포함 |

---

## Guard 1: deploy.yml — `checks: read` 권한 보존

`wait-for-ci`가 `gh api check-runs`를 호출하므로 `checks: read` 필수.
`deploy.yml`에서 `permissions:` 블록 삭제/수정 시 403 → 배포 타임아웃 실패.
사전 자동 체크: `.husky/pre-push`.

## Guard 2: SQLAlchemy — PostgreSQL 전용 타입 금지

CI는 SQLite 사용. `mapped_column(JSONB` / `mapped_column(UUID(as_uuid` → CompileError.
올바른 패턴: `Uuid` (PK) + `JSON().with_variant(JSONB, "postgresql")` (JSON 필드).
사전 자동 체크: `.husky/pre-push` + PreToolUse 훅.

## Guard 3: Python — 표준 라이브러리 import 확인

`json.dumps()` → `import json`, `os.path.*` → `import os`, `re.match()` → `import re`.
ruff `F821 Undefined name`으로 CI 실패. 새 파일 작성 후 `ruff check` 필수.

## Guard 4: 미사용 변수 — F841 방지

`except Exception as exc:` → `exc` 사용하거나 `except Exception:` 으로 변경.
`last_error = exc` 할당 후 미참조 → ruff F841.

## Guard 5: TypeScript — 타입 파일 함께 커밋

`pages/*.tsx` 수정 → `types/*.ts` 동반 커밋 확인.
로컬 `tsc --noEmit` 통과해도 CI Docker에서 타입 파일 누락 시 실패.
사전 자동 체크: `.husky/pre-push` (`npx tsc --noEmit`).

## Guard 6: pyproject.toml — 빌드 백엔드

hatchling + `packages = ["app"]` 필수. setuptools는 `app/` + `alembic/` 혼동.
새 모듈 추가 시 기존 모듈(deal-mgmt, kiis) pyproject.toml 참조.

## Guard 7: pyproject.toml — dev 의존성 형식

`[project.optional-dependencies]` 사용 (pip 호환).
`[dependency-groups]` (PEP 735) = uv 전용 → pip 인식 불가 → CI 실패.
사전 자동 체크: `.husky/pre-push` + PreToolUse 훅.

## Guard 8: workflow YAML — Job-level permissions

job-level `permissions`는 workflow-level을 **완전히 대체** (병합 아님).
`actions/checkout@v4` 사용 Job에 `contents: read` 반드시 포함.

---

## 위반 감지 신호

- "로컬에서 빌드/테스트 통과했으니 CI도 될 것이다"
- "`deploy.yml` 수정했는데 permissions는 그대로일 거야"
- "이 `json` 함수는 다른 import에 포함됐겠지"
- "이 타입 파일은 나중에 커밋해도 돼"
- "CI가 Repository not found면 GitHub Settings 문제일 것이다"

## 상세 코드 예시

각 Guard의 올바른/금지 코드 패턴은 `/ci-diagnostic` 스킬 참조.

## 관련 파일

- `.husky/pre-push` — 자동 차단 게이트 (Guard 1~7)
- `.github/workflows/deploy.yml` — CI 게이트 의존 워크플로우
- `.github/workflows/ci.yml` — SQLite 기반 테스트 환경 정의
- `kiis/app/models/audit.py` — 올바른 크로스 DB 호환 타입 예시
