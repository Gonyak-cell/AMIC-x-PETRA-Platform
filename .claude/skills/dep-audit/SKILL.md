---
name: dep-audit
description: "Python 의존성 동기화 검증. /dep-audit [module]. 모듈 미지정 시 전체."
user-invocable: true
---

# Dependency Audit (Monorepo)

대상: $ARGUMENTS (deal-mgmt / kiis / im / fdd / all / 미지정=all)

## Module Paths

| Module | pyproject.toml | Source Dir |
|--------|---------------|-----------|
| deal-mgmt | `deal-mgmt/pyproject.toml` | `deal-mgmt/app/` |
| kiis | `kiis/pyproject.toml` | `kiis/app/` |
| im | `im/pyproject.toml` | `im/src/` |
| fdd | `fdd/backend/pyproject.toml` | `fdd/backend/app/` |

## Steps

### Step 1: 스크립트 실행

```bash
python .claude/skills/dep-audit/scripts/check_deps.py {module}
```

- `{module}` = 인자값 (deal-mgmt / kiis / im / fdd / all)
- 미지정 시 `all`

### Step 2: JSON 출력 읽기

스크립트가 각 모듈별 JSON 결과를 stdout으로 출력.

### Step 3: 리포트 생성

JSON 결과를 아래 형식으로 변환하여 사용자에게 출력:

```markdown
## Dependency Audit Report: {module}

### 미등록 패키지 (pyproject.toml에 추가 필요)
| 패키지 | import 위치 | 추가 방법 |
|--------|-----------|---------|
| {package} | {file}:{line} | `dependencies`에 `"{package}>={version}"` 추가 |

### 미사용 의존성 (제거 검토)
| 패키지 | 비고 |
|--------|------|
| {package} | import 없음 — 런타임 플러그인이면 유지 |

### 요약
- 등록 의존성: {n}개
- 실제 import: {n}개
- ❌ 미등록: {n}개 → Docker 빌드 실패 위험
- ⚠️ 미사용: {n}개 → 이미지 크기 증가
```

### Step 4: 미등록 패키지 발견 시

사용자에게 추가 방법 안내:
1. 해당 모듈의 `pyproject.toml` → `[project.dependencies]` 섹션에 추가
2. dev 전용이면 `[project.optional-dependencies] dev = [...]`에 추가
3. `pip install -e ".[dev]"` 로 설치 확인

## Notes

- 스크립트는 `ast.parse()`를 사용하여 정확한 import 분석 수행
- 표준 라이브러리(os, sys, json 등)는 자동 필터링
- 로컬 패키지(app.*, src.*, 상대 import)는 자동 제외
- import명 ≠ 패키지명인 경우 매핑 테이블로 해소 (PIL→Pillow, bs4→beautifulsoup4 등)
