# JSON 구조화 로깅 + 에러 코드 체계 구현 보고서

> 작성: 2026-02-24 22:32:00
> 브랜치: `feat/ma-workflow`
> 상태: ✅ 완료

---

## 1. 배경 및 목표

### 문제
- 4개 백엔드(FDD, KIIS, IM, Deal-mgmt)의 로깅이 파편화
- FDD만 JSONFormatter 존재, 나머지는 표준 텍스트 출력
- 에러 발생 시 함수명·입력값·스택 트레이스를 구조적으로 추적 불가
- FDD 외 3개 백엔드에 에러 코드 체계 부재

### 목표
1. 4개 백엔드에 통일된 JSON 로그 스키마 적용
2. ERROR 시 `error_code`, 함수명, 입력값, 스택 트레이스를 JSON으로 기록
3. 3개 백엔드(KIIS, IM, Deal-mgmt)에 `ErrorCode` IntEnum 도입

---

## 2. JSON 구조화 로깅 시스템

### 2.1 JSON 로그 스키마

**공통 필드 (모든 레벨)**:
```json
{
  "timestamp": "2026-02-24T15:30:45.123456+00:00",
  "level": "INFO",
  "logger": "kiis.app.services.dart_service",
  "message": "DART 기업 개황 조회 완료",
  "service": "kiis",
  "module": "dart_service",
  "function": "get_company_info",
  "line": 42,
  "request_id": "req_a1b2c3d4e5f67890"
}
```

**ERROR 전용 필드**:
```json
{
  "error": {
    "error_code": "MA-4001",
    "type": "WorkflowError",
    "message": "PRELIMINARY_REVIEW → CLOSING 전환 불가",
    "stacktrace": "Traceback (most recent call last):\n  File ...",
    "input": {
      "transaction_id": "txn_abc123",
      "from_stage": "PRELIMINARY_REVIEW",
      "to_stage": "CLOSING"
    }
  }
}
```

**HTTP 요청 필드 (미들웨어)**:
```json
{
  "http": {
    "method": "POST",
    "path": "/api/v1/transactions",
    "status_code": 201,
    "duration_ms": 145.32
  }
}
```

### 2.2 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 라이브러리 | 표준 `logging` 확장 | 기존 175+ 파일의 `logger.info/error` 호출 변경 없음 |
| 배포 전략 | Copy (4개 백엔드 독립 배치) | Docker 독립 빌드 컨텍스트 유지 |
| 개발/프로덕션 전환 | `json_output` 파라미터 | DEBUG 시 TextFormatter, 프로덕션 시 JSONFormatter |

### 2.3 생성된 모듈 (×4 백엔드 = 16개 파일)

| 모듈 | 역할 |
|------|------|
| `logging.py` | JSONFormatter + TextFormatter + setup_logging + get_logger + _sanitize |
| `log_context.py` | ContextVar 기반 request_id, user_id 관리 |
| `log_middleware.py` | RequestLoggingMiddleware (X-Request-ID, HTTP 정보 JSON 기록) |
| `log_decorators.py` | @log_error_with_input (에러 시 입력값 자동 캡처) |

**배치 경로**:

| 백엔드 | 경로 | SERVICE_NAME |
|--------|------|-------------|
| FDD | `fdd/backend/app/core/` | `"fdd"` |
| KIIS | `kiis/app/core/` | `"kiis"` |
| IM | `im/src/api/core/` | `"im"` |
| Deal-mgmt | `deal-mgmt/app/core/` | `"deal-mgmt"` |

### 2.4 main.py 통합

각 백엔드의 `main.py`에 다음 추가:
```python
from app.core.logging import setup_logging
from app.core.log_middleware import setup_request_logging

setup_logging(level=settings.log_level, json_output=not settings.DEBUG, service_name="...")
setup_request_logging(app)
```

### 2.5 @log_error_with_input 데코레이터 적용 (8개 함수)

| 백엔드 | 파일 | 함수 |
|--------|------|------|
| Deal-mgmt | `services/workflow_engine.py` | `advance_phase()` |
| Deal-mgmt | `ralph/orchestrator.py` | `run()` |
| KIIS | `services/reputation_service.py` | `calculate_reputation()` |
| KIIS | `services/kofia_service.py` | `_request_proframe()` |
| FDD | `services/ingestion/parser.py` | `ingest_file()` |
| FDD | `agents/qoe_analyzer.py` | `run()` |
| IM | `data_ingestor/pipeline.py` | `collect()` |
| IM | `narrative_generator/engine/orchestrator.py` | `generate()` |

### 2.6 CI 동기화 검증

`scripts/check-repo-sync.ps1`에 로깅 모듈 동기화 검증 추가:
- `log_context.py`, `log_decorators.py` → 4개 백엔드 해시 일치 검증
- `logging.py`, `log_middleware.py` → 존재 여부 확인 (백엔드별 차이 허용)

---

## 3. 에러 코드 체계

### 3.1 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| Enum 타입 | IntEnum (FDD 패턴) | JSONFormatter의 `.value` 추출 로직과 호환 |
| `.code` 필수 여부 | Optional (기본 None) | 기존 100+ `raise` 문 변경 없음 |
| ErrorSeverity | 미도입 | HTTP 상태 코드가 이미 심각도 역할 수행 |
| IM 서브모듈 | API 레이어만 | 내부 예외는 API 레이어에서 변환됨 |

### 3.2 에러 코드 범위

**KIIS** (`kiis/app/core/errors.py`):
| 범위 | 도메인 | 코드 수 |
|------|--------|--------|
| 1000-1999 | DART API | 7 |
| 2000-2999 | KOFIA | 3 |
| 3000-3999 | 공공데이터/REITs | 3 |
| 4000-4999 | 분석/평판 | 3 |
| 9000-9099 | 시스템 | 6 |

**IM** (`im/src/api/core/errors.py`):
| 범위 | 도메인 | 코드 수 |
|------|--------|--------|
| 1000-1999 | 데이터 인제스트 | 3 |
| 2000-2999 | 재무 엔진 | 2 |
| 3000-3999 | 내러티브/문서 | 5 |
| 4000-4999 | 태스크 | 2 |
| 5000-5999 | 유효성 검증 | 2 |
| 9000-9099 | 시스템 | 6 |

**Deal-mgmt** (`deal-mgmt/app/core/errors.py`):
| 범위 | 도메인 | 코드 수 |
|------|--------|--------|
| 1000-1999 | 거래 | 3 |
| 2000-2999 | 문서 | 3 |
| 3000-3999 | DD/체크리스트 | 2 |
| 4000-4999 | 워크플로우 | 4 |
| 5000-5999 | Ralph (AI) | 3 |
| 6000-6999 | 법률/컴플라이언스 | 3 |
| 9000-9099 | 시스템 | 5 |

### 3.3 예외 클래스 `.code` 자동 할당

**핵심**: 기존 `raise` 문을 변경하지 않고, 예외 클래스 내부에서 `.code`를 자동 설정.

- **KIIS**: DART 상태 코드(`"010"`, `"011"` 등) → `ErrorCode` 자동 매핑
- **IM**: `APIError` base에 optional `code` kwarg 추가, 서브클래스에 기본값 설정
- **Deal-mgmt**: 각 클래스에 `.code` 기본값 할당, `WorkflowError`는 optional override 지원

### 3.4 RFC 7807 응답에 error_code 포함

KIIS/Deal-mgmt: `_problem_response()`에 `error_code` 파라미터 추가
```json
{"error_code": "KIIS-1001", "type": "urn:kiis:error:dart:010", ...}
```

IM: `_api_error_handler()` 응답에 `error_code` 필드 추가
```json
{"error": "...", "details": {...}, "error_code": "IM-3003"}
```

---

## 4. 변경 파일 전체 목록

### 신규 생성 (19개)

| 파일 | 설명 |
|------|------|
| `fdd/backend/app/core/log_context.py` | ContextVar (request_id, user_id) |
| `fdd/backend/app/core/log_middleware.py` | 요청 로깅 미들웨어 |
| `fdd/backend/app/core/log_decorators.py` | 에러 입력값 캡처 데코레이터 |
| `kiis/app/core/logging.py` | JSONFormatter + setup_logging |
| `kiis/app/core/log_context.py` | ContextVar |
| `kiis/app/core/log_middleware.py` | 요청 로깅 미들웨어 |
| `kiis/app/core/log_decorators.py` | 에러 입력값 캡처 데코레이터 |
| `kiis/app/core/errors.py` | ErrorCode IntEnum (20개) |
| `im/src/api/core/logging.py` | JSONFormatter + setup_logging |
| `im/src/api/core/log_context.py` | ContextVar |
| `im/src/api/core/log_middleware.py` | 요청 로깅 미들웨어 |
| `im/src/api/core/log_decorators.py` | 에러 입력값 캡처 데코레이터 |
| `im/src/api/core/errors.py` | ErrorCode IntEnum (20개) |
| `deal-mgmt/app/core/logging.py` | JSONFormatter + setup_logging |
| `deal-mgmt/app/core/log_context.py` | ContextVar |
| `deal-mgmt/app/core/log_middleware.py` | 요청 로깅 미들웨어 |
| `deal-mgmt/app/core/log_decorators.py` | 에러 입력값 캡처 데코레이터 |
| `deal-mgmt/app/core/errors.py` | ErrorCode IntEnum (22개) |
| 이 문서 | 구현 보고서 |

### 수정 (19개)

| 파일 | 변경 내용 |
|------|----------|
| `fdd/backend/app/core/logging.py` | JSONFormatter 확장 (service, request_id, error 블록, _sanitize) |
| `fdd/backend/app/main.py` | setup_logging에 service_name 추가, setup_request_logging 등록 |
| `fdd/backend/app/core/exceptions.py` | 에러 핸들러에 logger.error 추가 |
| `fdd/backend/app/services/ingestion/parser.py` | @log_error_with_input 적용 |
| `fdd/backend/app/agents/qoe_analyzer.py` | @log_error_with_input 적용 |
| `kiis/app/main.py` | setup_logging + setup_request_logging 추가 |
| `kiis/app/core/exceptions.py` | .code 속성 + DART 자동 매핑 + _problem_response 확장 |
| `kiis/app/services/reputation_service.py` | @log_error_with_input 적용 |
| `kiis/app/services/kofia_service.py` | @log_error_with_input 적용 |
| `im/src/api/__init__.py` | setup_logging + setup_request_logging + error_code 응답 |
| `im/src/api/exceptions.py` | APIError에 code kwarg + 서브클래스 기본값 |
| `im/src/data_ingestor/pipeline.py` | @log_error_with_input 적용 |
| `im/src/narrative_generator/engine/orchestrator.py` | @log_error_with_input 적용 |
| `deal-mgmt/app/main.py` | setup_logging + setup_request_logging 추가 |
| `deal-mgmt/app/core/exceptions.py` | .code 속성 + _problem_response 확장 |
| `deal-mgmt/app/services/workflow_engine.py` | @log_error_with_input 적용 |
| `deal-mgmt/app/ralph/orchestrator.py` | @log_error_with_input 적용 |
| `scripts/check-repo-sync.ps1` | 로깅 모듈 동기화 검증 추가 |

---

## 5. 검증 결과

| 항목 | 결과 |
|------|------|
| Deal-mgmt 워크플로우 테스트 (26개) | ✅ 통과 |
| KIIS 인증 가드 테스트 (7개) | ✅ 통과 |
| 3개 백엔드 에러 코드 단위 검증 | ✅ 통과 |
| KIIS DART 상태 코드 자동 매핑 | ✅ "010"→DART_AUTH_FAILED, "999"→None |
| 기존 `raise` 문 변경 | 0건 |

---

## 6. 기존 코드 영향

- **175개+ 파일의 `logger.info/error` 호출 변경 없음** — 포매터 교체만으로 JSON 출력 전환
- **100+ 기존 `raise` 문 변경 없음** — 예외 클래스 내부에서 `.code` 자동 설정
- `extra={"ctx": {...}}` 패턴 하위 호환 유지
- FDD의 기존 `mask_amount()` 유지

---

## 7. 미적용 (범위 제한)

- ErrorSeverity: FDD 전용 유지 (나머지 백엔드 미도입)
- IM 서브모듈(data_ingestor, narrative_generator 등): API 레이어만 적용
- 라우터의 `raise HTTPException(...)` → 커스텀 예외 변환: ~110건 미변환
- structlog/loguru: 미도입 (표준 logging 유지)

---

## 8. 향후 확장 가능

1. **로그 수집 파이프라인**: ELK/Datadog 연동 시 JSON 포맷 즉시 파싱 가능
2. **에러 코드 확장**: 각 백엔드 도메인별 코드 추가 (현재 ~20개/백엔드 → 필요시 확장)
3. **IM 서브모듈 에러 코드**: data_ingestor, narrative_generator 등 내부 예외에 코드 추가
4. **ErrorSeverity 확장**: 로그 집계 대시보드에서 심각도별 필터링이 필요해지면 도입
5. **HTTPException 통합**: 라우터의 HTTPException을 커스텀 예외로 통일하는 리팩터링
