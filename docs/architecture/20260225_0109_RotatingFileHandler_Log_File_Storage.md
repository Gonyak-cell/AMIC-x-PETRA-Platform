# RotatingFileHandler 로그 파일 저장 기능 구현

> 작성: 2026-02-25 01:09
> 브랜치: `feat/ma-workflow`

## 개요

4개 백엔드(FDD, KIIS, IM, Deal-mgmt)의 JSON 구조화 로깅 시스템에 **파일 저장 기능**을 추가.
기존 stdout JSON 출력에 더해, `LOG_DIR` 환경변수 설정만으로 로그 파일이 자동 생성된다.

## 생성 파일 구조

```
{LOG_DIR}/
├── {service}.log           # 전체 로그 (INFO+)  — 10MB × 5 백업
└── {service}-error.log     # 에러 전용 (ERROR+) — 10MB × 3 백업
```

예시 (`LOG_DIR=./logs`):
```
logs/
├── fdd.log
├── fdd-error.log
├── kiis.log
├── kiis-error.log
├── im.log
├── im-error.log
├── deal-mgmt.log
└── deal-mgmt-error.log
```

## 활성화 방법

### 방법 1: `.env` 파일
```env
LOG_DIR=./logs
```

### 방법 2: 환경변수 직접 설정
```bash
export LOG_DIR=/var/log/amic
```

### 방법 3: Docker Compose
```yaml
services:
  fdd-backend:
    environment:
      - LOG_DIR=/app/logs
    volumes:
      - ./logs/fdd:/app/logs
```

**미설정 시**: 기존처럼 stdout만 출력 (하위 호환 100%).

## 설계 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 파일 포맷 | JSON 고정 | 파일 로그는 파싱/검색용 → 항상 JSON |
| 로테이션 크기 | 10MB | 일반적 FastAPI 서비스 기준 적정 |
| 전체 로그 백업 수 | 5 | 최대 60MB (10MB × 6파일) |
| 에러 로그 백업 수 | 3 | 최대 40MB (10MB × 4파일) |
| 에러 파일 레벨 | ERROR+ | WARNING은 전체 로그에서만 확인 |
| 디렉토리 자동 생성 | `mkdir(parents=True)` | 첫 실행 시 수동 생성 불필요 |
| 환경변수 폴백 | `LOG_DIR` | config 미설정 시에도 환경변수로 활성화 가능 |

## 변경 파일 목록 (12개)

### logging.py — `_setup_file_handlers()` 추가 (4개)
| 파일 | 변경 내용 |
|------|----------|
| `fdd/backend/app/core/logging.py` | `import os, RotatingFileHandler, Path` 추가, `setup_logging(log_dir=)` 파라미터, `_setup_file_handlers()` 함수 |
| `kiis/app/core/logging.py` | 동일 |
| `im/src/api/core/logging.py` | 동일 |
| `deal-mgmt/app/core/logging.py` | 동일 |

### config.py — `LOG_DIR` 설정 추가 (4개)
| 파일 | 설정명 | 기본값 |
|------|--------|--------|
| `fdd/backend/app/config.py` | `log_dir: str` | `""` |
| `kiis/app/core/config.py` | `LOG_DIR: str` | `""` |
| `im/src/api/config.py` | `log_dir: str` (Field) | `""` |
| `deal-mgmt/app/core/config.py` | `LOG_DIR: str` | `""` |

### main.py — `setup_logging()` 호출에 `log_dir` 전달 (4개)
| 파일 | 변경 |
|------|------|
| `fdd/backend/app/main.py` | `log_dir=settings.log_dir or None` 추가 |
| `kiis/app/main.py` | `log_dir=settings.LOG_DIR or None` 추가 |
| `deal-mgmt/app/main.py` | `log_dir=settings.LOG_DIR or None` 추가 |
| `im/src/api/__init__.py` | `log_dir=cfg.log_dir or None` 추가 |

## 핵심 코드

### `_setup_file_handlers()` (4개 백엔드 동일)

```python
def _setup_file_handlers(log_dir: str) -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    json_fmt = JSONFormatter()

    # 전체 로그 파일
    all_handler = RotatingFileHandler(
        log_path / f"{SERVICE_NAME}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    all_handler.setFormatter(json_fmt)
    root.addHandler(all_handler)

    # 에러 전용 로그 파일
    error_handler = RotatingFileHandler(
        log_path / f"{SERVICE_NAME}-error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_fmt)
    root.addHandler(error_handler)
```

### `setup_logging()` 파라미터 확장

```python
def setup_logging(
    *,
    level: str = "INFO",
    json_output: bool = True,
    service_name: str | None = None,
    log_dir: str | None = None,       # ← 신규
) -> None:
    # ... 기존 stdout 핸들러 설정 ...

    # 파일 핸들러 (log_dir 또는 LOG_DIR 환경변수)
    file_dir = log_dir or os.environ.get("LOG_DIR")
    if file_dir:
        _setup_file_handlers(file_dir)
```

## 검증 결과

### 파일 핸들러 동작 테스트
```
생성된 파일: ['deal-mgmt-error.log', 'deal-mgmt.log']
deal-mgmt.log 라인 수: 2       (info + error)
deal-mgmt-error.log 라인 수: 1 (error만)
```

### 기존 테스트 영향 없음
| 백엔드 | 결과 | 비고 |
|--------|------|------|
| deal-mgmt | 120/121 통과 | 1건 실패는 기존 integrations 테스트 (변경 무관) |
| kiis | 27/28 통과 | 1건 실패는 기존 JWT 시크릿 테스트 (변경 무관) |

### .gitignore
`*.log`과 `logs/`가 이미 포함 — 추가 수정 불필요.

## 로그 파일 JSON 출력 예시

### 전체 로그 (`{service}.log`)
```json
{"timestamp": "2026-02-24T16:06:23.887546+00:00", "level": "INFO", "logger": "deal-mgmt.test", "message": "test info message", "service": "deal-mgmt", "module": "main", "function": "create_transaction", "line": 42}
```

### 에러 로그 (`{service}-error.log`)
```json
{"timestamp": "2026-02-24T16:06:23.889937+00:00", "level": "ERROR", "logger": "deal-mgmt.test", "message": "test error message", "service": "deal-mgmt", "module": "main", "function": "create_transaction", "line": 45, "error": {"type": "ValueError", "message": "Invalid input", "stacktrace": "...", "error_code": "MA-1002"}}
```

## 하위 호환성

- `LOG_DIR` 미설정 시 → 기존 동작과 100% 동일 (stdout만)
- `setup_logging()` 기존 호출 → `log_dir` 파라미터 기본값 `None` → 변경 없음
- 기존 `raise` 문, `logger.error()` 호출 → 변경 0건
