# CI/Deploy 회귀 방지 규칙

> **핵심**: CI/Deploy 실패는 사전 차단 가능하다. 아래 체크리스트를 실수 발생 전에 적용한다.

## 적용 시점

다음 파일을 수정할 때 **자동 적용**:
- `.github/workflows/deploy.yml`
- `*/app/models/*.py` (SQLAlchemy 모델)
- `deal-mgmt/**/*.py`, `kiis/**/*.py`, `fdd/**/*.py`, `im/**/*.py` (Python 백엔드)

---

## 규칙 1: deploy.yml — `checks: read` 권한 보존

**배경**: `wait-for-ci` 단계는 `gh api /repos/{repo}/commits/{sha}/check-runs`를 호출한다.
이 API는 **`checks: read` 권한이 없으면 403 Forbidden**을 반환하여 Deploy 전체가 타임아웃으로 실패한다.

**필수 보존 블록**:
```yaml
permissions:
  checks: read
  contents: read
```

**금지**:
- `deploy.yml`에서 `permissions:` 블록 삭제
- `wait-for-ci` 단계를 수정할 때 `permissions:` 블록과 함께 삭제

**사전 자동 체크**: `.husky/pre-push` — `deploy.yml`에 `checks: read`가 없으면 푸시 차단.

---

## 규칙 2: SQLAlchemy 모델 — PostgreSQL 전용 타입 금지

**배경**: CI 테스트는 SQLite를 사용한다 (`DATABASE_URL: sqlite+aiosqlite:///./test.db`).
`sqlalchemy.dialects.postgresql.JSONB`, `UUID(as_uuid=True)`는 SQLite 컴파일러가 렌더링하지 못해
`CompileError`가 발생한다.

**올바른 패턴**:
```python
# ✅ 크로스 DB 호환 (PostgreSQL + SQLite)
from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
value: Mapped[dict | None] = mapped_column(
    JSON().with_variant(JSONB, "postgresql"), nullable=True
)
```

**금지**:
```python
# ❌ PostgreSQL 전용 — SQLite CI 실패
from sqlalchemy.dialects.postgresql import JSONB, UUID

id = mapped_column(UUID(as_uuid=True), ...)
value = mapped_column(JSONB, ...)
```

**사전 자동 체크**: `.husky/pre-push` — `mapped_column(JSONB` 또는 `mapped_column(UUID(as_uuid` 패턴 감지 시 경고.

---

## 규칙 3: Python — 표준 라이브러리 import 누락 금지

**배경**: `json`, `os`, `re` 등 표준 라이브러리를 사용하면서 import를 빠뜨리면
ruff `F821 Undefined name` 에러로 CI 실패.

**체크리스트**:
- `json.dumps()` / `json.loads()` / `json.JSONDecodeError` 사용 시 → `import json` 필수
- `os.path.*` 사용 시 → `import os` 필수
- `re.match()` / `re.compile()` 사용 시 → `import re` 필수

**사전 체크** (수동): 새 Python 파일 작성 후 ruff 실행:
```bash
cd deal-mgmt && python -m ruff check app/path/to/file.py
```

---

## 규칙 4: 미사용 변수 — F841 방지

**배경**: 예외를 `except Exception as exc:` 로 캡처하고 `exc`를 사용하지 않으면
ruff `F841 Local variable assigned but never used` 에러.

**올바른 패턴**:
```python
# ✅ 변수를 실제로 사용
except Exception as exc:
    logger.warning("실패: %s", exc)
    last_error = exc  # 이후 f-string 또는 raise에서 사용

# ✅ 변수 불필요 시 제거
except Exception:
    continue
```

**금지**:
```python
# ❌ 할당 후 미사용
except Exception as exc:
    last_error = exc  # 이후 어디서도 사용 안 됨
    continue
```

---

## 규칙 5: TypeScript — 관련 타입 파일 함께 커밋

**배경**: 컴포넌트 파일만 커밋하고 관련 타입 파일을 빠뜨리면,
로컬에서 타입이 있어 `tsc --noEmit`이 통과하더라도 CI의 Docker 빌드에서 실패.

**체크리스트**: 다음 파일을 수정할 때 함께 커밋 확인:
- `pages/*.tsx` 수정 → `types/*.ts`가 변경됐는지 확인
- `hooks/use*.ts` 수정 → `types/*.ts`의 새 필드가 있으면 함께 커밋
- `git status`로 미커밋 타입 파일 존재 여부 항상 확인

**사전 자동 체크**: `.husky/pre-push` — TypeScript 타입 체크 (`npx tsc --noEmit`).

---

## 규칙 6: pyproject.toml — 빌드 백엔드 통일

**배경**: setuptools flat-layout auto-discovery는 top-level에 여러 패키지(`app/`, `alembic/`)가 있으면
혼동되어 `Multiple top-level packages discovered` 에러가 발생한다.
hatchling + `packages = ["app"]`이 명시적이고 안정적이다.

**필수 패턴**:
```toml
[tool.hatch.build.targets.wheel]
packages = ["app"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**금지**:
```toml
# ❌ top-level에 app/ 외 디렉토리(alembic/)가 있는 경우
[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.build_meta"
# packages 미지정 → flat-layout 에러
```

**사전 체크**: 새 모듈 추가 시 기존 모듈(deal-mgmt, kiis)의 pyproject.toml을 참조.

---

## 규칙 7: pyproject.toml — dev 의존성 표준 형식

**배경**: `[dependency-groups]`(PEP 735)는 uv 전용이다. pip은 `[project.optional-dependencies]`만 인식한다.
CI가 `pip install -e ".[dev]"`을 사용하므로, `[dependency-groups]`를 쓰면 dev 의존성(pytest-cov 등)이 설치되지 않는다.

**필수 패턴**:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-cov>=6.0.0",
    # ...
]
```

**금지**:
```toml
# ❌ pip에서 인식 불가 — CI 실패
[dependency-groups]
dev = [...]
```

**사전 자동 체크**: `.husky/pre-push` Guard 6 — `[dependency-groups]` 감지 시 푸시 차단.

---

## 규칙 8: CI/workflow YAML — Job-level permissions 주의

**배경**: GitHub Actions에서 job-level `permissions` 블록은 workflow-level `permissions`를 **병합하지 않고 완전히 대체**한다. job-level에 `contents: read`를 빠뜨리면 `actions/checkout`이 `Repository not found`로 실패한다.

**필수 확인**:
```yaml
# workflow-level
permissions:
  contents: read
  pull-requests: write

jobs:
  my-job:
    permissions:
      # ⚠️ 여기서 contents: read 를 빠뜨리면 checkout 실패!
      pull-requests: read
      contents: read    # ← 반드시 포함
```

**체크리스트**: `.github/workflows/*.yml` 수정 시:
- job-level `permissions` 블록이 있으면 `contents: read` 포함 여부 확인
- `actions/checkout@v4`를 사용하는 Job에는 반드시 `contents: read` 필요

---

## 위반 감지 신호 (이 생각이 들면 체크리스트 실행)

- "로컬에서 빌드/테스트 통과했으니 CI도 될 것이다"
- "`deploy.yml` 수정했는데 permissions는 그대로일 거야"
- "이 `json` 함수는 다른 import에 포함됐겠지"
- "이 타입 파일은 나중에 커밋해도 돼"
- "CI가 Repository not found면 GitHub Settings 문제일 것이다"
- "`pip install -e .[dev]` 실패해도 fallback이 있으니 괜찮을 것이다"

## 관련 파일

- `.husky/pre-push` — 자동 차단 게이트 (Guard 1~6)
- `.github/workflows/deploy.yml` — CI 게이트 의존 워크플로우
- `.github/workflows/ci.yml` — SQLite 기반 테스트 환경 정의
- `kiis/app/models/audit.py` — 올바른 크로스 DB 호환 타입 예시
- `.claude/rules/ci-deploy-failure-diagnostic.md` — CI/Deploy 실패 진단 규칙
