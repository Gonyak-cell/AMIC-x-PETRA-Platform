# 코드 리뷰 리포트: Cross-cutting — 배치 3

- 라운드: 1
- 모듈: Chunk 8 크로스커팅
- 배치: 3 (보안, 성능, 예외처리, 동시성)
- 시작: 2026-03-05 03:08
- 종료: 2026-03-05 03:22

## 리뷰 방법

3개 병렬 서브에이전트로 스캔:
- 에이전트 1: backend-security-reviewer (보안)
- 에이전트 2: performance-profiler (성능)
- 에이전트 3: python-code-reviewer (예외처리 + 동시성)

## 수정된 이슈

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 | 수정 내용 |
|---|------|-----|------|-----|--------|----------|
| 1 | 예외처리 | kiis/app/core/elasticsearch.py | 116-117 | ES 연결 실패 시 `logger.warning()`에 `exc_info=True` 누락 — 예외 원인이 로그에 기록되지 않음 | Medium | `exc_info=True` 추가 |
| 2 | 예외처리 | kiis/app/core/security.py | 229-231 | 비활성 사용자에 HTTP 400 반환 — RFC 의미상 403 Forbidden이 적합 | Medium | `HTTP_400_BAD_REQUEST` → `HTTP_403_FORBIDDEN` |

## 모듈 청크별 이관 이슈 (수정하지 않음)

아래 이슈들은 구조적/아키텍처 변경이 필요하여 해당 모듈의 전용 청크에서 처리한다.

### → Chunk 2 (FDD 백엔드)로 이관

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 |
|---|------|-----|------|-----|--------|
| D1 | 성능 | fdd/backend/app/database.py | 1-27 | 동기 SQLAlchemy 엔진 — KIIS/DM/IM은 모두 async 전환 완료 | High |
| D2 | 성능 | fdd/backend/app/database.py | 21-26 | `get_db()`에서 예외 시 rollback 누락 — 트랜잭션 누수 가능 | High |
| D3 | 성능 | fdd/backend/app/database.py | 6-10 | pool_size=20 과다 (비동기 전환 시 축소 필요) | Medium |
| D4 | 보안 | fdd/backend/app/auth/dependencies.py | 58-59 | `AUTH_ENABLED=False` 프로덕션 차단 로직 불완전 (경고만, RuntimeError 없음) | Medium |
| D5 | 보안 | fdd/backend/app/auth/password.py | 14-17 | bcrypt 비표준 검증 패턴 (`hashpw` + `hmac.compare_digest`) | Low |

### → Chunk 4 (IM 백엔드)로 이관

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 |
|---|------|-----|------|-----|--------|
| D6 | 동시성 | im/src/api/security/blacklist.py | 17-20 | Redis 매 호출 새 클라이언트 생성 — 연결 풀 미사용 | High |
| D7 | 예외처리 | im/src/api/dependencies.py | 95-117 | `verify_exp=False` 재디코딩 — 기존 payload에서 email 추출하면 불필요 | Critical |
| D8 | 성능 | im/src/api/db/session.py | 40-47 | pool_recycle, pool_timeout 미설정 | Medium |
| D9 | 보안 | im/src/api/config.py | 30 | DB URL 기본값에 평문 자격증명 포함, 프로덕션 차단 없음 | Medium |
| D10 | 보안 | im/src/api/middleware/cors.py | 29 | `allow_headers=["*"]` 와일드카드 | Medium |

### → Chunk 3 (KIIS 백엔드)로 이관

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 |
|---|------|-----|------|-----|--------|
| D11 | 동시성 | kiis/app/core/security.py | 202-212 | FDD 토큰→KIIS 사용자 자동 생성 시 동시 요청 IntegrityError 가능 (upsert 필요) | High |

### → Chunk 5 (Deal-Mgmt 백엔드)로 이관

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 |
|---|------|-----|------|-----|--------|
| D12 | 동시성 | deal-mgmt/app/core/rate_limiter.py | 36-61 | 인메모리 Rate Limiter에 asyncio.Lock 없음 + 다중 워커 무력화 | High |
| D13 | 동시성 | deal-mgmt/app/core/dependencies.py | 36-65 | 싱글턴 클라이언트 초기화 레이스 컨디션 | Medium |
| D14 | 성능 | deal-mgmt/app/core/pagination.py | 54-61 | count + data 직렬 2회 쿼리 — asyncio.gather()로 병렬화 가능 | Medium |
| D15 | 성능 | deal-mgmt/app/core/blob_storage.py | 125-135 | download_blob()이 파일 전체를 메모리 로딩 — 대용량 위험 | Medium |
| D16 | 동시성 | deal-mgmt/app/core/blob_storage.py | 155-156 | `download_blob_to_file`에서 동기 `open()` 사용 | Medium |

## 이슈 없음 확인 (Read로 검증)

### 보안 (관점 1)
- fdd/backend/app/core/logging.py: 민감정보 마스킹 `_sanitize()` 구현, `_SENSITIVE_KEYS` 필터링 ✅
- fdd/backend/app/core/exceptions.py: 500 에러 시 `"An unexpected error occurred."` 제네릭 메시지 반환 ✅
- fdd/backend/app/auth/token.py: JWT `algorithms=[...]` 명시적 검증, JTI 포함 ✅
- fdd/backend/app/auth/rbac.py: 최소 권한 원칙 준수 ✅
- kiis/app/core/security.py: `_check_dev_env()` — AUTH_ENABLED=False를 local/dev/test로 제한 ✅
- deal-mgmt/app/core/security.py: 가장 강력한 AUTH_ENABLED 차단 (ENV 검증) ✅
- deal-mgmt/app/core/blob_storage.py: path traversal 방지 (`startswith` 검증) ✅
- im/src/api/security/api_keys.py: SHA-256 해시 기반 API 키 저장 ✅
- im/src/api/security/password.py: `bcrypt.checkpw()` 표준 구현 ✅
- amic-platform/src/components/auth/AuthProvider.tsx: 쿠키 기반 인증, localStorage 미사용 ✅
- amic-platform/src/api/client.ts: 401 자동 갱신, 동시 중복 방지 ✅

### 성능 (관점 2)
- kiis/app/core/redis.py: max_connections=20 적정, graceful degradation ✅
- kiis/app/core/database.py: pool_recycle=3600, pool_pre_ping=True ✅
- deal-mgmt/app/core/database.py: Celery 전용 풀 분리(pool_size=3) ✅
- deal-mgmt/app/core/security.py: DB 조회 없이 클레임만 추출하는 경량 패턴 ✅

### 예외처리 (관점 4)
- fdd/backend/app/core/exceptions.py: RFC 7807 완전 구현 ✅
- fdd/backend/app/core/errors.py: ErrorCode 체계 명확 ✅
- kiis/app/core/exceptions.py: RFC 7807 + DART 에러 매핑 ✅
- deal-mgmt/app/core/exceptions.py: 모든 핸들러 `exc_info=exc` 포함 ✅

### 동시성 (관점 5)
- deal-mgmt/app/core/log_context.py: ContextVar 요청별 격리 ✅
- deal-mgmt/app/core/security.py: `_service_token_lock` asyncio.Lock 사용 ✅
- bare `except:` 미사용: 모든 모듈에서 `except Exception` 이상 구체적 예외 사용 ✅

## 검증 결과

- KIIS ruff check: ✅ 0건
- KIIS ruff format: ✅ 0건

## 에러 카운트

| 관점 | 발견 | Chunk 8 수정 | 모듈 이관 |
|------|------|-------------|----------|
| 보안 | 9건 | 0 (1건 배치2 기수정) | 5건 |
| 성능 | 10건 | 0 | 6건 |
| 예외처리 | 6건 | 2건 | 2건 |
| 동시성 | 8건 | 0 | 3건 |
| 합계 | 33건 | 2건 수정 | 16건 이관 |

**참고**: 이관 16건 중 일부는 여러 에이전트에서 중복 보고된 이슈 (실질 고유 이슈 ~12건)

## 충족 관점 체크리스트

- [x] 1. 보안 (Chunk 8 범위 내 이슈 없음, 구조적 이슈는 모듈별 이관)
- [x] 2. 성능 (Chunk 8 범위 내 이슈 없음, 구조적 이슈는 모듈별 이관)
- [x] 4. 예외처리 (2건 수정, 나머지 이관)
- [x] 5. 동시성 (Chunk 8 범위 내 수정 없음, 구조적 이슈는 모듈별 이관)
