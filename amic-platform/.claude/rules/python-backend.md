# Python Backend Rules (FastAPI / Pydantic v2 / SQLAlchemy 2.0)

> 출처: software-dev-ai-claude-toolkit (Ashfaqbs) 참조, 프로젝트 스택에 맞게 커스터마이즈

## Python 표준
- Python 3.12+. 모든 함수 시그니처에 type hints 필수.
- 데이터 구조는 `@dataclass(frozen=True)` 또는 Pydantic `BaseModel` 사용.
- 포맷: `ruff format`. 린트: `ruff check`. 타입 체크: `pyright`.
- 프로덕션 코드에서 `print()` 금지 → `logging` 모듈 사용.
- 의존성 관리: `requirements.txt` 또는 `pyproject.toml`에 버전 고정.

## FastAPI 규칙
- 모든 request/response에 Pydantic 모델 사용. raw dict로 API I/O 금지.
- `Depends()`로 의존성 주입 (DB 세션, 인증, 서비스).
- I/O-bound 작업: `async def`. CPU-bound: `def`.
- 라우터는 도메인별로 구성: `routers/transactions.py`, `routers/legal_documents.py`.
- 전역 예외 핸들러: `@app.exception_handler()`.
- fire-and-forget 작업: `BackgroundTasks` 사용.

## 프로젝트 디렉토리 구조 (모노레포)

**표준 구조 (deal-mgmt, kiis):**
```
{module}/app/
  main.py           # FastAPI app, 미들웨어, startup events
  core/             # 인증, 미들웨어, 예외, 설정
  routers/          # API 라우트 핸들러
  models/           # SQLAlchemy 모델
  schemas/          # Pydantic 스키마 (request/response)
  services/         # 비즈니스 로직
```

**FDD (routers 대신 api):**
```
fdd/backend/app/
  main.py
  core/             # exceptions, errors, logging
  api/              # API 핸들러 (routers/ 아님)
  models/
  schemas/
  services/
```

**IM (완전히 다른 구조):**
```
im/src/api/
  main.py
  routes/           # API 핸들러 (routers/ 아님)
  schemas/
  services/
```

## 데이터베이스 액세스
- PostgreSQL: `SQLAlchemy 2.0` + `asyncpg` (비동기) 또는 동기 모드.
- 커넥션 풀링 필수. 세션은 컨텍스트 매니저로 안전하게 종료.
- 마이그레이션: Alembic 사용. 수동 스키마 변경 금지.

## 코드 품질
- 한 함수에 하나의 책임. 함수가 너무 길면 분리.
- 에러 처리: 구체적인 예외 타입 사용 (`raise ValueError`, `raise HTTPException`).
- 매직 넘버/문자열 금지 → 상수 또는 Enum 사용.
- 불필요한 주석 금지. 코드가 자명하게 작성.
