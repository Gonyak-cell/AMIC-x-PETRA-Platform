# Code Review — SI/VC/FI 매핑 배포 후 13관점 통합 리뷰

> **Review Date**: 2026-03-04 20:50 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: SI/VC/FI 매핑 BE 4파일 + FE 9파일
> **Method**: Quality Gates + 4-Agent Parallel Review + Cross-Verification
> **Quality Gates**: ruff(✅) tsc(✅)
> **Protocol**: VCP v1.1 + Self-Challenge (SC-1~SC-6) + FP Blacklist (12항목)

## 배경

이전 리뷰(R1~R12 + 13관점 통합)에서 Critical=0, CONFIRMED 수정 2건 완료 후 배포.
배포 완료(CI ✅ + Deploy ✅ + 헬스체크 ✅) 후 **fresh 13관점 통합 리뷰** 수행.

---

## Summary

| Severity | Count | Confidence Distribution |
|----------|-------|------------------------|
| Critical | 0     | — |
| Major    | 0     | — |
| Moderate | 4     | HIGH: 3 / MEDIUM: 1 |
| Low      | 1     | HIGH: 1 |
| Minor    | 1     | HIGH: 1 |
| **Total**| **6** | HIGH: **5** / MEDIUM: **1** |

**보안**: 0건 (8개 항목 전체 PASS + 17개 엣지케이스 PASS)
**수정 대상**: 0건 (Critical/Major+HIGH+CONFIRMED = 0)

---

## 이슈 목록 (6건, 전부 보고만)

### BE 성능 (1건)

#### [BE-R1] VC 매핑 업종별 기업 조회 N+1 쿼리 — Moderate/HIGH

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

**영향**: 인덱스(`ix_vc_companies_industry_revenue`)가 있어 단건은 빠르나, RTT 누적. `WHERE industry_name IN (...)` 단일 쿼리 + Python 그룹핑으로 개선 가능.

---

### BE 데이터 무결성 (1건)

#### [BE-R2] BuyerCandidate 중복 방지에 DB 레벨 Unique Constraint 부재 — Moderate/MEDIUM

**파일**: `si_mapping_service.py:282-315`, `buyer_candidate.py`
**문제**: `bulk_add_to_buyers`와 `bulk_add_vc_to_buyers` 모두 SELECT-then-INSERT 패턴으로 중복 방지. `BuyerCandidate` 모델에 `(transaction_id, company_name)` unique constraint 없음. 동시 요청 시 TOCTOU 경합 가능.

**영향**: 현재 6명 사용자 환경에서 실제 경합 확률 낮음. 데이터 무결성이 애플리케이션 코드에만 의존.

---

### FE 품질 (2건)

#### [FE-R2] FIRecommendModal N+1 API 호출 패턴 — Moderate/HIGH

**파일**: `FIRecommendModal.tsx:76-83`
**문제**: 선택된 GP마다 개별 `maApi.post()` 호출을 `Promise.allSettled`로 병렬 실행. SI 매핑은 `useBulkAddBuyers` 벌크 API 사용. FI는 벌크 API 없이 N개 개별 요청.

```tsx
const results = await Promise.allSettled(
  toAdd.map((gpName) =>
    maApi.post(`/transactions/${txnId}/buyers`, { ... }),
  ),
);
```

**영향**: 20개 선택 시 20개 HTTP 요청 동시 발생. 부분 실패 시 롤백 없음.

#### [FE-R5] FIRecommendModal useMutation 미사용 — Moderate/MEDIUM

**파일**: `FIRecommendModal.tsx:31, 65-114`
**문제**: 코드베이스 전체에서 모든 POST 뮤테이션이 `useMutation` 패턴 사용. 이 컴포넌트만 직접 `async` + `useState(isSubmitting)` + `try/finally` 패턴.

**영향**: `onClose()` 후 `finally`에서 `setIsSubmitting(false)` 실행 (언마운트 후 state 업데이트). React 18에서는 경고 없으나 비일관.

---

### FE 접근성 (2건)

#### [FE-R3] SICandidateTable `<th>` scope 누락 — Low/HIGH

**파일**: `SICandidateTable.tsx:105-131`
**문제**: 7개 `<th>` 요소 모두 `scope="col"` 누락. 동일 모듈 VcMappingResult는 모든 `<th>`에 `scope="col"` 적용 중. WCAG 1.3.1 위반.

#### [FE-R4] FIRecommendCard checkbox accessible name 과도 — Minor/HIGH

**파일**: `FIRecommendCard.tsx:42-49`
**문제**: `<label>` 내부 전체 텍스트(GP명+뱃지+펀드+섹터+매칭이유)가 checkbox의 accessible name이 됨. 동일 코드베이스 다른 checkbox는 `aria-label="기업명 선택"` 패턴 사용.

---

## 보안 검증 결과

| 검증 항목 | 결과 | 비고 |
|----------|------|------|
| SQL Injection | ✅ PASS | 전 엔드포인트 ORM + ILIKE escape |
| IDOR | ✅ PASS | 쓰기: txn_id 접근 제어, 읽기: 공개 참조 데이터 |
| 인증/인가 | ✅ PASS | 전 엔드포인트 JWT + 역할 기반 접근 제어 |
| XSS | ✅ PASS | dangerouslySetInnerHTML 미사용 |
| Rate Limiting | ✅ PASS | 비용 높은 엔드포인트 보호 |
| 입력 검증 | ✅ PASS | Pydantic 스키마 + FastAPI Query 제약 |
| 민감정보 | ✅ PASS | 등록번호 마스킹 + 감사 로그 마스킹 |
| 엣지케이스 | ✅ PASS | 17개 시나리오 검증 |

---

## API 계약 일관성

| 검증 항목 | 결과 |
|----------|------|
| 엔드포인트 URL/메서드 일치 | 10/10 정합 |
| 요청 스키마 필드명/타입/nullable | 전체 정합 |
| 응답 스키마 필드명/타입/nullable | 전체 정합 |
| Decimal/UUID/Enum 직렬화 | 전체 정합 |

---

## 수렴 추이

```
이전 리뷰 (R1~R12 + 13관점):
  R8:  C=0  M+H=0  수정=0  DR=1
  R9:  C=0  M+H=0  수정=0
  R10: C=0  M+H=0  수정=3
  R11: C=0  M+H=0  수정=2
  R12: C=0  M+H=0  수정=0  → CONVERGED
  13관점: C=0  M+H(CONFIRMED)=2  → 수정 완료

배포 후 리뷰 (이번):
  Critical=0  Major+HIGH=0
  Moderate+HIGH=3 (보고만)
  Moderate+MEDIUM=1 (보고만)
  Low/Minor=2 (보고만)
  보안=0
  수정 대상=0건

판정: CONVERGED (Critical/Major+HIGH = 0건 유지)
```

---

## FP Prevention

- FP Blacklist: 12항목 적용 (이전 리뷰 기반)
- Self-Challenge 거부: FE 3건 (R1 종업원수 "0" truthy, R6 aria-hidden 동기화, R7 non-null assertion 안전)
- 교차 검증 대상: 0건 (Critical/Major+HIGH 없음)

---

## Methodology

- **Agents**: BE 심층(7관점), FE 심층(6관점), 통합(API+에러전파+직렬화), 보안+엣지케이스
- **Files scanned**: BE 4파일 + FE 9파일 = 13파일
- **Protocol**: VCP v1.1 + SC-1~SC-6 Self-Challenge
- **FP Prevention**: FP Blacklist 12항목 + Self-Challenge 3건 거부
- **Fix Gate**: Critical/Major + HIGH + CONFIRMED만 수정 (해당 0건)
