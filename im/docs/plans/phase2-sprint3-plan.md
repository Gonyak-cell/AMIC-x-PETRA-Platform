# Phase 2 Sprint 3 마무리 계획 — E2E 파이프라인 + 캐싱 + 에러 복구

> 작성일: 2026-02-09
> 상태: ✅ 구현 완료 (v0.2.1, 223 tests)

## Context

Phase 2 Data Ingestor는 Sprint 1-2에서 개별 모듈(DART client, parsers, crawlers, aggregator)이 모두 구현됨 (15파일, 161 tests). Sprint 3에서 이 모듈들을 묶어 E2E 파이프라인으로 만들고, 캐싱과 에러 복구를 추가하여 모듈을 완성한다.

---

## 파일 생성/수정 목록

| 파일 | 작업 | 예상 크기 |
|------|------|----------|
| `src/data_ingestor/cache.py` | **신규** — CacheManager, CachedDartClient | ~250줄 |
| `src/data_ingestor/pipeline.py` | **신규** — DataCollectionPipeline, PipelineConfig, CollectionResult | ~350줄 |
| `src/data_ingestor/exceptions.py` | **수정** — CacheError, PipelineError 추가 | +10줄 |
| `src/data_ingestor/__init__.py` | **수정** — 신규 클래스 export, v0.2.1 | +15줄 |
| `tests/test_data_ingestor/test_cache.py` | **신규** — 캐시 테스트 | ~250줄 |
| `tests/test_data_ingestor/test_pipeline.py` | **신규** — 파이프라인 테스트 | ~350줄 |

---

## 1. cache.py — 캐싱 레이어

### 핵심 클래스

```
CacheTTL(int, Enum)
  - COMPANY_INFO = 86400 (24h)
  - FINANCIAL_STATEMENTS = 86400
  - NEWS = 21600 (6h)
  - WEB_INFO = 604800 (7일)

CacheConfig(dataclass)
  - redis_url, prefix, default_ttl, memory_max_size, enable_redis

CacheManager (async context manager)
  - get(key) → Any | None
  - set(key, value, ttl) → None
  - delete(key), clear(pattern)
  - Redis 우선, 연결 실패 시 메모리 dict 폴백
  - 메모리 캐시: dict[key, (value, expiry_timestamp)]

CachedDartClient (DartAPIClient 래퍼)
  - 동일 인터페이스 (get_company_info, get_financial_statements 등)
  - 캐시 미스 → API 호출 → 캐시 저장
  - 캐시 히트 → 즉시 반환
  - 직렬화: Pydantic model_dump_json / model_validate_json
```

### 설계 원칙

- 기존 DartAPIClient는 **수정하지 않음** — 래퍼 패턴
- Redis가 없어도 동작 (메모리 폴백)
- redis-py async (`redis.asyncio`) 사용 (이미 requirements에 포함)

---

## 2. pipeline.py — E2E 파이프라인 + 에러 복구

### 핵심 클래스

```
DataPriority(Enum): REQUIRED, IMPORTANT, OPTIONAL

StepResult(dataclass)
  - step_name, success, priority, error, duration_ms

CollectionResult(dataclass)
  - data: IMDocumentData | None
  - steps: list[StepResult], warnings, errors
  - is_success (필수 데이터 성공 여부), summary, duration_ms

PipelineConfig(dataclass)
  - dart_api_key, financial_years=3, base_year
  - include_shareholders, include_dividends, include_news, include_web_info
  - news_days=30, news_count=20
  - enable_cache, cache_config, timeout

DataCollectionPipeline (async context manager)
  - collect(corp_code) → CollectionResult
```

### 수집 흐름

```
collect(corp_code)
  │
  ├─ Phase 1: DART 기업정보 [REQUIRED] ← 먼저 (homepage_url 필요)
  │    실패 시 → 즉시 중단, result.data = None
  │
  ├─ Phase 2: DART 나머지 + 크롤링 [asyncio.gather 병렬]
  │    ├─ 재무제표 2025 [IMPORTANT]
  │    ├─ 재무제표 2024 [IMPORTANT]
  │    ├─ 재무제표 2023 [IMPORTANT]
  │    ├─ 주주정보 [OPTIONAL]
  │    ├─ 배당정보 [OPTIONAL]
  │    ├─ 뉴스 [OPTIONAL]
  │    └─ 웹사이트 [OPTIONAL]
  │
  └─ Phase 3: DataAggregator로 통합 → IMDocumentData
```

### 에러 복구 전략

| 데이터 | 우선순위 | 실패 시 |
|--------|---------|---------|
| DART 기업정보 | REQUIRED | 파이프라인 중단, errors에 기록 |
| DART 재무제표 (연도별) | IMPORTANT | 경고, 나머지 연도로 진행 |
| 주주/배당 | OPTIONAL | 경고, 계속 진행 |
| 뉴스/웹사이트 | OPTIONAL | 경고, 계속 진행 |

`_safe_step(name, priority, coroutine)` 메서드가 모든 단계를 try/except로 감싸고 StepResult에 기록. asyncio.gather에서 개별 예외가 전파되지 않음.

---

## 3. exceptions.py 추가

```python
class CacheError(DataIngestorError):
    """캐시 관련 예외."""
    pass

class PipelineError(DataIngestorError):
    """파이프라인 관련 예외."""
    pass
```

---

## 4. __init__.py 업데이트

```python
# 추가 export
"CacheManager", "CachedDartClient", "CacheConfig", "CacheTTL",
"DataCollectionPipeline", "PipelineConfig", "CollectionResult",
"StepResult", "DataPriority", "CacheError", "PipelineError"

__version__ = "0.2.1"
```

---

## 5. 구현 순서 (의존성 기준)

### Step 1: 기반 작업 (병렬)

- exceptions.py에 CacheError, PipelineError 추가
- cache.py 작성 (CacheTTL → CacheConfig → CacheManager → CachedDartClient)

### Step 2: pipeline.py 작성

- PipelineConfig, DataPriority, StepResult, CollectionResult 데이터 클래스
- DataCollectionPipeline._safe_step, _fetch_* 메서드
- _collect_dart_data, _collect_crawl_data (asyncio.gather 병렬)
- _aggregate, collect 오케스트레이터

### Step 3: 통합

- __init__.py 업데이트 (exports + version)

### Step 4: 테스트 (병렬)

- test_cache.py 작성
- test_pipeline.py 작성

### Step 5: 검증

- `pytest tests/test_data_ingestor/ -v` (기존 161 + 신규 ~50-60)
- 전체 통과 확인

---

## 6. 테스트 전략

- **외부 의존성 없음**: Redis mock, DART API mock, Playwright mock
- `CacheConfig(enable_redis=False)` — 메모리 전용 모드로 Redis 없이 테스트
- `AsyncMock(spec=DartAPIClient)` — 모든 DART API 호출 mock
- 기존 패턴 따름: class-based, `@pytest.mark.asyncio`, `MagicMock`/`AsyncMock`

---

## 7. 알려진 이슈

- `FinancialStatementsCollection`에 `bsns_year`/`fs_div` 필드가 Pydantic 모델에 선언되지 않아 `extra="ignore"`로 무시됨. 테스트에서 MagicMock으로 우회. 별도 후속 티켓으로 필드 추가 예정.
