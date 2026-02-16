# KIIS - Korea Investment Intelligence System

## 프로젝트 개요
DART, KOFIA, 리츠정보시스템의 투자정보를 통합하여 인텔리전스를 제공하는 백엔드 API 시스템.
상세 구현 계획: @docs/plans/KIIS_구현계획서.md

## 기술 스택
- Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / Alembic
- PostgreSQL 16 / Redis 7
- httpx (async HTTP) / BeautifulSoup4
- pytest / ruff / uv

## 프로젝트 구조

```text
app/
├── main.py              # FastAPI 앱 초기화, 라우터 등록
├── core/
│   ├── config.py        # Pydantic Settings (환경변수)
│   ├── database.py      # async SessionLocal, engine
│   └── exceptions.py    # 전역 예외 핸들러
├── routers/             # API 엔드포인트 (도메인별 분리)
│   └── dart.py
├── services/            # 비즈니스 로직 (외부 API 호출 등)
│   └── dart_service.py
├── schemas/             # Pydantic v2 요청/응답 스키마
│   └── dart.py
├── models/              # SQLAlchemy ORM 모델
├── utils/
│   ├── http_client.py   # 공용 httpx AsyncClient
│   └── rate_limiter.py  # API Rate Limiter
migrations/              # Alembic 마이그레이션 (수동 편집 금지)
tests/                   # pytest 테스트
```

## 핵심 규칙

### 코드 스타일
- ruff로 린트 (line-length=120)
- 타입 힌트 필수
- async/await 패턴 사용 (동기 함수 금지)
- Pydantic v2 스키마 사용 (`model_config = ConfigDict(from_attributes=True)`)

### API 설계
- 경로: `/api/v1/{domain}/{resource}`
- 응답: Pydantic 스키마 기반 JSON
- 에러: HTTPException + 전역 예외 핸들러
- 페이지네이션: `?page=1&size=20` (최대 100)

### 데이터베이스
- SQLAlchemy 2.0 async 패턴
- `expire_on_commit=False` 필수
- 모든 모델에 TimestampMixin (created_at, updated_at)
- Alembic 자동 마이그레이션 (`migrations/versions/` 수동 편집 금지)

### 테스트
- pytest-asyncio (asyncio_mode="auto")
- 외부 API는 pytest-httpx로 모킹 (URL 매칭: `url=` 파라미터 사용)
- 테스트 DB: SQLite async (또는 별도 PostgreSQL)
- pytest-httpx 0.36+: `url=re.compile(r".*pattern.*")` 으로 regex 매칭

### 보안
- .env로 시크릿 관리 (절대 커밋 금지)
- DART API 키 Rate Limiting (분당 900회)
- CORS 설정 필수

## 흔한 실수 방지

1. async 함수에서 `await` 누락 → 코루틴 객체 반환됨
2. `requests` 대신 반드시 `httpx` (async) 사용
3. DB 세션에 `expire_on_commit=False` 누락 → 세션 종료 후 속성 접근 에러
4. httpx AsyncClient는 `aclose()` 사용 (`close()`는 제거됨)
5. `migrations/versions/` 파일 수동 편집 → Alembic으로만 관리

## 자동화 설정 (.claude/)

### Hooks (자동 실행)

- **PreToolUse (Edit|Write)**: `.env`, `migrations/versions/` 파일 편집 자동 차단
- **PostToolUse (Edit|Write)**: `.py` 파일 편집 후 자동 `ruff format` + `ruff check --fix`
- **Stop (prompt)**: 작업 완료 여부 LLM 평가 → 미완료 시 자동 계속 진행

### Permissions (자동 적용)

- 허용: `uv run pytest/ruff/uvicorn/alembic`, `git status/diff/log/add/commit`
- 차단: `.env` 읽기, `rm -rf`, `git push --force`, `git reset --hard`

### Skills (자동+수동 호출)

- `/test [파일]` - 테스트 실행 + 실패 분석 (관련 상황에서 자동 호출됨)
- `/lint [경로]` - ruff check + format 일괄 실행
- `/migrate "설명"` - Alembic 마이그레이션 안전 워크플로우 (생성→검토→왕복테스트)

## 명령어

- 의존성 설치: `uv sync`
- 서버 실행: `uv run uvicorn app.main:app --reload --port 8000`
- 테스트: `uv run pytest tests/ -v`
- 린트: `uv run ruff check .`
- 포맷: `uv run ruff format .`
- DB 마이그레이션 생성: `uv run alembic revision --autogenerate -m "description"`
- DB 마이그레이션 적용: `uv run alembic upgrade head`
- DB 롤백: `uv run alembic downgrade -1`
- Docker: `docker-compose up -d`
