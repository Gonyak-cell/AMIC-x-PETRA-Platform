# AMIC x PETRA Platform — 배포 전 수동 작업 상세 가이드

> 생성: 2026-02-13 18:54
> 수정: 2026-02-13 18:59

---

## 요약 체크리스트

| # | 작업 | 필수 시점 | 없으면 |
|---|------|-----------|--------|
| 1a | Sentry Secrets (4개) | CI에서 소스맵 업로드 원할 때 | CI 빌드는 정상, 소스맵 업로드만 skip |
| 1b | Deploy Secrets (4개) | 자동 배포 원할 때 | CI는 정상, Deploy 워크플로우만 실패 |
| 2 | .env 실제 값 입력 | 서버 첫 기동 전 | Docker 컨테이너 시작 실패 |
| 3 | 도메인 + SSL 설정 | HTTPS 필요 시 | HTTP 전용(prod-nossl.conf)으로 대체 가능 |

### 현재 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| GitHub Secrets (Sentry 4개) | ⏳ 대기 | Sentry 계정 생성 필요 |
| GitHub Secrets (Deploy 4개) | ⏳ 대기 | 서버 준비 필요 |
| .env 프로덕션 설정 | ⏳ 대기 | 서버에서 수행 |
| nginx 도메인 설정 | ⏳ 대기 | 도메인 미정 → prod-nossl.conf 사용 |
| SSL 인증서 | ⏳ 대기 | 도메인 확정 후 |

---

## 1. GitHub Secrets 설정

GitHub 레포 → Settings → Secrets and variables → Actions 에서 아래 시크릿을 등록해야 합니다.

### Sentry 관련 (4개)

| Secret | 얻는 방법 | 예시 값 |
|--------|-----------|---------|
| `VITE_SENTRY_DSN` | Sentry 프로젝트 → Settings → Client Keys (DSN) | `https://abc123@o123456.ingest.sentry.io/456789` |
| `SENTRY_AUTH_TOKEN` | Sentry → Settings → Auth Tokens → Create New Token (scope: `org:read`, `project:releases`, `project:write`) | `sntrys_eyJ...` |
| `SENTRY_ORG` | Sentry URL에서 확인: `sentry.io/organizations/{이값}/` | `amic-petra` |
| `SENTRY_PROJECT` | Sentry 프로젝트 이름 (Settings → General) | `amic-platform` |

**Sentry 계정이 아직 없다면:**

1. [sentry.io](https://sentry.io) 가입 (Developer 플랜 무료 — 월 5,000 에러)
2. Organization 생성 → 이름 기록 (`SENTRY_ORG`)
3. React 프로젝트 생성 → 이름 기록 (`SENTRY_PROJECT`)
4. Settings → Client Keys (DSN) → DSN 복사 (`VITE_SENTRY_DSN`)
5. Settings → Auth Tokens → Create New Token
   - Scopes: `org:read`, `project:releases`, `project:write`
   - 토큰 복사 (`SENTRY_AUTH_TOKEN`)

### 배포 서버 관련 (4개)

| Secret | 설명 | 예시 값 |
|--------|------|---------|
| `DEPLOY_HOST` | 프로덕션 서버 IP 또는 도메인 | `123.456.789.10` |
| `DEPLOY_USER` | SSH 접속 유저명 | `ubuntu` |
| `DEPLOY_SSH_KEY` | SSH 프라이빗 키 (서버에 대응하는 공개키 등록 필수) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEPLOY_PATH` | 서버에서 프로젝트가 위치하는 절대경로 | `/opt/amic-platform` |

**SSH 키 생성 (아직 없다면):**

```bash
# 로컬에서 키 생성
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/amic_deploy

# 서버에 공개키 등록
ssh-copy-id -i ~/.ssh/amic_deploy.pub ubuntu@123.456.789.10

# 프라이빗 키 내용을 GitHub Secret에 복사
cat ~/.ssh/amic_deploy
```

> 서버가 아직 없는 경우 이 4개 시크릿은 나중에 설정해도 됩니다.
> CI 파이프라인(lint → test → build → E2E)은 배포 시크릿 없이도 정상 동작합니다. Deploy 워크플로우만 실패합니다.

### 등록 방법

**방법 A: 스크립트 사용 (권장)**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-github-secrets.ps1
```

**방법 B: 개별 등록 (gh CLI)**

```powershell
# Sentry
echo "https://abc@o123.ingest.sentry.io/456" | gh secret set VITE_SENTRY_DSN
echo "sntrys_eyJ..." | gh secret set SENTRY_AUTH_TOKEN
echo "amic-petra" | gh secret set SENTRY_ORG
echo "amic-platform" | gh secret set SENTRY_PROJECT

# Deploy
echo "123.456.789.10" | gh secret set DEPLOY_HOST
echo "ubuntu" | gh secret set DEPLOY_USER
echo "/opt/amic-platform" | gh secret set DEPLOY_PATH
gh secret set DEPLOY_SSH_KEY < ~/.ssh/amic_deploy
```

**방법 C: GitHub 웹 UI**

`https://github.com/Gonyak-cell/AMIC-x-PETRA-Platform/settings/secrets/actions`

---

## 2. .env.production.example → .env 복사 후 실제 값 입력

> 이 작업은 **프로덕션 서버**에서 수행합니다. (로컬 개발 환경이 아님)

```bash
# 서버에서 프로젝트 루트로 이동
cd /opt/amic-platform   # DEPLOY_PATH와 동일

# 템플릿 복사
cp .env.production.example .env

# 편집
nano .env   # 또는 vim
```

### 변경해야 할 항목

```bash
# ── 인프라 ──
DOMAIN=amic.example.com          # 실제 도메인
SSL_CERT_EMAIL=admin@amic.com    # Let's Encrypt 인증서 발급 이메일

# ── FDD ──
FDD_DB_PASSWORD=여기에_강력한_비밀번호    # openssl rand -base64 32 로 생성
FDD_JWT_SECRET=여기에_64자_랜덤_문자열    # openssl rand -hex 32 로 생성
FDD_CORS_ORIGINS=https://amic.example.com

# ── KIIS ──
KIIS_DB_PASSWORD=여기에_강력한_비밀번호
KIIS_SECRET_KEY=여기에_64자_랜덤_문자열
KIIS_CORS_ORIGINS=https://amic.example.com
KIIS_REDIS_PASSWORD=여기에_강력한_비밀번호

# ── IM ──
IM_DB_PASSWORD=여기에_강력한_비밀번호
IM_SECRET_KEY=여기에_64자_랜덤_문자열
IM_CORS_ORIGINS=https://amic.example.com
IM_REDIS_PASSWORD=여기에_강력한_비밀번호

# ── API 키 (기존 개발용 키 그대로 또는 프로덕션 키로 교체) ──
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DART_API_KEY=...
BRANDFETCH_API_KEY=...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...

# ── Sentry ──
SENTRY_DSN=https://...@...ingest.sentry.io/...   # 백엔드용
SENTRY_ENVIRONMENT=production
```

### 비밀번호/시크릿 생성 빠른 명령어

```bash
# 강력한 비밀번호 (각 서비스별 다르게 생성)
openssl rand -base64 32

# 64자 hex 시크릿
openssl rand -hex 32
```

> `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

---

## 3. nginx/prod.conf 도메인 변경

`nginx/prod.conf` 파일에서 `platform.example.com`을 실제 도메인으로 변경합니다.

### 변경 위치 (2곳, 49~50번 줄)

```nginx
# 변경 전
ssl_certificate /etc/letsencrypt/live/platform.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/platform.example.com/privkey.pem;

# 변경 후 (예: amic.example.com)
ssl_certificate /etc/letsencrypt/live/amic.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/amic.example.com/privkey.pem;
```

### .env에서 도메인 변경

```bash
DOMAIN=amic.example.com
FDD_CORS_ORIGINS=https://amic.example.com
KIIS_CORS_ORIGINS=https://amic.example.com
IM_CORS_ORIGINS=https://amic.example.com
```

### SSL 인증서 발급

```bash
# 서버에서 — 먼저 HTTP만으로 certbot 실행
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx

# certbot으로 인증서 발급
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.ssl.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot -d amic.example.com

# SSL 포함하여 전체 기동
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.ssl.yml up -d
```

### 도메인 없이 운영 (임시)

`nginx/prod-nossl.conf` (HTTP 전용)를 대신 사용할 수 있습니다.
`docker-compose.ssl.yml` 없이 기동하면 됩니다.
