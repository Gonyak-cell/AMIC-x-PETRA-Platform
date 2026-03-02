# Code Review — FI Auto-Mapping R5 (13-Perspective Gap Analysis)

> **Review Date**: 2026-03-02 10:23 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: FI Auto-Mapping 시스템 (deal-mgmt + amic-platform), 13-Perspective 중 R4 미수행 관점
> **Method**: 3-Agent Parallel Review (R2+R4 심화, R5, R6)
> **Base Review**: R4 (20260302_0209) 5-Agent 리뷰 완료 → 13건 수정 완료
> **Quality Gates**: ruff(PASS) pytest 26/26(PASS) tsc(PASS)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 2     | HIGH: 2               | P1: 2               |
| Moderate | 6     | HIGH: 4 / MEDIUM: 2   | P2: 6               |
| Minor    | 9     | HIGH: 3 / MEDIUM: 6   | P3: 9               |
| **Total**| **17**| HIGH: **9** / MEDIUM: **8** | P1: **2** / P2: **6** / P3: **9** |

**FP Prevention**: 가설 31건 검증, 14건 사전 거부 (거부율: 45%)
**Cross-Agent Dedup**: 3건 중복 발견 → 병합 (높은 심각도 유지)

---

## 13-Perspective Coverage

| Round | Perspective | R4 수행 | R5 수행 | Agent |
|-------|------------|---------|---------|-------|
| R1 | 기본 린트/타입/스타일 | ✅ | — | — |
| R2 | Security STRIDE | ❌ | ✅ | Agent 1 |
| R2 | 위협 모델링 | ❌ | ✅ | Agent 1 |
| R3 | 데이터 흐름 | ✅ 부분 | — | — |
| R3 | API 계약 | ✅ 부분 | — | — |
| R4 | 에러 핸들링 심화 | ❌ | ✅ | Agent 1 |
| R4 | 관측성 | ❌ | ✅ | Agent 1 |
| R5 | 성능 | ❌ | ✅ | Agent 2 |
| R5 | 배포 안전성 | ❌ | ✅ | Agent 2 |
| R5 | 의존성/결합도 | ❌ | ✅ | Agent 2 |
| R6 | 도메인 로직 | ❌ | ✅ | Agent 3 |
| R6 | 테스트 품질 | ❌ | ✅ | Agent 3 |
| R6 | 인지 복잡도 | ❌ | ✅ | Agent 3 |
| R6 | 접근성 | ✅ | — | — |

---

## Findings

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [R5-01] fi_recommendations DB 쿼리 예외 미처리 — [Major/HIGH] — Priority: P1

**관점**: R4 에러 핸들링 심화
**위치**: `deal-mgmt/app/routers/pef_registry.py:107-119`
**점수**: 70 (심각도 70 × 신뢰도 1.0)

**현상**:
`fi_recommendations()` 함수의 메인 DB 쿼리(line 107-119)가 `try/except` 없이 실행된다. DB 연결 실패, 타임아웃, 쿼리 에러 시 unhandled 500이 반환된다.

**증거**:
```python
# pef_registry.py:107-119 — 예외 처리 없음
stmt = select(PefFundRegistry).where(
    PefFundRegistry.registration_date.isnot(None),
    PefFundRegistry.registration_date >= "2021-01-01",
    PefFundRegistry.total_committed_capital.isnot(None),
    PefFundRegistry.total_committed_capital > 0,
)
if exclude_project_funds:
    stmt = stmt.where(~PefFundRegistry.pef_name.contains("프로젝트"))
    if target_name:
        stmt = stmt.where(~PefFundRegistry.pef_name.contains(target_name))

result = await db.execute(stmt)  # ← DB 에러 시 500
rows = result.scalars().all()
```

**비교**: 동일 라우터의 `list_pef_funds()`(line 33-39)와 `count_pef_funds()`(line 45-55)도 동일한 패턴.

**권장 수정**:
```python
try:
    result = await db.execute(stmt)
    rows = result.scalars().all()
except SQLAlchemyError:
    logger.exception("FI recommendation query failed: txn=%s", txn_id)
    raise HTTPException(status_code=503, detail="추천 데이터 조회에 실패했습니다")
```

---

#### [R5-02] 성공 경로 로그 완전 부재 — [Major/HIGH] — Priority: P1

**관점**: R4 관측성
**위치**: `deal-mgmt/app/routers/pef_registry.py` (전체)
**점수**: 70 (심각도 70 × 신뢰도 1.0)

**현상**:
3개 엔드포인트 모두 성공 경로에서 로그를 남기지 않는다. 운영 환경에서 요청 빈도, 매칭 결과, 응답 크기 등을 파악할 수 없다.

**증거**:
- `list_pef_funds()`: 로그 0건
- `count_pef_funds()`: 로그 0건
- `fi_recommendations()`: 로그 0건 (R4에서 security.py에만 `logger.debug` 추가됨)

**비교**: `deal-mgmt/app/routers/buyers.py`에서는 `logger.info("Short-list promotion: ...")` 등 성공 경로 로그가 존재.

**권장 수정**:
```python
logger.info(
    "FI recommendations: txn=%s, target=%s억, matched_gps=%d, total_funds=%d",
    txn_id, deal_value, len(recommendations), sum(r.fund_count for r in recommendations),
)
```

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [R5-03] list/count 엔드포인트 DB 예외 미처리 — [Moderate/HIGH] — Priority: P2

**관점**: R4 에러 핸들링 심화
**위치**: `deal-mgmt/app/routers/pef_registry.py:33-55`
**점수**: 40 (심각도 40 × 신뢰도 1.0)

**현상**:
`list_pef_funds()`와 `count_pef_funds()`도 DB 쿼리 예외 처리가 없다. R5-01과 동일한 패턴이나 영향도가 낮음 (단순 조회).

---

#### [R5-04] FE 부분 실패 메시지 미구분 — [Moderate/HIGH] — Priority: P2

**관점**: R4 에러 핸들링 심화
**위치**: `amic-platform/src/modules/ma/hooks/usePefRegistry.ts:51`
**점수**: 40 (심각도 40 × 신뢰도 1.0)

**현상**:
`useFIRecommendations` 훅이 에러 발생 시 `error.message`만 전달하며, HTTP 상태 코드(422 vs 503 vs 401)에 따른 분기 처리가 없다.

**증거**:
```typescript
// usePefRegistry.ts:44-52
queryFn: async () => {
  const { data } = await maApi.get<FIRecommendation[]>(
    `/transactions/${txnId}/fi-recommendations`,
    { params: apiParams },
  );
  return data;
},
// error 처리 = react-query 기본 (toast 없음, 상태 코드 구분 없음)
```

---

#### [R5-05] 에러 로그 컨텍스트 부족 — [Moderate/HIGH] — Priority: P2

**관점**: R4 관측성
**위치**: `deal-mgmt/app/routers/pef_registry.py:92-94`
**점수**: 40 (심각도 40 × 신뢰도 1.0)

**현상**:
배수 역전 검증 실패 시 422를 반환하지만 로그를 남기지 않는다. 클라이언트 오류 패턴 분석이 불가능.

```python
if lower_multiplier > upper_multiplier:
    raise HTTPException(status_code=422, detail="하한 배수가 상한 배수보다 클 수 없습니다")
# ← 로그 없음
```

---

#### [R5-06] 라우터 단일 함수 5개 책임 (인지 복잡도) — [Moderate/HIGH] — Priority: P2

**관점**: R6 인지 복잡도 + R5 결합도
**위치**: `deal-mgmt/app/routers/pef_registry.py:56-175`
**점수**: 40 (심각도 40 × 신뢰도 1.0)
**교차 검증**: Agent 2 + Agent 3 동시 발견

**현상**:
`fi_recommendations()` 함수가 ~120줄에 5개 책임을 혼합:
1. 입력 검증 (line 87-94)
2. Transaction 조회 (line 96-105)
3. DB 쿼리 + 필터링 (line 107-119)
4. GP 그룹핑 + 매칭 알고리즘 (line 121-158)
5. 응답 직렬화 (line 160-175)

**비교**: 동일 프로젝트의 `buyers.py`는 서비스 레이어 분리 패턴 사용 (`buyer_marketing.py` 등).

**참고**: R4 리뷰에서도 인라인 로직 관련 지적(R4-15)이 있었으나 의도적으로 스킵됨. MVP 단계에서 서비스 분리의 ROI가 낮다고 판단. 향후 알고리즘 복잡도 증가 시 분리 권장.

---

#### [R5-07] 경계값 테스트 미비 — [Moderate/MEDIUM] — Priority: P2

**관점**: R6 테스트 품질
**위치**: `deal-mgmt/tests/test_fi_mapping.py`
**점수**: 24 (심각도 40 × 신뢰도 0.6)

**현상**:
`test_equal_multipliers_boundary`(line 695)가 `lower=1.0, upper=1.0`을 테스트하지만, 정확히 경계에 걸리는 값(`target * 0.5` 또는 `target * 3.0`)의 포함/제외를 명시적으로 검증하는 테스트가 없다.

**증거**: `test_range_filter_lower_bound`(line 304)와 `test_range_filter_upper_bound`(line 352)는 범위 밖 GP를 검증하지만, 정확히 경계(equality)인 GP의 동작은 테스트하지 않음.

---

#### [R5-08] 마이그레이션 052 `__import__` 비표준 패턴 — [Moderate/MEDIUM] — Priority: P2

**관점**: R5 배포 안전성
**위치**: `deal-mgmt/migrations/versions/052_pef_fund_registry.py`
**점수**: 24 (심각도 40 × 신뢰도 0.6)

**현상**:
`__import__("app.models")` 패턴이 일반적인 Alembic 마이그레이션에서 비표준이다. 다른 마이그레이션(045, 046, 047)에서는 이 패턴이 사용되지 않음. `target_metadata`를 위해 모델을 임포트하는 것은 `env.py`에서 처리하는 것이 일반적.

**영향**: 마이그레이션 자체는 정상 동작하나, 유지보수 시 혼란 가능.

---

### P3 — 저우선 (점수: <30)

---

#### [R5-09] upper_multiplier 최대 10x 허용 — [Minor/HIGH] — Priority: P3

**관점**: R2 Security (정보 노출)
**위치**: `deal-mgmt/app/routers/pef_registry.py:74`
**점수**: 20 (심각도 20 × 신뢰도 1.0)

**현상**:
`upper_multiplier` 최대값이 `10.0`이므로 `target * 10`까지 조회 가능. 거래금액 1000억 기준 10,000억까지의 GP 정보가 노출될 수 있다. 비즈니스 관점에서 5x가 더 적절할 수 있으나, 현재 파라미터로 공개 설정이므로 Low risk.

---

#### [R5-10] match_reason에서 거래금액 범위 역추정 가능 — [Minor/HIGH] — Priority: P3

**관점**: R2 Security (정보 노출)
**위치**: `deal-mgmt/app/routers/pef_registry.py:161-170`
**점수**: 20 (심각도 20 × 신뢰도 1.0)

**현상**:
`match_reason`에 `"최소 펀드 약정총액 {X}이(가) 거래금액 범위({Y}~{Z}) 이내"`가 포함되어, 거래금액의 하한/상한이 API 응답으로 노출된다. CLIENT 역할 사용자에게도 동일한 응답이 반환됨 (현재 CLIENT는 403으로 차단되므로 실제 노출은 없음).

---

#### [R5-11] FE 422 에러 미구분 처리 — [Minor/MEDIUM] — Priority: P3

**관점**: R4 에러 핸들링
**위치**: `amic-platform/src/modules/ma/hooks/usePefRegistry.ts`
**점수**: 12 (심각도 20 × 신뢰도 0.6)

**현상**:
배수 역전(422)과 인증 실패(401)와 서버 에러(500)를 동일하게 처리. 422는 사용자 입력 오류이므로 별도 메시지가 적절하나, 현재 FE에서 커스텀 배수를 전달하는 UI가 없으므로 실제 발생 가능성 낮음.

---

#### [R5-12] `contains()` 이스케이프 미처리 — [Minor/MEDIUM] — Priority: P3

**관점**: R2 Security (인젝션)
**위치**: `deal-mgmt/app/routers/pef_registry.py:116-118`
**점수**: 12 (심각도 20 × 신뢰도 0.6)

**현상**:
`target_name`을 `contains()` (= SQL `LIKE '%{name}%'`)에 직접 전달. `%` 또는 `_` 와일드카드 문자가 포함된 회사명이 있으면 의도하지 않은 매칭이 발생할 수 있다. SQLAlchemy ORM이므로 SQL 인젝션은 아니지만, LIKE 와일드카드 이스케이프가 누락됨.

**영향**: 회사명에 `%`, `_`가 포함되는 경우는 매우 드물어 실제 위험 낮음.

---

#### [R5-13] 프로젝트 펀드 키워드 "프로젝트"만 제외 — [Minor/MEDIUM] — Priority: P3

**관점**: R6 도메인 로직
**위치**: `deal-mgmt/app/routers/pef_registry.py:115`
**점수**: 12 (심각도 20 × 신뢰도 0.6)

**현상**:
프로젝트 펀드 제외 로직이 `"프로젝트"` 키워드만 사용. 실제 프로젝트 펀드는 `"PJ"`, `"프로젝트투자"`, `"특별목적"` 등 다양한 명칭이 있을 수 있다. 현재 `seed_pef_registry.py` 데이터 기준으로는 "프로젝트"만으로 충분하나, 실제 금감원 데이터에서는 다른 패턴도 존재할 수 있음.

---

#### [R5-14] registration_date 형식 미정규화 — [Minor/MEDIUM] — Priority: P3

**관점**: R6 도메인 로직
**위치**: `deal-mgmt/app/models/pef_fund_registry.py:24`
**점수**: 12 (심각도 20 × 신뢰도 0.6)

**현상**:
`registration_date`가 `String(10)`으로 저장되며 YYYY-MM-DD 형식이 강제되지 않는다. 문자열 비교(`>= "2021-01-01"`)는 형식이 일관된 경우에만 정확. 시드 데이터는 정규화되어 있으나, 외부 데이터 수집 시 `"2021.01.01"` 등 다른 형식이 유입될 수 있음.

---

#### [R5-15] 테스트명 "as_number" vs 실제 str 검증 불일치 — [Minor/MEDIUM] — Priority: P3

**관점**: R6 테스트 품질
**위치**: `deal-mgmt/tests/test_fi_mapping.py:730`
**점수**: 12 (심각도 20 × 신뢰도 0.6)

**현상**:
`test_serialization_decimal_as_number`라는 테스트명이지만, 실제로는 Decimal이 `str`로 직렬화되는 것을 검증한다. 테스트명과 검증 내용이 불일치.

```python
# line 730
async def test_serialization_decimal_as_number(...):
    # line 763-764: 실제로 str 검증
    assert isinstance(rec["min_fund_size"], str)
    assert isinstance(rec["total_committed_sum"], str)
```

---

#### [R5-16] capital=0/None GP 제외 테스트 부재 — [Minor/HIGH] — Priority: P3

**관점**: R6 테스트 품질
**위치**: `deal-mgmt/tests/test_fi_mapping.py`
**점수**: 20 (심각도 20 × 신뢰도 1.0)

**현상**:
SQL 쿼리에서 `total_committed_capital > 0`과 `IS NOT NULL` 조건이 있지만, capital이 정확히 0인 GP 또는 NULL인 GP가 결과에서 제외되는 것을 명시적으로 테스트하는 케이스가 없다.

**참고**: 기존 테스트의 시드 데이터가 모두 양수값이므로 암묵적으로 통과하지만, 명시적 검증이 바람직.

---

#### [R5-17] CLIENT 역할 FI 추천 403 테스트 부재 — [Minor/HIGH] — Priority: P3

**관점**: R2 Security + R6 테스트 품질
**위치**: `deal-mgmt/tests/test_fi_mapping.py`
**점수**: 20 (심각도 20 × 신뢰도 1.0)

**현상**:
`fi_recommendations` 엔드포인트에 `require_write_access()` 의존성이 있어 CLIENT 역할은 403이 반환되어야 하지만, 이를 검증하는 테스트가 없다.

**비교**: `test_client_rbac.py`에서 다른 엔드포인트의 CLIENT 역할 차단은 테스트하고 있으나, FI 추천 엔드포인트는 포함되지 않음.

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | 스키마 확장 (min_fund_size, match_reason) | ✅ 완료 | `schemas/pef_registry.py:33-44` — 2필드 + serializer |
| 2 | 알고리즘 재작성 (날짜필터+프로젝트제외+GP그룹핑+범위필터) | ✅ 완료 | `routers/pef_registry.py:56-175` — 전체 재작성 |
| 3 | 테스트 11개 | ✅ 초과 달성 (26개) | `tests/test_fi_mapping.py` — 26/26 PASS |
| 4 | FE 타입 + 훅 (params 추가) | ✅ 완료 | `types/pef_registry.ts`, `hooks/usePefRegistry.ts` |
| 5 | FE 모달 UI (min_fund_size, match_reason 표시) | ✅ 완료 | `FIRecommendModal.tsx` — NaN guard + allSettled |

**계획 외 추가 구현**:
- `PefCountOut` 스키마 (count 엔드포인트용)
- 배수 역전 검증 (422)
- equal multipliers 경계 테스트
- 직렬화 검증 테스트

---

## Cross-Agent Dedup

| 중복 발견 | Agent | 병합 결과 |
|----------|-------|---------|
| PEF 전체 메모리 로딩 | Agent 1 + Agent 2 | → Info로 통합 (기존 R4-06과 동일, 의도적 스킵) |
| 라우터 단일 함수 다책임 | Agent 2 + Agent 3 | → R5-06으로 병합 (Moderate/HIGH, 교차 검증됨) |
| 테스트 경계값 미비 | Agent 2 + Agent 3 | → R5-07로 병합 (Moderate/MEDIUM) |

---

## Priority Matrix

### P1 — 스프린트 우선 (2건)
1. [R5-01] [Major/HIGH]: DB 쿼리 예외 미처리 — `pef_registry.py:107-119` (점수: 70)
2. [R5-02] [Major/HIGH]: 성공 경로 로그 부재 — `pef_registry.py` 전체 (점수: 70)

### P2 — 개선 권장 (6건)
1. [R5-03] [Moderate/HIGH]: list/count DB 예외 미처리 — `pef_registry.py:33-55` (점수: 40)
2. [R5-04] [Moderate/HIGH]: FE 에러 상태 코드 미구분 — `usePefRegistry.ts:51` (점수: 40)
3. [R5-05] [Moderate/HIGH]: 에러 로그 컨텍스트 부족 — `pef_registry.py:92-94` (점수: 40)
4. [R5-06] [Moderate/HIGH]: 라우터 5개 책임 혼합 — `pef_registry.py:56-175` (점수: 40, 교차 검증)
5. [R5-07] [Moderate/MEDIUM ⚠️]: 경계값 테스트 미비 — `test_fi_mapping.py` (점수: 24)
6. [R5-08] [Moderate/MEDIUM ⚠️]: 마이그레이션 `__import__` — `052_pef_fund_registry.py` (점수: 24)

### P3 — 저우선 (9건)
1. [R5-09] [Minor/HIGH]: upper_multiplier 10x 허용 — `pef_registry.py:74` (점수: 20)
2. [R5-10] [Minor/HIGH]: match_reason 거래금액 노출 — `pef_registry.py:161-170` (점수: 20)
3. [R5-16] [Minor/HIGH]: capital=0/None 제외 테스트 없음 — `test_fi_mapping.py` (점수: 20)
4. [R5-17] [Minor/HIGH]: CLIENT 403 테스트 없음 — `test_fi_mapping.py` (점수: 20)
5. [R5-11] [Minor/MEDIUM ⚠️]: FE 422 에러 미구분 — `usePefRegistry.ts` (점수: 12)
6. [R5-12] [Minor/MEDIUM ⚠️]: contains() 이스케이프 — `pef_registry.py:116-118` (점수: 12)
7. [R5-13] [Minor/MEDIUM ⚠️]: 프로젝트 키워드 한정 — `pef_registry.py:115` (점수: 12)
8. [R5-14] [Minor/MEDIUM ⚠️]: registration_date 미정규화 — `pef_fund_registry.py:24` (점수: 12)
9. [R5-15] [Minor/MEDIUM ⚠️]: 테스트명 불일치 — `test_fi_mapping.py:730` (점수: 12)

---

## Methodology

- **Agents**: 3 (Security+ErrorHandling+Observability, Performance+Deploy+Dependencies, DomainLogic+TestQuality+CognitiveComplexity)
- **Files scanned**: 8 (routers/pef_registry.py, schemas/pef_registry.py, core/security.py, models/pef_fund_registry.py, tests/test_fi_mapping.py, types/pef_registry.ts, hooks/usePefRegistry.ts, FIRecommendModal.tsx)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Agent간 교차 검증 3건
- **Base review**: R4 (5-agent, 15건 발견, 13건 수정 완료)

## 검증 투명성

### 검증 통계
- 검증한 가설: 31건
- 거부된 가설 (사전 제거): 14건
- 보고된 이슈: 17건
- 거부율: 45%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| R4에서 이미 수정됨 | 5 | JWT 로그, 리턴 타입, Decimal 직렬화 등 |
| 의도적 스킵 (확인됨) | 3 | PEF 메모리 로딩(R4-06), 서비스 분리(R4-15) |
| 반증됨 | 3 | "인증 누락" → `Depends(require_write_access())` 확인 |
| 범위 외 | 2 | Docker/인프라 관련 |
| 신뢰도 불충분 | 1 | 증거 약함 |
