# 코드 리뷰 리포트: Cross-cutting — 배치 4

- 라운드: 1
- 모듈: Chunk 8 크로스커팅
- 배치: 4 (아키텍처, 테스트 커버리지, 코드 품질)
- 시작: 2026-03-05 03:22
- 종료: 2026-03-05 03:33

## 리뷰 방법

2개 병렬 서브에이전트로 스캔:
- 에이전트 1: 아키텍처(관점 3) + 코드 품질(관점 13) — 46개 파일 Read
- 에이전트 2: 테스트 커버리지(관점 11)

## 수정된 이슈

없음. 배치 4의 발견 사항은 모두 구조적/장기적 개선 사항으로, 코드 수정 없이 관찰 결과만 기록한다.

## 아키텍처 관찰 (관점 3)

### DRY 위반: 4중 복제 인프라 코드

| 인프라 유형 | FDD | KIIS | Deal-Mgmt | IM | 추정 중복 |
|------------|-----|------|-----------|-----|---------|
| 로깅 (JSONFormatter + setup_logging) | core/logging.py | core/logging.py | core/logging.py | core/logging.py | ~400줄 |
| 로그 컨텍스트 (ContextVar) | core/log_context.py | core/log_context.py | core/log_context.py | core/log_context.py | ~200줄 |
| 로그 미들웨어 (RequestLoggingMiddleware) | core/log_middleware.py | core/log_middleware.py | core/log_middleware.py | middleware/logging.py | ~260줄 |
| 에러 코드 체계 (ErrorCode Enum) | core/errors.py | core/errors.py | core/errors.py | exceptions.py | ~250줄 |

**합계**: ~1,110줄의 실질적 복제 코드

**현재 방식의 합리성**: 마이크로서비스 모노레포에서 각 서비스가 독립 배포/빌드되므로, 공유 패키지 없이 복사하는 것은 실용적 선택이다. 단, SERVICE_NAME만 다르고 나머지 로직이 동일한 상태가 지속되면 동기화 이슈가 발생한다.

**권장 (장기)**: `shared/` 내부 패키지로 추출하여 `setup_logging(service_name="fdd")` 형태로 통일.

### JWT 라이브러리 불일치

| 모듈 | 라이브러리 | 비고 |
|------|-----------|------|
| FDD | `python-jose` | 최신 유지보수 활발 |
| KIIS | `python-jose` | |
| Deal-Mgmt | `PyJWT` (`jwt`) | FastAPI 공식 권장 |
| IM | `PyJWT` (`jwt`) | |

API 호환이므로 즉시 통일 필요는 없으나, 보안 패치 주기가 다를 수 있다.

### 양호한 아키텍처 패턴

- **FE API 클라이언트**: `createApiClient()` 팩토리 패턴으로 4개 모듈 클라이언트를 2줄씩 생성 → DRY 우수
- **의존성 역전**: 모든 core/ 파일이 routers/services/models를 import하지 않음 ✅
- **순환 의존성**: 탐지되지 않음 ✅
- **관심사 분리**: blob_storage, rate_limiter 등 각각 단일 책임 ✅

## 코드 품질 관찰 (관점 13)

### 패턴 불일치 (모듈 간)

| 항목 | FDD | KIIS | Deal-Mgmt | IM |
|------|-----|------|-----------|-----|
| password 검증 | `hashpw+hmac` | `checkpw` | (deal-mgmt 자체 없음) | `checkpw` |
| time 측정 | `perf_counter` | `perf_counter` | `perf_counter` | `time.time` |
| 설정 클래스 | `@lru_cache Settings` | 글로벌 인스턴스 | `@lru_cache Settings` | `@lru_cache APIConfig` |

### 양호한 코드 품질

- snake_case/camelCase 규칙 준수: BE=snake_case, FE=camelCase ✅
- 데드 코드 미탐지: 미사용 함수/클래스 없음 ✅
- 매직 넘버: pool_size, TTL 등 모두 설정 파일에서 관리 ✅
- 함수 복잡도: 50줄 초과 함수 없음 ✅

## 테스트 커버리지 관찰 (관점 11)

### 모듈별 테스트 등급

| 모듈 | 소스 파일 수 | 테스트 파일 수 | 등급 | 비고 |
|------|------------|-------------|------|------|
| FDD auth/ | 4 | 4 | A | 전수 테스트 보유 |
| KIIS core/ | 9 | 1 | D | security.py만 간접 테스트 |
| Deal-Mgmt core/ | 7 | 2 | D | security, config만 테스트 |
| IM security/ + api/ | 7 | 7 | A | 전수 테스트 보유 |

### 최우선 테스트 보완 대상 (모듈별 청크에서 처리)

| 소스 파일 | 핵심 미테스트 함수 | 이관 대상 |
|----------|-----------------|----------|
| kiis/app/core/exceptions.py | RFC 7807 응답 포맷 검증 | Chunk 3 |
| kiis/app/core/elasticsearch.py | init_elasticsearch 연결/인덱스 생성 | Chunk 3 |
| kiis/app/core/redis.py | init_redis graceful degradation | Chunk 3 |
| kiis/app/core/pagination.py | paginate() 경계값 테스트 | Chunk 3 |
| deal-mgmt/app/core/exceptions.py | RFC 7807 핸들러 매핑 | Chunk 5 |
| deal-mgmt/app/core/blob_storage.py | path traversal 방지 검증 | Chunk 5 |
| deal-mgmt/app/core/rate_limiter.py | 윈도우 만료, 리밋 도달 | Chunk 5 |
| deal-mgmt/app/core/pagination.py | paginate() 경계값 | Chunk 5 |

## 검증 결과

- 코드 수정 없음 → 별도 검증 불요

## 에러 카운트

| 관점 | 발견 | Chunk 8 수정 | 비고 |
|------|------|-------------|------|
| 아키텍처 | 3건 (High DRY) + 6건 (Medium) | 0 | 장기 개선 사항 |
| 테스트 커버리지 | 8건 미테스트 파일 | 0 | 모듈별 청크에서 보완 |
| 코드 품질 | 7건 (Low 패턴 불일치) | 0 | 모듈별 청크에서 통일 |
| 합계 | 24건 관찰 | 0건 수정 | 전체 이관/장기 |

## 충족 관점 체크리스트

- [x] 3. 아키텍처 (DRY 위반 기록, 순환 의존성 없음 확인)
- [x] 11. 테스트 커버리지 (갭 분석 완료, 모듈별 이관)
- [x] 13. 코드 품질 (네이밍 규칙 준수, 데드코드 없음 확인)
