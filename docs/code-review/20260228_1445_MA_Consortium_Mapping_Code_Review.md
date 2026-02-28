# Code Review — MA 컨소시엄/공동투자 매핑 구현

> **Review Date**: 2026-02-28 14:45
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MA 워크플로우 컨소시엄/공동투자자 매핑 통합 — Phase F~I (데이터 레이어, 백엔드 API, 프론트엔드, 테스트)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(PASS) build(PASS) ruff(PASS) pytest(924/928 PASS — 4건 pre-existing VDR)
> **Review Gates**: Backend(deal-mgmt available) Agent-Filtering(5개 에이전트 호출, 0개 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1 / MEDIUM: 0 / LOW: 0 | P0: 1 |
| Major    | 1     | HIGH: 1 / MEDIUM: 0 / LOW: 0 | P1: 1 |
| Moderate | 8     | HIGH: 2 / MEDIUM: 6 / LOW: 0 | P2: 5 / P3: 3 |
| Minor    | 8     | HIGH: 0 / MEDIUM: 5 / LOW: 3 | P2: 1 / P3: 7 |
| **Total**| **18**| HIGH: **4** / MEDIUM: **11** / LOW: **3** | P0: **1** / P1: **1** / P2: **6** / P3: **10** |

**FP Prevention**: 가설 43건 검증, 1건 FALSE_POSITIVE 제거 (거부율: 2.3%) | 교차 검증 10건 수행 (Critical+Major 전수)
**Cross-Agent**: 3건 교차 발견 (float→Decimal, equity CHECK, delete access)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 11건 하향 조정
- LOW 신뢰도 이슈 3건 하향 조정
- Cross-verification에서 심각도 하향 8건 (CRITICAL→MODERATE 2건, HIGH→MINOR 2건, HIGH→MODERATE 1건, MAJOR→MINOR 1건, MAJOR→MODERATE 1건, HIGH→LOW 1건)

---

## Findings

### [C-1] _STAGE_LABELS 키가 MarketingStage enum 값과 완전 불일치 — [Critical/HIGH] — Priority: P0

**위치**: `deal-mgmt/app/services/buyer_export_service.py:54-61`
**카테고리**: 완전성(§2) — 기능적 결함
**신뢰도**: HIGH (교차 검증 CONFIRMED)
**교차 검증**: review-verifier 확인 (+15)

**근거**:
```python
# buyer_export_service.py:54-61 — 현재 코드
_STAGE_LABELS: dict[str, str] = {
    "INITIAL_CONTACT": "초기 접촉",
    "NDA_PROCESS": "NDA 절차",
    "CIM_DISTRIBUTION": "CIM 배포",
    "IOI_PROCESS": "IOI 절차",
    "DD_PROCESS": "DD 절차",
    "FINAL_BID": "최종 입찰",
}

# enums.py:95-103 — 실제 MarketingStage enum 값
class MarketingStage(enum.StrEnum):
    IDENTIFIED = "IDENTIFIED"
    EMAIL_SENT = "EMAIL_SENT"
    PHONE_CALL = "PHONE_CALL"
    ADVISOR_MEETING = "ADVISOR_MEETING"
    NDA_SIGNED = "NDA_SIGNED"
    TARGET_MEETING = "TARGET_MEETING"
```

**설명**: `_STAGE_LABELS` 딕셔너리의 6개 키(`INITIAL_CONTACT`, `NDA_PROCESS` 등)가 `MarketingStage` enum의 6개 값(`IDENTIFIED`, `EMAIL_SENT` 등)과 **0% 일치**한다. `_STAGE_LABELS.get(stage, stage)` 호출 시 항상 키 매칭 실패하여 raw enum 값이 반환된다.

**영향**: Excel 내보내기의 "최근 활동 단계" 컬럼이 의도된 한글 라벨(`초기 접촉`, `NDA 절차` 등) 대신 항상 영문 raw 값(`IDENTIFIED`, `EMAIL_SENT` 등)을 표시한다. 19열 확장 기능의 핵심 사용자 경험이 깨짐.

**수정 제안**:
```python
_STAGE_LABELS: dict[str, str] = {
    "IDENTIFIED": "발굴",
    "EMAIL_SENT": "이메일 발송",
    "PHONE_CALL": "전화 접촉",
    "ADVISOR_MEETING": "어드바이저 미팅",
    "NDA_SIGNED": "NDA 체결",
    "TARGET_MEETING": "대상회사 미팅",
}
```

**우선순위 점수**: 100 × 1.0 + 15(verifier) = **115** → P0

---

### [M-1] extra_data nullable 불일치 BE↔FE — [Major/HIGH] — Priority: P1

**위치**: `deal-mgmt/app/schemas/buyer.py:32` (BE) / `amic-platform/src/modules/ma/types/buyer.ts:51` (FE)
**카테고리**: 안정성(§4) — 모듈 간 계약
**신뢰도**: HIGH (교차 검증 CONFIRMED)
**교차 검증**: review-verifier 확인 (+15)

**근거**:
```python
# BE: buyer.py:32
extra_data: dict | None = None  # nullable
```
```typescript
// FE: buyer.ts:51
extra_data: Record<string, unknown>;  // non-nullable
```

**설명**: BE 스키마에서 `extra_data`는 `dict | None`이므로 API 응답에 `null`이 올 수 있다. FE 타입에서 `Record<string, unknown>`으로 정의되어 `null`을 허용하지 않음.

**영향**: `extra_data`가 `null`인 buyer 조회 시 FE에서 `buyer.extra_data.someKey` 접근 시 런타임 TypeError 발생 가능.

**수정 제안**: FE 타입을 `extra_data: Record<string, unknown> | null`로 수정하고, 사용처에 null guard 추가.

**우선순위 점수**: 70 × 1.0 + 15(verifier) = **85** → P1

---

### [m-1] ConsortiumPanel 삭제 확인 대화상자 없음 — [Moderate/HIGH] — Priority: P2

**위치**: `amic-platform/src/modules/ma/components/buyers/ConsortiumPanel.tsx:249`
**카테고리**: 품질(§3) — UX
**신뢰도**: HIGH (교차 검증 CONFIRMED, Major에서 Moderate로 하향)
**교차 검증**: review-verifier 확인 (+15)

**근거**:
```tsx
// ConsortiumPanel.tsx:249
onClick={() => deleteMapping.mutate(m.id)}
```

**설명**: 삭제 버튼 클릭 시 확인 과정 없이 즉시 `mutate` 호출. `window.confirm()`, 모달, 토스트 확인 등 어떤 형태의 확인도 없음.

**영향**: 실수로 컨소시엄 매핑 삭제 가능. 매핑은 재생성 가능하고 감사 로그에 기록되므로 데이터 유실 위험은 제한적이나, UX 관행 위반.

**수정 제안**: `if (window.confirm("컨소시엄 매핑을 삭제하시겠습니까?")) deleteMapping.mutate(m.id)` 또는 기존 toast 확인 패턴 사용.

**우선순위 점수**: 40 × 1.0 + 15(verifier) = **55** → P2

---

### [m-2] update_consortium_mapping 불필요 buyer 재쿼리 — [Moderate/HIGH] — Priority: P2

**위치**: `deal-mgmt/app/routers/consortium.py:186-192`
**카테고리**: 품질(§3) — 성능
**신뢰도**: HIGH (교차 발견: python-quality + performance)
**교차 에이전트**: +10

**근거**:
```python
# consortium.py:186-192 — commit 후 불필요 재쿼리
lead = await db.get(BuyerCandidate, mapping.lead_buyer_id)
co = await db.get(BuyerCandidate, mapping.co_investor_buyer_id)
return {
    **ConsortiumMappingOut.model_validate(mapping).model_dump(),
    "lead_buyer_name": lead.company_name if lead else None,
    "co_investor_buyer_name": co.company_name if co else None,
}
```

**설명**: `update_consortium_mapping`은 status/equity_share_pct/notes만 수정하는데, commit 후 lead/co buyer를 재쿼리하여 company_name을 가져옴. 이 buyer 데이터는 수정되지 않았으므로 불필요한 DB 호출 2회.

**영향**: 매 UPDATE 요청마다 불필요한 SELECT 2회. 현재 규모에서 성능 영향은 미미하지만 비효율적.

**수정 제안**: mapping 객체에서 relationship으로 접근하거나, update 전에 이미 가져온 데이터를 재사용.

**우선순위 점수**: 40 × 1.0 + 10(cross) = **50** → P2

---

### [m-3] float → Decimal 패턴 불일치 — [Moderate/MEDIUM] — Priority: P2

**위치**: `deal-mgmt/app/models/buyer_candidate.py:32-36`, `deal-mgmt/app/models/consortium_mapping.py:47`
**카테고리**: 정합성(§1) — 패턴 불일치
**신뢰도**: MEDIUM (DESIGN_RISK — 교차 발견: python-quality + migration)
**교차 에이전트**: +10, 교차 검증: +15

⚠️ 이 이슈는 원래 CRITICAL로 보고되었으나, 교차 검증에서 DESIGN_RISK(기술부채)로 재분류되었습니다.

**근거**:
```python
# buyer_candidate.py:32-36
ioi_value: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
loi_value: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
final_offer_value: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)

# consortium_mapping.py:47
equity_share_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

# earnout.py:24-29 — 올바른 패턴
target_value: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
```

**설명**: DB 컬럼 `Numeric(20,2)`에 Python `float` 매핑 사용. 동일 코드베이스 `earnout.py`는 `Decimal`을 올바르게 사용. DB 레벨에서 정밀도는 보장되지만, Python 레벨의 부동소수점 정밀도 문제가 극단적 값에서 발생 가능.

**영향**: 실제 M&A 딜 금액 범위(~수조원)에서 float precision 문제 발생 가능성은 매우 낮으나, 패턴 통일이 바람직.

**수정 제안**: `Mapped[float]` → `Mapped[Decimal]`로 변경, 스키마에서도 `float` → `Decimal` 변환.

**우선순위 점수**: 40 × 0.6 + 10(cross) + 15(verifier) = **49** → P2

---

### [m-4] dart_company_search에 check_client_deal_access 누락 — [Moderate/MEDIUM] — Priority: P2

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:274-291`
**카테고리**: 안정성(§4) — 접근 제어
**신뢰도**: MEDIUM (교차 검증 CONFIRMED, HIGH에서 Moderate로 하향)
**교차 검증**: review-verifier 확인 (+15)

⚠️ 이 이슈는 원래 HIGH로 보고되었으나, 교차 검증에서 Moderate로 재분류되었습니다 (DART 검색은 외부 API 프록시이므로 실질적 데이터 노출 없음).

**근거**:
```python
# buyer_marketing.py:274-280
async def dart_company_search(...):
    await transaction_service.get_transaction(db, txn_id)  # 존재 여부만 확인
    # check_client_deal_access 호출 없음

# 비교 — dart_financial_summary (라인 294-302):
await check_client_deal_access(db, txn_id, claims)  # ← 있음
```

**설명**: `dart_company_search`는 `check_client_deal_access`를 호출하지 않아 CLIENT 역할이 할당되지 않은 딜의 DART 검색을 할 수 있음. 같은 파일의 `dart_financial_summary`는 올바르게 호출.

**영향**: DART 검색은 외부 API 프록시이므로 딜 데이터를 노출하지 않지만, 접근 제어 패턴 불일치.

**수정 제안**: `await check_client_deal_access(db, txn_id, claims)` 추가.

**우선순위 점수**: 40 × 0.6 + 15(verifier) = **39** → P2

---

### [m-5] equity_share_pct DB CHECK 제약조건 누락 — [Moderate/MEDIUM] — Priority: P2

**위치**: `deal-mgmt/app/models/consortium_mapping.py:47`, `deal-mgmt/migrations/versions/043_consortium_mapping.py`
**카테고리**: 안정성(§4) — 데이터 무결성
**신뢰도**: MEDIUM (교차 발견: security + migration)
**교차 에이전트**: +10

**근거**:
```python
# consortium_mapping.py:47
equity_share_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
# → DB 레벨 범위 검증 없음

# 스키마에서 Pydantic 검증:
equity_share_pct: float | None = Field(None, ge=0, le=100)
# → API 레벨에서만 검증
```

**설명**: `equity_share_pct`는 0~100% 범위여야 하나, DB 레벨의 `CheckConstraint`가 없음. Pydantic 스키마의 `Field(ge=0, le=100)`으로 API 레벨에서만 검증. 직접 DB 조작 시 범위 밖 값 입력 가능.

**영향**: Pydantic 우회 시(직접 SQL, 마이그레이션 스크립트 등) 잘못된 지분율 저장 가능.

**수정 제안**: `CheckConstraint("equity_share_pct >= 0 AND equity_share_pct <= 100")` 추가.

**우선순위 점수**: 40 × 0.6 + 10(cross) = **34** → P2

---

### [m-6] Content-Disposition 헤더 비검증 파일명 — [Moderate/MEDIUM] — Priority: P3

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:399-404`
**카테고리**: 안정성(§4) — 보안
**신뢰도**: MEDIUM

**근거**:
```python
# buyer_marketing.py:399-404
response.headers["Content-Disposition"] = (
    f'attachment; filename="{txn.code_name or txn_id}_buyers.xlsx"'
)
```

**설명**: `txn.code_name`이 사용자 입력으로, 특수문자(`"`, `\n` 등) 포함 시 Content-Disposition 헤더 인젝션 가능.

**영향**: 브라우저에서 파일명이 깨지거나, HTTP 응답 분할 공격 가능성 (매우 낮음).

**수정 제안**: `urllib.parse.quote(txn.code_name)` 또는 안전한 문자만 허용하는 sanitize 함수 적용.

**우선순위 점수**: 40 × 0.6 = **24** → P3

---

### [m-7] ConsortiumPanel ARIA 접근성 속성 누락 — [Moderate/MEDIUM] — Priority: P3

**위치**: `amic-platform/src/modules/ma/components/buyers/ConsortiumPanel.tsx:94-253`
**카테고리**: 품질(§3) — 접근성
**신뢰도**: MEDIUM

**설명**: `<select>`, `<input>`, `<button>` 요소에 `aria-label`, `aria-describedby` 등 ARIA 속성 누락. 스크린 리더 사용자가 폼 요소의 목적을 파악하기 어려움.

**영향**: WCAG 2.1 AA 기준 미달. 내부 도구이므로 법적 위험은 낮으나 접근성 모범 사례 위반.

**우선순위 점수**: 40 × 0.6 = **24** → P3

---

### [m-8] SOLE_BUYER가 컨소시엄 매핑에 포함 가능 — [Moderate/MEDIUM] — Priority: P3

**위치**: `deal-mgmt/app/routers/consortium.py:95-110` (create_consortium_mapping)
**카테고리**: 품질(§3) — 비즈니스 로직
**신뢰도**: MEDIUM

**설명**: `DealRole.SOLE_BUYER`인 buyer가 컨소시엄 매핑의 lead/co-investor로 등록 가능. 비즈니스 논리상 SOLE_BUYER는 단독 매수자이므로 컨소시엄 구조에 포함되면 모순.

**영향**: 데이터 모순 가능. 단, deal_role은 수시로 변경될 수 있어 엄격한 제약보다는 UI 경고가 적절할 수 있음.

**수정 제안**: 생성 시 SOLE_BUYER 체크 + 경고 반환, 또는 FE에서 SOLE_BUYER를 선택 옵션에서 필터링.

**우선순위 점수**: 40 × 0.6 = **24** → P3

---

### [L-1] delete_consortium_mapping check_client_deal_access 패턴 불일치 — [Minor/MEDIUM] — Priority: P2

**위치**: `deal-mgmt/app/routers/consortium.py:198-222`
**카테고리**: 정합성(§1) — 패턴 일관성
**신뢰도**: MEDIUM (교차 검증 PARTIAL, HIGH에서 Minor로 하향)
**교차 에이전트**: +10, 교차 검증: +15

⚠️ 원래 HIGH(보안)으로 보고되었으나, 교차 검증에서 `require_write_access()`가 CLIENT를 이미 차단하고 `check_client_deal_access`는 비-CLIENT에게 no-op이므로 실질적 보안 취약점 없음 확인. 패턴 일관성 이슈로 재분류.

**우선순위 점수**: 20 × 0.6 + 10(cross) + 15(verifier) = **37** → P2

---

### [L-2] server_default ORM↔마이그레이션 불일치 — [Minor/MEDIUM] — Priority: P3

**위치**: `deal-mgmt/app/models/consortium_mapping.py:44-46` / `deal-mgmt/migrations/versions/043_consortium_mapping.py:92-103`
**카테고리**: 정합성(§1)
**신뢰도**: MEDIUM (교차 검증 CONFIRMED, MAJOR에서 Minor로 하향)
**교차 검증**: review-verifier 확인 (+15)

**설명**: 마이그레이션 DDL에 `server_default="TAPPING"` 있으나 ORM 모델에는 `default=ConsortiumStatus.TAPPING`만 있음. 런타임 동작에 영향 없으나 Alembic autogenerate 시 불필요한 drift 감지 가능.

**우선순위 점수**: 20 × 0.6 + 15(verifier) = **27** → P3

---

### [L-3] buyer_marketing_logs 복합 인덱스 — [Minor/MEDIUM] — Priority: P3

**위치**: `deal-mgmt/app/models/buyer_marketing_log.py`
**카테고리**: 품질(§3) — 성능
**신뢰도**: MEDIUM (교차 검증 DESIGN_RISK, HIGH에서 Minor로 하향)
**교차 검증**: review-verifier 확인 (+15)

**설명**: `(transaction_id, buyer_id, stage, log_date)` 복합 인덱스 없음. 현재 데이터 규모에서 문제 없으나, 향후 데이터 성장 시 GROUP BY/ORDER BY 쿼리 성능 저하 가능.

**우선순위 점수**: 20 × 0.6 + 15(verifier) = **27** → P3

---

### [L-4] buyers.py 반환 타입 힌트 누락 — [Minor/MEDIUM] — Priority: P3

**위치**: `deal-mgmt/app/routers/buyers.py`
**카테고리**: 정합성(§1) — 코딩 표준
**신뢰도**: MEDIUM

**설명**: 6개 핸들러 함수에 반환 타입 힌트 누락. CI 강행 규정(python-ci-standards.md)에서 모든 함수에 타입 힌트를 요구.

**우선순위 점수**: 20 × 0.6 = **12** → P3

---

### [L-5] Query invalidation 범위 차이 — [Minor/MEDIUM] — Priority: P3

**위치**: `amic-platform/src/modules/ma/hooks/useConsortiumMappings.ts`
**카테고리**: 정합성(§1) — 패턴
**신뢰도**: MEDIUM

**설명**: `useConsortiumMappings`의 mutation onSuccess에서 쿼리 무효화 범위가 `useMarketingLogs`보다 좁음. 기존 훅은 관련 쿼리를 더 넓게 무효화.

**우선순위 점수**: 20 × 0.6 = **12** → P3

---

### [L-6] Function-level import — [Minor/LOW] — Priority: P3

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:229,284,344,388`
**카테고리**: 정합성(§1)
**신뢰도**: LOW

**설명**: `BuyerTier`, `ConsortiumMapping`, `aliased`, `build_buyer_excel`를 함수 내부에서 import. 순환 참조 방지 목적이라면 정당화되지만, 그렇지 않다면 모듈 최상단으로 이동 권장.

**우선순위 점수**: 20 × 0.3 = **6** → P3

---

### [L-7] notes 필드 길이 제한 없음 — [Minor/LOW] — Priority: P3

**위치**: `deal-mgmt/app/models/consortium_mapping.py:48`
**카테고리**: 안정성(§4)
**신뢰도**: LOW

**설명**: `notes: Mapped[str | None] = mapped_column(Text, nullable=True)` — `Text` 타입은 길이 무제한. 악의적 대용량 입력 가능성.

**우선순위 점수**: 20 × 0.3 = **6** → P3

---

### [L-8] created_by_email 자동 주입 미문서화 — [Minor/LOW] — Priority: P3

**위치**: `deal-mgmt/app/routers/buyer_marketing.py` (create_marketing_log)
**카테고리**: 완전성(§2)
**신뢰도**: LOW

**설명**: `created_by_email`이 JWT claims에서 자동 추출되어 저장되는 동작이 API 문서나 스키마에 명시되지 않음. 클라이언트가 이 필드를 직접 설정하려 하면 무시됨.

**우선순위 점수**: 20 × 0.3 = **6** → P3

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
1. [C-1] [Critical/HIGH]: _STAGE_LABELS enum 키 완전 불일치 — buyer_export_service.py (점수: 115)

### P1 — 스프린트 우선 (점수: 60-89)
1. [M-1] [Major/HIGH]: extra_data nullable 불일치 BE↔FE — buyer.ts (점수: 85)

### P2 — 개선 권장 (점수: 30-59)
1. [m-1] [Moderate/HIGH]: ConsortiumPanel 삭제 확인 없음 — ConsortiumPanel.tsx (점수: 55)
2. [m-2] [Moderate/HIGH]: update_consortium 불필요 buyer 재쿼리 — consortium.py (점수: 50)
3. [m-3] [Moderate/MEDIUM ⚠️]: float→Decimal 패턴 불일치 — buyer_candidate.py (점수: 49, 원래 Critical→Moderate 하향)
4. [m-4] [Moderate/MEDIUM ⚠️]: dart_company_search 접근 제어 누락 — buyer_marketing.py (점수: 39, 원래 High→Moderate 하향)
5. [L-1] [Minor/MEDIUM ⚠️]: delete_consortium 패턴 불일치 — consortium.py (점수: 37, 원래 High→Minor 하향)
6. [m-5] [Moderate/MEDIUM]: equity_share_pct DB CHECK 누락 — consortium_mapping.py (점수: 34)

### P3 — 저우선 (점수: <30)
1. [L-2] [Minor/MEDIUM ⚠️]: server_default ORM↔마이그레이션 불일치 (점수: 27, 원래 Major→Minor 하향)
2. [L-3] [Minor/MEDIUM ⚠️]: buyer_marketing_logs 복합 인덱스 (점수: 27, 원래 High→Minor 하향)
3. [m-6] [Moderate/MEDIUM]: Content-Disposition 헤더 (점수: 24)
4. [m-7] [Moderate/MEDIUM]: ARIA 접근성 누락 (점수: 24)
5. [m-8] [Moderate/MEDIUM]: SOLE_BUYER 컨소시엄 참여 가능 (점수: 24)
6. [L-4] [Minor/MEDIUM]: 반환 타입 힌트 누락 (점수: 12)
7. [L-5] [Minor/MEDIUM]: Query invalidation 범위 차이 (점수: 12)
8. [L-6] [Minor/LOW]: Function-level import (점수: 6)
9. [L-7] [Minor/LOW]: notes 길이 제한 없음 (점수: 6)
10. [L-8] [Minor/LOW]: created_by_email 미문서화 (점수: 6)

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| F-1 | DealRole, ConsortiumStatus enum | ✅ | enums.py:105-120 |
| F-2 | BuyerCandidate CI Guard 2 수정 + deal_role | ✅ | buyer_candidate.py (Uuid, JSON variant) |
| F-3 | BuyerMarketingLog.created_by_email | ✅ | buyer_marketing_log.py |
| F-4 | ConsortiumMapping 모델 | ✅ | consortium_mapping.py |
| F-5 | 모델 레지스트리 업데이트 | ✅ | models/__init__.py |
| F-6 | Alembic 마이그레이션 043 | ✅ | 043_consortium_mapping.py |
| G-1 | Buyer 스키마 deal_role | ✅ | schemas/buyer.py |
| G-2 | MarketingLog created_by_email | ✅ | schemas/marketing_log.py |
| G-3 | Consortium 스키마 | ✅ | schemas/consortium.py |
| G-4 | Consortium CRUD API (5개) | ✅ | routers/consortium.py |
| G-5 | Excel 19열 확장 | ⚠️ | buyer_export_service.py — _STAGE_LABELS 불일치 (C-1) |
| G-6 | MarketingLog created_by 저장 | ✅ | routers/buyer_marketing.py |
| G-7 | main.py 라우터 등록 | ✅ | main.py |
| H-1 | Buyer 타입 확장 | ⚠️ | buyer.ts — extra_data nullable 불일치 (M-1) |
| H-2 | Consortium 타입 | ✅ | types/consortium.ts |
| H-3 | 상수 추가 | ✅ | constants.ts |
| H-4 | Consortium 훅 | ✅ | hooks/useConsortiumMappings.ts |
| H-5 | DealRoleBadge | ✅ | DealRoleBadge.tsx |
| H-6 | ConsortiumPanel | ⚠️ | ConsortiumPanel.tsx — 삭제 확인 없음 (m-1) |
| H-7 | ShortListOverview 수정 | ✅ | ShortListOverview.tsx |
| H-8 | NDA_SIGNED 토스트 제안 | ✅ | ShortListOverview.tsx |
| H-9 | TransactionWorkspacePage 수정 | ✅ | TransactionWorkspacePage.tsx |
| I-1 | Consortium CRUD 테스트 | ✅ | test_consortium.py (13/13) |

**구현율**: 20/23 항목 완전 구현 (87%), 3건 부분 구현 (C-1, M-1, m-1)

---

## 품질 게이트 상태 (§7)

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| ruff check | ✅ PASS | §1 린트 정합성 [자동 검증됨] |
| ruff format | ✅ PASS | §1 포맷팅 [자동 검증됨] |
| pytest | ✅ 924/928 PASS (4건 pre-existing VDR) | §2 테스트 완전성 [자동 검증됨] |
| tsc --noEmit | ✅ PASS | §3 타입 에러 [자동 검증됨] |
| vite build | ✅ PASS | §2 빌드 성공 [자동 검증됨] |

---

## Methodology

- **Agents**: backend-security-reviewer, python-code-reviewer, performance-profiler, migration-validator, general-purpose (frontend)
- **Excluded Agents**: 0개
- **Files scanned**: ~30개 (deal-mgmt 22파일 + amic-platform 8파일)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 10건 전수 검증
- **Backend availability**: deal-mgmt(available), FDD(available), KIIS(available), IM(available)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 43건
- 거부된 가설 (사전 제거): 1건
- 보고된 이슈: 18건
- 거부율: 2.3%

### 교차 검증 결과 (10건)

| # | 이슈 | 원래 심각도 | 판정 | 조정 심각도 |
|---|------|-----------|------|-----------|
| 1 | _STAGE_LABELS 불일치 | Critical | CONFIRMED | Critical |
| 2 | float→Decimal | Critical | DESIGN_RISK | Moderate |
| 3 | downgrade() enum 삭제 | Critical | DESIGN_RISK | Low (보고 제외) |
| 4 | delete check_client_deal_access | High | PARTIAL | Minor |
| 5 | dart_company_search access | High | CONFIRMED | Moderate |
| 6 | marketing log CRUD access | High | FALSE_POSITIVE (FP-IMPL) | N/A |
| 7 | server_default mismatch | Major | CONFIRMED | Minor |
| 8 | extra_data nullable | Major | CONFIRMED | Major |
| 9 | ConsortiumPanel delete confirm | Major | CONFIRMED | Moderate |
| 10 | marketing_logs index | High | DESIGN_RISK | Minor |

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 심각도 과대 평가 | 7 | CRITICAL→Moderate (float→Decimal: DB Numeric이 정밀도 보장) |
| 반증됨 | 1 | marketing log CRUD: list에 check_client_deal_access 실제 존재 |
| 패턴 재평가 | 1 | downgrade() enum: sa.Enum.drop()이 표준 API |
| 보안 위협 재평가 | 1 | delete check: require_write_access()가 CLIENT 차단 |
