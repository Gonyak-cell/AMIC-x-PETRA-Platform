# 프로덕션 CORS/JWT/DB 비밀번호 수정 보고서

**작성일**: 2026-02-26 11:39
**대상 환경**: `https://ap-platform.kr` (Azure VM 52.231.69.38)
**브랜치**: `feat/ma-workflow`
**선행 문서**: `20260226_1119_Production_Dashboard_Error_Fix.md`

---

## 1. 문제 요약

이전 세션에서 대시보드 에러를 수정한 후 추가로 발견된 문제들:

| # | 증상 | 근본 원인 | 영향 |
|---|------|----------|------|
| 1 | IM 모듈 JWT 인증 실패 (401) | `docker-compose.prod.yml`에 IM `JWT_SECRET` 환경변수 누락 | IM API 전체 인증 불가 |
| 2 | KIIS CORS 환경변수 무시됨 | 환경변수명 `CORS_ORIGINS` → pydantic 필드명 `ALLOWED_ORIGINS` 불일치 | CORS 정책 미적용 |
| 3 | nginx CSP가 프론트엔드 스크립트 차단 | `script-src 'self'`에 `'unsafe-inline'` 누락 (Vite 빌드 호환) | 프론트엔드 JS 실행 차단 가능 |
| 4 | .env CORS 값 형식 오류 | `list[str]` 타입에 쉼표 구분 문자열 전달 | KIIS/IM pydantic 파싱 에러로 시작 실패 |
| 5 | DB 비밀번호 불일치 (FDD, KIIS) | `docker compose up -d`로 컨테이너 재생성 시 기존 볼륨의 PG 비밀번호 불변 | DB 연결 실패 → 500/migration_ok: false |
| 6 | deal-mgmt DB 비밀번호 불일치 | 동일 원인 (볼륨 비밀번호 ≠ .env 비밀번호) | migration_ok: false |

---

## 2. 근본 원인 분석

### 2.1 IM JWT_SECRET 환경변수 누락 (CRITICAL)

- **코드**: `im/src/api/config.py:61-64` — `jwt_secret_key: str = Field(default="change-me-in-production", alias="JWT_SECRET")`
- **docker-compose.prod.yml**: `SECRET_KEY: ${SHARED_JWT_SECRET}` 설정했으나, `JWT_SECRET`은 미설정
- **결과**: IM이 기본값 `"change-me-in-production"`으로 JWT 검증 → FDD 발급 토큰과 시크릿 불일치 → 401

### 2.2 KIIS CORS 환경변수명 불일치 (MEDIUM)

- **docker-compose.prod.yml**: `CORS_ORIGINS: ${KIIS_CORS_ORIGINS}`
- **KIIS config**: `ALLOWED_ORIGINS: list[str]` (alias 없음)
- **결과**: pydantic_settings가 `CORS_ORIGINS` env를 `ALLOWED_ORIGINS` 필드에 매핑하지 못함

### 2.3 nginx CSP 호환성 (MEDIUM)

- **위치**: `nginx/prod.conf:71`, `nginx/prod-nossl.conf:41`
- **문제**: `script-src 'self'` — Vite 빌드의 인라인 스크립트 차단 가능
- **수정**: `script-src 'self' 'unsafe-inline'` (이미 prod.conf에 적용되어 있었으나 prod-nossl.conf에도 동기화)

### 2.4 .env CORS 값 형식 오류 (CRITICAL)

- **문제**: `KIIS_CORS_ORIGINS=https://ap-platform.kr,http://52.231.69.38` (쉼표 구분)
- **KIIS/IM config**: `ALLOWED_ORIGINS: list[str]` → pydantic은 JSON 배열 필요
- **에러**: `pydantic_settings.exceptions.SettingsError: error parsing value for field "ALLOWED_ORIGINS"`
- **수정**: `["https://ap-platform.kr","http://52.231.69.38"]` (JSON 배열 형식)

### 2.5 PostgreSQL 볼륨 비밀번호 불일치 (CRITICAL)

- **원인**: PostgreSQL Docker 이미지는 데이터 디렉토리 **최초 생성 시에만** `POSTGRES_PASSWORD`를 적용
- **상황**: 기존 볼륨이 존재하는 상태에서 `.env`의 비밀번호가 변경됨 → DB 내 실제 비밀번호는 구값 유지
- **영향**: API가 `.env`의 새 비밀번호로 연결 시도 → `FATAL: password authentication failed`
- **해당 DB**: FDD (`autofdd`), KIIS (`kiis_user`), deal-mgmt (`deal_mgmt_user`)

---

## 3. 수정 내역

### 3.1 코드 수정 (커밋 완료)

| 파일 | 변경 내용 |
|------|----------|
| `docker-compose.prod.yml` (im-api) | `JWT_SECRET: ${SHARED_JWT_SECRET}` 추가 |
| `docker-compose.prod.yml` (kiis-api) | `CORS_ORIGINS` → `ALLOWED_ORIGINS` 변경 |
| `nginx/prod.conf:71` | CSP `script-src 'self' 'unsafe-inline'` |
| `nginx/prod-nossl.conf:41` | 동일 CSP 수정 |

### 3.2 서버 .env 수정

```diff
- FDD_CORS_ORIGINS=http://52.231.69.38
- KIIS_CORS_ORIGINS=http://52.231.69.38
- IM_CORS_ORIGINS=http://52.231.69.38
- MA_CORS_ORIGINS=http://52.231.69.38
+ FDD_CORS_ORIGINS=https://ap-platform.kr,http://52.231.69.38
+ KIIS_CORS_ORIGINS=["https://ap-platform.kr","http://52.231.69.38"]
+ IM_CORS_ORIGINS=["https://ap-platform.kr","http://52.231.69.38"]
+ MA_CORS_ORIGINS=["https://ap-platform.kr","http://52.231.69.38"]
```

### 3.3 DB 비밀번호 동기화 (VM 작업)

```sql
-- FDD
ALTER USER autofdd WITH PASSWORD '14e739a8712576f07e025ef97b80d998';
-- KIIS
ALTER USER kiis_user WITH PASSWORD 'a919a6a09bb01ee61b32b0d9b81ba5ec';
-- deal-mgmt
ALTER USER deal_mgmt_user WITH PASSWORD 'b743b5942f227ce4fa09cd66bf6aa899';
```

### 3.4 컨테이너 재시작

```bash
docker compose restart fdd-api kiis-api deal-mgmt-api
docker exec amic-nginx nginx -s reload
```

---

## 4. 검증 결과

```
=== Health Checks ===
FDD:  {"status":"ok","version":"0.1.0","migration_ok":true}  ✅
KIIS: {"status":"ok","version":"0.1.0"}                       ✅
IM:   {"status":"ok","migration_ok":true}                     ✅
MA:   {"status":"ok","service":"deal-mgmt","migration_ok":true} ✅

=== Login + Cross-module Auth ===
Login (POST /api/fdd/auth/login):      200 ✅ → {"message":"로그인 성공"}
auth/me (GET /api/fdd/auth/me):        200 ✅ → {"email":"jwsuh@amic.kr","role":"ADMIN"}
MA transactions (GET /api/ma/transactions): 200 ✅ → {"items":[],"total":0}
```

---

## 5. 교훈 및 재발 방지

| 교훈 | 재발 방지 |
|------|----------|
| `docker-compose.prod.yml`에서 모든 모듈의 `JWT_SECRET` 명시 필요 | `.env.production.example`에 필수 환경변수 목록 관리 |
| pydantic `list[str]` 필드는 JSON 배열 형식 필요 | CORS 타입별 형식을 규칙 문서에 명시 (`post-deploy-verification.md`) |
| PostgreSQL 볼륨 비밀번호는 최초 생성 시만 적용 | DB 비밀번호 변경 시 `ALTER USER` 필수 |
| `docker compose restart`는 `.env` 변경 미반영 | `.env` 변경 후 `up -d --no-deps <service>` 사용 |
| 환경변수명은 pydantic 필드명/alias와 정확히 일치해야 함 | `docker compose config`로 최종 환경변수 확인 |

---

## 6. 자동화 규칙 추가

`.claude/rules/post-deploy-verification.md` 신규 생성:
- 코드 수정 → 문서 저장 → 커밋 & 푸시 → 서버 CORS/헬스체크 검증 절차 자동 적용
- CORS 타입별 형식 규칙 (str vs list[str])
- DB 비밀번호 불일치 대응 절차
