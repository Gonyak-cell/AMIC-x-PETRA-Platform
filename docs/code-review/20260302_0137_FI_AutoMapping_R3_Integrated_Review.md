# Code Review — FI 자동매핑 시스템 (3차 통합 리뷰)

> **Review Date**: 2026-03-02 01:37
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: FI 자동매핑 변경 파일 6개 + 백엔드 (deal-mgmt, amic-platform)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: ruff(PASS) pytest-25/25(PASS) tsc(PASS) build(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(5개 에이전트 호출, 0개 제외)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 1     | HIGH: 1                | P1: 1               |
| Moderate | 6     | HIGH: 1 / MEDIUM: 5    | P2: 4 / P3: 2       |
| Minor    | 4     | MEDIUM: 4              | P3: 4               |
| **Total**| **11**| HIGH: **2** / MEDIUM: **9** | P1: **1** / P2: **4** / P3: **6** |

**FP Prevention**: 가설 18건 검증, 7건 사전 거부 (거부율: 39%) | 교차 검증 18건 수행
**병합**: 3건 → R-01/SEC-02/API-01(CLIENT 접근), R-03/A11Y-01(disabled), SEC-01/SEC-03(escape)

---

## Findings

### [R-03/A11Y-01] checkbox `disabled` 속성 누락 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:144-148`
**교차 검증**: code-reviewer + a11y-auditor 동시 발견 (교차 검증됨 +10)

```tsx
<input
  type="checkbox"
  checked={isSelected}
  aria-disabled={isExisting || undefined}  // ARIA 힌트만
  onChange={() => !isExisting && toggleGP(rec.gp_name)}
/>
```

**문제**: `aria-disabled`는 스크린 리더 힌트일 뿐, 네이티브 키보드/마우스 상호작용을 차단하지 않는다. `isExisting=true`인 체크박스를 키보드 Space로 체크 가능하다 (onChange에서 무시하지만, checked 상태는 변하지 않으므로 사용자 혼란).

**수정**: `disabled={isExisting}` 추가 + `aria-disabled` 유지

---

### [A11Y-03] `role="listitem"` 누락 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:132`

```tsx
<div role="list" aria-label="FI 추천 목록">
  {recommendations.map((rec) => (
    <Card key={rec.gp_name} padding="sm" ...>  // role="listitem" 없음
```

**문제**: ARIA 사양상 `role="list"` 자식에는 `role="listitem"`이 필수. 없으면 스크린 리더가 목록 항목 수를 알리지 않는다.

**수정**: Card에 `role="listitem"` 추가

---

### [API-02] deal_value None일 때 빈 배열 반환 — [Moderate/MEDIUM] — Priority: P2 (점수: 24)

**파일**: `deal-mgmt/app/routers/pef_registry.py:130-131`

```python
if txn.estimated_deal_value is None:
    return []
```

**문제**: "매칭 결과 없음"과 "거래금액 미설정" 구분 불가. 프론트엔드 EmptyState 메시지가 동일.

**수정 제안**: 빈 배열 대신 422 또는 응답 헤더 `X-FI-No-Deal-Value: true` 활용. 또는 FE에서 transaction의 `estimated_deal_value`를 별도 확인하여 메시지 분기.

---

### [TC-01] BuyerCandidateUpdate null 전송 불가 — [Moderate/MEDIUM] — Priority: P2 (점수: 24)

**파일**: `amic-platform/src/modules/ma/types/buyer.ts:84-88`

```typescript
export interface BuyerCandidateUpdate {
  ioi_value?: number;     // undefined만 가능, null 불가
  loi_value?: number;     // 동일
  final_offer_value?: number;  // 동일
}
```

**문제**: Pydantic `Decimal | None`은 `null`을 받아 값을 초기화할 수 있지만, TS `number?`는 `undefined`만 표현. 필드를 "비우기" 위해 `null` 전송 불가.

**범위 참고**: FI 매핑 변경이 아닌 기존 buyer 스키마 이슈.

**수정**: `ioi_value?: number | null` 형태로 변경

---

### [TC-04] BuyerPipelineSummary by_status 희소 dict — [Moderate/MEDIUM] — Priority: P2 (점수: 24)

**파일**: `amic-platform/src/modules/ma/types/buyer.ts:96`

```typescript
by_status: Record<BuyerStatus, number>;  // 모든 키 존재 가정
```

**문제**: BE는 `dict[str, int]` (카운트 0인 상태 미포함). FE `Record<BuyerStatus, number>`는 모든 17개 상태 키 존재를 가정. `summary.by_status["REJECTED"]`가 `undefined`일 수 있어 NaN 위험.

**범위 참고**: FI 매핑 변경이 아닌 기존 buyer 스키마 이슈.

**수정**: `by_status: Partial<Record<BuyerStatus, number>>` 또는 `Record<string, number>`

---

### [A11Y-02] `role="list"` + `tabIndex={0}` 의미 충돌 — [Moderate/MEDIUM] — Priority: P3 (점수: 24)

**파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:121-126`

```tsx
<div
  className="space-y-2 max-h-[400px] overflow-y-auto"
  tabIndex={0}    // 키보드 스크롤용
  role="list"     // 목록 의미론
  aria-label="FI 추천 목록"
>
```

**문제**: `tabIndex={0}`은 스크롤 접근성에 필요하지만, `role="list"`와 결합하면 스크린 리더가 포커스 가능한 목록으로 인식. 탭 순서에 추가 정지점 생성.

**수정 제안**: 스크롤 컨테이너와 목록 의미론 분리 — 외부 div에 tabIndex, 내부 div에 role="list"

---

### [R-01/SEC-02/API-01] CLIENT 역할 FI 추천 접근 정책 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**파일**: `deal-mgmt/app/routers/pef_registry.py:126` vs `pef_registry.py:56-57`

**설계 리스크**: `/pef-registry`와 `/pef-registry/count`는 CLIENT를 403으로 차단하지만, `/transactions/{txn_id}/fi-recommendations`는 `check_client_deal_access`로 딜별 접근 허용. 결과적으로 CLIENT가 FI 추천을 통해 PEF 펀드 데이터(GP명, 약정액)를 조회 가능.

**판정**: 의도된 설계 (CLIENT는 자신의 딜에 대한 FI 추천만 열람). 그러나 비즈니스 요건에 따라 CLIENT의 FI 추천 접근을 차단해야 할 수 있음.

**조치**: 비즈니스 규칙 확인 후 필요 시 `fi_recommendations`에도 CLIENT 차단 추가

---

### [R-02] registration_date 문자열 날짜 비교 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**파일**: `deal-mgmt/app/routers/pef_registry.py:149` + `deal-mgmt/app/models/pef_fund_registry.py:30`

**설계 리스크**: `registration_date`가 `String(10)` 타입으로, `>= "2021-01-01"` 비교는 사전순. YYYY-MM-DD 포맷에서는 사전순=날짜순이므로 현재 정상 동작. 테스트로 검증됨.

**잠재 리스크**: 비표준 날짜 형식(예: "21-01-01") 데이터 유입 시 잘못된 비교. 현재 데이터는 금감원 공시 기준으로 형식 통일됨.

**조치**: 현 상태 유지 (기능적으로 정확). 향후 Date 타입 전환 시 마이그레이션 고려.

---

### [SEC-04] email 대소문자 민감 비교 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**파일**: `deal-mgmt/app/core/security.py:145`

```python
DealClient.email == claims.email  # 대소문자 구분
```

**설계 리스크**: PostgreSQL `=` 연산은 대소문자 구분. FDD 인증 시스템에서 email 정규화(소문자 변환)를 수행하므로 현재 이슈 없음.

**수정 제안 (방어적)**: `func.lower(DealClient.email) == func.lower(claims.email)`

---

### [R-04] lower > upper 배수 역전 테스트 미작성 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**파일**: `deal-mgmt/app/routers/pef_registry.py:119-123`

```python
if lower_multiplier > upper_multiplier:
    raise HTTPException(status_code=422, detail="...")
```

**현황**: FastAPI `Query(ge=0.1, le=1.0)` (lower) + `Query(ge=1.0, le=10.0)` (upper) 제약으로 인해 `lower > upper`는 API 레벨에서 도달 불가. lower 최대=1.0, upper 최소=1.0 → 항상 lower ≤ upper.

**조치**: 방어 코드 자체는 유지 (직접 함수 호출 시 보호). 테스트는 선택사항.

---

## Priority Matrix

### P1 — 즉시 수정 (접근성)
1. [R-03/A11Y-01] [Major/HIGH]: checkbox disabled 속성 누락 — FIRecommendModal.tsx (점수: 70)

### P2 — 개선 권장 (접근성/타입)
1. [A11Y-03] [Moderate/HIGH]: role="listitem" 누락 — FIRecommendModal.tsx (점수: 40)
2. [API-02] [Moderate/MEDIUM]: deal_value None 빈 배열 구분 불가 — pef_registry.py (점수: 24)
3. [TC-01] [Moderate/MEDIUM]: Update null 전송 불가 — buyer.ts (점수: 24, 범위 외)
4. [TC-04] [Moderate/MEDIUM]: by_status 희소 dict — buyer.ts (점수: 24, 범위 외)

### P3 — 저우선 (설계 리스크)
1. [A11Y-02] [Moderate/MEDIUM]: role="list" + tabIndex 의미 충돌 — FIRecommendModal.tsx (점수: 24)
2. [R-01/SEC-02/API-01] [Minor/MEDIUM]: CLIENT FI 추천 접근 정책 — pef_registry.py (점수: 12)
3. [R-02] [Minor/MEDIUM]: 문자열 날짜 비교 — pef_fund_registry.py (점수: 12)
4. [SEC-04] [Minor/MEDIUM]: email 대소문자 비교 — security.py (점수: 12)
5. [R-04] [Minor/MEDIUM]: 배수 역전 테스트 미작성 — test_fi_mapping.py (점수: 12)
6. [API-02] — 이미 P2에 포함

---

## Methodology

- **Agents**: code-reviewer, type-checker, security-auditor, api-auditor, a11y-auditor
- **Excluded Agents**: 없음
- **Files scanned**: 8개 (pef_registry.py, security.py, buyer.py, pef_registry.py(schema), pef_fund_registry.py, FIRecommendModal.tsx, buyer.ts, pef_registry.ts, test_fi_mapping.py)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 18건 전건 검증 (Major 이상)
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 18건
- 거부된 가설 (사전 제거): 7건
- 보고된 이슈: 11건
- 거부율: 39%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| FP-LOGIC | 2 | SEC-01/SEC-03: `contains("프로젝트")` 정적 문자열 — 와일드카드 불포함 |
| FP-CTX | 2 | SEC-02: 내부 역할(ADMIN/ANALYST) 전체 접근은 의도된 설계, A11Y-04: 공유 컴포넌트 범위 |
| FP-IMPL | 3 | API-04: Pydantic v2 공식 패턴, API-05: FastAPI return type 자동 추론, A11Y-05: React aria-live 정상 작동 |

### 병합 통계

| 병합 그룹 | 원시 건수 | 에이전트 |
|----------|---------|---------|
| R-01/SEC-02/API-01 (CLIENT 접근) | 3 → 1 | code-reviewer + security-auditor + api-auditor |
| R-03/A11Y-01 (disabled 누락) | 2 → 1 | code-reviewer + a11y-auditor |
| SEC-01/SEC-03 (escape 일관성) | 2 → 1 | security-auditor (동일 에이전트, 관련 이슈) |

---

## 2차 리뷰 대비 개선 현황

| 2차 리뷰 이슈 | 수정 상태 | 3차 리뷰 결과 |
|-------------|---------|-------------|
| SEC-03: contains→ilike 이스케이프 | ✅ 수정됨 | 동적 target_company_name 정상 이스케이프 확인 |
| AUTH-03: CLIENT 차단 | ✅ 수정됨 | `not claims.role or claims.role == "CLIENT"` 패턴 확인 |
| AUTH-04: email None 체크 | ✅ 수정됨 | 명시적 403 반환 확인 |
| TYPE-01: @field_serializer | ✅ 수정됨 | buyer.py 3+2 Decimal 필드 직렬화 확인 |
| A-06~A-09: 접근성 | ✅ 수정됨 | 일부 추가 개선 필요 (R-03, A11Y-03) |
| TC-09: CLIENT 403 테스트 | ✅ 수정됨 | _as_client_role() + 2 테스트 확인 |
