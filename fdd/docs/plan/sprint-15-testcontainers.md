# Sprint 15 — SQLite→PostgreSQL Testcontainers 마이그레이션

> 작성일: 2026년 02월 10일 12시 23분
> 상태: PLANNED
> 선행조건: Docker Desktop 설치 및 실행 필요

---

## 1. 배경

Sprint 14에서 PostgreSQL/Docker 의존 테스트 30+ 파일을 제거했습니다.
기존 conftest.py가 로컬 PostgreSQL 인스턴스에 의존하여 Docker 없는 환경에서 테스트 실행이 불가능했습니다.

**Testcontainers**를 도입하면:
- Docker만 있으면 어디서든 PostgreSQL 테스트 실행 가능
- CI/CD에서도 동일한 환경 보장
- SQLite 호환성 문제 (JSON, Array, CTE 등) 완전 해소

---

## 2. 작업 범위

### Phase 1: 인프라 설정 (conftest.py + 의존성)

| 항목 | 내용 |
|------|------|
| `pyproject.toml` | `testcontainers[postgres]>=4.0.0` dev 의존성 추가 |
| `backend/tests/conftest.py` | testcontainers PostgreSQL fixture 구현 |
| pytest marker | `@pytest.mark.db` — DB 테스트 마킹, `--skip-db` 옵션 |

**conftest.py 핵심 설계:**
```python
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """Session-scoped PostgreSQL 컨테이너 — 전체 테스트에서 1회만 시작."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

@pytest.fixture(scope="function")
def db(postgres_container):
    """Function-scoped DB session — 매 테스트마다 트랜잭션 롤백."""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    session = SessionLocal(bind=engine)
    yield session
    session.rollback()
    session.close()
```

### Phase 2: 핵심 테스트 복원

삭제된 테스트 중 우선순위별 복원:

| 우선순위 | 파일 | 테스트 수 (예상) | 의존 모듈 |
|----------|------|-----------------|-----------|
| P0 | `test_deals.py` | ~15 | Deal CRUD |
| P0 | `test_uploads.py` | ~20 | 인제스트 파이프라인 |
| P0 | `test_coa_mapper.py` | ~25 | CoA 매핑 |
| P1 | `test_qoe_engine.py` | ~20 | QoE 엔진 |
| P1 | `test_nwc_engine.py` | ~15 | NWC 엔진 |
| P1 | `test_debt_engine.py` | ~15 | Debt 엔진 |
| P2 | `test_tie_out.py` | ~20 | Tie-out 검증 |
| P2 | `test_evidence.py` | ~18 | Evidence Ledger |
| P2 | `test_report_builder.py` | ~20 | Report IR |
| P3 | `test_*_api.py` (6개) | ~60 | API 엔드포인트 |
| P3 | `test_*_golden.py` (5개) | ~40 | Golden 회귀 |
| P3 | 기타 (`hashing`, `guardrails`, `validator` 등) | ~30 | 유틸리티 |

### Phase 3: CI/CD 설정

| 항목 | 내용 |
|------|------|
| GitHub Actions | Docker-in-Docker 서비스 추가 |
| pytest 설정 | `--skip-db` 기본값 (Docker 없는 환경 대응) |
| 테스트 분리 | `pytest -m "not db"` — 순수 단위 테스트만 실행 |

---

## 3. 의존성

- **Docker Desktop** (Windows/Mac) 또는 Docker Engine (Linux)
- `testcontainers[postgres]>=4.0.0`
- `postgres:16-alpine` Docker 이미지

---

## 4. 성공 기준

- [ ] `pytest -m db` 실행 시 PostgreSQL 컨테이너 자동 시작
- [ ] 복원된 테스트 전체 PASS
- [ ] `pytest -m "not db"` — Docker 없이도 단위 테스트 실행 가능
- [ ] CI에서 DB 테스트 포함 전체 통과

---

## 5. 리스크

| 리스크 | 대응 |
|--------|------|
| Docker Desktop 미설치 환경 | `@pytest.mark.db` + `--skip-db` 옵션으로 우회 |
| 컨테이너 시작 시간 (~5초) | session scope로 1회만 시작 |
| CI Docker-in-Docker 권한 | GitHub Actions `services:` 블록 사용 |
| Windows 경로 이슈 | testcontainers-python 4.x에서 해결됨 |
