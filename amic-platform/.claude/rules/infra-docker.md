# Infrastructure Rules (Docker + docker-compose)

> 출처: software-dev-ai-claude-toolkit (Ashfaqbs) 참조, 프로젝트 스택에 맞게 커스터마이즈

## Docker 규칙
- 멀티스테이지 빌드로 이미지 크기 최소화. 빌드/런타임 스테이지 분리.
- 특정 베이스 이미지 태그 사용 (예: `python:3.12-slim`). `latest` 태그 금지.
- non-root 사용자로 실행. `USER appuser` 추가.
- Dockerfile 레이어 순서: OS 의존성 → 앱 의존성 → 소스 코드 (캐시 극대화).
- `.dockerignore`에 제외: `.git`, `node_modules`, `__pycache__/`, `.env`, `*.pyc`.
- 컨테이너당 하나의 프로세스. 로컬 개발은 docker-compose 사용.
- 헬스체크: `HEALTHCHECK` 지시어 또는 compose에서 정의.

## docker-compose 규칙
- 환경별 compose 파일 분리: `docker-compose.yml` (공통), `docker-compose.prod.yml` (프로덕션).
- 서비스 간 의존성: `depends_on` + 헬스체크 condition 사용.
- 볼륨 마운트: 개발 시 소스 코드 마운트, 프로덕션에서는 이미지에 포함.
- 네트워크: 서비스별 필요한 네트워크만 연결.

## 모노레포 서비스 구성
```yaml
services:
  # 백엔드 API
  fdd-api:           # FDD 백엔드 (포트 8000)
  kiis-api:          # KIIS 백엔드 (포트 8001)
  im-api:            # IM 백엔드 (포트 8002)
  deal-mgmt-api:     # Deal Management 백엔드 (포트 8003)

  # 데이터베이스 (모듈별 독립)
  fdd-db:            # FDD 전용 PostgreSQL (포트 5433)
  kiis-db:           # KIIS 전용 PostgreSQL (포트 5434)
  im-db:             # IM 전용 PostgreSQL (포트 5435)
  deal-mgmt-db:      # Deal Management 전용 PostgreSQL (포트 5436)

  # 부가 서비스
  fdd-pptx:          # FDD PPTX 서비스 (포트 3100)
  kiis-redis:        # KIIS Redis (포트 6379)
  im-redis:          # IM Redis (포트 6380)
  im-celery-worker:  # IM Celery Worker
  im-celery-beat:    # IM Celery Beat

  # 프론트엔드 & 프록시
  frontend:          # React 프론트엔드 (포트 5173)
  nginx:             # 리버스 프록시 (dev:3000 / prod:80)
```
- **주의**: 공유 DB 없음. 각 모듈이 독립 PostgreSQL 인스턴스 사용.

## nginx 규칙
- 리버스 프록시로 백엔드 서비스 라우팅.
- SSL/TLS 종단 처리.
- 보안 헤더 추가 (`X-Frame-Options`, `X-Content-Type-Options` 등).
- gzip 압축 활성화.
- 정적 파일 캐싱 설정.
