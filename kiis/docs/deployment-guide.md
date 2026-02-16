# KIIS 배포 및 운영 가이드

## Quick Start (개발 환경)

### 사전 요구사항

- Python 3.11+
- Docker & Docker Compose
- uv (Python 패키지 매니저)
- Git

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone <repository-url>
cd kiis-project

# 2. 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 DART_API_KEY 등 필수 값 입력

# 3. Docker 컨테이너 실행 (PostgreSQL + Redis + ElasticSearch)
docker-compose up -d

# 4. Python 의존성 설치
uv sync

# 5. 데이터베이스 마이그레이션
uv run alembic upgrade head

# 6. 개발 서버 실행
uv run uvicorn app.main:app --reload --port 8000
```

### 접속 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

---

## Docker 프로덕션 배포

### 1. 환경변수 준비

```bash
# 프로덕션 환경변수 파일 생성
cp .env.example .env

# SECRET_KEY 생성
python -c "import secrets; print(secrets.token_urlsafe(64))"

# .env 파일에서 모든 CHANGE-THIS 값을 실제 값으로 교체
```

### 2. 컨테이너 실행

```bash
# 프로덕션 모드 실행
docker-compose -f docker-compose.prod.yml up -d

# 상태 확인
docker-compose -f docker-compose.prod.yml ps

# Health Check
curl http://localhost:8000/health
```

### 3. 프로덕션 체크리스트

- [ ] `SECRET_KEY`를 안전한 랜덤 값으로 변경
- [ ] `DEBUG=False` 설정
- [ ] `DART_API_KEY` 유효한 키 입력
- [ ] `DATABASE_URL` 프로덕션 DB 접속 정보로 변경
- [ ] `ALLOWED_ORIGINS`를 실제 프론트엔드 도메인으로 제한
- [ ] PostgreSQL 비밀번호를 안전한 값으로 변경
- [ ] Redis 인증 설정 (필요 시)

---

## 환경변수 설명

### 앱 기본 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `APP_NAME` | 애플리케이션 이름 | `KIIS` |
| `DEBUG` | 디버그 모드 | `False` |
| `SECRET_KEY` | JWT 서명 및 암호화용 비밀 키 | `change-this-to-a-random-secret-key` |

### 데이터베이스

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 비동기 접속 URL | `postgresql+asyncpg://kiis_user:kiis_dev_password@localhost:5432/kiis` |
| `DB_POOL_SIZE` | 커넥션 풀 크기 | `10` |
| `DB_POOL_MAX_OVERFLOW` | 최대 초과 커넥션 | `20` |
| `DB_POOL_RECYCLE` | 커넥션 재활용 주기 (초) | `3600` |
| `DB_POOL_TIMEOUT` | 커넥션 타임아웃 (초) | `30` |

### Redis

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `REDIS_URL` | Redis 접속 URL | `redis://localhost:6379/0` |

### JWT 인증

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `JWT_ALGORITHM` | JWT 서명 알고리즘 | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 액세스 토큰 만료 시간 (분) | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 리프레시 토큰 만료 시간 (일) | `7` |

### ElasticSearch

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `ELASTICSEARCH_URL` | ElasticSearch 접속 URL | `""` (빈 값이면 비활성화) |

### CORS

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `ALLOWED_ORIGINS` | CORS 허용 Origin 목록 | `["http://localhost:3000", "http://localhost:8000"]` |

### Rate Limiting

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `RATE_LIMIT_LOGIN_MAX` | 로그인 Rate Limit 최대 요청 수 | `5` |
| `RATE_LIMIT_LOGIN_WINDOW` | 로그인 Rate Limit 윈도우 (초) | `60` |

### DART API (금융감독원)

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `DART_API_KEY` | Open DART API 인증 키 | `""` |
| `DART_BASE_URL` | DART API 기본 URL | `https://opendart.fss.or.kr/api` |
| `DART_RATE_LIMIT_PER_MINUTE` | DART 분당 최대 요청 수 | `900` |
| `DART_RATE_LIMIT_PER_DAY` | DART 일일 최대 요청 수 | `9000` |

### KOFIA (금융투자협회)

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `KOFIA_DIS_BASE_URL` | KOFIA 공시 시스템 URL | `https://dis.kofia.or.kr` |
| `KOFIA_RATE_LIMIT_PER_MINUTE` | KOFIA 분당 최대 요청 수 | `20` |
| `KOFIA_RATE_LIMIT_PER_DAY` | KOFIA 일일 최대 요청 수 | `1000` |
| `KOFIA_REQUEST_DELAY` | KOFIA 요청 간 최소 간격 (초) | `3.0` |

### REITs (리츠정보시스템)

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `REITS_BASE_URL` | 리츠정보시스템 URL | `https://reits.molit.go.kr` |
| `REITS_RATE_LIMIT_PER_MINUTE` | 리츠 분당 최대 요청 수 | `20` |
| `REITS_RATE_LIMIT_PER_DAY` | 리츠 일일 최대 요청 수 | `500` |
| `REITS_REQUEST_DELAY` | 리츠 요청 간 최소 간격 (초) | `3.0` |

---

## API 구조

### Base URL

```
http://localhost:8000/api/v1/
```

### API 그룹

| 그룹 | 경로 | 설명 |
|------|------|------|
| **Auth** | `/api/v1/auth/` | 사용자 인증 및 토큰 관리 |
| **DART** | `/api/v1/dart/` | 금융감독원 전자공시 데이터 조회 |
| **KOFIA** | `/api/v1/kofia/` | 금융투자협회 펀드 정보 조회 |
| **REITs** | `/api/v1/reits/` | 리츠 정보 조회 및 분석 |
| **Companies** | `/api/v1/companies/` | 기업 정보 통합 조회 |
| **News** | `/api/v1/news/` | 금융 뉴스 수집 및 NLP 분석 |
| **Entity Resolution** | `/api/v1/entities/` | 기업명 동일성 판별 |
| **Analysis** | `/api/v1/analysis/` | 평판 분석 및 스코어링 |
| **Deals** | `/api/v1/deals/` | 딜 소싱 및 투자 DNA 분석 |
| **Disclosures** | `/api/v1/disclosures/` | 전자공시 딥링크 관리 |
| **Portfolio** | `/api/v1/portfolio/` | 포트폴리오 생존분석 |
| **Managers** | `/api/v1/managers/` | 심사역(Key Man) 이동 추적 |
| **Sanctions** | `/api/v1/sanctions/` | 금융 제재 경중 분류 |
| **Search** | `/api/v1/search/` | ElasticSearch 통합검색 |
| **Dashboard** | `/api/v1/dashboard/` | 시스템 대시보드 요약 |
| **Watchlist** | `/api/v1/watchlist/` | 관심 기업 모니터링 |
| **Alerts** | `/api/v1/alerts/` | 알림 이력 관리 |

### API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 에러 응답 형식

모든 에러 응답은 다음과 같은 표준 형식을 따릅니다.

```json
{
    "detail": "에러 메시지",
    "code": "ERROR_CODE",
    "timestamp": "2024-01-01T00:00:00+00:00"
}
```

주요 에러 코드:

| 코드 | HTTP 상태 | 설명 |
|------|-----------|------|
| `DART_UNREGISTERED_KEY` | 401 | DART API 미등록 키 |
| `DART_RATE_LIMITED` | 429 | DART API 호출 한도 초과 |
| `DART_NO_RESULT` | 404 | DART 조회 결과 없음 |
| `DART_INVALID_PARAMS` | 400 | DART 파라미터 오류 |
| `DART_SYSTEM_MAINTENANCE` | 503 | DART 시스템 점검 중 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 Rate Limit 초과 |
| `EXTERNAL_API_ERROR` | 502 | 외부 API 통신 오류 |

---

## 테스트

### 단위 테스트

```bash
# 전체 테스트 실행
uv run pytest tests/ -v

# 특정 테스트 파일 실행
uv run pytest tests/test_dart_service.py -v

# 특정 테스트 함수 실행
uv run pytest tests/test_dart_service.py::test_function_name -v
```

### 통합 테스트

```bash
# 통합 테스트 (실제 API 키 필요)
uv run pytest tests/integration/ -v -m integration
```

### E2E 테스트

```bash
# End-to-End 테스트
uv run pytest tests/e2e/ -v -m e2e
```

### 테스트 커버리지

```bash
# HTML 커버리지 리포트 생성
uv run pytest tests/ --cov=app --cov-report=html

# 터미널에 커버리지 요약 출력
uv run pytest tests/ --cov=app --cov-report=term-missing
```

---

## 개발 도구

### 코드 린트 및 포맷

```bash
# 린트 검사
uv run ruff check .

# 린트 자동 수정
uv run ruff check . --fix

# 코드 포맷
uv run ruff format .
```

### 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 자동 생성
uv run alembic revision --autogenerate -m "description"

# 마이그레이션 적용 (최신)
uv run alembic upgrade head

# 마이그레이션 롤백 (1단계)
uv run alembic downgrade -1

# 마이그레이션 이력 확인
uv run alembic history
```

### Docker 관리

```bash
# 컨테이너 시작
docker-compose up -d

# 컨테이너 중지
docker-compose down

# 로그 확인
docker-compose logs -f

# 볼륨 포함 완전 제거
docker-compose down -v
```

---

## 인프라 구성

### Docker Compose 서비스

| 서비스 | 이미지 | 포트 | 용도 |
|--------|--------|------|------|
| PostgreSQL | `postgres:16-alpine` | 5432 | 주 데이터베이스 |
| Redis | `redis:7-alpine` | 6379 | 캐싱 및 Rate Limiting |
| ElasticSearch | `elasticsearch:8.12.0` | 9200 | 통합 검색 엔진 |

### Health Check 엔드포인트

```bash
# 애플리케이션
curl http://localhost:8000/health

# PostgreSQL
docker exec kiis-postgres pg_isready -U kiis_user -d kiis

# Redis
docker exec kiis-redis redis-cli ping

# ElasticSearch
curl http://localhost:9200/_cluster/health
```
