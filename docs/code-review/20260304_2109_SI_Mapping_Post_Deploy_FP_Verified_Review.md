# Code Review — SI/VC/FI 매핑 배포 후 허위양성 검증 강화 리뷰

> **Review Date**: 2026-03-04 21:09 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: SI/VC/FI 매핑 BE 4파일 + FE 9파일
> **Method**: Quality Gates + 4-Agent Parallel Review (×5 에이전트) + 전체 이슈 교차 검증
> **Quality Gates**: ruff(✅) tsc(✅)
> **Protocol**: VCP v1.1 + Self-Challenge (SC-1~SC-6) + FP Blacklist (18항목) + 전수 교차 검증

## 배경

이전 리뷰(R1~R12 + 13관점 통합 + 배포 후 리뷰)에서 Critical=0, CONFIRMED 수정 0건.
사용자 요청: **"허위 리뷰 반드시 검증"** — 모든 이슈에 대해 오케스트레이터가 직접 Read로 교차 검증.

---

## Summary

| Severity | Count | Confidence Distribution |
|----------|-------|------------------------|
| Critical | 0     | — |
| Major    | 0     | — |
| Moderate | 3     | HIGH: 3 |
| Low      | 3     | HIGH: 2 / MEDIUM: 1 |
| Minor    | 0     | — |
| **Total**| **6** | HIGH: **5** / MEDIUM: **1** |

**보안**: 0건 (8개 항목 전체 PASS + 17개 엣지케이스 PASS)
**API 계약**: 0건 (10/10 엔드포인트 정합, 20+ 스키마 정합)
**수정 대상**: 0건 (Critical/Major+HIGH+CONFIRMED = 0)

---

## 허위양성 방지 투명성

### 에이전트 운용

| 에이전트 | 검토 이슈 | 보고 | 거부 | 거부율 |
|---------|----------|------|------|--------|
| BE 심층 #1 | 9 | 1 | 8 | 89% |
| BE 심층 #2 | 7 | 0 | 7 | 100% |
| FE 심층 #1 | 11 | 3 | 8 (SC) + 3 (FP Blacklist) | 79% |
| FE 심층 #2 | 12 | 3 | 9 (SC) + 3 (FP Blacklist) | 75% |
| 통합 | 10 endpoints | 0 | — | — |
| 보안+엣지 | 8+17 | 0 | — | — |
| **합계** | **39+ 후보** | **7 (중복 제거 후 6)** | **38+** | **~85%** |

### 오케스트레이터 교차 검증 (전수)

| 이슈 ID | 에이전트 보고 | 교차 검증 | 판정 |
|---------|-------------|----------|------|
| BE-R1 | N+1 쿼리 | Read 968-984행 확인 | **CONFIRMED** |
| FE-I1 | 탭 전환 선택 초기화 | Read 230-233행 확인 | **DESIGN_RISK** |
| FE-I2 | partial success 미닫힘 | Read 95-110행 확인 | **CONFIRMED** |
| FE-I3 | Escape 이벤트 버블링 | Read 91-93행 + 64-76행 확인 | **CONFIRMED** |
| FE-R5 | useMutation 미사용 | FP Blacklist #18 | 보고만 |
| FE-R3 | th scope 누락 | FP Blacklist #17 | 보고만 |

### SC 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| SC-2 반증됨 | 8 | "button이 label 바깥에 있음", "expression index 존재 확인" |
| SC-4 맥락 무관 | 12 | "asyncio 단일 스레드로 경합 불가", "읽기 전용이라 불일치 없음" |
| SC-5 영향 미미 | 5 | "6명 환경 동시 부하 낮음", "모달 표준 동작" |
| SC-6 동일 패턴 | 6 | FP Blacklist 항목과 일치 |
| FP Blacklist 자동 거부 | 7 | #2, #3, #5, #6, #7, #11, #13 등 |

---

## 이슈 목록 (6건, 전부 보고만)

### BE 성능 (1건)

#### [BE-R1] VC 매핑 업종별 기업 조회 N+1 쿼리 — Moderate/HIGH — CONFIRMED

**파일**: `si_mapping_service.py:968-984`
**문제**: `map_vc_candidates`에서 전방+후방 관련 업종(최대 40개)에 대해 각각 개별 SELECT 쿼리 실행. 1회 매핑 요청당 최대 40회 DB 왕복.

```python
for ind in unique_related:       # 최대 40회 반복
    ind_q = (
        select(VcCompany)
        .where(VcCompany.industry_name == ind, ...)
        .order_by(VcCompany.revenue.desc())
        .limit(top_n)
    )
    rows = (await db.execute(ind_q)).scalars().all()   # 매번 DB 왕복
```

**교차 검증**: Read로 968-984행 직접 확인. `WHERE industry_name IN (...)` 단일 쿼리 + Python 그룹핑으로 개선 가능. 동일 파일 `map_si_candidates`는 인메모리 인덱스로 0회 DB 쿼리 달성 (설계 비일관).
**영향**: 인덱스(`ix_vc_companies_industry_revenue`)가 있어 단건은 빠르나, RTT 누적.

---

### FE UX/품질 (3건)

#### [FE-I3] KsicSearchInput Escape 이벤트 미차단으로 드롭다운 닫기 시 부모 모달까지 닫힘 — Moderate/HIGH — CONFIRMED

**파일**: `KsicSearchInput.tsx:91-93`, `SIMappingPanel.tsx:64-76`
**문제**: KsicSearchInput의 Escape 핸들러가 `e.stopPropagation()`을 호출하지 않아, 이벤트가 document까지 버블링 → SIMappingPanel의 Escape 핸들러가 `onClose()` 호출. KSIC 드롭다운만 닫으려 했으나 전체 패널이 닫히는 결과 발생.

```tsx
// KsicSearchInput.tsx:91-93
} else if (e.key === "Escape") {
  setIsOpen(false);
  setHighlightIdx(-1);
  // e.stopPropagation() 미호출 ← 이벤트 버블링
}

// SIMappingPanel.tsx:64-76
document.addEventListener("keydown", handleKeyDown);
// handleKeyDown: if (e.key === "Escape") { ... onClose(); }
```

**교차 검증**: Read로 KsicSearchInput.tsx:91-93 확인 — `stopPropagation` 없음. SIMappingPanel.tsx:74 — `document.addEventListener` 확인. 이벤트 전파 경로상 두 핸들러 모두 실행됨.
**영향**: KSIC 검색 중 Escape 시 패널 전체 닫힘 → 사용자 입력 손실. `e.stopPropagation()` 1줄 추가로 해결 가능.

#### [FE-I1] VcMappingResult 탭 전환 시 선택 상태 전체 초기화 — Moderate/HIGH — DESIGN_RISK

**파일**: `VcMappingResult.tsx:230-233`
**문제**: 탭 전환 시 `setSelectedIds(new Set())`로 선택 상태를 전부 초기화. forward에서 5개 선택 → backward 탭 이동 → forward 선택분 소멸.

```tsx
onClick={() => {
  setActiveTab(key);
  setSelectedIds(new Set());  // ← 탭 전환 시 무조건 초기화
}}
```

**교차 검증**: Read로 230-233행 확인. 탭별 독립 선택은 합리적 UX 설계일 수 있으나, "탭 전환 시 선택이 초기화됩니다" 안내 없음. **DESIGN_RISK로 분류**.
**영향**: 크로스탭 누적 선택 후 일괄 등록 워크플로우 불가.

#### [FE-I2] FIRecommendModal partial success 시 모달 미닫힘 + 선택 미초기화 — Low/HIGH — CONFIRMED

**파일**: `FIRecommendModal.tsx:95-110`
**문제**: `added > 0 && failed > 0` 경로에서 `toast.warning`만 표시. `onClose()` 미호출, `selected` 미초기화. 성공한 GP가 `selected`에 남아 재제출 가능.

```tsx
if (added > 0 && failed === 0) {
  toast.success(...);
  onClose();   // ← 여기서만 닫힘
} else if (added > 0 && failed > 0) {
  toast.warning(...);  // ← 모달 열린 채, selected 미초기화
}
```

**교차 검증**: Read로 95-110행 확인. `invalidateQueries` 호출(91행)로 `existingCompanyNames`가 갱신되어 재제출 시 `toAdd` 필터(73행)에서 걸리는 부분 완화 존재. 그러나 리렌더 타이밍에 따라 중복 가능.
**영향**: partial success 시 중복 제출 위험 (서버 측 중복 방어로 데이터 오류는 방지됨).

---

### FE 접근성/패턴 (2건)

#### [FE-R3] SICandidateTable `<th>` scope 누락 — Low/HIGH — FP Blacklist #17

**파일**: `SICandidateTable.tsx:105-131`
**문제**: 7개 `<th>` 요소 모두 `scope="col"` 누락. 동일 모듈 VcMappingResult는 모든 `<th>`에 `scope="col"` 적용 중. WCAG 1.3.1 위반.

#### [FE-R5] FIRecommendModal useMutation 미사용 — Moderate/HIGH — FP Blacklist #18

**파일**: `FIRecommendModal.tsx:31, 65-114`
**문제**: 코드베이스 전체에서 모든 POST 뮤테이션이 `useMutation` 패턴 사용. 이 컴포넌트만 직접 `async` + `useState(isSubmitting)` + `try/finally` 패턴. React Query 상태 관리 우회.

---

## 보안 검증 결과

| 검증 항목 | 결과 | 비고 |
|----------|------|------|
| SQL Injection | ✅ PASS | 전 엔드포인트 ORM + ILIKE escape |
| IDOR | ✅ PASS | 쓰기: txn_id 접근 제어, 읽기: 공개 참조 데이터 |
| 인증/인가 | ✅ PASS | 전 엔드포인트 JWT + 역할 기반 접근 제어 |
| XSS | ✅ PASS | dangerouslySetInnerHTML 미사용 |
| Rate Limiting | ✅ PASS | 비용 높은 엔드포인트 보호 (5회/60초) |
| 입력 검증 | ✅ PASS | Pydantic 스키마 + FastAPI Query 제약 |
| 민감정보 | ✅ PASS | 등록번호 마스킹 + 감사 로그 마스킹 |
| 엣지케이스 | ✅ PASS | 17개 시나리오 검증 |

---

## API 계약 일관성

| 검증 항목 | 결과 |
|----------|------|
| 엔드포인트 URL/메서드 일치 | 10/10 정합 |
| 요청 스키마 필드명/타입/nullable | 전체 정합 (20+ 스키마) |
| 응답 스키마 필드명/타입/nullable | 전체 정합 |
| Decimal/UUID/Enum 직렬화 | 전체 정합 (14+ Decimal 필드 확인) |
| 에러 전파 경로 | 12개 경로 전체 정합 |

---

## 수렴 추이

```
이전 리뷰:
  R8:  C=0  M+H=0  수정=0  DR=1
  R9:  C=0  M+H=0  수정=0
  R10: C=0  M+H=0  수정=3
  R11: C=0  M+H=0  수정=2
  R12: C=0  M+H=0  수정=0  → CONVERGED
  13관점: C=0  M+H(CONFIRMED)=2  → 수정 완료
  배포후#1: C=0 M+H=0 Mod=4 Low=1 Minor=1 → CONVERGED

배포후#2 (이번, FP 검증 강화):
  Critical=0  Major+HIGH=0
  Moderate+HIGH=3 (CONFIRMED=2, DESIGN_RISK=1)
  Low+HIGH=2 (CONFIRMED=1, FP Blacklist=1)
  Moderate+HIGH(FP Blacklist)=1
  보안=0  API=0
  수정 대상=0건
  에이전트 거부율=~85% (39+ 후보 → 6건 보고)

판정: CONVERGED (Critical/Major+HIGH = 0건 유지, 5회 연속)
```

---

## FP Prevention

- **FP Blacklist**: 18항목 적용 — 7건 자동 거부
- **Self-Challenge 거부**: 31건 (SC-2: 8건, SC-4: 12건, SC-5: 5건, SC-6: 6건)
- **교차 검증**: 6건 전수 검증 (CONFIRMED: 3, DESIGN_RISK: 1, FP Blacklist: 2)
- **에이전트 중복 보고**: FE-I1(탭 초기화)이 FE Agent 1 + FE Agent 2에서 동시 보고 → 중복 제거

---

## Methodology

- **Agents**: BE 심층(7관점) ×2, FE 심층(6관점) ×2, 통합(API+에러+직렬화), 보안+엣지케이스 = 6개 에이전트
- **Files scanned**: BE 4파일 + FE 9파일 = 13파일
- **Protocol**: VCP v1.1 + SC-1~SC-6 Self-Challenge + FP Blacklist 18항목
- **FP Prevention**: 에이전트 39+ 후보 → SC/FP로 33+ 거부 → 6건 보고 (거부율 ~85%)
- **교차 검증**: Critical/Major만이 아닌 **전체 이슈** 대상 교차 검증 (사용자 요청)
- **Fix Gate**: Critical/Major + HIGH + CONFIRMED만 수정 (해당 0건)
