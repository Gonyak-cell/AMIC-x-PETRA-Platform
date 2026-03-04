# Chunk 2 FDD Backend — Review Findings

**리뷰 일시**: 2026-03-05 04:09:46
**범위**: `fdd/backend/app/` (api, models, schemas, services, core, utils, agents, qa) + tests + alembic
**총 스캔 파일**: app/ 253개 + tests/ 117개 + alembic/ 19개 = **389개 Python 파일**
**직접 읽은 파일**: 27개 (핵심 파일 샘플링)
**Grep 검색 패턴**: 8종 (JSONB, json.dumps, except Exception, os.getenv, bare except, float(), UUID(as_uuid), open())

---

## 1. Deferred Issue Re-verification (Chunk 8에서 보류된 5건)

| # | 이슈 | 파일:라인 | 상태 | 검증 결과 |
|---|------|----------|------|----------|
| D1 | 동기 SQLAlchemy 엔진 사용 — 다른 모듈(KIIS/DM/IM)은 async 사용 | `database.py:1-14` | **확인** | `create_engine` + `Session` (동기). 다른 모듈은 `create_async_engine` + `AsyncSession` 사용. FDD만 동기 방식. 현재 블로킹 이슈는 아니지만, 장기적으로 플랫폼 통합 시 async 전환 필요. |
| D2 | `get_db()` 제너레이터에 rollback 누락 | `database.py:21-26` | **확인** | `try: yield db / finally: db.close()` 구조. 예외 발생 시 `db.rollback()` 호출 없이 바로 `close()`. 미커밋 트랜잭션이 롤백 없이 닫힐 수 있음. 올바른 패턴: `except: db.rollback(); raise / finally: db.close()` |
| D3 | 커넥션 풀 사이즈 30 (pool_size=20 + max_overflow=10) — 프로덕션 적정성 | `database.py:8-9` | **확인** | Azure VM E2s_v3 (2 vCPU, 16GB RAM) 환경에서 30 커넥션. PostgreSQL 기본 `max_connections=100`이므로 단일 모듈로는 여유. 단, 모노레포 4개 모듈이 동일 DB 사용 시 120(30x4) > 100 초과 가능. |
| D4 | `AUTH_ENABLED=False` 시 ADMIN 권한 dev 사용자 반환 — 프로덕션 가드 미흡 | `auth/dependencies.py:39-44`, `config.py:51-55` | **확인** | `_DEV_USER`는 `UserRole.ADMIN` 고정. `config.py`에서 `AUTH_ENABLED=False` 시 WARNING 로그만 출력, 프로덕션에서 차단하지 않음. `jwt_secret`은 프로덕션에서 `RuntimeError`로 차단하지만, `auth_enabled`는 경고만. |
| D5 | `bcrypt.hashpw` + `hmac.compare_digest` 비표준 검증 패턴 | `auth/password.py:14-17` | **확인** | `bcrypt.checkpw()` 대신 수동으로 `hashpw()` 호출 후 `hmac.compare_digest()` 비교. 기능적으로는 동작하지만 bcrypt 라이브러리의 공식 API를 우회. `bcrypt.checkpw()`가 내부적으로 동일 작업 + 타이밍 공격 방지를 수행하므로 표준 API 사용이 권장됨. |

---

## 2. New Issues Found

| # | 관점 | 파일:라인 | 이슈 | 심각도 |
|---|------|----------|------|--------|
| N1 | **보안** | `api/industries.py:15-22` | **인증 완전 누락** — `get_industries()` 엔드포인트에 `get_current_user` 의존성 없음. 인증 없이 접근 가능. 산업 목록은 민감 데이터는 아니지만, 플랫폼 일관성 상 인증 필요. | Medium |
| N2 | **보안** | `api/exchange_rates.py:34-63` | **쓰기 엔드포인트 권한 미분리** — `create_exchange_rate`, `update_exchange_rate`, `delete_exchange_rate` 모두 `get_current_user`만 사용. `require_permission(Permission.X)` 없음. 일반 사용자도 환율 CRUD 가능. `webhooks.py`는 `require_permission(Permission.WEBHOOK_MANAGE)` 사용하는 것과 비교해 불일치. | High |
| N3 | **데이터 무결성** | `services/report/report_service.py:460-658` (다수 라인) | **금액 계산에 `float()` 사용** — report_service.py에서 18개 이상의 `float()` 호출. 퍼센트 계산, 분산/표준편차 계산 등에서 `Decimal` → `float` 변환. CLAUDE.md Money Rules 위반 (`NEVER float`). chart 서비스(bar.py, pie.py, waterfall.py, line.py)도 동일 패턴. | Medium |
| N4 | **에러 처리** | 22개 파일, 총 60건 | **광범위한 `except Exception` 사용** — 특히 `services/report/report_service.py`(18건), `agents/guardrails.py`(4건), `services/analysis/orchestrator.py`(5건), `services/narrative/engine.py`(4건). 다수가 에러를 로깅 없이 삼키거나 범용 메시지로 대체. 디버깅 어렵고 원인 추적 불가. | Medium |
| N5 | **설정/구성** | `services/llm/client.py:92-93,169,241-242` | **LLM API 키를 `os.getenv`로 직접 읽음** — 6개의 `os.getenv` 호출 (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL_NAME`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, `GOOGLE_API_KEY`, `GOOGLE_MODEL_NAME`). 중앙 `Settings` 클래스를 우회하여 설정 관리 분산. `.env.example` 누락, 테스트 시 모킹 어려움, 설정값 검증 불가. | Medium |
| N6 | **성능/리소스** | `api/reports.py:626`, `api/exports.py:110` | **StreamingResponse에서 `open()` 파일 핸들 미관리** — `StreamingResponse(open(file_path, "rb"), ...)` 패턴. 파일 핸들이 명시적으로 닫히지 않음. 요청 중단/예외 시 파일 디스크립터 누수 가능. 올바른 패턴: 제너레이터 함수에서 `with open(...) as f:` 사용 후 yield. | Low |
| N7 | **아키텍처** | 27개 모델 파일, 98건 | **`UUID(as_uuid=True)` PostgreSQL 방언 직접 사용** — 모든 모델이 `sqlalchemy.dialects.postgresql.UUID` 사용. CI에서 SQLite 테스트 시 `conftest.py`의 이벤트 리스너로 우회하지만, `sqlalchemy.Uuid` (SA 2.0+ 내장) 사용이 크로스 DB 호환성에 더 안전. `db_types.py`의 `JsonbColumn` 패턴과 일관성 부족. | Low |
| N8 | **동시성** | `database.py:14` | **`expire_on_commit=False` 전역 설정** — 모든 세션에서 커밋 후 객체가 만료되지 않아 stale 데이터 참조 위험. 특히 웹 요청 간 공유되는 객체가 있을 경우 문제. 단, 현재 `get_db()` 패턴으로 요청당 세션을 생성하므로 실질적 위험은 낮음. | Low |
| N9 | **보안** | `config.py:39,51-55` | **`AUTH_ENABLED` 프로덕션 가드 비대칭** — `jwt_secret`은 프로덕션에서 `RuntimeError`를 발생시키지만(강제 차단), `auth_enabled=False`는 WARNING 로그만 출력. 프로덕션에서 `AUTH_ENABLED=False`가 배포되면 전체 인증 우회. ENV=production 체크를 동일하게 적용해야 함. | High |
| N10 | **에러 처리** | `api/exchange_rates.py:57,94` | **`except Exception`으로 모든 DB 에러를 409로 변환** — IntegrityError(중복키)뿐만 아니라 ConnectionError, OperationalError 등 모든 예외가 "Duplicate" 메시지로 반환. 실제 원인을 숨김. `except IntegrityError`로 한정 필요. | Medium |
| N11 | **데이터 무결성** | `services/chart/bar.py:56`, `pie.py:65`, `waterfall.py:69`, `line.py:71` | **차트 서비스의 `Decimal` → `float` 변환** — 모든 차트 서비스가 `float(v)` 변환. 차트 렌더링 목적으로 `float`이 불가피할 수 있으나, 금액 표시 라벨에서 정밀도 손실 가능. | Low |
| N12 | **보안** | `auth/dependencies.py:24-25` | **`HTTPBearer(auto_error=False)` 설정** — Authorization 헤더 없이도 요청이 계속 진행됨. 쿠키 폴백을 위한 의도적 설계지만, 엔드포인트에서 auth 의존성을 빠뜨리면(N1처럼) 완전 무인증 접근 가능. | Low |

---

## 3. Good Patterns (우수 패턴)

### 크로스 DB JSON 타입 호환 (`db_types.py`)
```python
# fdd/backend/app/utils/db_types.py
JsonbColumn = JSON().with_variant(JSONB(), "postgresql")
```
모든 모델에서 JSONB 직접 사용 대신 `JsonbColumn`을 일관되게 사용. CI(SQLite)와 프로덕션(PostgreSQL) 모두 호환. Grep 결과 `mapped_column(JSONB` 직접 사용 0건 확인.

### Decimal 파싱 안전 패턴 (`ingestion/parser.py`)
```python
def safe_decimal(value: Any) -> Decimal | None:
    return Decimal(str(value))  # float → str → Decimal 변환
```
Excel 파싱 시 `float` → `Decimal` 변환을 `str()` 중간 단계로 처리하여 부동소수점 정밀도 손실 방지. CLAUDE.md Money Rules 준수.

### 권한 분리 패턴 (`webhooks.py`, `exports.py`)
```python
# webhooks.py — 모든 엔드포인트에 require_permission 적용
current_user: CurrentUser = require_permission(Permission.WEBHOOK_MANAGE)

# exports.py — 읽기/삭제 권한 분리
current_user: CurrentUser = require_permission(Permission.EXPORT_READ)     # GET
current_user: CurrentUser = require_permission(Permission.EXPORT_DELETE)    # DELETE
```

### RFC 7807 에러 포맷 (`core/exceptions.py`)
```python
class FDDError(Exception):
    """FDD 도메인 예외 기본 클래스."""
    def to_problem_detail(self) -> dict[str, Any]:
        return {"type": ..., "title": ..., "status": ..., "detail": ..., "instance": ...}
```
에러 코드 체계(1000=ingest, 2000=mapping, 3000=QoE, ...)와 RFC 7807 Problem Details 표준 포맷 일관 적용.

### 감사 로그 시스템 (`services/audit/audit_service.py`)
- before/after 상태 저장, changed_fields 자동 추출
- IP, User-Agent 기록
- entity_type + entity_id 인덱스로 빠른 이력 조회

### Rate Limiting (`api/qoe.py`)
```python
@limiter.limit("5/minute")  # QoE 계산 엔드포인트에 속도 제한
```

### 듀얼 모드 테스트 (`tests/conftest.py`)
- 기본: SQLite in-memory (빠른 CI)
- 옵션: `--use-pg` 플래그로 testcontainers PostgreSQL 사용

---

## 4. Summary

| 항목 | 수치 |
|------|------|
| 총 스캔 대상 파일 | 389개 (app 253 + tests 117 + alembic 19) |
| 직접 읽은 파일 | 27개 |
| Grep 검색 패턴 | 8종 |
| **보류 이슈 재검증** | 5건 전체 확인 (D1~D5) |
| **신규 이슈** | 12건 (N1~N12) |
| - High | 2건 (N2 환율 권한 미분리, N9 AUTH_ENABLED 프로덕션 가드) |
| - Medium | 5건 (N1 산업 인증 누락, N3 float() 금액 계산, N4 except Exception, N5 LLM os.getenv, N10 DB 에러 변환) |
| - Low | 5건 (N6 파일 핸들 누수, N7 UUID 방언, N8 expire_on_commit, N11 차트 float, N12 auto_error=False) |
| **우수 패턴** | 6건 (JsonbColumn, safe_decimal, 권한 분리, RFC 7807, 감사 로그, Rate Limiting) |

### 우선 수정 권장 순서

1. **N9** (High) — `config.py`에서 `AUTH_ENABLED=False` + 프로덕션 환경 시 `RuntimeError` 추가 (jwt_secret과 동일 패턴)
2. **N2** (High) — `exchange_rates.py` 쓰기 엔드포인트에 `require_permission` 적용
3. **N10** (Medium) — `exchange_rates.py`의 `except Exception` → `except IntegrityError`로 한정
4. **N1** (Medium) — `industries.py`에 `get_current_user` 의존성 추가
5. **N5** (Medium) — LLM 설정을 `Settings` 클래스에 통합
6. **N3/N11** (Medium/Low) — report_service.py, chart 서비스의 `float()` 사용 검토 (Decimal 유지 가능한 부분 식별)

---

*Reviewed by Claude Code (read-only observation, no files modified)*
