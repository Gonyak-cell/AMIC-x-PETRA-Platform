# 병렬 에이전트 워크플로우

> **핵심**: 모듈 격리가 잘 되어 있는 모노레포에서 병렬 에이전트를 활용하여 개발 속도를 극대화한다.
> 같은 파일을 동시에 수정하는 상황만 피하면 된다.

## 적용 시점

**병렬 작업이 가능한 경우에만 적용.**
단일 모듈 내 순차 작업에는 적용하지 않는다.

## 병렬 진행 가능한 조합

| 조합 | 이유 | 예시 |
|------|------|------|
| **BE + FE** | 모듈 경계 명확, 파일 중복 없음 | deal-mgmt API + amic-platform UI |
| **서로 다른 BE 모듈** | 완전 독립 디렉토리 | fdd + kiis, im + deal-mgmt |
| **테스트 + 코드** | 읽기/쓰기 분리 가능 | 코드 작성 에이전트 + 테스트 작성 에이전트 |

## 순차 진행 필수 (병렬 금지)

| 상황 | 이유 |
|------|------|
| **공유 파일 수정** | `core/`, `shared/`, `contexts/`, `lib/` — 충돌 불가피 |
| **BE 스키마 → FE 타입** | FE 타입은 BE 스키마에 의존 — 순서 필수 |
| **마이그레이션 + 모델** | Alembic revision 체인 — 동시 생성 불가 |
| **CI/인프라 파일** | deploy.yml, docker-compose — 단일 에이전트만 |

## 모듈별 작업 범위

```
에이전트 A (BE):
  deal-mgmt/app/routers/
  deal-mgmt/app/services/
  deal-mgmt/app/schemas/
  deal-mgmt/app/models/
  deal-mgmt/tests/

에이전트 B (FE):
  amic-platform/src/modules/{name}/
  amic-platform/src/types/
  amic-platform/src/components/  (해당 모듈 전용)
```

## worktree 활용

```bash
# BE worktree 생성
git worktree add .claude/worktrees/backend -b feat/backend-work

# FE worktree 생성
git worktree add .claude/worktrees/frontend -b feat/frontend-work

# 작업 완료 후 merge
git merge feat/backend-work
git merge feat/frontend-work

# worktree 정리
git worktree remove .claude/worktrees/backend
git worktree remove .claude/worktrees/frontend
```

## 단계별 체크포인트

- 파일 3~5개 수정마다 **커밋** (롤백 포인트 확보)
- PR은 **400줄 이내**로 분할 (git-workflow.md 준수)
- 각 에이전트는 작업 완료 시 **diff 요약** 제공
- 병렬 작업 merge 전 **tsc + ruff 검증** 필수

## 충돌 방지 체크리스트

- [ ] 두 에이전트의 작업 범위가 파일 단위로 겹치지 않는가?
- [ ] 공유 파일(core/, types/, contexts/)을 한쪽만 수정하는가?
- [ ] BE 스키마 변경이 FE에 영향을 주면 BE 우선 완료인가?
- [ ] merge 전 양쪽 모두 테스트 통과인가?
