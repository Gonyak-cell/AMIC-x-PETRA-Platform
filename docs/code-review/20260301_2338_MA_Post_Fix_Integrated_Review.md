# Post-Fix Integrated Review — MA 6대 핵심 지시사항

> **Review Date**: 2026-03-01 23:38
> **Reviewer**: Claude Code (4-agent parallel review)
> **Scope**: R2-R6 38개 이슈 수정 후 검증 + 미발견 이슈 탐지
> **Method**: Post-Fix Verification + 4-Agent Deep Dive (Security + Migration + Performance + Python Quality)
> **Tests**: 1080 passed, 14 skipped (ruff clean)

---

## Summary

| Severity | Count | Priority Distribution |
|----------|-------|-----------------------|
| Critical | 3     | P0: 3 |
| Major    | 5     | P1: 5 |
| Moderate | 7     | P2: 7 |
| Minor    | 6     | P3: 6 |
| Info     | 4     | P3: 4 |
| **Total**| **25**| P0: **3** / P1: **5** / P2: **7** / P3: **10** |

**교차 검증**: 4건 (046 COMMIT ×2, UUID ×2, GP 인덱스 ×2, Content-Disposition ×2)

---

## P0 — 즉시 수정 (3건)

### [PF-C1] Pydantic 스키마 float→Decimal 미전환 — Decimal 수정 효과 무력화

- **위치**: `deal-mgmt/app/schemas/transaction.py:24,35-37,71-73,101-103`
- **심각도**: Critical / HIGH — **점수: 100**
- **에이전트**: python-code-reviewer

`transaction.py` 모델은 `Decimal`로 변경되었으나, Pydantic 스키마 3종(`TransactionOut`, `TransactionCreate`, `TransactionUpdate`)의 4개 필드가 `float`으로 남아 있음. DB에서 읽은 `Decimal`이 `float`으로 암묵 변환되어 부동소수점 오차 재도입.

```python
# schemas/transaction.py — 여전히 float
estimated_deal_value: float | None = None
target_stake: float | None = None
new_share_ratio: float | None = None
old_share_ratio: float | None = None
```

**수정**: 4개 필드 `float` → `Decimal`, `from decimal import Decimal` 추가.

---

### [PF-C2] dashboard.py — Decimal에 float() 강제 변환

- **위치**: `deal-mgmt/app/routers/dashboard.py:37,47`
- **심각도**: Critical / HIGH — **점수: 100**
- **에이전트**: python-code-reviewer

모델의 `estimated_deal_value`가 `Decimal`인데 `float()`으로 명시 변환하여 P0 수정 효과 무력화.

```python
total_value = sum(float(t.estimated_deal_value) for t in transactions if t.estimated_deal_value)
phase_counts[p][1] += float(t.estimated_deal_value)
```

**수정**: `float()` 제거, `Decimal` 그대로 집계. `DashboardStats.total_deal_value`도 `Decimal`로 변경.

---

### [PF-C3] 마이그레이션 046 — COMMIT이 Alembic 트랜잭션 파괴

- **위치**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:32`
- **심각도**: Critical / HIGH — **점수: 110** (교차 검증 +10)
- **에이전트**: backend-security-reviewer + migration-validator

`bind.execute(sa.text("COMMIT"))`이 Alembic 트랜잭션을 강제 커밋. 이후 UPDATE 실패 시 enum은 추가됐으나 데이터 마이그레이션 미완료 + alembic_version 불일치 상태 발생.

**수정**: 046을 두 마이그레이션으로 분리 (046a: enum ADD VALUE, 046b: UPDATE) 또는 env.py에서 `transaction_per_migration=False` 설정.

---

## P1 — 스프린트 우선 (5건)

### [PF-M1] 046 downgrade — PostgreSQL에서 실행 불가

- **위치**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:49`
- **심각도**: Major / HIGH — **점수: 70**
- **에이전트**: migration-validator

downgrade에서 `SET phase = 'BIDDING_DD'` 실행 시 PostgreSQL enum에 `BIDDING_DD` 값이 없어 `invalid input value for enum` 오류 발생. downgrade 실질 불가.

**수정**: PostgreSQL dialect 분기 추가하여 enum 재생성 방식 처리 또는 downgrade 명시적 금지(`raise NotImplementedError`).

---

### [PF-M2] Content-Disposition — filename= 파라미터에 비ASCII 잔존

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py:425-432`
- **심각도**: Major / HIGH — **점수: 80** (교차 검증 +10)
- **에이전트**: backend-security-reviewer + python-code-reviewer

`re.sub(r"[^\w\s\-.]", "_", ...)` 패턴에서 `\w`가 유니코드를 매칭하여 한글이 `filename=` (ASCII 전용 필드)에 남음. RFC 6266 위반, 일부 환경 파싱 오류.

**수정**: `re.ASCII` 플래그 적용 또는 `.encode("ascii", errors="replace").decode("ascii")` 추가.

---

### [PF-M3] marketing log 엔드포인트 — txn 존재 검증 누락

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py:62-194` (4개 엔드포인트)
- **심각도**: Major / HIGH — **점수: 70**
- **에이전트**: backend-security-reviewer

`list_marketing_logs`, `create_marketing_log`, `update_marketing_log`, `delete_marketing_log` 모두 `transaction_service.get_transaction()` 누락. 비-CLIENT 역할이 존재하지 않는 txn_id로 마케팅 로그 CRUD 가능.

**수정**: 4개 엔드포인트에 `await transaction_service.get_transaction(db, txn_id)` 선행 호출 추가.

---

### [PF-M4] require_role() — 에러 메시지에 유효 역할명 노출

- **위치**: `deal-mgmt/app/core/security.py:94-97`
- **심각도**: Major / HIGH — **점수: 70**
- **에이전트**: backend-security-reviewer

`detail=f"권한이 부족합니다. 필요한 역할: {', '.join(roles)}"` — 공격자 역할 열거(Role Enumeration) 가능.

**수정**: `detail="이 작업을 수행할 권한이 없습니다"`.

---

### [PF-M5] promote-short-list — 불필요한 N회 db.refresh()

- **위치**: `deal-mgmt/app/routers/buyers.py:230-231`
- **심각도**: Major / HIGH — **점수: 70**
- **에이전트**: performance-profiler

`expire_on_commit=False` 설정에도 커밋 후 N건 개별 `db.refresh(b)` 호출. 20명 승격 시 20회 추가 SELECT.

**수정**: refresh 루프 제거 (`expire_on_commit=False`이므로 메모리 상태 유지됨).

---

## P2 — 개선 권장 (7건)

### [PF-Mod1] PEF 레지스트리 — CLIENT 역할 무제한 접근

- **위치**: `deal-mgmt/app/routers/pef_registry.py:29-61`
- **심각도**: Moderate / HIGH — **점수: 40**
- **에이전트**: backend-security-reviewer

인증만 요구(`get_jwt_claims`), 역할 제한 없음. CLIENT가 전체 PE 펀드 재무정보 조회 가능.

---

### [PF-Mod2] contact_email — 이메일 포맷 검증 미적용

- **위치**: `deal-mgmt/app/schemas/buyer.py:42,55`
- **심각도**: Moderate / HIGH — **점수: 40**
- **에이전트**: backend-security-reviewer

`ioi_date`/`loi_date`에 pattern 추가했으나 `contact_email`은 max_length만 적용.

---

### [PF-Mod3] DART 검색 — txn 존재 검증 없이 외부 서비스 호출

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py:292-308`
- **심각도**: Moderate / HIGH — **점수: 40**
- **에이전트**: backend-security-reviewer

존재하지 않는 txn_id로 KIIS 외부 서비스 호출 가능.

---

### [PF-Mod4] GP 인덱스 — 마이그레이션 미적용 (모델과 불일치)

- **위치**: `deal-mgmt/migrations/versions/045:45` vs `deal-mgmt/app/models/pef_fund_registry.py:19-22`
- **심각도**: Moderate / HIGH — **점수: 50** (교차 검증 +10)
- **에이전트**: migration-validator + performance-profiler

모델에 GP 인덱스 3개 선언했으나 마이그레이션에서 생성 누락. 프로덕션 DB에 인덱스 미존재.

---

### [PF-Mod5] ilike 검색 — btree 인덱스 미활용

- **위치**: `deal-mgmt/app/routers/pef_registry.py:43-46`
- **심각도**: Moderate / HIGH — **점수: 40**
- **에이전트**: performance-profiler

`ILIKE '%검색어%'` 패턴은 btree 인덱스 사용 불가. 1,137건 규모에서는 수용 가능하나 증가 시 성능 저하.

---

### [PF-Mod6] audit — COUNT 이중 실행 + created_at 인덱스 누락

- **위치**: `deal-mgmt/app/services/audit_service.py:76-79`, `deal-mgmt/app/models/audit.py`
- **심각도**: Moderate / HIGH — **점수: 40**
- **에이전트**: performance-profiler

COUNT + SELECT 2회 실행, `created_at` 인덱스 없어 날짜 필터 + ORDER BY에 seq scan.

---

### [PF-Mod7] FI recommendations — 응답 크기 무제한

- **위치**: `deal-mgmt/app/routers/pef_registry.py:95-137`
- **심각도**: Moderate / HIGH — **점수: 40**
- **에이전트**: performance-profiler

500건 PEF → GP 그룹핑 → 반환 제한 없음. 대용량 JSON 응답 가능.

---

## P3 — 저우선 (10건)

| # | 이슈 | 파일 | 에이전트 | 점수 |
|---|------|------|---------|------|
| PF-L1 | UUID(as_uuid=True) PostgreSQL 전용 (30+파일, 기존 알려진 이슈) | transaction.py:17 | migration + python | 30 |
| PF-L2 | permit_analysis_service.py — float() 변환 잔존 | permit_analysis_service.py:156 | python | 20 |
| PF-L3 | export_audit_logs — 10,000건 일괄 메모리 로드 | audit.py (router):61 | performance | 20 |
| PF-L4 | empty role 에러 메시지 CLIENT와 혼용 | security.py:112 | security | 12 |
| PF-L5 | 045 op.get_bind() SQLAlchemy 2.0 deprecated | 045:63 | migration | 12 |
| PF-L6 | buyers.py `is not False` 가독성 | buyers.py:333 | python | 20 |
| PF-L7 | DART 검색 쿼리 로그 노출 | buyer_marketing.py:307 | security | 12 |
| PF-L8 | audit old_value Enum 직렬화 암묵 의존 | buyers.py:341 | python | 12 |
| PF-L9 | pef_registry.py ORM/Pydantic 타입 혼용 | pef_registry.py:129 | python | 12 |
| PF-L10 | remove_buyer CASCADE COUNT 순차 2회 | buyers.py:373-384 | performance | 20 |

---

## 이전 38개 수정 검증 결과

| 수정 항목 | 검증 상태 |
|----------|---------|
| P0: transaction.py float→Decimal | ⚠️ 모델 OK, **스키마/사용처 미전환** (PF-C1, PF-C2 참조) |
| P1: buyers.py 상태전이 새니타이즈 | ✅ 올바르게 구현 |
| P1: buyers.py 연락처 검증 헬퍼 | ✅ 올바르게 구현 |
| P1: buyers.py contact null화 방지 | ✅ 올바르게 구현 |
| P1: buyers.py BID_DROPPED 전이 확장 | ✅ 올바르게 구현 |
| P1: buyer_marketing.py txn 검증 추가 | ⚠️ short_list_marketing_overview만 추가, **4개 로그 엔드포인트 누락** (PF-M3) |
| P1: buyer_marketing.py RFC 5987 | ⚠️ filename* OK, **filename= 비ASCII 잔존** (PF-M2) |
| P1: buyer_marketing.py max_length | ✅ 올바르게 구현 |
| P1: buyer_marketing.py Excel 예외처리 | ✅ 올바르게 구현 |
| P1: pef_registry.py ORDER BY | ✅ 올바르게 구현 |
| P1: pef_registry.py 에러 새니타이즈 | ✅ 올바르게 구현 |
| P1: migrations sa.text() | ✅ 올바르게 구현 |
| P1: migration 046 COMMIT 패턴 | ⚠️ sa.text() OK, **트랜잭션 파괴 문제 잔존** (PF-C3) |
| P1: migration 046 downgrade 순서 | ⚠️ 순서 OK, **PostgreSQL enum 불가** (PF-M1) |
| P1/P2: pef_fund_registry.py GP indexes | ⚠️ 모델 OK, **마이그레이션 미적용** (PF-Mod4) |
| P2: security.py empty role | ✅ 올바르게 구현 |
| P2: audit_service.py logger | ✅ 올바르게 구현 |
| P2: schemas/buyer.py date pattern | ✅ 올바르게 구현 |
| P3: boundary tests 3개 | ✅ 올바르게 구현 |

**검증 요약**: 19개 수정 중 **13개 완전 검증 (✅)**, **6개 부분/후속 이슈 발견 (⚠️)**

---

## Methodology

- **에이전트**: backend-security-reviewer, migration-validator, performance-profiler, python-code-reviewer
- **파일 스캔**: 11개 수정 파일 + 연관 파일 15개
- **교차 검증**: 4건 (2개 이상 에이전트가 동일 이슈 발견)
- **프로토콜**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
