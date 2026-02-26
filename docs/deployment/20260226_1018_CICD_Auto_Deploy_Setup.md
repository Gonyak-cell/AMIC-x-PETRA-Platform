# CI/CD 자동 배포 설정 가이드

> **작성일**: 2026-02-26 10:18
> **워크플로우 파일**: `.github/workflows/deploy.yml`

---

## 1. 동작 방식

```
로컬 코드 수정 → git push → GitHub Actions 자동 트리거 → 서버 배포
```

### 배포 파이프라인 (6단계)

| 단계 | 동작 |
|------|------|
| 1. DB Backup | 배포 전 자동 백업 (스크립트 있는 경우) |
| 2. Git Pull | 서버에서 해당 브랜치 최신 코드 pull |
| 3. Detect Changes | 변경 파일 기반으로 재빌드 대상 서비스 자동 감지 |
| 4. Build & Restart | 변경된 서비스만 Docker 빌드 + 재시작 |
| 5. DB Migrations | 변경된 백엔드의 Alembic migration 자동 실행 |
| 6. Health Check | 4개 API + 프론트엔드 헬스체크, 실패 시 자동 롤백 |

### 변경 감지 규칙

| 변경 경로 | 재빌드 대상 |
|-----------|------------|
| `amic-platform/` | frontend, nginx |
| `nginx/` | nginx |
| `fdd/` | fdd-api + FDD migration |
| `kiis/` | kiis-api + KIIS migration |
| `im/` | im-api, im-celery-worker, im-celery-beat + IM migration |
| `deal-mgmt/` | deal-mgmt-api + MA migration |

---

## 2. 트리거 조건

### 자동 (push)
```yaml
on:
  push:
    branches: [master, develop, feat/ma-workflow]
```

### 수동 (workflow_dispatch)
GitHub Actions 탭 → Deploy → Run workflow → scope 선택:
- `auto` — 변경 파일 기반 자동 감지 (기본)
- `all` — 전체 서비스 재빌드
- `frontend-only` — 프론트엔드만
- `backend-only` — 백엔드 전체

---

## 3. GitHub Secrets (4개)

| Secret | 값 | 설명 |
|--------|-----|------|
| `DEPLOY_HOST` | `52.231.69.38` | Azure VM 공용 IP |
| `DEPLOY_USER` | `azureuser` | SSH 사용자명 |
| `DEPLOY_SSH_KEY` | PEM 키 전체 내용 | SSH 인증 키 |
| `DEPLOY_PATH` | `/opt/amic-platform` | 서버 코드 경로 |

### Secrets 설정 위치
GitHub → 리포지토리 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### PEM 키 파일 위치
```
OneDrive - 주식회사 페트라브릿지파트너스/AMIC의 파일 - 3. Administration/기타. 플랫폼/amic-platform-prod_key.pem
```

---

## 4. 일상 사용법

### 코드 수정 후 배포
```bash
git add <파일>
git commit -m "feat(...): 설명"
git push origin feat/ma-workflow
# → 자동 배포 시작. GitHub Actions 탭에서 진행 상황 확인 가능
```

### 배포 상태 확인 (로컬에서)
```bash
gh run list --limit 5          # 최근 배포 목록
gh run view <run-id> --log     # 배포 로그 상세
gh run watch <run-id>          # 실시간 모니터링
```

### 수동 배포 (GitHub 웹)
1. GitHub → Actions 탭 → Deploy 워크플로우
2. **Run workflow** 클릭
3. scope 선택 (auto/all/frontend-only/backend-only)
4. **Run workflow** 실행

### 수동 배포 (서버 직접)
```bash
ssh -i "amic-platform-prod_key.pem" azureuser@52.231.69.38
cd /opt/amic-platform
git pull origin feat/ma-workflow
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 5. 주요 설정값

| 항목 | 값 |
|------|-----|
| SSH 타임아웃 | 30분 (`command_timeout: 30m`) |
| Docker 빌드 | 캐시 사용 (`--no-cache` 제거됨) |
| 헬스체크 대기 | 15초 (`sleep 15`) |
| 롤백 | 헬스체크 실패 시 이전 커밋으로 자동 롤백 |
| 동시 실행 | 불가 (`concurrency` 설정, 순차 실행) |

---

## 6. 트러블슈팅

### 배포 타임아웃
- 현재 30분 설정. 초과 시 `deploy.yml`의 `command_timeout` 값 증가

### 헬스체크 실패로 롤백됨
- GitHub Actions 로그에서 어떤 서비스가 FAILED인지 확인
- 서버 SSH 접속 후 `docker logs <컨테이너명>` 으로 상세 로그 확인

### 변경 감지가 안 됨 (No relevant services)
- `scope: all` 로 수동 실행하여 전체 재빌드

### SSH 접속 실패
- `DEPLOY_SSH_KEY` 시크릿 값이 PEM 키 전체 내용인지 확인
- `-----BEGIN RSA PRIVATE KEY-----` ~ `-----END RSA PRIVATE KEY-----` 포함 필수
