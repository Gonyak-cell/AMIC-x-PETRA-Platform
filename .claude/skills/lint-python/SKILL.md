---
name: lint-python
description: "Python 백엔드 린팅. 사용법: /lint-python [module]. 모듈 미지정 시 전체. 예: /lint-python kiis"
user-invocable: true
disable-model-invocation: true
---

# Python Linting (Monorepo)

대상: $ARGUMENTS (fdd / kiis / im / 미지정=전체)

## Module Paths
| Module | Path | Runner |
|--------|------|--------|
| fdd | `fdd/backend/` | `ruff` or `python -m ruff` |
| kiis | `kiis/` | `uv run ruff` or `ruff` |
| im | `im/` | `ruff` or `python -m ruff` |

## Steps

### 특정 모듈 지정 시
```bash
cd {module_path}
ruff check --fix .
ruff format .
```

### 전체 실행 시
```bash
# FDD
cd fdd/backend && ruff check --fix . && ruff format .

# KIIS
cd kiis && ruff check --fix . && ruff format .

# IM
cd im && ruff check --fix . && ruff format .
```

## Output
각 모듈별:
- PASS: 린트 에러 0건
- FAIL: 에러 목록 + 자동 수정 결과
- 자동 수정 불가 항목은 수동 수정 가이드 제공
