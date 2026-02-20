# AMIC x PETRA Platform — 프로덕션 배포 가이드

> 작성: 2026-02-20 15:21
> 대상: 최초 프로덕션 배포 및 운영 담당자

---

## 1. 서버 사양

| 항목 | 최소 | 권장 |
|------|------|------|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| CPU | 4 cores | 8 cores |
| RAM | 16 GB | 24 GB |
| Storage | 50 GB SSD | 100 GB SSD |
| Network | 공인 IP, 포트 80/443 | + 도메인 + SSL |

**메모리 내역** (docker-compose.prod.yml 기준):
- FDD API: 2G / KIIS API: 1G / IM API: 2G / MA API: 2G
- DB x4: ~3G / Redis x2: ~1G / Elasticsearch: 2G
- nginx + frontend: ~512M

---

## 2. 서버 초기 설정

```bash
# Docker 설치
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 확인 (Docker 최신 버전에 포함)
docker compose version

# 기타 도구
sudo apt update && sudo apt install -y git curl pwgen
```

---

## 3. 리포지토리 클론

```bash
cd /opt  # 또는 원하는 배포 경로
git clone https://github.com/Gonyak-cell/AMIC-x-PETRA-Platform.git
cd AMIC-x-PETRA-Platform
git checkout master
```

---

## 4. 환경변수 설정

```bash
cp .env.production.example .env
nano .env  # 또는 vim .env
```

### 필수 변경 항목

**비밀 키 생성** (64자 랜덤):
```bash
pwgen -s 64 6
```

| 변수 | 설명 | 예시 |
|------|------|------|
| `DOMAIN` | 도메인 (IP 사용 시 서버 IP) | `platform.example.com` |
| `SSL_CERT_EMAIL` | SSL 인증서 이메일 | `admin@example.com` |
| `SHARED_JWT_SECRET` | **공유 JWT 시크릿** (4개 백엔드 공통) | `pwgen -s 64 1` |
| `FDD_DB_PASSWORD` | FDD DB 비밀번호 | `pwgen -s 64 1` |
| `FDD_CORS_ORIGINS` | 허용 도메인 | `https://platform.example.com` |
| `KIIS_DB_PASSWORD` | KIIS DB 비밀번호 | `pwgen -s 64 1` |
| `KIIS_CORS_ORIGINS` | 허용 도메인 | `https://platform.example.com` |
| `DART_API_KEY` | DART 공시정보 API 키 | https://opendart.fss.or.kr 에서 발급 |
| `KIIS_REDIS_PASSWORD` | KIIS Redis 비밀번호 | `pwgen -s 32 1` |
| `KIIS_ES_PASSWORD` | Elasticsearch 비밀번호 | `pwgen -s 32 1` |
| `IM_DB_PASSWORD` | IM DB 비밀번호 | `pwgen -s 64 1` |
| `IM_CORS_ORIGINS` | 허용 도메인 | `https://platform.example.com` |
| `IM_REDIS_PASSWORD` | IM Redis 비밀번호 | `pwgen -s 32 1` |
| `OPENAI_API_KEY` | OpenAI API 키 | https://platform.openai.com |
| `ANTHROPIC_API_KEY` | Anthropic Claude API 키 | https://console.anthropic.com |
| `GEMINI_API_KEY` | Google Gemini API 키 | https://aistudio.google.com |
| `BRANDFETCH_API_KEY` | Brandfetch 로고 API (선택) | https://brandfetch.com |
| `PINECONE_API_KEY` | Pinecone 벡터 DB (선택) | https://app.pinecone.io |
| `PINECONE_ENVIRONMENT` | Pinecone 환경 | `us-east-1-aws` |
| `MA_DB_PASSWORD` | M&A DB 비밀번호 | `pwgen -s 64 1` |
| `MA_CORS_ORIGINS` | 허용 도메인 (**JSON 배열 필수**) | `["https://platform.example.com"]` |

> **주의**: `CHANGE_ME`가 남아 있으면 서비스 시작 실패. 모든 값을 실제로 변경해야 합니다.
> **참고**: JWT 시크릿은 `SHARED_JWT_SECRET` 하나로 통합됨 — FDD에서 로그인 후 KIIS/IM/MA에서 동일 토큰 검증.

---

## 5. 도메인 / SSL 설정

### 옵션 A: IP만 사용 (HTTP, 내부 테스트용)

추가 설정 불필요. `docker-compose.prod.yml`이 이미 `prod-nossl.conf` 사용.

- 접속: `http://서버IP`
- `.env`에서 `*_CORS_ORIGINS=http://서버IP` 로 설정

### 옵션 B: 도메인 + HTTPS (프로덕션)

**1) DNS 설정**
- A 레코드: `platform.your-domain.com` → 서버 공인 IP

**2) SSL 인증서 발급**
```bash
# Certbot 설치
sudo apt install -y certbot

# 인증서 발급 (nginx 중지 상태에서)
sudo certbot certonly --standalone \
  -d platform.your-domain.com \
  --email admin@your-domain.com \
  --agree-tos --non-interactive
```

**3) nginx 설정 전환**
```bash
# docker-compose.prod.yml에서 nginx 볼륨 수정:
#   ./nginx/prod-nossl.conf → ./nginx/prod.conf
# + Let's Encrypt 인증서 볼륨 추가

# nginx/prod.conf에서 도메인 변경 (2곳):
sed -i 's/platform.example.com/platform.your-domain.com/g' nginx/prod.conf
```

**4) docker-compose.prod.yml nginx 수정**:
```yaml
nginx:
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/prod.conf:/etc/nginx/conf.d/default.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
    - /var/www/certbot:/var/www/certbot:ro
```

**5) SSL 자동 갱신**
```bash
# crontab에 추가
0 3 1,15 * * certbot renew --quiet && docker compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## 6. 초기 배포

```bash
# 전체 빌드 및 시작 (첫 실행 시 이미지 빌드에 10~15분 소요)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 로그 확인 (에러 없는지)
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=50

# 헬스 체크
curl -sf http://localhost/api/fdd/health && echo " FDD OK"
curl -sf http://localhost/api/kiis/health && echo " KIIS OK"
curl -sf http://localhost/api/im/health && echo " IM OK"
curl -sf http://localhost/api/ma/health && echo " MA OK"
curl -sf http://localhost/ > /dev/null && echo " Frontend OK"
```

---

## 7. 초기 사용자 생성

```bash
docker compose exec fdd-api python scripts/seed-users.py
```

---

## 8. 스모크 테스트

브라우저에서 접속 후 아래 확인:

- [ ] 로그인 페이지 로드
- [ ] 로그인 성공 (seed 계정)
- [ ] 대시보드 KPI 카드 로드
- [ ] FDD: 거래 목록 → 거래 생성
- [ ] KIIS: 회사 검색 → 상세 페이지
- [ ] IM: 문서 목록 → 문서 생성
- [ ] MA: 트랜잭션 목록 → 워크스페이스
- [ ] 사이드바 모듈 전환

---

## 9. 백업 자동화

```bash
# 수동 실행 테스트
bash scripts/backup-all-dbs.sh

# cron 등록 (매일 새벽 2시)
crontab -e
# 아래 줄 추가:
0 2 * * * /opt/AMIC-x-PETRA-Platform/scripts/backup-all-dbs.sh >> /var/log/db-backup.log 2>&1
```

- 백업 위치: `backups/YYYYMMDD-HHMMSS/`
- 자동 정리: 7일 이상 백업 삭제
- 4개 DB: fdd.sql.gz, kiis.sql.gz, im.sql.gz, deal-mgmt.sql.gz

---

## 10. GitHub Actions CI/CD 설정

### GitHub Secrets 등록

```powershell
# 로컬에서 실행 (gh CLI 인증 필요)
.\scripts\setup-github-secrets.ps1
```

또는 수동으로 GitHub Settings → Secrets → Actions에서:

| Secret | 설명 |
|--------|------|
| `DEPLOY_HOST` | 서버 IP 또는 도메인 |
| `DEPLOY_USER` | SSH 접속 유저명 |
| `DEPLOY_SSH_KEY` | SSH 개인 키 (전체 내용) |
| `DEPLOY_PATH` | 서버 내 리포지토리 경로 (예: `/opt/AMIC-x-PETRA-Platform`) |
| `VITE_SENTRY_DSN` | Sentry DSN (선택) |
| `SENTRY_AUTH_TOKEN` | Sentry Auth Token (선택) |
| `SENTRY_ORG` | Sentry Organization (선택) |
| `SENTRY_PROJECT` | Sentry Project (선택) |

### 배포 동작

- **자동**: `master` 브랜치 CI 통과 시 자동 배포
- **수동**: GitHub Actions → Deploy → Run workflow (scope: auto/all/frontend-only/backend-only)
- **스마트 감지**: `auto` 모드에서 변경된 모듈만 재빌드
- **롤백**: 헬스 체크 실패 시 이전 커밋으로 자동 복원

---

## 11. 롤백 절차

### 배포 실패 (자동 롤백)

deploy.yml이 헬스 체크 실패 시 자동으로 이전 커밋 복원.

### 수동 롤백

```bash
cd /opt/AMIC-x-PETRA-Platform

# 이전 커밋 확인
git log --oneline -5

# 특정 커밋으로 복원
git checkout <COMMIT_HASH>
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### DB 마이그레이션 롤백

```bash
# 백업에서 복원 (최신 백업 사용)
LATEST=$(ls -td backups/*/ | head -1)
gunzip < "$LATEST/fdd.sql.gz" | docker exec -i amic-fdd-db psql -U autofdd autofdd

# 또는 Alembic downgrade (1단계 롤백)
docker compose exec fdd-api alembic downgrade -1
```

---

## 12. 모니터링 (선택)

### Sentry 에러 추적

1. https://sentry.io 에서 프로젝트 생성
2. `.env`에 `SENTRY_DSN` 설정
3. Alert Rules 설정:
   - Error rate > 10/hour → Email
   - Unhandled exception → 즉시 알림

### Uptime 모니터링

- [UptimeRobot](https://uptimerobot.com) (무료) — 4개 헬스 엔드포인트 등록
- `/api/fdd/health`, `/api/kiis/health`, `/api/im/health`, `/api/ma/health`

### 로그 확인

```bash
# 전체 로그 (최근 100줄)
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100

# 특정 서비스
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f fdd-api

# 에러만
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=500 | grep -i error
```

---

## 부록: 배포 전 체크리스트

### 코드 준비
- [ ] `master` 브랜치 최신
- [ ] `tsc --noEmit` 에러 0건
- [ ] `npm run build` 성공
- [ ] 백엔드 pytest 모두 통과

### 서버 준비
- [ ] Docker + Docker Compose 설치
- [ ] 서버 사양 충족 (4+ CPU, 16GB+ RAM)
- [ ] 포트 80 (+ 443) 방화벽 오픈
- [ ] SSH 키 기반 인증 설정

### 환경변수
- [ ] `.env` 파일 생성 완료
- [ ] `CHANGE_ME` 값 모두 변경 (24개)
- [ ] API 키 유효성 확인 (DART, OpenAI, Anthropic, Gemini)
- [ ] CORS_ORIGINS 정확히 설정

### 배포 후
- [ ] 4개 백엔드 헬스 체크 통과
- [ ] 프론트엔드 로드 확인
- [ ] 로그인 + 기본 동작 확인
- [ ] 백업 cron 등록
- [ ] (선택) Sentry 알림 설정
- [ ] (선택) Uptime 모니터링 등록
