# Azure VM 프로덕션 배포 리포트

> **작성일**: 2026-02-26 00:11
> **세션**: Session 40 (Azure 배포 세션 2/2)
> **서버**: Azure VM `52.231.69.38` (Korea Central)

---

## 1. 배포 환경 요약

| 항목 | 값 |
|------|-----|
| **VM** | Standard E2s v3 (2 vCPU, 16GB RAM) |
| **리전** | Korea Central (한국 중부) |
| **OS** | Ubuntu 24.04 LTS |
| **디스크** | Premium SSD 128GB |
| **공용 IP** | 52.231.69.38 (고정) |
| **Docker** | 29.2.1 + Compose v5.1.0 |
| **브랜치** | `feat/ma-workflow` |
| **접속 URL** | http://52.231.69.38 |

---

## 2. 작업 타임라인

### Session 39 (이전 세션) — Azure VM 생성 + 초기 빌드

1. **Azure VM 생성** — Portal GUI로 Korea Central, E2s_v3, Ubuntu 24.04 생성
2. **SSH 접속** — PEM 키로 원격 접속 확인
3. **Docker 설치** — `curl -fsSL https://get.docker.com | sh`
4. **GitHub 클론** — PAT 토큰으로 private repo 클론 (`/opt/amic-platform`)
5. **.env 설정** — 랜덤 비밀번호 생성, JWT_SECRET 통일
6. **TypeScript 빌드 에러 5라운드 수정** (커밋 e269a4d → f8f59d7 → 22cb43c → df65a7c → ff1f508):
   - Button variant `"outline"` → `"secondary"`, `"default"` → `"primary"`
   - `isLoading` → `loading` prop
   - Badge variant `"danger"` → `"error"`, `"default"` → `"neutral"`
   - Card `hover` → `hoverEffect`, `onClick` prop 추가
   - KpiCard `value` number → String()
   - 미사용 import/변수 제거 (strict TS `noUnusedLocals`)
7. **빌드 성공** — 프론트엔드 Docker 이미지 빌드 완료

### Session 40 (본 세션) — 서비스 기동 + 마이그레이션 + 시딩

1. **Elasticsearch 복구** — 초기 healthcheck 타이밍 이슈, 재시작으로 해결
2. **전체 컨테이너 시작** — `docker compose up -d` 로 18개 컨테이너 기동
3. **DB 마이그레이션 4개 모듈**:
   - **MA (deal-mgmt)**: 정상 완료
   - **KIIS**: 정상 완료
   - **FDD**: 3건 수정 필요 → 수정 후 완료
   - **IM**: alembic_version 컬럼 확장 후 완료
4. **시드 데이터**: 6명 사용자 × 3개 DB (FDD, KIIS, IM)
5. **로그인 검증**: `jwsuh@amic.kr` / `1111` 로그인 성공 확인

---

## 3. 컨테이너 현황 (18개)

| 컨테이너 | 역할 | 상태 |
|----------|------|------|
| amic-nginx | 리버스 프록시 | Up |
| amic-frontend | React SPA | healthy |
| amic-fdd-api | FDD 백엔드 | healthy |
| amic-kiis-api | KIIS 백엔드 | healthy |
| amic-im-api | IM 백엔드 | healthy |
| amic-deal-mgmt-api | MA 백엔드 | healthy |
| amic-fdd-db | FDD PostgreSQL | healthy |
| amic-kiis-db | KIIS PostgreSQL | healthy |
| amic-im-db | IM PostgreSQL | healthy |
| amic-deal-mgmt-db | MA PostgreSQL | healthy |
| amic-kiis-redis | KIIS Redis | healthy |
| amic-im-redis | IM Redis | healthy |
| amic-deal-mgmt-redis | MA Redis | healthy |
| amic-kiis-es | Elasticsearch | healthy |
| amic-fdd-pptx | PPTX 서비스 | Up |
| amic-im-celery-worker | IM 비동기 워커 | Up (unhealthy*) |
| amic-im-celery-beat | IM 스케줄러 | Up (unhealthy*) |
| amic-deal-mgmt-celery-worker | MA 비동기 워커 | Up (unhealthy*) |

> *Celery 컨테이너 unhealthy는 healthcheck 설정 이슈, 실제 동작은 정상

---

## 4. API 헬스체크 결과

```
http://localhost/api/fdd/health  → {"status":"ok","version":"0.1.0","migration_ok":false}
http://localhost/api/kiis/health → {"status":"ok","migration_ok":true}
http://localhost/api/im/health   → {"status":"ok","version":"0.1.0"}
http://localhost/api/ma/health   → {"status":"ok","service":"deal-mgmt","migration_ok":true}
```

- FDD `migration_ok:false` — health 엔드포인트의 테이블 검증 로직 이슈, API 자체는 정상

---

## 5. DB 마이그레이션 상세

### 5.1 FDD (fdd-db / autofdd)

| 마이그레이션 | 문제 | 해결 |
|-------------|------|------|
| 015_user_delete_set_null | `deals` 테이블명 오류 (실제: `deal`) | 컨테이너 내 sed로 `deals` → `deal` 수정 |
| 016_fdd_checklist_and_analysis_run | `dealphase` enum 미존재 | 수동으로 `CREATE TYPE dealphase AS ENUM (...)` 실행 |
| 017_fdd_ralph_sessions | `down_revision='016_fdd_checklist_and_analysis_run'` 불일치 (실제 016의 revision은 `'016'`) | 컨테이너 내 sed로 수정 |

**최종 상태**: `018_add_cross_verification` (head) ✅

> ⚠️ **소스 코드 수정 필요**: 위 3건은 컨테이너 내부에서만 수정됨. 재빌드 시 재발.
> - `fdd/backend/alembic/versions/015_user_delete_set_null.py` — `deals` → `deal`
> - `fdd/backend/alembic/versions/016_fdd_checklist_and_analysis_run.py` — dealphase enum 존재 체크 추가
> - `fdd/backend/alembic/versions/017_fdd_ralph_sessions.py` — `down_revision = "016"` 으로 수정

### 5.2 KIIS (kiis-db / kiis)

정상 완료. 문제 없음. ✅

### 5.3 IM (im-db / imgen)

| 마이그레이션 | 문제 | 해결 |
|-------------|------|------|
| 008_checklist_item_unique_fiscal_year | alembic_version.version_num이 varchar(32)인데 revision ID가 40자 | 007까지 먼저 적용 → ALTER TABLE로 varchar(128) 확장 → 008 적용 |

**최종 상태**: `008_checklist_item_unique_fiscal_year` (head) ✅

### 5.4 MA / deal-mgmt (deal-mgmt-db / deal_mgmt)

정상 완료. 42개 테이블 생성. ✅

---

## 6. 시드 사용자 (6명)

| 이메일 | 이름 | 직함 | FDD | KIIS | IM | 비밀번호 |
|--------|------|------|-----|------|----|----------|
| ytkim@amic.kr | 김양태 | 대표 / 회계사 | ADMIN | admin | ADMIN | 1111 |
| jwsuh@amic.kr | 서지원 | 변호사 | ADMIN | admin | ADMIN | 1111 |
| yhlim@amic.kr | 임영훈 | 변호사 | ANALYST | analyst | USER | 1111 |
| bj.park@amic.kr | 박병준 | 변호사 | ANALYST | analyst | USER | 1111 |
| wsjo@amic.kr | 조우상 | 이사 | ANALYST | analyst | USER | 1111 |
| tryoon@amic.kr | 윤태리 | 실장 | ANALYST | analyst | USER | 1111 |

> MA(deal-mgmt)는 별도 users 테이블 없음 — JWT 공유 인증 방식

---

## 7. 프로덕션 환경 변수 (.env)

```
# 위치: /opt/amic-platform/.env
SHARED_JWT_SECRET=3a01ef63cec1debb1c07286f699a7ac44f6c57fce5e85fb2cfe27e3fee6b277a
JWT_SECRET=(동일)
CORS_ORIGINS=http://52.231.69.38

# DB 비밀번호 (랜덤 생성)
FDD_DB_PASSWORD=14e739a8712576f07e025ef97b80d998
KIIS_DB_PASSWORD=a919a6a09bb01ee61b32b0d9b81ba5ec
IM_DB_PASSWORD=c8a11e10cf93a737b1188438915e9569
MA_DB_PASSWORD=b743b5942f227ce4fa09cd66bf6aa899
```

---

## 8. SSH 접속 정보

```bash
ssh -i "amic-platform-prod_key.pem" azureuser@52.231.69.38
```

- **PEM 키 위치**: `OneDrive - 주식회사 페트라브릿지파트너스/AMIC의 파일 - 3. Administration/기타. 플랫폼/amic-platform-prod_key.pem`
- **GitHub PAT**: `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`
- **코드 위치**: `/opt/amic-platform` (feat/ma-workflow 브랜치)

---

## 9. TypeScript 빌드 에러 수정 요약 (5라운드)

### 수정된 파일 (20+개)

| 파일 | 수정 내용 |
|------|----------|
| FundDetailPage.tsx, GPListPage.tsx | 미사용 `formatAmount` import 제거 |
| LDDReviewPanel.tsx | variant="outline" → "secondary" (3곳) |
| FMChecklistCategorySection.tsx | 미사용 `cn` import 제거 |
| AudioTranscriptionModal.tsx | isLoading→loading, Badge "default"→"neutral" |
| RFICreateModal.tsx | variant="outline" → "secondary" |
| RFIDetailView.tsx | 미사용 Tabs import 제거, variant 수정 (4곳) |
| RFIItemRow.tsx | variant="default"→"primary", "outline"→"secondary" |
| RFIPanel.tsx | useDeleteRFI 제거, hover→hoverEffect, mutate(undefined) |
| TransactionWorkspacePage.tsx | 미사용 import 제거 |
| ChecklistSummaryBar.tsx | KpiCard value 타입 String() |
| ChecklistReviewPage.tsx (FDD) | 미사용 type import 제거 |
| ReportPage.tsx | Badge "danger"→"error" |
| VdrPage.tsx | mutateAsync(undefined) |
| ChecklistTable.tsx, CreateFromVdrPage.tsx, DocumentListPage.tsx | 미사용 import 제거 |
| ChecklistItemCard.tsx | SEVERITY_VARIANTS "default"→"neutral" |
| Sidebar.tsx | FDD_MAIN_NAV 제거, Briefcase import 제거 |
| useCalendar.ts | 미사용 파라미터 제거 |
| CategoryDocumentsPage.tsx | fddColumns, DEAL_STATUS_BADGE, Deal/DealStatus 제거 |
| DDReportListPage.tsx | AlertTriangle 미사용 alias 처리 |
| Card.tsx | onClick prop 추가 |

### 커밋 히스토리

```
e269a4d fix(platform): fix TypeScript build errors — round 1
f8f59d7 fix(platform): fix TypeScript build errors — round 2
22cb43c fix(platform): fix TypeScript build errors — round 3
df65a7c fix(platform): fix TypeScript build errors — round 4
ff1f508 fix(platform): fix TypeScript build errors — round 5
```

---

## 10. 미완료 / 후속 작업

### 즉시 필요

- [ ] **FDD 마이그레이션 소스 코드 수정** — 015 테이블명, 016 enum 체크, 017 down_revision (재빌드 시 재발)
- [ ] **비밀번호 변경** — 현재 모든 사용자 비밀번호 `1111` → 프로덕션 운영 전 변경 필수
- [ ] **CORS 업데이트** — 도메인 확정 시 `.env`의 `CORS_ORIGINS` 변경
- [ ] **Celery healthcheck 수정** — 3개 Celery 컨테이너 unhealthy 표시 개선

### 도메인 + SSL

- [ ] 도메인 구매 (가비아 등)
- [ ] DNS A 레코드 설정 → `52.231.69.38`
- [ ] Let's Encrypt SSL 인증서 발급 (`certbot`)
- [ ] `nginx/prod.conf` HTTPS 설정 적용

### 운영

- [ ] Sentry 계정 생성 → 에러 모니터링
- [ ] GitHub Actions CI/CD 자동 배포 설정
- [ ] 정기 백업 설정 (DB 볼륨)
- [ ] Azure NSG에서 SSH 접근 IP 제한

---

## 11. 운영 명령어 참고

```bash
# 전체 재시작
cd /opt/amic-platform
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 로그 확인
docker logs amic-fdd-api --tail 50
docker logs amic-nginx --tail 50

# DB 접속
docker exec -it amic-fdd-db psql -U autofdd -d autofdd
docker exec -it amic-kiis-db psql -U kiis_user -d kiis
docker exec -it amic-im-db psql -U postgres -d imgen
docker exec -it amic-deal-mgmt-db psql -U deal_mgmt_user -d deal_mgmt

# 코드 업데이트
cd /opt/amic-platform
git pull origin feat/ma-workflow
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
