# 버전 관리 규칙

> **핵심**: 모든 커밋은 버전 번호를 반영한다. VERSION 파일이 Single Source of Truth.

## 적용 시점

**커밋을 생성할 때 자동 적용.**

## 버전 체계 (SemVer)

```
MAJOR.MINOR.PATCH
  │     │     └── 버그 수정, 사소한 개선
  │     └──────── 새 기능 추가, 기존 기능 개선
  └────────────── 호환성 깨지는 변경 (API 계약 변경)
```

## VERSION 파일 = Single Source of Truth

- 루트 `VERSION` 파일에 현재 버전이 기록된다.
- 모든 모듈의 버전은 이 파일을 따른다:
  - `amic-platform/package.json` → `"version"`
  - `deal-mgmt/pyproject.toml` → `version`
  - `kiis/pyproject.toml` → `version`
  - `fdd/backend/pyproject.toml` → `version`

## 커밋 시 버전 업데이트 규칙

### 자동 판단 기준

| 커밋 타입 | 버전 변경 | 예시 |
|----------|----------|------|
| `fix(*)` | PATCH +1 | 0.9.0 → 0.9.1 |
| `feat(*)` | MINOR +1, PATCH=0 | 0.9.1 → 0.10.0 |
| `refactor`, `perf`, `test`, `docs`, `chore` | 변경 없음 | — |
| BREAKING CHANGE | MAJOR +1 | 0.10.0 → 1.0.0 |

### 필수 절차

1. 커밋 타입에 따라 VERSION 파일 업데이트 여부를 판단한다.
2. 버전이 변경되면:
   - `VERSION` 파일을 새 버전으로 수정한다.
   - `bash scripts/sync-version.sh` 를 실행하여 모든 모듈에 동기화한다.
   - 동기화된 파일들을 함께 커밋에 포함한다.
3. 여러 커밋을 연속으로 할 때는 **마지막 커밋에서만** 버전을 올린다 (중간 커밋마다 올리지 않는다).
4. 하나의 세션에서 fix + feat가 섞이면 **feat 기준**(MINOR)으로 올린다.

### 예외

- `docs`, `chore`, `test`만 있는 커밋은 버전을 올리지 않는다.
- `.claude/rules/`, `.claude/plans/`, `docs/` 만 수정하는 커밋은 버전을 올리지 않는다.
- 버전 동기화 커밋 자체(`chore: bump version`)는 추가 버전 업데이트를 하지 않는다.

## 동기화 스크립트

```bash
# 현재 VERSION 파일 기준으로 모든 모듈 동기화
bash scripts/sync-version.sh

# 특정 버전으로 강제 설정
bash scripts/sync-version.sh 1.0.0
```

## 관련 파일

- `VERSION` — 루트 버전 파일
- `scripts/sync-version.sh` — 동기화 스크립트
- `.husky/pre-push` — push 전 검증
