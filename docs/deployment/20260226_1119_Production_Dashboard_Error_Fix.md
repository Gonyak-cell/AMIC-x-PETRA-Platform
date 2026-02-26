# 프로덕션 대시보드 에러 수정 보고서

**작성일**: 2026-02-26 11:19
**대상 환경**: `https://ap-platform.kr` (Azure VM 52.231.69.38)
**브랜치**: `feat/ma-workflow`

---

## 1. 문제 요약

프로덕션 배포 후 로그인은 성공하지만 대시보드에서 에러 발생:

| # | 증상 | 엔드포인트 | HTTP 코드 |
|---|------|-----------|-----------|
| 1 | MA 거래 목록 로드 실패 | `GET /api/ma/transactions` | 500 |
| 2 | KIIS 알림 카운트 실패 | `GET /api/kiis/alerts/unread-count` | 401 |
| 3 | FDD 사용자 정보 실패 (선행 수정) | `GET /api/fdd/auth/me` | 500 |

---

## 2. 근본 원인 분석

### 2.1 KIIS 401 — JWT_SECRET 불일치

- **원인**: `docker-compose.prod.yml`에서 KIIS에 `JWT_SECRET`을 설정하지 않음
- **결과**: base `docker-compose.yml`의 기본값 `dev-shared-jwt-secret-change-in-production` 사용
- **영향**: FDD가 `70618b39...` 시크릿으로 발급한 JWT를 KIIS가 다른 시크릿으로 검증 → 서명 불일치 → 401
- **KIIS 코드 참조**: `kiis/app/core/security.py:48-56` — `settings.JWT_SECRET or settings.SECRET_KEY` 순서로 사용. `JWT_SECRET`이 truthy이면 `SECRET_KEY` 무시

### 2.2 deal-mgmt 500 — DB 테이블 누락

- **직접 원인**: `transactions` 테이블이 존재하지 않음
- **근본 원인 1**: Alembic 마이그레이션 체인 단절
  - `024`의 `down_revision = "023"` → 실제 ID는 `"023_ldd_multi_llm"`
  - 시작 시 `alembic upgrade head` 실패 → 핵심 테이블 미생성
- **근본 원인 2**: Migration 024에 중복 인덱스 생성
  - `sa.Column("deal_type", ..., index=True)` + `op.create_index("ix_ldd_reports_deal_type", ...)`
  - `index=True`가 자동으로 인덱스를 생성하므로 `op.create_index()`에서 `DuplicateTableError` 발생

### 2.3 FDD 500 — token_blacklist 테이블 누락 (선행 수정 완료)

- **원인**: `token_blacklist` 테이블이 DB에 없음
- **영향**: `get_current_user()` → `is_token_blacklisted(db, jti)` 쿼리 실패 → 500
- **수정**: raw SQL로 `token_blacklist` 테이블 직접 생성

### 2.4 추가 발견 — IM DB 테이블 누락

- **원인**: IM은 Alembic 마이그레이션 없이 `create_all()` 방식 사용. 이전 세션에서 `users` 테이블만 수동 생성
- **영향**: `documents`, `companies`, `audit_logs` 등 7개 테이블 누락

### 2.5 추가 발견 — FDD Alembic 체인 단절

- `017`의 `down_revision = "016_fdd_checklist_and_analysis_run"` → 실제 ID는 `"016"`
- 현재 테이블은 이미 존재하므로 즉각적 영향 없으나, 향후 마이그레이션 시 문제 발생 가능

---

## 3. 수정 내역

### 3.1 코드 수정 (3개 파일)

| 파일 | 변경 내용 | 커밋 |
|------|----------|------|
| `docker-compose.prod.yml` (kiis-api 섹션) | `JWT_SECRET: ${SHARED_JWT_SECRET}` 추가 | `a331a6f` |
| `deal-mgmt/migrations/versions/024_ldd_deal_type_template.py` | `down_revision = "023"` → `"023_ldd_multi_llm"` | `a331a6f` |
| `fdd/backend/alembic/versions/017_fdd_ralph_sessions.py` | `down_revision = "016_fdd_checklist_and_analysis_run"` → `"016"` | `a331a6f` |
| `deal-mgmt/migrations/versions/024_ldd_deal_type_template.py` | `index=True` 제거 (중복 인덱스 방지) | `7fca584` |

### 3.2 VM 작업 내역

1. **코드 반영**: git pull 불가(PAT 만료) → Python/sed로 3개 파일 직접 수정
2. **deal-mgmt DB 정비**:
   - 기존 `users` 테이블 DROP (raw SQL로 생성된 불완전한 테이블)
   - `alembic upgrade head` 실행 → 001~027 전체 마이그레이션 성공
   - 결과: 42개 테이블 생성, alembic_version = `027`
3. **IM DB 정비**:
   - `Base.metadata.create_all()` 비동기 실행 (`engine.begin()` → `run_sync`)
   - 8개 테이블 생성: `users`, `documents`, `companies`, `audit_logs`, `im_checklists`, `im_checklist_items`, `im_ralph_sessions`, `api_keys`
4. **FDD Alembic stamp**: `alembic stamp head` → 018 기록
5. **컨테이너 재생성**:
   - `docker compose up -d --force-recreate kiis-api deal-mgmt-api im-api`
   - KIIS: 새 `JWT_SECRET` 환경변수 반영
6. **nginx reload**:
   - 컨테이너 재생성으로 IP 변경 → nginx DNS 캐시 무효화 필요
   - `docker exec amic-nginx nginx -s reload`

---

## 4. 검증 결과

```
Login (POST /api/fdd/auth/login):       200 ✅
auth/me (GET /api/fdd/auth/me):         200 ✅ → {"email":"jwsuh@amic.kr","role":"ADMIN"}
MA transactions (GET /api/ma/transactions): 200 ✅ → {"items":[],"total":0}
KIIS alerts (GET /api/kiis/alerts/unread-count): 200 ✅ → {"count":0}

FDD health:  200 ✅
KIIS health: 200 ✅
IM health:   200 ✅
MA health:   200 ✅
```

---

## 5. 교훈 및 재발 방지

| 교훈 | 재발 방지 |
|------|----------|
| Alembic `down_revision`은 정확한 revision ID 문자열이어야 함 | 마이그레이션 생성 시 `alembic heads` 명령으로 현재 head 확인 |
| `sa.Column(index=True)` + `op.create_index()` 중복 사용 금지 | 둘 중 하나만 사용. 명시적 인덱스명이 필요하면 `create_index()`만 사용 |
| `docker-compose.prod.yml` 환경변수 누락 시 base의 dev 기본값 적용 | 프로덕션 배포 전 `docker compose config` 출력 검토 |
| `docker compose restart`는 환경변수를 갱신하지 않음 | 환경변수 변경 시 반드시 `--force-recreate` 사용 |
| 컨테이너 재생성 후 nginx DNS 캐시 무효화 필요 | 컨테이너 recreate 후 `nginx -s reload` 실행 |
| deal-mgmt는 자체 User DB 없음 (FDD JWT 클레임 전용) | 시딩 대상에서 deal-mgmt 제외 |

---

## 6. DB 현황 (수정 후)

| 모듈 | DB | 테이블 수 | Alembic 버전 | 사용자 |
|------|-----|----------|-------------|--------|
| FDD | autofdd | ~18 | 018 (stamp) | 6명 |
| KIIS | kiis | ~15 | 별도 관리 | 6명 |
| IM | imgen | 8 | create_all (no alembic) | 6명 |
| deal-mgmt | deal_mgmt | 42 | 027 | N/A (JWT 클레임) |
