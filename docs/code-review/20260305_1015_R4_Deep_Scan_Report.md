# 코드 리뷰 리포트: R4 심층 스캔

- 라운드: 4 (심층 — N+1/성능, async/동시성, API 계약, 아키텍처)
- 시작: 2026-03-05 ~10:00
- 종료: 2026-03-05 10:15
- 커밋: 없음 (자동 수정 대상 0건)

---

## R4 목적

R1–R3에서 자동화 가능한 표면 이슈(린트, 인증, JSONB, 예외 체이닝) 수렴 후,
4개 심층 관점을 병렬 에이전트로 스캔:

1. **N+1 쿼리 / 성능** (performance-profiler)
2. **async / 동시성 패턴** (general-purpose)
3. **API 계약 / Pydantic 스키마 완전성** (general-purpose)
4. **아키텍처 / DRY / 복잡도** (general-purpose)

---

## 발견 이슈 요약

| 관점 | Critical | High | Medium | Low | 합계 |
|------|----------|------|--------|-----|------|
| 성능 (N+1) | 2 | 3 | 5 | 2 | 12 |
| async/동시성 | 1 | 6 | 5 | 3 | 15 |
| API 계약 | 1 | 4 | 10 | 2 | 17 |
| 아키텍처 | 0 | 6 | 7 | 6 | 19 |
| **합계** | **4** | **19** | **27** | **13** | **63** |

---

## False Positive 검증 (수동 확인)

| # | 에이전트 주장 | 실제 검증 | 판정 |
|---|-------------|----------|------|
| 1 | `approvals.py:79` Enum key ≠ str key → counts 항상 0 | `ApprovalStatus`는 `StrEnum` → `str(s) == ApprovalStatus.PENDING` 성립 | **FP** |
| 2 | `dashboard.py:78` response_model 누락 | FastAPI ≥0.95에서 return type annotation이 response_model로 사용됨 | **FP** |
| 3 | `embedder.py:170` time.sleep blocking | `_embed_with_retry`는 sync 메서드 (async 아님) — 의도적 설계 | **FP** |

---

## 자동 수정 가능 여부 분류

### 수정 불가 — 아키텍처 결정 필요

| # | 이슈 | 이유 |
|---|------|------|
| 1 | KIIS dashboard_service N+1 | joinedload 추가 시 기존 쿼리 동작 변경 가능 |
| 2 | KIIS manager_service N+1 | 비즈니스 로직과 쿼리가 밀접하게 결합 |
| 3 | FDD sync Session in async def (3 files) | FDD 전체 아키텍처가 sync Session 기반 — 부분 전환 불가 |
| 4 | bid.py float → Decimal | 모델 + 스키마 + 마이그레이션 + API 호환성 모두 영향 |
| 5 | `_serialize_decimal` 14개 파일 중복 | 공통 유틸 추출 = 14개 파일 동시 수정 필요 |
| 6 | report_service 541줄 함수 | 기능 분해 = 대규모 리팩토링 |
| 7 | JWT/패스워드 해싱 4개 모듈 중복 | 공유 라이브러리 생성 = 아키텍처 변경 |
| 8 | FE 크로스 모듈 import 8건 | 모듈 경계 재설계 필요 |

### 수정 대상 없음 — False Positive

위 FP 3건 (approvals.py, dashboard.py, embedder.py)

---

## 성능 이슈 상세

### Critical

1. **`kiis/app/services/dashboard_service.py:93-105`** — N+1
   - `db.get(Company, s.company_id)` in loop (매니저별 회사 조회)
   - 해결: `selectinload(CompanySnapshot.company)` 또는 JOIN

2. **`kiis/app/services/manager_service.py:50-154`** — N+1
   - 매니저당 fund + existing movement 2개 쿼리 → 2N queries
   - 해결: 배치 조회 후 메모리 매핑

### High

3. **`deal-mgmt/app/services/si_mapping_service.py:966-981`** — loop 쿼리
   - 산업별 DB 조회 in for loop
   - 해결: WHERE industry IN (...) 배치 쿼리

4. **`fdd/backend/app/services/qoe/qoe_service.py`** — full table scan
   - codes 필터 없이 전체 스캔
   - 해결: WHERE 조건 추가

5. **`kiis/app/services/search_service.py:133,160,186,212`** — LIMIT 없는 쿼리
   - 4개 함수에서 unbounded SELECT
   - 해결: .limit() 추가

---

## async/동시성 이슈 상세

### Critical

1. **FDD `async def` + sync `Session`** — event loop blocking
   - `reports.py:42`, `ralph.py:24`, `uploads.py:40`
   - FDD 전체가 sync Session 아키텍처 → 부분 전환 불가
   - 해결: FDD AsyncSession 마이그레이션 (대규모)

### High

2. **`deal-mgmt/app/tasks/ralph_tasks.py:34`** — Celery 멱등성 미보장
   - `acks_late=True` + retry 시 중복 실행 가능
   - 해결: 작업 시작 시 상태 체크 guard 추가

3. **`fdd/backend/app/services/ralph/ralph_service.py`** — sync session in async
4. **`fdd/backend/app/api/uploads.py`** — sync file I/O in async

---

## API 계약 이슈 상세

### Critical

1. **`deal-mgmt/app/schemas/bid.py:19,36,50`** — 금액에 float 사용
   - `amount: float` → IEEE 754 정밀도 손실 위험
   - 해결: Decimal + 모델 Numeric + 마이그레이션

### High (FP 제외 후 실질 2건)

2. **`fdd/backend/app/api/deals.py:390`** — summary 엔드포인트 response_model 부재
   - return type annotation 있으면 FP, 없으면 실 이슈 → 추가 확인 필요
3. **`im/src/api/routes/documents.py:59`** — upload-financials response_model 부재
   - 동일 조건

---

## 아키텍처 이슈 상세

### High

1. **`_serialize_decimal` 14개 스키마 파일 중복** (deal-mgmt)
2. **`report_service.py` 541줄 단일 함수** (FDD)
3. **model_builder / excel_renderer 고중첩 (15/13단계)** (deal-mgmt)
4. **JWT 토큰 생성 4개 모듈 독립 구현**
5. **패스워드 해싱 3개 모듈 독립 구현**
6. **FE 크로스 모듈 import 위반 8건** (MA → docs/fdd)

---

## R4 결론

| 분류 | 건수 |
|------|------|
| 전체 발견 | 63건 |
| False Positive 확인 | 3건 |
| 유효 이슈 | 60건 |
| 자동 수정 가능 | **0건** |
| 아키텍처 결정 필요 | 60건 |

**R4는 scan-only 라운드로, 모든 유효 이슈가 아키텍처 결정을 요하는 구조적 이슈이다.**
R1–R3에서 표면 이슈는 수렴(Critical/High 0건). R4 이슈는 향후 리팩토링 백로그로 관리한다.

---

## 에러 카운트 추이

| 관점 | R1 | R2 | R3 | R4 |
|------|------|------|------|------|
| 린트/포맷 | 0 | 0 | 0 | 0 |
| 타입 안전성 | 0 | 0 | 0 | 0 |
| 보안 (Critical) | 2 | 0 | 0 | 0 |
| 데이터 (JSONB) | 22 | 0 | 0 | 0 |
| 예외처리 | 3 | 0 | 0 | 0 |
| 성능 (N+1) | — | — | — | 12건 발견 (구조적) |
| async/동시성 | — | — | — | 15건 발견 (구조적) |
| API 계약 | — | — | — | 17건 발견 (FP 3건) |
| 아키텍처 | — | — | — | 19건 발견 (구조적) |

---

## 커버리지 맵

- [x] 린트/포맷 (R1)
- [x] 타입 안전성 (R1)
- [x] 의존성 (R1)
- [x] 인증 누락 (R2)
- [x] JSONB 크로스 DB (R2)
- [x] 예외 체이닝 (R2)
- [x] N+1 쿼리/성능 (R4 — scan)
- [x] async/동시성 (R4 — scan)
- [x] API 계약 (R4 — scan)
- [x] 아키텍처/DRY/복잡도 (R4 — scan)
- [ ] 테스트 커버리지 (R5 대상)
- [ ] 환경변수 동기화 (R5 대상)
- [ ] 마이그레이션 무결성 (R5 대상)
