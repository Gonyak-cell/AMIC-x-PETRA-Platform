# 배포 파이프라인 영구 안정화 보고서

> 작성: 2026-02-26 15:44
> 상태: **완료** — 4개 모듈 프로덕션 정상 가동 확인

---

## 1. 문제 요약

프로덕션 대시보드에서 M&A Deals: **Unreachable**, Deal Doc Studio: **Degraded** 표시.
로그인 코드를 수정하지 않았는데 배포 후 반복적으로 서비스가 깨지는 현상.

---

## 2. 근본 원인 (3가지)

### 2-1. Docker BuildKit 이미지 스왑

- `docker-compose.yml`에 `image:` 태그 없이 빌드하면 BuildKit이 병렬 빌드 시 이미지를 잘못 매핑
- 예: fdd-api 컨테이너에 kiis-api 이미지가 배치되는 현상
- 헬스체크 `service` 필드로 감지 가능

### 2-2. Alembic 3중 실행

- `docker-entrypoint.sh` + `main.py lifespan` + `deploy.yml` 세 곳에서 `alembic upgrade head` 실행
- 동시 실행 시 락 충돌, DuplicateTableError, alembic_version 불일치 발생
- IM DB에는 `alembic_version` 테이블 자체가 없어 모든 마이그레이션을 처음부터 실행 시도 → 이미 존재하는 `users` 테이블 생성 시도 → 크래시

### 2-3. 안전장치 부재

- 환경변수 누락 시 배포 진행 → 런타임 에러
- 헬스체크에서 DB 연결 미확인 → "서비스 올라왔지만 DB 죽음" 상태 미감지
- 이미지 스왑 감지 불가 → 잘못된 이미지로 배포 완료 처리

---

## 3. 수정 내역

### 3-1. 코드 수정

| 파일 | 변경 | 이유 |
|------|------|------|
| `kiis/scripts/docker-entrypoint.sh` | `alembic upgrade head` 4줄 제거 → 주석 1줄 | Alembic 중복 실행 방지 (deploy.yml에서만 관리) |
| `im/src/api/routes/health.py` | `HealthResponse`에 `service: str`, `db: str` 필드 추가 | deploy.yml 헬스체크에서 이미지 스왑/DB 감지 |

### 3-2. deploy.yml 수정 (사용자 직접 수정)

| 항목 | 내용 |
|------|------|
| `--no-cache` 제거 | image 태그로 이미지 스왑 방지됨 → `--no-cache` 불필요 (빌드 시간만 증가) |
| 환경변수 검증 게이트 (Step 3.5) | 9개 필수 변수 누락 시 배포 즉시 중단 |
| 이미지 스왑 감지 | 헬스체크에서 `service` 필드와 기대값 비교 (case 문으로 ma→deal-mgmt 매핑) |
| 디버그 출력 | 헬스체크 실패 시 raw 응답 + 컨테이너 로그 출력 |
| sleep 15→30 | IM depends_on 체인 (im-db, im-redis) 대기 시간 확보 |
| 안정성 재확인 (Step 7) | 배포 30초 후 재검증 → 지연 크래시 감지 |
| 컨테이너 로그 캡처 (Step 8) | docker stats + 6개 서비스 로그 항상 출력 |

### 3-3. 프로덕션 즉시 복구 (SSH)

| 단계 | 명령 | 결과 |
|------|------|------|
| IM DB alembic_version stamp | `CREATE TABLE alembic_version` + `INSERT 008_checklist_uq_fiscal_yr` | 테이블 생성 + 버전 스탬프 완료 |
| im-api 재시작 | `docker compose up -d im-api` | healthy 상태 전환 |
| nginx 리로드 | `docker compose exec -T nginx nginx -s reload` | upstream IP 갱신 |

### 3-4. 인프라 보호 규칙 생성

`.claude/rules/infra-freeze.md` — Tier 1/Tier 2 파일 보호:
- Tier 1: `docker-compose*.yml`, `deploy.yml` → 절대 수정 금지
- Tier 2: `nginx/prod.conf`, `entrypoint.sh`, `main.py` lifespan/health → 사용자 확인 필수

---

## 4. 최종 검증 결과

### 프로덕션 헬스체크 (2026-02-26 15:30경)

```json
FDD:  {"status":"ok", "service":"fdd",       "version":"0.1.0", "migration_ok":true, "db":"ok"}
KIIS: {"status":"ok", "service":"kiis",      "migration_ok":true, "db":"ok"}
IM:   {"status":"ok", "service":"im",        "version":"0.1.0", "db":"ok"}
MA:   {"status":"ok", "service":"deal-mgmt", "migration_ok":true, "db":"ok"}
```

### 현재 Alembic 실행 지점 (단일화 완료)

| 실행 위치 | FDD | KIIS | IM | MA |
|----------|-----|------|----|----|
| `*/scripts/docker-entrypoint.sh` | ❌ 없음 | ❌ 없음 | ❌ 없음 (entrypoint 자체 없음) | ❌ 없음 |
| `*/main.py` lifespan | ❌ 없음 | ❌ 없음 | ❌ 없음 | ❌ 없음 |
| `deploy.yml` Step 5 | ✅ 유일 | ✅ 유일 | ✅ 유일 | ✅ 유일 |

### Docker image 태그 현황

모든 서비스에 `image:` 태그 존재 → BuildKit 이미지 스왑 방지.

---

## 5. 관련 파일

| 파일 | 역할 |
|------|------|
| `.github/workflows/deploy.yml` | CI/CD 배포 파이프라인 (8단계) |
| `docker-compose.yml` | 서비스 정의 + image 태그 |
| `docker-compose.prod.yml` | 프로덕션 오버라이드 (workers, volumes) |
| `docker-compose.ssl.yml` | SSL/인증서 설정 |
| `kiis/scripts/docker-entrypoint.sh` | KIIS 컨테이너 진입점 |
| `im/src/api/routes/health.py` | IM 헬스체크 엔드포인트 |
| `.claude/rules/infra-freeze.md` | 인프라 파일 보호 규칙 |
| `.claude/rules/code-freeze.md` | 전체 소스코드 동결 규칙 |

---

## 6. 관련 문서

- `docs/deployment/20260226_1429_FDD_MA_502_Fix.md` — 이미지 스왑 버그 최초 발견/수정
- `docs/deployment/20260226_1254_CICD_Health_Check_SSL_Fix.md` — 헬스체크 SSL 우회 수정
- `docs/deployment/20260226_1237_Production_Diagnostic_System.md` — 통합 진단 시스템
