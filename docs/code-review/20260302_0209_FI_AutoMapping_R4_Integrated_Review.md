# Code Review — FI Auto-Mapping R4 (13-Perspective Integrated)

> **Review Date**: 2026-03-02 02:09 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: FI 자동매핑 시스템 (9개 파일)
> **Method**: Quality Gates + 5 Parallel Agents + Cross-Verification + Scope Filtering
> **Quality Gates**: ruff(PASS) pytest-26/26(PASS) tsc(PASS)
> **Review Round**: 4차 (누적: R1→29건 수정, R2→11건 수정, R3→11건 수정)

## Review Scope

| # | 파일 | 유형 |
|---|------|------|
| 1 | `deal-mgmt/app/routers/pef_registry.py` | BE 라우터 |
| 2 | `deal-mgmt/app/core/security.py` | BE 인증/인가 |
| 3 | `deal-mgmt/app/schemas/pef_registry.py` | BE 스키마 |
| 4 | `deal-mgmt/app/schemas/buyer.py` | BE 스키마 |
| 5 | `deal-mgmt/app/models/pef_fund_registry.py` | BE 모델 |
| 6 | `deal-mgmt/tests/test_fi_mapping.py` | 테스트 (26개) |
| 7 | `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx` | FE 모달 |
| 8 | `amic-platform/src/modules/ma/types/pef_registry.ts` | FE 타입 |
| 9 | `amic-platform/src/modules/ma/types/buyer.ts` | FE 타입 |

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2 | HIGH: 2 | P0: 2 |
| Major | 1 | HIGH: 1 | P1: 1 |
| Moderate | 3 | HIGH: 3 | P2: 3 |
| Minor | 9 | HIGH: 7 / MEDIUM: 2 | P2: 4 / P3: 5 |
| **Total** | **15** | **HIGH: 13 / MEDIUM: 2** | **P0: 2 / P1: 1 / P2: 7 / P3: 5** |

**FP Prevention**: 가설 39건 검증, 24건 사전 거부 (거부율: 62%)
**Cross-Verification**: Critical + Major 3건 수행, 3건 CONFIRMED

---

## Findings

### [R4-01] buyer.ts BuyerCandidate Decimal 필드 타입 불일치 (BE `str` ↔ FE `number`) — [Critical/HIGH] — Priority: P0 (점수: 110)

**교차 검증됨**: code-reviewer(R4-01) + type-checker(TC-05)

- **File**: `amic-platform/src/modules/ma/types/buyer.ts:48-52`
- **BE Code** (`deal-mgmt/app/schemas/buyer.py:38-41`):
  ```python
  @field_serializer("ioi_value", "loi_value", "final_offer_value")
  @classmethod
  def _serialize_decimal(cls, v: Decimal | None) -> str | None:
      return str(v) if v is not None else None
  ```
- **FE Code** (`buyer.ts:48-52`):
  ```typescript
  ioi_value: number | null;      // ❌ BE는 str | None 반환
  loi_value: number | null;      // ❌
  final_offer_value: number | null;  // ❌
  ```
- **Issue**: BE `BuyerCandidateOut`의 `@field_serializer`가 Decimal을 `str`로 직렬화. 실제 API 응답은 `"1500.0000"` (문자열)이지만 FE 타입은 `number`를 기대. `ioi_value * 100` 같은 산술 연산 시 `string * number → NaN`. 동일 패턴의 `PefFund.total_committed_capital`은 이미 `string | null`로 올바르게 선언됨.
- **Fix**: `ioi_value: string | null`, `loi_value: string | null`, `final_offer_value: string | null`로 변경. `BuyerCandidateUpdate` (lines 84/86/88)도 동일 적용.

---

### [R4-02] Card 컴포넌트가 `role="listitem"` prop을 DOM에 전달하지 않음 — [Critical/HIGH] — Priority: P0 (점수: 100)

- **File**: `amic-platform/src/components/ui/Card.tsx:6-18` + `FIRecommendModal.tsx:135`
- **Card.tsx**:
  ```typescript
  export interface CardProps {
    title?: string;
    // ... role 미포함
    className?: string;
    onClick?: React.MouseEventHandler<HTMLDivElement>;
  }
  export function Card({ title, ..., className, onClick }: CardProps) {
    return <div className={cn(...)} onClick={onClick}> // ...rest spread 없음
  ```
- **FIRecommendModal.tsx:135**:
  ```tsx
  <Card key={rec.gp_name} role="listitem" padding="sm" ...>
  ```
- **Issue**: `CardProps`에 `role`이 없고, Card 함수가 `...rest`를 spread하지 않으므로 `role="listitem"`이 DOM `<div>`에 도달하지 않음. R3에서 추가한 `role="listitem"` 수정이 실제로 작동하지 않아 `role="list"` / `role="listitem"` 시맨틱 구조가 깨진 상태. tsc는 React 19 타입에서 이를 잡지 않음 (검증됨: `tsc --noEmit` 0 errors).
- **WCAG**: 1.3.1 Info and Relationships (Level A), 4.1.2 Name, Role, Value (Level A)
- **Fix**: Card 컴포넌트에서 rest props를 전달하도록 수정:
  ```typescript
  export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    // ... 기존 props
  }
  export function Card({ title, ..., className, onClick, ...rest }: CardProps) {
    return <div {...rest} className={cn(...)} onClick={onClick}>
  ```

---

### [R4-03] buyer.ts BuyerPipelineSummary Decimal 필드 동일 타입 불일치 — [Major/HIGH] — Priority: P1 (점수: 80)

**교차 검증됨**: code-reviewer(R4-02) + type-checker(TC-06)

- **File**: `amic-platform/src/modules/ma/types/buyer.ts:98-99`
- **BE Code** (`buyer.py:105-108`):
  ```python
  @field_serializer("avg_ioi_value", "avg_loi_value")
  @classmethod
  def _serialize_decimal(cls, v: Decimal | None) -> str | None:
      return str(v) if v is not None else None
  ```
- **FE Code**:
  ```typescript
  avg_ioi_value: number | null;   // ❌ BE는 str | None 반환
  avg_loi_value: number | null;   // ❌
  ```
- **Fix**: `avg_ioi_value: string | null`, `avg_loi_value: string | null`로 변경.

---

### [R4-04] `formatBillion` NaN 가드 부재 — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **File**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:83-87`
- **Code**:
  ```typescript
  const formatBillion = (v: string | number) => {
    const n = typeof v === "string" ? parseFloat(v) : v;
    if (n >= 10000) return `${(n / 10000).toFixed(1)}조`;
    return `${n.toLocaleString()}억`;
  };
  ```
- **Issue**: `parseFloat("")` → `NaN`, `NaN >= 10000` → `false` → `"NaN억"` 렌더링. 현재 호출 지점(`min_fund_size`, `total_committed_sum`)에서는 항상 유효한 값이지만, 방어 로직 필요.
- **Fix**: `if (isNaN(n) || n === 0) return "—";` 가드 추가.

---

### [R4-05] `handleAdd` 순차 호출 시 부분 성공 UX — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **File**: `FIRecommendModal.tsx:56-81`
- **Issue**: for 루프로 GP를 순차 추가하므로 (1) 중간 실패 시 성공/실패 혼합 상태, (2) 5개+ GP 추가 시 UX 느림. 부모 컴포넌트의 buyers 쿼리 자동 리페치 여부에 따라 모달 재열기 시 이미 추가된 GP를 "추가됨"으로 표시하지 못할 수 있음.
- **Fix**: `Promise.allSettled`로 병렬 처리 고려. 또는 부모의 쿼리 무효화 확인.

---

### [R4-06] `fi_recommendations` 전체 PEF 레코드 메모리 로딩 — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **File**: `deal-mgmt/app/routers/pef_registry.py:163`
- **Code**: `pefs = list((await db.execute(q)).scalars().all())`
- **Issue**: 현재 1,137건은 문제 없으나, SQL LIMIT 없이 전체 로딩. 데이터 증가 시 리스크.
- **Fix**: 현재 유지 가능. 장기적으로 SQL GROUP BY + MIN() 또는 안전 LIMIT 추가 고려.

---

### [R4-07] `_apply_search_filter` 타입 힌트 누락 — [Minor/HIGH] — Priority: P2 (점수: 30)

**교차 검증됨**: code-reviewer(R4-04) + type-checker(TC-07)

- **File**: `deal-mgmt/app/routers/pef_registry.py:35`
- **Code**: `def _apply_search_filter(q, search: str):`
- **Fix**: `def _apply_search_filter(q: Select, search: str) -> Select:`

---

### [R4-08] `_format_billions` Decimal 나눗셈 정밀도 — [Minor/HIGH] — Priority: P2 (점수: 30)

**교차 검증됨**: code-reviewer(R4-05) + api-auditor(API-09)

- **File**: `deal-mgmt/app/routers/pef_registry.py:82-86`
- **Code**: `return f"{value / 10000:.1f}조"` — `10000`은 int 리터럴
- **Fix**: `Decimal("10000")` 사용하여 Decimal 정밀도 유지.

---

### [R4-09] `security.py` `require_role`/`require_write_access` 반환 타입 미선언 — [Minor/HIGH] — Priority: P2 (점수: 30)

**교차 검증됨**: type-checker(TC-12 + TC-13)

- **File**: `deal-mgmt/app/core/security.py:89,110`
- **Fix**: 반환 타입 `Callable[..., Coroutine[Any, Any, JWTClaims]]` 추가.

---

### [R4-10] `buyer.py` `extra_data` bare `dict` 타입 — [Minor/HIGH] — Priority: P2 (점수: 30)

**교차 검증됨**: type-checker(TC-08 + TC-09)

- **File**: `deal-mgmt/app/schemas/buyer.py:34,56,60,87,91`
- **Fix**: `dict[str, Any]`로 변경.

---

### [R4-11] `pef_fund_count` endpoint `response_model` 미선언 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **File**: `deal-mgmt/app/routers/pef_registry.py:66`
- **Issue**: 다른 2개 엔드포인트는 `response_model` 명시, count만 누락. OpenAPI 문서 일관성.
- **Fix**: `PefCountOut` 스키마 생성 및 `response_model=PefCountOut` 적용.

---

### [R4-12] 배수 역전 검증 도달 불가 (dead code) — [Minor/HIGH] — Priority: P3 (점수: 20)

- **File**: `deal-mgmt/app/routers/pef_registry.py:119-123`
- **Issue**: `lower_multiplier ≤ 1.0`, `upper_multiplier ≥ 1.0`이므로 `lower > upper` 조건이 절대 참이 될 수 없음. Query validation이 먼저 적용됨.
- **Fix**: 방어 코드로 유지하되, 주석으로 "safety net" 명시 권장.

---

### [R4-13] OpenAPI 에러 응답 미선언 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **File**: `deal-mgmt/app/routers/pef_registry.py:89-92`
- **Issue**: 404, 422, 403 에러 시나리오가 `responses=` 파라미터에 명시되지 않음.
- **Fix**: `responses={403: {...}, 404: {...}, 422: {...}}` 추가.

---

### [R4-14] JWT 디코드 실패 시 원본 예외 로깅 없음 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

- **File**: `deal-mgmt/app/core/security.py:79-80`
- **Code**: `except JWTError: raise credentials_exception`
- **Fix**: `logger.debug("JWT decode failed", exc_info=True)` 추가.

---

### [R4-15] 권한 체크 인라인 중복 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

- **File**: `deal-mgmt/app/routers/pef_registry.py:56-57,73-74`
- **Issue**: CLIENT 차단 로직이 2개 엔드포인트에 동일하게 인라인 중복. `require_role()` 의존성 사용 가능.
- **Fix**: `Depends(require_role("ADMIN", "MEMBER"))` 사용으로 중복 제거.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
1. [R4-01] **[Critical/HIGH]**: buyer.ts Decimal 필드 `number | null` → `string | null` 전환 필요 — buyer.ts (점수: 110)
2. [R4-02] **[Critical/HIGH]**: Card `role="listitem"` DOM 미전달 — Card.tsx (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89)
1. [R4-03] **[Major/HIGH]**: BuyerPipelineSummary avg Decimal 타입 불일치 — buyer.ts (점수: 80)

### P2 — 개선 권장 (점수: 30-59)
1. [R4-04] **[Moderate/HIGH]**: formatBillion NaN 가드 — FIRecommendModal.tsx (점수: 40)
2. [R4-05] **[Moderate/HIGH]**: handleAdd 순차 호출 UX — FIRecommendModal.tsx (점수: 40)
3. [R4-06] **[Moderate/HIGH]**: PEF 전체 메모리 로딩 — pef_registry.py (점수: 40)
4. [R4-07] **[Minor/HIGH]**: _apply_search_filter 타입 힌트 — pef_registry.py (점수: 30, 교차검증)
5. [R4-08] **[Minor/HIGH]**: _format_billions Decimal 정밀도 — pef_registry.py (점수: 30, 교차검증)
6. [R4-09] **[Minor/HIGH]**: require_role 반환 타입 — security.py (점수: 30, 교차검증)
7. [R4-10] **[Minor/HIGH]**: bare dict 타입 — buyer.py (점수: 30, 교차검증)

### P3 — 저우선 (점수: <30)
1. [R4-11] **[Minor/HIGH]**: pef_fund_count response_model — pef_registry.py (점수: 20)
2. [R4-12] **[Minor/HIGH]**: dead code (배수 역전 검증) — pef_registry.py (점수: 20)
3. [R4-13] **[Minor/HIGH]**: OpenAPI 에러 응답 — pef_registry.py (점수: 20)
4. [R4-14] **[Minor/MEDIUM]**: JWT 예외 로깅 — security.py (점수: 12)
5. [R4-15] **[Minor/MEDIUM]**: 권한 체크 중복 — pef_registry.py (점수: 12)

---

## 범위 외 관찰 (Security Design Risks)

보안 에이전트가 11건의 관찰을 보고했으나, 모두 FI 매핑 변경 사항이 아닌 기존 코드 패턴임:

| 관찰 | 분류 | 비고 |
|------|------|------|
| `.env` API 키 관리 | 인프라 | gitignore로 보호 중, 코드 리뷰 범위 외 |
| AUTH_ENABLED=False 우회 가능성 | 기존 패턴 | ENV 체크로 방어 중 |
| CLIENT 역할 FI 추천 접근 | 설계 결정 | 3라운드 연속 보고, 의도적 설계 확인 |
| JWT 알고리즘 환경변수 오버라이드 | 기존 설정 | config.py, 별도 보안 리뷰 권장 |
| notes/rejection_reason 길이 무제한 | 기존 스키마 | buyer.py, 별도 태스크 권장 |
| Rate Limiting 미적용 | 아키텍처 | 전체 API 공통, 별도 태스크 권장 |

---

## Methodology

- **Agents**: code-reviewer, type-checker, security-auditor, api-auditor, a11y-auditor
- **Files scanned**: 9
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 3건 — 3건 CONFIRMED
- **Scope filtering**: Security 11건 범위 외 처리 (기존 코드, FI 미관련)

## 검증 투명성

### 검증 통계
- 에이전트 원본 발견: 39건
- 범위 외 거부: 14건 (Security 11 + A11Y 2 + test-only 1)
- 중복 병합: 10건 → 5건
- 보고된 이슈: 15건
- 거부율: 62% (24/39)

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 범위 외 (기존 코드) | 14 | SEC-CRIT-01(.env), SEC-HIGH-01(auth bypass) |
| 중복 병합 | 10→5 | R4-01=TC-05, R4-04=TC-07 등 |
| 이론적 우려 | 1 | A11Y-10 (포커스 트랩 이론적) |

### R3 → R4 개선 추적

| R3 이슈 | R4 상태 | 비고 |
|---------|---------|------|
| R-03/A11Y-01 (checkbox disabled) | ✅ 수정 확인 | disabled + aria-disabled 적용 |
| A11Y-02 (스크롤/리스트 분리) | ✅ 수정 확인 | tabIndex 분리, role="list" 내부 |
| A11Y-03 (role="listitem") | ⚠️ **미작동** | Card가 prop 미전달 (R4-02) |
| API-02 (deal_value None) | ✅ 수정 확인 | HTTPException(422) |
| TC-01 (nullable number) | ⚠️ **방향 오류** | `number | null`이 아닌 `string | null` 필요 (R4-01) |
| TC-04 (Partial Record) | ✅ 수정 확인 | |
| SEC-04 (email case) | ✅ 수정 확인 | func.lower() 적용 |
| R-04 (equal multipliers) | ✅ 수정 확인 | 테스트 추가 |
