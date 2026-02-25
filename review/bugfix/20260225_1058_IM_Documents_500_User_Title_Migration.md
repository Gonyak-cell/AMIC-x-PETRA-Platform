# IM Documents 500 에러 수정 — users.title 마이그레이션 미적용

> **수정일**: 2026-02-25 10:58
> **심각도**: Critical
> **카테고리**: bugfix / migration
> **상태**: ✅ 완료

## 증상

- Deal Document Studio (`/docs`) 접속 시 `Request failed with status code 500 GET /api/im/documents`
- IM 백엔드의 모든 인증 필요 엔드포인트에서 동일 500 발생

## 근본 원인

**위치**: `im/alembic/versions/004_add_user_title.py` + IM PostgreSQL DB

User 모델에 `title` 컬럼이 추가되었으나 Alembic 마이그레이션이 DB에 적용되지 않아, `get_current_user()` → `SELECT ... users.title ... FROM users` 실행 시 `UndefinedColumnError` 발생.

### 에러 스택트레이스 (docker logs)

```
sqlalchemy.exc.ProgrammingError:
  <class 'asyncpg.exceptions.UndefinedColumnError'>:
  column users.title does not exist
[SQL: SELECT users.id, users.email, users.hashed_password,
       users.full_name, users.title, users.role, users.is_active,
       users.created_at, users.updated_at
 FROM users WHERE users.id = $1]
```

### 에러 발생 흐름

```
GET /api/im/documents (프론트엔드 → Vite proxy → IM 백엔드)
  → get_current_user() (dependencies.py:42)
    → JWT 토큰 검증 성공
    → DB에서 사용자 조회: SELECT ... users.title ... FROM users WHERE id = $1
    → ProgrammingError: column users.title does not exist ← 500
```

### 확정 근거

| # | 근거 유형 | 내용 |
|---|----------|------|
| 1 | 에러 메시지 일치 | `UndefinedColumnError: column users.title does not exist` — 정확한 컬럼명 지목 |
| 2 | SQL 확인 | `SELECT ... users.title ... FROM users` — ORM이 모델의 title 컬럼을 쿼리에 포함 |
| 3 | git status 확인 | `?? im/alembic/versions/004_add_user_title.py` — 미커밋 신규 파일 (DB 미적용) |
| 4 | Alembic 체인 오류 | `down_revision = "003"` → 실제 003 revision ID는 `"003_add_data_source"` — 체인 깨짐 |
| 5 | docker-compose.yml | `command: uvicorn ...` — 마이그레이션 자동 실행 없이 서버 직접 시작 |

## 수정 내용

### 1. 마이그레이션 revision 체인 수정

**파일**: `im/alembic/versions/004_add_user_title.py`

```diff
- revision = "004"
- down_revision = "003"
+ revision = "004_add_user_title"
+ down_revision = "003_add_data_source"
```

### 2. 마이그레이션 DB 적용

```bash
docker exec amic-im-api alembic upgrade head
# → Running upgrade 003_add_data_source -> 004_add_user_title
```

### 3. docker-compose.yml — 자동 마이그레이션 추가 (재발 방지)

**4개 백엔드 모두 적용** (fdd-api, kiis-api, deal-mgmt-api, im-api):

```diff
- command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
+ command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

### 4. `im/src/api/core/__init__.py` 신규 생성

namespace package → explicit package 전환 (import 안정성 개선).

## 검증

```bash
# 마이그레이션 적용 확인
docker exec amic-im-api alembic current
# → 004_add_user_title (head)

# API 응답 확인
curl http://localhost:8002/health
# → {"status":"ok","version":"0.1.0"}

curl http://localhost:8002/api/v1/documents
# → 401 (인증 필요) — 500 아닌 정상 응답
```

## 영향 범위

- **변경 파일**: 3개 수정 + 1개 신규
  - `im/alembic/versions/004_add_user_title.py` (revision 체인 수정)
  - `docker-compose.yml` (4개 백엔드 자동 마이그레이션)
  - `im/src/api/core/__init__.py` (신규)
- **영향 서비스**: im-api (즉시), fdd-api/kiis-api/deal-mgmt-api (다음 재시작 시)
- **사이드 이펙트**: 컨테이너 시작 시 alembic upgrade head 실행 → 시작 시간 1~2초 증가

## 참고: 다른 백엔드 마이그레이션 상태

| 백엔드 | alembic upgrade head 결과 | 상태 |
|--------|--------------------------|------|
| im-api | ✅ 성공 (004_add_user_title 적용) | 해결 |
| deal-mgmt-api | ✅ 성공 (이미 최신) | 정상 |
| fdd-api | ❌ 실패 (deals 테이블 관련 마이그레이션 체인 문제) | 별도 대응 필요 |
| kiis-api | ❌ 실패 (title 컬럼 이미 존재 — 버전 추적 불일치) | 별도 대응 필요 |
