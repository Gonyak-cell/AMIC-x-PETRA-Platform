---
name: db-migrate
description: "모노레포 DB 마이그레이션 도우미. 사용법: /db-migrate {module} {description}. 모듈: fdd, kiis, im. 예: /db-migrate kiis add_reputation_index"
user-invocable: true
disable-model-invocation: true
---

# Database Migration Manager (Monorepo)

모듈 및 설명: $ARGUMENTS
(첫 번째 단어 = 모듈명, 나머지 = 마이그레이션 설명)

## Module Paths
| Module | Working Dir | Command Prefix |
|--------|------------|----------------|
| fdd | `fdd/backend` | `alembic` |
| kiis | `kiis` | `uv run alembic` |
| im | `im` | `alembic` |

Steps:

1. **Check Docker DB**:
```bash
docker compose ps db
```
If db is not running, start it: `docker compose up -d db`

2. **Verify model registration**: Check that all model files are imported in the module's models `__init__.py`

3. **Generate migration**:
```bash
cd {working_dir} && {command_prefix} revision --autogenerate -m "{description}"
```

4. **Review**: Display the generated migration file — show the `upgrade()` and `downgrade()` functions. Ask user to confirm before applying.

5. **Apply migration**:
```bash
cd {working_dir} && {command_prefix} upgrade head
```

6. **Verify**:
```bash
cd {working_dir} && {command_prefix} current
```

Common issues:
- "Target database is not up to date" → run upgrade head first
- Model not detected → check it's imported in models/__init__.py
- JSONB columns require PostgreSQL (not SQLite)
