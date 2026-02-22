# KIIS KOFIA 검색 데이터 3계층 캐싱 시스템

> 작성일: 2026-02-17 18:52
> 상태: **구현 완료** (Phase A + B)

## 개요

KOFIA API를 통해 한 번 검색한 펀드 데이터를 DB에 영속 저장하여, 동일/유사 검색 시 즉시 활용하는 3계층 캐싱 시스템.

**핵심 효과**: 응답 시간 2~3초 → 5ms (DB) / 0ms (프론트엔드 캐시)

## 아키텍처

```
요청 → [L1] TanStack Query (브라우저 메모리)
        │  staleTime: 5분(목록), 10분(상세)
        │  gcTime: 30분
        │  HIT → 0ms 즉시 반환
        │
       [L2] Redis (@cache 데코레이터)
        │  TTL: 6시간 (기존 유지)
        │  HIT → ~1ms 반환
        │
       [L3] PostgreSQL (영속 저장소)
        │  kofia_last_synced로 freshness 판별 (24시간)
        │  HIT(최신) → ~5ms DB 쿼리
        │  MISS → KOFIA API 호출 → DB upsert → 반환
        │  API 실패 → DB stale 데이터 fallback
        │
       [외부] KOFIA DIS API
            Rate Limit: 3초 간격, 분당 20회
```

## 변경 파일

### 백엔드 (Phase A)

| 파일 | 변경 |
|------|------|
| `kiis/app/models/fund.py` | `kofia_last_synced` 컬럼 추가 (DateTime, timezone-aware) |
| `kiis/app/services/kofia_service.py` | `sync_funds_to_db()` 목록 upsert, `sync_fund_detail_to_db()` 상세+매니저 upsert |
| `kiis/app/routers/kofia.py` | DB-first 전략, `_query_fresh_funds_from_db()`, 싱글톤 패턴, 상세 동기화 |
| `kiis/app/main.py` | lifespan: 자동 마이그레이션 + 싱글톤 정리 |
| `kiis/app/core/config.py` | `KOFIA_DB_FRESHNESS_HOURS: int = 24` |
| `kiis/migrations/versions/bd86aed05da0_*.py` | Alembic 마이그레이션 |

### 프론트엔드 (Phase B)

| 파일 | 변경 |
|------|------|
| `amic-platform/src/modules/kiis/hooks/useFunds.ts` | staleTime 5~10분, gcTime 30분 설정 |

## 핵심 로직

### DB-first 전략 (`list_funds` 엔드포인트)

```python
# 1단계: DB에 최신 데이터 있으면 즉시 반환
db_result = await _query_fresh_funds_from_db(db, ...)
if db_result is not None:
    return db_result

# 2단계: KOFIA API 호출 → DB 동기화
items, total = await service.search_funds(...)
await service.sync_funds_to_db(db, items)  # upsert

# 3단계: API 실패 시 DB stale 데이터 fallback
return await _fallback_funds_from_db(db, ...)
```

### Freshness 판별

- `Fund.kofia_last_synced >= (현재 - 24시간)` → 최신
- `company_name` 필터가 있으면 해당 운용사 데이터만 체크
- 환경변수 `KOFIA_DB_FRESHNESS_HOURS`로 조정 가능

### DB Upsert

- PostgreSQL `ON CONFLICT DO UPDATE` (fund_code unique index)
- 벌크 insert (라운드트립 1회)
- 목록 검색: `sync_funds_to_db()` — 10개 필드 upsert
- 상세 조회: `sync_fund_detail_to_db()` — 17개 필드 + 매니저 동기화

## 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `KOFIA_DB_FRESHNESS_HOURS` | 24 | DB 데이터 최신 판별 기준 (시간) |

## 검증 방법

1. **DB 동기화**: `GET /kofia/funds?company_name=한국투자` → `SELECT * FROM funds` 확인
2. **DB-first**: 동일 검색 2회 → 로그에서 1회차 "Synced N funds", 2회차 "DB cache hit"
3. **KOFIA 장애**: API URL을 잘못 설정 → DB stale 데이터로 정상 응답
4. **프론트엔드**: DevTools Network → 5분 내 재방문 시 네트워크 요청 없음
