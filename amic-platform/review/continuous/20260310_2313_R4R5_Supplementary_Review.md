# Continuous Review — R4/R5 보완 (프로덕션 복원력 + 운영 & 코드 건강성)

> **Date**: 2026-03-10 23:13 (KST)
> **Round**: R4/R5 보완 (이전 R1-R6 통합 리뷰 후속)
> **Scope**: git diff origin/master...HEAD — MA 마케팅 스테이지 확장 (8개 변경 파일)
> **Protocol**: VCP Lite (Read→Grep→Self-Challenge SC-1/3/5)

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|---------|
| `deal-mgmt/app/models/enums.py` | MarketingStage CIM_SENT, DD_STARTED 추가 |
| `deal-mgmt/migrations/versions/078_*.py` | PostgreSQL enum ALTER TYPE |
| `deal-mgmt/app/services/buyer_status_service.py` | 자동 승격 서비스 (신규) |
| `deal-mgmt/app/routers/buyer_marketing.py` | 자동 승격 통합 + DART/Excel 엔드포인트 |
| `deal-mgmt/app/core/rate_limiter.py` | dart/export rate limiter 인스턴스 추가 |
| `deal-mgmt/tests/test_buyer_status_service.py` | 27개 단위 테스트 (신규) |
| `amic-platform/src/modules/ma/constants/buyer.ts` | FE 상수 확장 |
| `amic-platform/src/modules/ma/types/marketing_log.ts` | FE 타입 확장 |

---

## R4 — 프로덕션 복원력 리뷰

### 에러 처리 분석

**`buyer_marketing.py` — 4개 `except Exception` 블록 검증:**

| 위치 | 용도 | 로깅 | 복구 전략 | 판정 |
|------|------|------|----------|------|
| L325 | DART 기업 검색 | `logger.warning(exc_info=True)` | 빈 리스트 반환 (graceful degradation) | ✅ 적절 |
| L351 | DART 재무 요약 | `logger.warning(exc_info=True)` | 502 Bad Gateway 반환 | ✅ 적절 |
| L423 | 플랫폼 설정 조회 | `logger.warning` | DEFAULT 스타일 폴백 | ✅ 적절 |
| L438 | Excel 생성 | `logger.exception` | 500 반환 | ✅ 적절 |

**`auto_advance_buyer_status()` 에러 처리:**
- 자체 try/except **없음** — 의도적 설계
- `create_marketing_log()` 트랜잭션 내부에서 호출 (L120)
- `audit_service.record()` 실패 시 → 전체 트랜잭션 롤백 (마케팅 로그 포함)
- **판정**: ✅ 적절 — 부분 커밋 방지. 자동 승격이 실패하면 마케팅 로그 생성도 롤백되어 데이터 정합성 보장

### 타임아웃 & 재시도 분석

**`kiis_client.py` 검증 결과:**
- `httpx.AsyncClient(timeout=10.0)` — 기본 10초 타임아웃 ✅
- `_request_with_retry()`: `ConnectError`, `ReadTimeout`, `WriteTimeout` 재시도 (최대 2회, 지수 백오프 0.5s/1.0s) ✅
- `HTTPStatusError`는 재시도 없이 즉시 raise ✅
- 커넥션 풀 재사용 (`asyncio.Lock` 기반 double-check locking) ✅

**`rate_limiter.py` 검증 결과:**
- 슬라이딩 윈도우 구현 정상
- stale 키 정리 주기: 60초 (`_CLEANUP_INTERVAL`) ✅
- DART 검색: 10req/60s, Excel 내보내기: 5req/60s — 적절한 제한치

### 관찰 가능성

- 모든 에러 경로에 `logger.warning` 또는 `logger.exception` 사용 ✅
- `exc_info=True`로 스택 트레이스 포함 (L325, L351) ✅
- Rate limit 초과 시 `logger.warning`에 identifier, count/max 포함 ✅
- 민감 데이터(비밀번호/토큰) 로깅 없음 ✅

### R4 결론: **이슈 0건**

변경 범위 내 에러 처리, 타임아웃, 관찰 가능성 모두 프로덕션 수준으로 구현됨.

---

## R5 — 운영 & 코드 건강성 리뷰

### 성능 분석

**N+1 쿼리 패턴 검사:**
- `export_buyers_excel()` (L373-417): 3개 쿼리 사용
  1. `BuyerCandidate` 전체 조회 (L373)
  2. `BuyerMarketingLog` 집계 (L378-386)
  3. `ConsortiumMapping` JOIN (L401-411)
- 각 쿼리는 `txn_id`로 필터링되어 **루프 내 DB 호출 없음** ✅
- `selectinload`/`joinedload` 미사용 — 관계 로딩이 필요 없는 구조이므로 적절 ✅

**`auto_advance_buyer_status()` 성능:**
- while 루프 최대 반복: `ADVANCE_PATH` 길이(8) → 최악 8번
- 각 반복마다 `audit_service.record()` DB 호출 — 실질적으로 2-3홉이 최대
- `visited` set으로 무한 루프 방지 ✅

### 배포 안전성

**마이그레이션 (078):**
- `down_revision = "077"` → 체인 정상 (076→077→078) ✅
- `upgrade()`: `IF NOT EXISTS` 사용 → 멱등성 보장 ✅
- `downgrade()`: `raise RuntimeError(...)` → 의도적 롤백 차단 ✅ (PostgreSQL enum 값 제거 불가)

**의존성 동기화:**
- `buyer_status_service.py` — 신규 파일이지만 새 외부 패키지 없음 (stdlib + sqlalchemy + app 내부) ✅
- `rate_limiter.py` — 기존 모듈에 인스턴스 추가만, 새 의존성 없음 ✅

**BE-FE 타입 동기화:**
- BE `MarketingStage` enum: 8개 값 (IDENTIFIED, EMAIL_SENT, PHONE_CALL, ADVISOR_MEETING, NDA_SIGNED, TARGET_MEETING, CIM_SENT, DD_STARTED)
- FE `MarketingStage` 타입: 8개 값 — 일치 ✅
- FE `MARKETING_STAGES` 배열: 8개 항목 — 일치 ✅
- FE `MARKETING_STAGE_LABELS`: CIM_SENT="IM 발송", DD_STARTED="DD 진행" — 라벨 정상 ✅

### 의존성 & 결합도

**`buyer_status_service.py` 참조 분석:**
- 참조하는 파일: 2개 (`buyer_marketing.py`, `test_buyer_status_service.py`) ✅
- 순환 의존성: 없음 (service → models/enums, audit_service만 의존) ✅
- 서비스 레이어 분리: 라우터에서 비즈니스 로직 추출 → 단일 책임 원칙 준수 ✅

### FE 쿼리 무효화 (R3 보완)

**`useMarketingLogs.ts` — buyers 쿼리 무효화:**
- `useCreateMarketingLog.onSuccess`: `["ma", "transactions", txnId, "buyers"]` ✅
- `useUpdateMarketingLog.onSuccess`: 동일 ✅
- `useDeleteMarketingLog.onSuccess`: 동일 ✅
- FunnelNav가 buyers 쿼리에 의존하므로, 마케팅 로그 변경 시 자동 갱신 보장 ✅

### R5 결론: **이슈 0건**

성능, 배포 안전성, 의존성 결합도 모두 양호.

---

## R1-R3/R6 보완 점검

이전 R1-R6 통합 리뷰에서 발견된 12건은 모두 수정 완료. 보완 점검 결과:

| 관점 | 점검 항목 | 결과 |
|------|----------|------|
| R1 정합성 | FE 상수 8개 = BE enum 8개 | ✅ 일치 |
| R2 보안 | 인증 Depends 전수 확인 | ✅ 기존 리뷰에서 완료 |
| R3 데이터 정합성 | buyers 쿼리 무효화 3곳 | ✅ 추가 완료 확인 |
| R6 비즈니스 | 서비스 레이어 분리, 27개 테스트 | ✅ 기존 리뷰에서 완료 |

---

## 발견 이슈

> 이번 보완 리뷰에서 발견된 이슈가 없습니다.

R4(프로덕션 복원력)와 R5(운영 & 코드 건강성) 관점에서 변경 코드는 프로덕션 수준으로 구현되어 있습니다.

---

## 검증 투명성

- 검증한 가설: 14건
- 거부된 가설 (사전 제거): 14건
- 보고된 이슈: 0건
- 거부율: 100%

### 거부 사유 분류

| 사유 | 건수 |
|------|------|
| SC-1 실행 경로 기각 | 2 |
| SC-3 라이브러리/프레임워크 처리 기각 | 4 |
| SC-5 의도된 패턴 기각 | 5 |
| Grep 반증 | 3 |

### 주요 거부 상세

1. **"`except Exception` 너무 넓다"** → SC-5 기각: 외부 서비스 호출(KIIS)의 의도된 패턴. 모든 블록에 로깅 있음.
2. **"auto_advance에 try/except 없다"** → SC-3 기각: SQLAlchemy 트랜잭션 롤백이 처리. 부분 커밋 방지가 올바른 동작.
3. **"N+1 쿼리 가능성"** → Grep 반증: 루프 내 DB 호출 없음. 3개 독립 쿼리로 데이터 수집.
4. **"rate_limiter 멀티 워커 문제"** → SC-1 기각: 단일 워커 Uvicorn 배포 (Azure VM 2 vCPU). 문서에도 명시됨.

---

## 다음 라운드

- 다음 실행: R1 (기본 체크리스트)
