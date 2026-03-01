# Code Review — FI 자동매핑 (수정 후 재리뷰)

> **Review Date**: 2026-03-02 01:19 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: FI 자동매핑 시스템 — 29건 수정 후 재검증
> **Method**: Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: ruff(PASS) pytest(23/23 PASS) tsc(PASS) vite-build(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(5개 에이전트 호출, 0개 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 7     | HIGH: 5 / MEDIUM: 2   | P1: 5 / P2: 2       |
| Moderate | 4     | MEDIUM: 4              | P3: 4                |
| **Total**| **11**| HIGH: **5** / MEDIUM: **6** | P1: **5** / P2: **2** / P3: **4** |

**FP Prevention**: 가설 15건 검증, 4건 사전 거부 (거부율: 27%) | 교차 검증 1건 수행 (SEC-03/CONTAIN-01 교차 확인)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 6건 하향 조정 (Major/MEDIUM → P2, Moderate/MEDIUM → P3)

---

## Findings

### [SEC-03] `contains()` LIKE 와일드카드 이스케이프 누락 — [Major/HIGH] — Priority: P1

**점수**: 80 (심각도 70 × 신뢰도 1.0 + 교차검증 보너스 10)

**위치**: [pef_registry.py:155-157](deal-mgmt/app/routers/pef_registry.py#L155-L157)

**문제**: `_apply_search_filter()`는 `%`, `_` 이스케이프를 수행하지만, `fi_recommendations()` 내 `contains()` 호출은 이스케이프 없이 사용된다.

```python
# 안전 (line 37-38): _apply_search_filter
escaped = search.replace("%", r"\%").replace("_", r"\_")
pattern = f"%{escaped}%"
return q.where(PefFundRegistry.pef_name.ilike(pattern, escape="\\"))

# 미이스케이프 (line 155-157): fi_recommendations
q = q.where(~PefFundRegistry.pef_name.contains("프로젝트"))  # 정적 문자열 — 안전
if txn.target_company_name and len(txn.target_company_name) >= 2:
    q = q.where(~PefFundRegistry.pef_name.contains(txn.target_company_name))  # DB 값 — 위험
```

`txn.target_company_name`에 `%` 또는 `_`가 포함되면 LIKE 패턴이 의도와 다르게 동작한다. 예: 기업명 "A%B" → `LIKE '%A%B%'` → 모든 A...B 패턴 매칭.

**영향**: 프로젝트 펀드 제외 로직이 과잉/과소 필터링할 수 있음. 공격 벡터는 아님(DB 값이므로 authorized user가 설정), 하지만 데이터 정확성 영향.

**교차 검증**: code-reviewer(CONTAIN-01) + security-auditor(SEC-03) 양쪽에서 독립 발견 → **CONFIRMED**

**권장 수정**: `contains()` → `~PefFundRegistry.pef_name.ilike(f"%{escaped_name}%", escape="\\")` 패턴 적용

---

### [TYPE-01] `BuyerCandidateOut` Decimal 필드 `field_serializer` 누락 — [Major/HIGH] — Priority: P1

**점수**: 70 (심각도 70 × 신뢰도 1.0)

**위치**: [buyer.py:27,29,31](deal-mgmt/app/schemas/buyer.py#L27-L31), [buyer.py:97-98](deal-mgmt/app/schemas/buyer.py#L97-L98)

**문제**: `pef_registry.py`에서 SCHEMA-01 수정(Decimal → float serializer 추가)이 적용되었으나, 동일 패턴의 `buyer.py` 스키마에는 미적용.

```python
# buyer.py — field_serializer 없음
class BuyerCandidateOut(BaseModel):
    ioi_value: Decimal | None = None    # line 27
    loi_value: Decimal | None = None    # line 29
    final_offer_value: Decimal | None = None  # line 31

class BuyerPipelineSummary(BaseModel):
    avg_ioi_value: Decimal | None = None  # line 97
    avg_loi_value: Decimal | None = None  # line 98
```

Pydantic v2 기본 동작: `Decimal` → JSON 문자열 `"1500.00"`. 프론트엔드에서 `number` 타입 기대 시 타입 불일치.

**확정 근거**:
1. `pef_registry.py:23-26` — 동일 패턴에 `@field_serializer` 이미 적용됨
2. `buyer.py:27,29,31` — Decimal 필드 5개에 serializer 없음
3. Pydantic v2 문서 — Decimal은 기본 JSON string 직렬화
4. 프론트엔드 `buyer.ts` 타입이 `number` 기대

**교차 검증**: type-checker 에이전트 단독 발견 → **CONFIRMED**

---

### [A-06] 스크롤 컨테이너 키보드 접근 불가 — [Major/HIGH] — Priority: P1

**점수**: 70 (심각도 70 × 신뢰도 1.0)

**위치**: [FIRecommendModal.tsx:120](amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx#L120)

**문제**: `max-h-[400px] overflow-y-auto` 스크롤 컨테이너에 `tabIndex`가 없다.

```tsx
<div className="space-y-2 max-h-[400px] overflow-y-auto">
```

`tabIndex={0}`이 없으면 키보드 전용 사용자가 이 영역에 포커스를 줄 수 없어 스크롤이 불가능하다. WCAG 2.1 AA 2.1.1 (Keyboard) 위반.

**권장 수정**: `tabIndex={0}` + `role="list"` + `aria-label="FI 추천 목록"` 추가

---

### [A-07] 상태 전환 스크린 리더 미알림 — [Major/HIGH] — Priority: P1

**점수**: 70 (심각도 70 × 신뢰도 1.0)

**위치**: [FIRecommendModal.tsx:95-117](amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx#L95-L117)

**문제**: 로딩 → 에러/빈 결과/결과 목록 전환이 조건부 렌더링으로 구현되어 있으나, 영속적인 `aria-live` 영역이 없다.

```tsx
{isLoading && (<div className="flex justify-center py-8"><Spinner /></div>)}
{!isLoading && isError && (<EmptyState ... />)}
{!isLoading && recommendations && recommendations.length > 0 && (<div>...</div>)}
```

스크린 리더는 조건부 렌더링으로 나타나는 콘텐츠 변경을 자동 감지하지 못한다. 영속적인 wrapper `<div aria-live="polite">`가 필요하다.

**권장 수정**: 로딩/에러/결과 영역을 하나의 `<div aria-live="polite">` wrapper로 감싸기

---

### [TC-09] CLIENT 역할 403 테스트 부재 — [Major/HIGH] — Priority: P1

**점수**: 70 (심각도 70 × 신뢰도 1.0)

**위치**: [test_fi_mapping.py](deal-mgmt/tests/test_fi_mapping.py) (전체)

**문제**: 23개 테스트 모두 conftest의 ADMIN 모의 JWT를 사용한다. CLIENT 역할이 `list_pef_funds`/`pef_fund_count`에서 403을 받는지 검증하는 테스트가 없다.

```python
# pef_registry.py:56-57 — 테스트되지 않은 분기
if claims.role == "CLIENT":
    raise HTTPException(status_code=403, ...)
```

**권장 수정**: CLIENT 역할 헤더를 사용하는 테스트 2건 추가 (list_pef_funds 403, pef_fund_count 403)

---

### [A-08] 장식용 아이콘 `aria-hidden` 누락 — [Major/MEDIUM] — Priority: P2

**점수**: 42 (심각도 70 × 신뢰도 0.6)

**위치**: [FIRecommendModal.tsx:153,157,161](amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx#L153)

**문제**: `<Building2>`, `<Target>`, `<TrendingUp>` 아이콘이 인접 텍스트("펀드 N개", "최소 X억" 등)의 장식 역할이지만 `aria-hidden="true"`가 없다.

```tsx
<Building2 className="h-3 w-3" />  {/* aria-hidden 없음 */}
```

Lucide 아이콘은 기본적으로 SVG `role="img"`를 가지므로, 스크린 리더가 아이콘을 무의미한 요소로 읽을 수 있다.

**⚠️ MEDIUM 신뢰도**: Lucide React의 실제 aria 기본 동작은 버전에 따라 다를 수 있음.

---

### [A-09] 선택 카운터 `aria-live` 누락 — [Major/MEDIUM] — Priority: P2

**점수**: 42 (심각도 70 × 신뢰도 0.6)

**위치**: [FIRecommendModal.tsx:177](amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx#L177)

**문제**: 체크박스 토글 시 `{selected.size}개 선택됨` 텍스트가 업데이트되지만 `aria-live` 속성이 없어 스크린 리더가 변경을 알리지 않는다.

```tsx
<span className="text-xs text-text-muted">
  {selected.size}개 선택됨
</span>
```

**권장 수정**: `aria-live="polite"` + `aria-atomic="true"` 추가

---

### [AUTH-03] 빈 JWT role 문자열의 CLIENT 체크 우회 — [Moderate/MEDIUM] — Priority: P3

**점수**: 24 (심각도 40 × 신뢰도 0.6)

**위치**: [security.py:85](deal-mgmt/app/core/security.py#L85), [pef_registry.py:56](deal-mgmt/app/routers/pef_registry.py#L56)

**문제**: JWT에 `role` 클레임이 없으면 `role=""` (빈 문자열)이 설정된다. `claims.role == "CLIENT"` 비교는 빈 문자열을 통과시킨다.

**완화 요소**: FDD JWT 발급자가 role을 항상 포함. `require_write_access()`는 `not claims.role` 체크로 빈 역할을 차단. pef_registry는 읽기 전용 엔드포인트만 포함.

**판정**: DESIGN_RISK — 현재는 안전하지만 방어적 코딩 관점에서 개선 가능

---

### [AUTH-04] `claims.email` None 시 우발적 보호 — [Moderate/MEDIUM] — Priority: P3

**점수**: 24 (심각도 40 × 신뢰도 0.6)

**위치**: [security.py:140](deal-mgmt/app/core/security.py#L140)

**문제**: JWT에 email 클레임이 없으면 `claims.email = None`. `check_client_deal_access`에서 `DealClient.email == None` 쿼리는 매칭 레코드가 없을 경우 403을 반환한다.

**판정**: DESIGN_RISK — 결과적으로 안전하지만, `DealClient.email`에 NULL 값이 존재하면 의도치 않은 접근 허용 가능

---

### [MEM-01] 전체 PEF 레코드 메모리 로드 — [Moderate/MEDIUM] — Priority: P3

**점수**: 24 (심각도 40 × 신뢰도 0.6)

**위치**: [pef_registry.py:159](deal-mgmt/app/routers/pef_registry.py#L159)

**문제**: `pefs = list((await db.execute(q)).scalars().all())` — 필터링된 전체 PEF를 메모리에 로드.

**현재 규모**: ~1,137건 (금감원 공시 기준). GP별 그룹핑 + min/sum 계산을 위해 불가피.

**판정**: DESIGN_RISK — 현재 규모에서는 적절. 5,000건 이상으로 증가 시 SQL 집계 함수 전환 검토

---

### [DATA-01] `registration_date` 문자열 비교 취약성 — [Moderate/MEDIUM] — Priority: P3

**점수**: 24 (심각도 40 × 신뢰도 0.6)

**위치**: [pef_registry.py:149](deal-mgmt/app/routers/pef_registry.py#L149)

**문제**: `registration_date`가 `String(10)`이며 날짜 비교가 문자열 `>=`로 수행된다. YYYY-MM-DD 형식이 보장될 때만 정확.

**현재 상태**: 시드 스크립트(`seed_pef_registry.py`)에서 Excel 파싱 시 형식 검증 없이 `str(row[4]).strip()` 사용. FSS 공시 데이터는 일관된 YYYY-MM-DD 형식.

**판정**: DESIGN_RISK — 현재 데이터에서는 안전하나, 시드 스크립트에 형식 검증 추가 권장

---

## False Positive 분석

| ID | 에이전트 | 주장 | 거부 사유 | FP 분류 |
|----|---------|------|----------|---------|
| TC-08 | code-reviewer | 배수 역전 수동 체크 테스트 누락 | `lower_multiplier` [0.1,1.0] × `upper_multiplier` [1.0,10.0] → 역전 불가능. 방어 코드는 도달 불가 | FP-LOGIC |
| CONTRACT-01 | api-auditor | `pef_fund_count` response_model 미지정 | FastAPI 0.100+에서 `-> dict[str, int]` 반환 타입이 response_model로 사용됨 | FP-IMPL |
| DATA-02 | api-auditor | Decimal→float 정밀도 손실 | 한국 PEF 시장 규모(~200조) 기준 최대 7자리. float 15자리 유효숫자 범위 내 | FP-CTX |
| DATA-03 | api-auditor | CLIENT 403/404 오라클 공격 | CLIENT는 미인증 txn에 항상 403 (존재/비존재 동일). 정보 누출 없음 | FP-LOGIC |

---

## Priority Matrix

### P1 — 즉시 수정 (점수: 60+)
1. [SEC-03] [Major/HIGH]: `contains()` 와일드카드 이스케이프 누락 — pef_registry.py:157 (점수: 80, 교차검증됨)
2. [TYPE-01] [Major/HIGH]: BuyerCandidateOut Decimal serializer 누락 — buyer.py:27-31 (점수: 70)
3. [A-06] [Major/HIGH]: 스크롤 컨테이너 키보드 접근 불가 — FIRecommendModal.tsx:120 (점수: 70)
4. [A-07] [Major/HIGH]: 상태 전환 스크린 리더 미알림 — FIRecommendModal.tsx:95-117 (점수: 70)
5. [TC-09] [Major/HIGH]: CLIENT 역할 403 테스트 부재 — test_fi_mapping.py (점수: 70)

### P2 — 개선 권장 (점수: 30-59)
1. [A-08] [Major/MEDIUM ⚠️]: 장식용 아이콘 aria-hidden 누락 — FIRecommendModal.tsx:153 (점수: 42)
2. [A-09] [Major/MEDIUM ⚠️]: 선택 카운터 aria-live 누락 — FIRecommendModal.tsx:177 (점수: 42)

### P3 — 저우선 (점수: <30)
1. [AUTH-03] [Moderate/MEDIUM ⚠️]: 빈 JWT role CLIENT 체크 우회 — security.py:85 (점수: 24)
2. [AUTH-04] [Moderate/MEDIUM ⚠️]: claims.email None 우발적 보호 — security.py:140 (점수: 24)
3. [MEM-01] [Moderate/MEDIUM ⚠️]: 전체 PEF 메모리 로드 — pef_registry.py:159 (점수: 24)
4. [DATA-01] [Moderate/MEDIUM ⚠️]: registration_date 문자열 비교 — pef_registry.py:149 (점수: 24)

---

## Methodology

- **Agents**: code-reviewer, type-checker, api-auditor, security-auditor, a11y-auditor (5개)
- **Excluded Agents**: 없음
- **Files scanned**: 7개 (pef_registry.py 라우터/스키마, buyer.py, security.py, FIRecommendModal.tsx, usePefRegistry.ts, test_fi_mapping.py)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: SEC-03/CONTAIN-01 (2개 에이전트 독립 발견)
- **Backend availability**: deal-mgmt(available)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 15건
- 거부된 가설 (사전 제거): 4건
- 보고된 이슈: 11건
- 거부율: 27%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| FP-LOGIC | 2 | TC-08: FastAPI Query 범위 제약으로 배수 역전 도달 불가; DATA-03: CLIENT 항상 403 |
| FP-IMPL | 1 | CONTRACT-01: FastAPI 반환 타입 → 암시적 response_model |
| FP-CTX | 1 | DATA-02: 한국 PEF 시장 규모에서 float 정밀도 충분 |

---

## 이전 리뷰(29건) 대비 개선 현황

| 이전 이슈 | 상태 | 비고 |
|----------|------|------|
| SCHEMA-01: Decimal 직렬화 | ✅ 해결 | field_serializer 추가, 테스트 검증 |
| PERF-02: registration_date 인덱스 | ✅ 해결 | 모델 + 마이그레이션 050 |
| AUTH-02: 인증 순서 | ✅ 해결 | check_client_deal_access → get_transaction 순서 |
| LOG-002: 입력 검증 순서 | ✅ 해결 | DB 쿼리 전 배수 역전 체크 |
| SEC-01: 검색 SQL Injection | ✅ 해결 | ilike + escape 패턴 적용 |
| API-01: 검색 파라미터 | ✅ 해결 | search + max_length 추가 |
| VAL-01: 입력 제한 | ✅ 해결 | ge/le 범위 적용 |
| ERR-001: 음수/0 로깅 | ✅ 해결 | logger.info 추가 |
| DI-002: 변수 분리 목적 | ✅ 해결 | 주석 추가 |
| U-02: 비활성 대비 | ✅ 해결 | opacity-70 + bg-bg-muted |
| U-04: 실패 시 모달 닫기 | ✅ 해결 | added > 0 조건 |
| A-01: 중복 aria-label | ✅ 해결 | 제거 |
| A-03: disabled → aria-disabled | ✅ 해결 | 패턴 전환 |
| SCHEMA-03: FE limit 파라미터 | ✅ 해결 | FIRecommendationParams.limit 추가 |
| TC-01~07: 테스트 확장 | ✅ 해결 | 11 → 23개 |
| **새로 발견 (P1)** | **5건** | SEC-03, TYPE-01, A-06, A-07, TC-09 |
| **새로 발견 (P2)** | **2건** | A-08, A-09 |
| **새로 발견 (P3)** | **4건** | AUTH-03, AUTH-04, MEM-01, DATA-01 |
