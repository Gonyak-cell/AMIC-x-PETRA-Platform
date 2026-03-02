# Code Review — MA Workflow Round 4 (13-Perspective Gap Analysis)

> **Review Date**: 2026-03-02 12:55 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `--diff origin/master` (전체 변경, ~200개 소스 파일) + `--backend` (deal-mgmt Python)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS) pytest(PASS: 1228/0) build(PASS)
> **Agents**: backend-security-reviewer, python-code-reviewer, migration-validator, performance-profiler, frontend-api-contract-reviewer

## Summary

| Severity | Raw | Cross-Verified | FP Removed | Confirmed |
|----------|-----|---------------|------------|-----------|
| Critical | 16  | 16            | 10         | **6**     |
| Major    | 26  | 26            | 16         | **10**    |
| **Total**| **42** | **42**     | **26**     | **16**    |

**FP Prevention**: 42건 검증, 26건 사전 거부 (거부율: 62%)

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 8 | MIG-03: `attachmententitytype` → Alembic이 CREATE TABLE 시 자동 생성 확인 |
| 범위 외 (레거시) | 5 | MIG-02: 초기 마이그레이션(001~015) 이미 프로덕션 적용, 변경 불가 |
| 설계상 의도 | 7 | MIG-11: platform_settings Integer PK 싱글턴 패턴, SEC-03: 공개 엔드포인트 주석 명시 |
| 중복 | 3 | CODE-07 = PERF-01, CODE-02 ≈ SEC-05 |
| 신뢰도 불충분 | 3 | SEC-07: ADMIN/MANAGER 전용 엔드포인트로 실질적 위험 낮음 |

---

## Findings

---

### P0 — 즉시 수정 (배포 차단)

---

#### [R4-MIG-01] Alembic 다중 헤드: revision "050" 중복 — [Critical/HIGH] — Priority: P0 (점수: 100)

**파일**: `deal-mgmt/migrations/versions/050_pef_registration_date_index.py:13` + `050_review_round3_indexes.py:14`

**증거**:
```python
# 050_pef_registration_date_index.py
revision = "050"
down_revision = "049"

# 050_review_round3_indexes.py
revision = "050"
down_revision = "049"
```

**영향**: `alembic upgrade head` 실행 시 다중 헤드 에러 → **프로덕션 배포 차단**. 051의 `down_revision = "050"`이 어느 파일을 가리키는지 불확정.

**수정**: `050_review_round3_indexes.py`의 revision을 `"050b"`로 변경, `down_revision = "050"` 유지. 051의 `down_revision`을 `"050b"`로 변경.

---

#### [R4-SEC-01] LDD 보고서 email=None 인가 우회 — [Critical/HIGH] — Priority: P0 (점수: 100)

**파일**: `deal-mgmt/app/routers/ldd_reports.py:50-55`

**증거**:
```python
if (
    claims.role != "ADMIN"
    and claims.email is not None      # ← email=None이면 전체 조건 False → 403 미발생
    and txn.lead_advisor_email != claims.email
    and txn.deal_captain_email != claims.email
):
    raise HTTPException(403, ...)
```

`security.py:88`에서 `email = payload.get("email")` → email 클레임 없는 JWT 토큰 시 `None`.

**영향**: email 클레임 없는 JWT 토큰으로 **모든 거래의 LDD 보고서 접근 가능**.

**수정**: `and claims.email is not None` 조건 제거. email=None이면 `lead_advisor_email != None` → True → 403 발생.

---

#### [R4-SEC-02] list_all_ldd_reports: 인가 없이 전체 LDD 조회 — [Critical/HIGH] — Priority: P0 (점수: 100)

**파일**: `deal-mgmt/app/routers/ldd_reports.py:68-74`

**증거**:
```python
@_default_sections_router.get("/ldd-reports")
async def list_all_ldd_reports(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),    # 인증만, 역할 제한 없음
):
    return [LDDReportOut.model_validate(r) for r in await ldd_report_service.list_all_ldd_reports(db)]
```

같은 파일 내 per-transaction 엔드포인트(line 84-99)는 `_get_and_authorize_txn`으로 역할+딜 접근 검증하지만, 이 전역 엔드포인트는 우회됨.

**영향**: CLIENT 포함 모든 인증 사용자가 **시스템 내 전체 LDD 보고서** 조회 가능. 법률실사 민감 정보 유출.

**수정**: `Depends(require_role("ADMIN", "MANAGER"))` 추가.

---

### P1 — 스프린트 우선 (데이터 정합성)

---

#### [R4-API-01] EarnoutOut/EarnoutSummary: Decimal 직렬화 누락 — [Critical/HIGH] — Priority: P1 (점수: 85)

**파일**:
- BE: `deal-mgmt/app/schemas/earnout.py:12-31` (EarnoutOut), `60-65` (EarnoutSummary)
- FE: `amic-platform/src/modules/ma/types/earnout.ts:24,25,29,66-68`

**증거**: `EarnoutOut`에 `target_value: Decimal`, `actual_value: Decimal | None`, `payment_amount: Decimal | None` → `@field_serializer` 없음. Pydantic V2는 Decimal을 `"1234.56"` 문자열로 직렬화. FE는 `number`로 기대.

동일 프로젝트의 `TransactionOut`, `ConsortiumMappingOut`, `DashboardRevenueItem` 등 모든 Decimal 스키마에는 `@field_serializer` 적용됨. EarnoutOut만 누락.

`EarnoutSummary`도 `total_target`, `total_actual`, `total_payment` 3개 Decimal 필드에 serializer 누락.

**영향**: Earnout 페이지에서 금액 표시 오류 또는 NaN 발생 가능.

**수정**:
- `EarnoutOut`에 `@field_serializer("target_value", "actual_value", "payment_amount")` 추가
- `EarnoutSummary`에 `@field_serializer("total_target", "total_actual", "total_payment")` 추가
- FE `earnout.ts`에서 `number` → `string | null` / `string` 변경

---

#### [R4-API-02] TransactionOut: corporate_info/financial_summary 필드 누락 — [Critical/HIGH] — Priority: P1 (점수: 85)

**파일**:
- BE 모델: `deal-mgmt/app/models/transaction.py:71-72` (두 필드 존재)
- BE 스키마: `deal-mgmt/app/schemas/transaction.py:13-56` (두 필드 **없음**)
- FE: `amic-platform/src/modules/ma/types/transaction.ts:80-81`

**증거**:
```python
# models/transaction.py:71-72 — DB에 존재
corporate_info: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
financial_summary: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
```
TransactionOut 스키마에 해당 필드 없음 → API 응답에서 제외됨.

**영향**: AI 문서 추출 파이프라인이 `corporate_info`/`financial_summary`를 DB에 저장해도, API 응답에 포함되지 않아 **프론트엔드에서 항상 undefined**. 추출 결과가 표시되지 않음.

**수정**: `TransactionOut`에 추가:
```python
corporate_info: dict | None = None
financial_summary: dict | None = None
```

---

#### [R4-API-03] NDAOut: AI 추출 3개 필드 누락 — [Critical/HIGH] — Priority: P1 (점수: 85)

**파일**:
- BE 모델: `deal-mgmt/app/models/nda.py:32-34` (3개 필드 존재)
- BE 스키마: `deal-mgmt/app/schemas/nda.py:11-25` (3개 필드 **없음**)
- FE: `amic-platform/src/modules/ma/types/nda.ts:15-17`

**증거**:
```python
# models/nda.py:32-34 — DB에 존재
counterparty_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
jurisdiction: Mapped[str | None] = mapped_column(String(200), nullable=True)
confidentiality_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
```
NDAOut 스키마에 해당 필드 없음.

**영향**: NDA AI 추출 결과가 DB에 저장되어도 API 응답에 미포함. 프론트엔드에서 상대방명, 관할권, 비밀유지 기간 표시 불가.

**수정**: `NDAOut`에 추가:
```python
counterparty_name: str | None = None
jurisdiction: str | None = None
confidentiality_period_months: int | None = None
```

---

### P2 — 개선 권장 (API 계약 정합성)

---

#### [R4-SEC-04] upload_attachment: check_client_deal_access 누락 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**: `deal-mgmt/app/routers/attachments.py:86-96`

**증거**: GET(line 65-66)과 DELETE(line 188-194)에는 `check_client_deal_access` 존재. POST만 누락.

**영향**: ANALYST/MANAGER가 자신이 담당하지 않는 거래에 파일 업로드 가능. `require_write_access()`가 CLIENT는 차단하지만 deal-level 격리 없음.

**수정**: line 96 뒤에 `await check_client_deal_access(db, txn_id, claims)` 추가.

---

#### [R4-API-04] BidOut: AI 추출 2개 필드 누락 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**:
- BE 모델: `deal-mgmt/app/models/bid.py:40-41` (2개 필드 존재)
- BE 스키마: `deal-mgmt/app/schemas/bid.py:11-28` (2개 필드 **없음**)
- FE: `amic-platform/src/modules/ma/types/bid.ts:32-33`

**증거**: `Bid` 모델에 `exclusivity_period_days`(Integer)와 `conditions_precedent`(JSON)가 있으나 `BidOut`, `BidCreate`, `BidUpdate` 스키마에 모두 누락.

**영향**: LOI/MOU AI 추출 후 저장된 독점 협상 기간/선행 조건이 API 응답에 미포함.

**수정**: 3개 스키마에 해당 필드 추가.

---

#### [R4-API-05] Transaction: target_stake 등 3개 필드 FE number ↔ BE string 불일치 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**:
- BE: `deal-mgmt/app/schemas/transaction.py:52-55` (`@field_serializer` → `str | None`)
- FE: `amic-platform/src/modules/ma/types/transaction.ts:68-70` (`number | null`)

**증거**: BE가 `str(v)`로 직렬화하지만 FE는 `number | null`로 정의. 동일 스키마의 `estimated_deal_value`는 FE에서 `string | null`로 올바르게 정의됨. 3개 필드만 불일치.

**수정**: FE `transaction.ts`에서 `target_stake`, `new_share_ratio`, `old_share_ratio`를 `string | null`로 변경.

---

#### [R4-API-06] ConsortiumMapping: equity_share_pct FE number ↔ BE string 불일치 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**:
- BE: `deal-mgmt/app/schemas/consortium.py:29-31` (`@field_serializer` → `str | None`)
- FE: `amic-platform/src/modules/ma/types/consortium.ts:11` (`number | null`)

**수정**: FE `consortium.ts`에서 `equity_share_pct`를 `string | null`로 변경.

---

#### [R4-API-07] RFIUpdate: status 필드 사일런트 드롭 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**:
- BE: `deal-mgmt/app/schemas/rfi.py:34-41` (`status` 필드 없음)
- FE: `amic-platform/src/modules/ma/types/rfi.ts:136` (`status?: RFIStatus`)

**증거**: FE `RFIUpdate`에 `status` 포함, PATCH 요청 시 전송. BE Pydantic 스키마에 없으므로 무시. 상태 변경은 `/send`, `/close` 전용 엔드포인트로만 동작.

**영향**: 프론트엔드에서 status 변경 PATCH가 성공(200)으로 응답하지만 실제 변경 없음 (사일런트 실패).

**수정**: FE `rfi.ts:RFIUpdate`에서 `status` 필드 제거.

---

#### [R4-CODE-04] model_builder.py: 재무 수치 float 사용 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**: `deal-mgmt/app/excel/model_builder.py:55-61`

**증거**:
```python
def _get_num(checklist_values: dict[str, str], title: str, default: float = 0.0) -> float:
    return float(val.replace(",", "").replace("%", "").replace("x", ""))
```

**영향**: M&A 재무모델 Excel 생성 시 수십억~수조 원 수치를 float으로 처리 → IEEE 754 정밀도 손실.

**수정**: `float` → `Decimal` 변환.

---

#### [R4-PERF-01] SI 매핑: 10,000건 ORM 전체 메모리 로드 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:547-578`

**증거**:
```python
_MAX_COMPANIES_FOR_MAPPING: int = 10_000
q = q.limit(_MAX_COMPANIES_FOR_MAPPING)
return list(result.scalars().all())  # 전체를 Python 메모리로 적재
```

**영향**: 단일 SI 매핑 요청에서 수백 MB 메모리 스파이크. 동시 요청 시 OOM 위험.

**수정**: 필요 컬럼만 select하거나, TTL 캐시 적용.

---

#### [R4-PERF-07] blob_storage: Azure 다운로드 전체 청크 메모리 집적 — [Major/HIGH] — Priority: P2 (점수: 55)

**파일**: `deal-mgmt/app/core/blob_storage.py:147-155`

**증거**:
```python
chunks = [chunk async for chunk in stream.chunks()]  # 전체 메모리 집적
await asyncio.to_thread(_write_chunks, chunks)
```
주석에는 "청크 단위로 쓰므로 힙 부담이 작다"고 있으나 실제로는 리스트 컴프리헨션으로 전체 메모리 적재.

**영향**: 100MB 파일 다운로드 시 100MB 메모리 스파이크.

**수정**: 청크를 순차적으로 파일에 기록 (진정한 스트리밍).

---

## 기술 부채 (Design Risk)

| ID | 설명 | 근거 |
|----|------|------|
| R4-MIG-02 | 초기 마이그레이션(001~015) `postgresql.UUID`/`JSONB` 직접 사용 | 이미 프로덕션 적용. CI는 `Base.metadata.create_all` 사용 |
| R4-MIG-04 | 데이터 마이그레이션(038,051,053) `downgrade() pass` | 비가역 데이터 변환. 운영 가이드 문서화 필요 |
| R4-SEC-06 | Rate limiter 인메모리 딕셔너리 (멀티 워커 우회) | 코드 내 한계 주석 존재. Redis 전환 중기 계획 |
| R4-PERF-02 | Transaction 검색 4-column ILIKE 풀스캔 | pg_trgm 확장 필요. 현재 데이터 규모에서 허용 범위 |
| R4-CODE-03 | document_extraction.reviewed_at String(50) | DateTime으로 전환 시 마이그레이션 + 서비스 수정 필요 |

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 배포 차단/보안)
1. [R4-MIG-01] [Critical/HIGH]: Alembic 다중 헤드 revision "050" 중복 — migrations/ (점수: 100)
2. [R4-SEC-01] [Critical/HIGH]: LDD 보고서 email=None 인가 우회 — ldd_reports.py (점수: 100)
3. [R4-SEC-02] [Critical/HIGH]: list_all_ldd_reports 인가 없음 — ldd_reports.py (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89, 데이터 정합성)
4. [R4-API-01] [Critical/HIGH]: EarnoutOut Decimal serializer 누락 — earnout.py (점수: 85)
5. [R4-API-02] [Critical/HIGH]: TransactionOut corporate_info/financial_summary 누락 — transaction.py (점수: 85)
6. [R4-API-03] [Critical/HIGH]: NDAOut 3개 AI 추출 필드 누락 — nda.py (점수: 85)

### P2 — 개선 권장 (점수: 30-59, API 정합성/코드 품질)
7. [R4-SEC-04] [Major/HIGH]: upload_attachment deal access 검증 누락 — attachments.py (점수: 55)
8. [R4-API-04] [Major/HIGH]: BidOut 2개 AI 추출 필드 누락 — bid.py (점수: 55)
9. [R4-API-05] [Major/HIGH]: Transaction 3개 필드 FE number↔BE string — transaction.ts (점수: 55)
10. [R4-API-06] [Major/HIGH]: ConsortiumMapping equity_share_pct FE number↔BE string — consortium.ts (점수: 55)
11. [R4-API-07] [Major/HIGH]: RFIUpdate status 사일런트 드롭 — rfi.ts (점수: 55)
12. [R4-CODE-04] [Major/HIGH]: model_builder float→Decimal 전환 필요 — model_builder.py (점수: 55)
13. [R4-PERF-01] [Major/HIGH]: SI 매핑 10K ORM 메모리 로드 — si_mapping_service.py (점수: 55)
14. [R4-PERF-07] [Major/HIGH]: blob 다운로드 메모리 집적 — blob_storage.py (점수: 55)

---

## Methodology

- **Agents**: backend-security-reviewer, python-code-reviewer, migration-validator, performance-profiler, general-purpose (FE/BE contract)
- **Files scanned**: ~200개 소스 파일 (origin/master 대비 전체 변경)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 42건 전수 검증
- **FP rate**: 62% (42건 중 26건 거부)

## 검증 투명성

### 검증 통계
- 검증한 가설: 42건
- 거부된 가설 (사전 제거): 26건
- 보고된 이슈: 16건 (P0: 3, P1: 3, P2: 8, 기술부채: 5)
- 거부율: 62%

### 이전 라운드 대비 추이

| Round | 원시 이슈 | 확정 이슈 | FP율 | P0 | P1 | P2 |
|-------|---------|---------|------|----|----|-----|
| 1 | 30 | 22 | 27% | 3 | 8 | 11 |
| 2 | 42 | 18 | 57% | 2 | 6 | 10 |
| 3 | 23 | 23 | 0% | 5 | 8 | 10 |
| **4** | **42** | **16** | **62%** | **3** | **3** | **8** |

**총 누적**: 원시 137건 → 확정 79건 → Round 1~3 모두 수정 완료 → Round 4에서 16건 신규 발견
