---
description: 모노레포 Git 워크플로 규칙
---
# Git Workflow Rules (모노레포)

## Branch Strategy
| Branch | Purpose | Merges to |
|--------|---------|-----------|
| `master` | Production-ready | — |
| `develop` | Integration | `master` |
| `feat/*` | New features | `develop` |
| `fix/*` | Bug fixes | `develop` |
| `hotfix/*` | Production fixes | `master` + `develop` |

## Branch Naming
```
feat/ma-workflow
feat/kiis-gp-search
fix/im-unreachable
fix/dashboard-kpi-loading
hotfix/cors-security
```

## Commit Messages (Conventional Commits)
```
feat(fdd/qoe): add adjustment candidate detection
fix(kiis/kofia): fix fund search pagination
feat(im/narrative): add market analysis section
fix(platform/dashboard): fix KPI loading state
chore(docker): update nginx config
chore(ci): add KIIS backend test stage
docs(architecture): add MA workflow plan
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `style`

**Scopes** (monorepo):
- Backend: `fdd/*`, `kiis/*`, `im/*`
- Frontend: `platform/*`
- Infra: `docker`, `nginx`, `ci`
- Docs: `architecture`, `api`

## PR Guidelines
- Max 400 lines changed
- Require CI pass before merge
- Squash merge to develop/master
- Link to issue if exists

## CI Checks (Required)
```yaml
# Backend (per module)
- ruff check
- ruff format --check
- pytest

# Frontend
- eslint
- tsc --noEmit
- vite build
```

## Protected Branch Rules
### master
- Require PR
- Require CI pass
- No force push
- No direct commits

## Dangerous Commands (Require User Confirmation)
```bash
git push --force          # Can overwrite history
git reset --hard          # Discards uncommitted changes
git clean -f              # Deletes untracked files
git branch -D             # Force deletes branch
```
