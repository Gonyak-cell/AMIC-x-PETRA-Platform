# Financial Models GET 500 에러 — Alembic 마이그레이션 체인 수정

- **일시**: 2026-02-25 21:25
- **카테고리**: bugfix
- **심각도**: Critical (API 엔드포인트 완전 장애)
- **영향 범위**: M&A 모듈 재무모델 탭 전체 사용 불가

---

## 증상

```
GET /api/ma/transactions/{txn_id}/financial-models → 500 Internal Server Error
```

프론트엔드에서 M&A 거래 워크스페이스의 재무모델 탭 접근 시 500 에러 반환.

---

## 근본 원인 확정

**위치**: `deal-mgmt/migrations/versions/` — 019, 020, 021 마이그레이션 3개 파일
**원인**: Alembic 마이그레이션 체인 버그 3건으로 migrations 019~021이 DB에 적용되지 못함 → `financial_models` 테이블 미존재 → SELECT 쿼리 실패 → 500

### 확정 근거

1. **DB 버전 확인**: `SELECT version_num FROM alembic_version` → `018` (019 이후 미적용)
2. **테이블 존재 확인**: `information_schema.tables`에서 `financial_models`, `fm_checklists`, `fm_checklist_items`, `rfis`, `rfi_items`, `vdr_text_caches`, `ldd_vdr_references` 모두 미존재 (`0 rows`)
3. **Alembic 에러 재현**: `alembic upgrade head` 실행 시 3단계 에러 순차 확인
4. **컨테이너 상태 확인**: `docker compose ps` → deal-mgmt-api Up(healthy), health 엔드포인트에서 `migration_ok: false` 확인
5. **코드 경로 확인**: `financial_models.py:39-45` → `financial_model_service.py:87-98` 코드 자체에 버그 없음 (단순 SELECT + Pydantic 직렬화)

---

## 수정 내용 (3개 파일)

### 1. Migration 019: asyncpg multi-statement 호환성

**파일**: `deal-mgmt/migrations/versions/019_ldd_vdr_integration.py` (라인 86~98)

**문제**: `op.execute()` 하나에 CREATE FUNCTION + CREATE TRIGGER 2개 SQL문을 넣음. asyncpg는 prepared statement에 여러 명령을 지원하지 않음.

**에러**: `asyncpg.exceptions.PostgresSyntaxError: cannot insert multiple commands into a prepared statement`

**수정**: 2개의 별도 `op.execute()` 호출로 분리

```python
# Before (에러)
op.execute(f"""
    CREATE OR REPLACE FUNCTION update_{table}_updated_at() ...;
    CREATE TRIGGER trg_{table}_updated_at ...;
""")

# After (수정)
op.execute(f"""
    CREATE OR REPLACE FUNCTION update_{table}_updated_at() ...;
""")
op.execute(f"""
    CREATE TRIGGER trg_{table}_updated_at ...;
""")
```

### 2. Migration 020: Enum 타입 중복 생성

**파일**: `deal-mgmt/migrations/versions/020_financial_models.py` (라인 18~72 제거)

**문제**: `op.execute("DO $$ BEGIN CREATE TYPE ... END $$")`로 enum을 먼저 만든 뒤, `op.create_table()`의 `sa.Enum()`이 같은 enum을 다시 만들려고 시도.

**에러**: `asyncpg.exceptions.DuplicateObjectError: type "financialmodeltype" already exists`

**수정**: 수동 CREATE TYPE 블록 6개 전부 제거. `sa.Enum()`이 `create_table` 시 자동 생성하도록 위임.

### 3. Migration 021: Revision 체인 불일치

**파일**: `deal-mgmt/migrations/versions/021_rfi_request_for_information.py` (라인 13)

**문제**: `down_revision = "020_financial_models"` — 존재하지 않는 revision ID 참조. 실제 migration 020의 revision은 `"020"`.

**에러**: `KeyError: '020_financial_models'` (Alembic revision graph 해석 실패)

**수정**: `down_revision = "020"`으로 변경.

---

## 검증 결과

| 항목 | 결과 |
|------|------|
| `alembic_version` | `021_rfi` (head) |
| `financial_models` 테이블 | EXISTS |
| `fm_checklists` 테이블 | EXISTS |
| `fm_checklist_items` 테이블 | EXISTS |
| `rfis` / `rfi_items` 테이블 | EXISTS |
| `vdr_text_caches` / `ldd_vdr_references` 테이블 | EXISTS |
| `/health` 엔드포인트 | `{"status":"ok","migration_ok":true}` |
| `GET /api/v1/transactions/{id}/financial-models` | **200 OK**, `[]` 반환 |

---

## 교훈 / 재발 방지

1. **Alembic revision ID 일관성**: revision 변수값과 파일명/주석의 이름이 다를 수 있으므로, `down_revision`은 반드시 이전 마이그레이션의 실제 `revision` 변수값을 참조해야 한다.
2. **asyncpg multi-statement 금지**: asyncpg는 `prepared statement`에 여러 SQL 문을 지원하지 않는다. 트리거 생성 등에서 반드시 문 단위로 분리.
3. **Enum 생성 이중화 금지**: `op.execute(CREATE TYPE)` + `sa.Enum(name=...)` in `create_table`은 enum을 2번 만들려고 시도한다. 둘 중 하나만 사용.
4. **마이그레이션 작성 후 로컬 검증 필수**: `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` 왕복 테스트로 체인 무결성 검증.
