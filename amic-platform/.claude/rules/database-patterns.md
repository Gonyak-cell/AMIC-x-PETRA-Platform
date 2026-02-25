# Database Patterns (PostgreSQL + Alembic)

> 출처: software-dev-ai-claude-toolkit (Ashfaqbs) 참조, 프로젝트 스택에 맞게 커스터마이즈

## PostgreSQL 규칙
- 스키마 변경은 반드시 Alembic 마이그레이션으로. 프로덕션 수동 변경 금지.
- WHERE, JOIN, ORDER BY에 사용되는 컬럼에 인덱스 생성. `EXPLAIN ANALYZE`로 확인.
- 공개 ID: `UUID`. 내부 PK: `BIGSERIAL` 또는 `Integer`.
- 날짜/시간 컬럼: `TIMESTAMPTZ` 사용 (`TIMESTAMP` 금지).
- 커넥션 풀링 필수 (asyncpg pool 또는 SQLAlchemy pool).
- 멀티 스테이트먼트는 트랜잭션 사용. 트랜잭션은 짧게 유지.
- `JSONB` 컬럼은 진정한 스키마리스 데이터에만 사용. 자주 쿼리하는 JSON 필드는 별도 컬럼으로 분리.

## 네이밍 규칙
- 테이블, 컬럼: `snake_case`, 복수형 테이블명 (`transactions`, `legal_documents`).
- 인덱스: `ix_{table}_{column}` 또는 `ix_{table}_{col1}_{col2}`.
- 외래키: `fk_{table}_{ref_table}`.

## Alembic 마이그레이션 규칙
- 마이그레이션 파일명: `{번호}_{설명}.py` (예: `007_phase6_legal_documents.py`).
- 모든 마이그레이션에 `upgrade()` + `downgrade()` 함수 필수.
- downgrade에서 데이터 손실이 발생할 수 있는 경우 주석으로 명시.
- 대용량 테이블 변경 시 온라인 마이그레이션 고려 (락 최소화).
- 마이그레이션 적용 전 반드시 테스트 환경에서 검증.

## 쿼리 최적화
- N+1 쿼리 방지: `joinedload()`, `selectinload()` 사용.
- 대량 데이터: 페이지네이션 필수 (`limit`/`offset` 또는 커서 기반).
- COUNT 쿼리 최소화. 필요 시 `func.count()` 사용.
- 복잡한 쿼리는 서비스 레이어에서 처리, 라우터에서 직접 쿼리 금지.
