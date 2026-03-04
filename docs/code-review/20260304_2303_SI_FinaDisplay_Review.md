# Code Review — SI 재무정보 표시 개선

> **Review Date**: 2026-03-04 23:03 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: SI 자동매핑 재무 폴백 테이블 — 3개 필드 + 부채비율 + 기준일자 추가 (3 files, +21 lines)
> **Method**: Review Gates + Quality Gates + Verified Single-Agent Review
> **Quality Gates**: ruff(PASS) tsc(PASS) eslint(PASS)
> **Review Gates**: Backend(deal-mgmt available) Agent-Filtering(code-reviewer 1개 호출)

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| Critical | 0     | —          | —        |
| Major    | 0     | —          | —        |
| Moderate | 1     | HIGH: 1    | P2: 1    |
| Minor    | 3     | HIGH: 2 / MEDIUM: 1 | P3: 3 |
| **Total**| **4** | HIGH: **3** / MEDIUM: **1** | P2: **1** / P3: **3** |

**FP Prevention**: 가설 6건 검증, 2건 사전 거부 (거부율: 33%)
**Priority Calculation**: 신뢰도 가중 우선순위 적용 — MEDIUM 1건 하향

---

## Findings

### [M-1] SI 매핑 목록 API에서 기준일자가 항상 null — [Moderate/HIGH] — Priority: P2 (점수: 40)

**위치**: `deal-mgmt/app/services/si_mapping_service.py:620-629`

**증거**:
```python
q = select(SICompany).options(
    defer(SICompany.jurir_no),
    defer(SICompany.corp_code),
    defer(SICompany.fina_base_date),       # ← defer (로딩 제외)
    defer(SICompany.fina_report_code),
    defer(SICompany.fina_report_name),
    defer(SICompany.fina_stat_synced_at),
    defer(SICompany.corp_basic_synced_at),
    defer(SICompany.corp_basic_base_date),  # ← defer (로딩 제외)
)
```

`_load_filtered_companies`에서 두 기준일자 필드를 `defer`로 제외. 이 함수로 로딩된 ORM 객체에서 `SICompanyOut.model_validate()`를 호출하면 `fina_base_date`와 `corp_basic_base_date`가 `None`으로 직렬화됨.

**영향**: SIDetailPanel은 딥다이브 API(`get_deep_dive`)를 사용하며, 딥다이브에서는 defer 없이 전체 컬럼을 로딩하므로 **현재 UI에서 실제 문제 없음**. 향후 목록 화면에서 기준일자 표시 시 주의 필요.

**권장**: 코드 주석 또는 향후 확장 시 defer 목록에서 제외 검토.

---

### [m-1] `parseFloat(company.debt_ratio).toFixed(2)` NaN 방어 부재 — [Minor/HIGH] — Priority: P3 (점수: 20)

**위치**: `amic-platform/src/modules/ma/components/si-mapping/SIDetailPanel.tsx:337`

**증거**:
```tsx
{company.debt_ratio != null && (
  <p className="text-xs text-text-secondary">
    부채비율: {parseFloat(company.debt_ratio).toFixed(2)}%
  </p>
)}
```

`debt_ratio != null` 체크는 `null`/`undefined`만 거름. BE `_serialize_decimal`이 `str(v)`를 반환하므로 빈 문자열 가능성은 사실상 없으나, 방어적 프로그래밍 관점에서 `isNaN` 체크 추가 가능.

**현실적 위험**: 극히 낮음 (Decimal→str 파이프라인상 빈 문자열 불가).

---

### [m-2] `formatDate` 비표준 입력 처리 — [Minor/HIGH] — Priority: P3 (점수: 20)

**위치**: `amic-platform/src/modules/ma/components/si-mapping/SIDetailPanel.tsx:301`

DB `fina_base_date`는 `String(8)` 타입으로 YYYYMMDD 형식 보장. `formatDate`도 `length !== 8`이면 원본 반환하는 안전 폴백 보유.

**판정**: 정상 동작, 추가 조치 불필요.

---

### [m-3] `row.value!` non-null assertion — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**위치**: `amic-platform/src/modules/ma/components/si-mapping/SIDetailPanel.tsx:328`

`.filter((row) => row.value != null)` 후 `row.value!` 사용. 런타임 안전하나 TypeScript narrowing이 filter 콜백을 추적하지 못함. **기존 코드 패턴과 동일** — 일관성 유지.

---

## Priority Matrix

### P2 — 개선 권장 (점수: 30-59)
1. [M-1] [Moderate/HIGH]: 목록 API defer로 기준일자 null — si_mapping_service.py (점수: 40)

### P3 — 저우선 (점수: <30)
1. [m-1] [Minor/HIGH]: parseFloat NaN 방어 — SIDetailPanel.tsx (점수: 20)
2. [m-2] [Minor/HIGH]: formatDate 비표준 입력 — SIDetailPanel.tsx (점수: 20)
3. [m-3] [Minor/MEDIUM ⚠️]: non-null assertion — SIDetailPanel.tsx (점수: 12, 신뢰도 하향)

## 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1 | SICompanyOut에 fina_base_date, corp_basic_base_date 추가 | ✅ | si_mapping.py:80-81 |
| 2 | SICompany TS에 동일 2필드 추가 | ✅ | si_mapping.ts:36-37 |
| 3 | seededRows에 pretax_income, capital_amount 추가 | ✅ | SIDetailPanel.tsx:281-285 |
| 4 | 부채비율 % 별도 표시 | ✅ | SIDetailPanel.tsx:335-338 |
| 5 | 기준일자 표시 (fina_base_date → formatDate, revenue_year 폴백) | ✅ | SIDetailPanel.tsx:299-304 |
| 6 | ruff + tsc 검증 | ✅ | 0 errors |

## 품질 게이트 상태

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| ruff check + format | ✅ PASS | 정합성 자동 검증됨 |
| tsc --noEmit | ✅ PASS | 타입 안전성 자동 검증됨 |
| eslint | ✅ PASS | 코드 품질 자동 검증됨 |

## Methodology

- Agents: code-reviewer
- Excluded Agents: type-checker, api-auditor, security-auditor, a11y-auditor (변경 범위 소규모)
- Files scanned: 3
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- Cross-verification: 건너뜀 (Critical/Major 0건)
- Backend availability: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 6건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 4건
- 거부율: 33%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | "formatDate가 위험하다" → 8자리 폴백 확인됨 |
| 범위 외 | 1 | 딥다이브 DART API 호출 안정성 — 기존 코드, 변경 없음 |
