# Code Review (Supplementary) — MA 마케팅 로그 + 미팅 로그 통합

> **Review Date**: 2026-03-11 12:20
> **Reviewer**: Claude Code (review-orchestrate — R2~R6 보충 리뷰)
> **Scope**: Marketing Log + Meeting Log Unification (BE migration, API compatibility, FE components)
> **Method**: 13개 관점 중 미수행 8개 관점 보충 — R3(데이터 무결성 + API 계약), R4+R5(회복성 + 운영), R6(비즈니스/UX + 접근성 + 테스트)
> **Base Review**: `20260311_1038_MA_Log_Unification_Code_Review.md` (P0-P2 수정 완료 후)
> **Quality Gates**: tsc(PASS) ruff(PASS) — 이전 세션에서 검증 완료

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 5     | HIGH: 4 / MEDIUM: 1 / LOW: 0 | P1: 4 / P2: 1 |
| Moderate | 5     | HIGH: 3 / MEDIUM: 2 / LOW: 0 | P2: 3 / P3: 2 |
| Minor    | 5     | HIGH: 2 / MEDIUM: 3 / LOW: 0 | P3: 5 |
| **Total**| **15**| HIGH: **9** / MEDIUM: **6** / LOW: **0** | P1: **4** / P2: **4** / P3: **7** |

**이전 리뷰 대비**: P0 이슈 0건 (이전 P0-P2 모두 수정 완료)

**중복 제거**: R3-11 = D5 (호환 레이어 auto_advance 누락) → 병합
**이미 수정된 이슈 제외**: 7건 (H-01 접근제어, Perf-2 SQL최적화, R1 auto_advance, R3 buyer_id검증, M-01 인덱스, M-04 downgrade경고, F1 null리셋)

**교차 검증**: R3-11과 D5가 동일 이슈를 독립 발견 → 교차검증 보너스 +10

---

## Findings

### [S-01] create_meeting_log에 buyer_id 교차 거래 검증 누락 — [Major/HIGH] — Priority: P1

**파일**: `deal-mgmt/app/routers/meeting_logs.py`
**위치**: `create_meeting_log` 함수 (기존 리뷰에서 update에만 검증 추가됨)

**증거**:
- 이전 P2 수정에서 `update_meeting_log`에 buyer_id 교차 거래 검증 추가됨
- 그러나 `create_meeting_log`에는 동일 검증이 **여전히 누락**
- 공격자가 다른 거래의 buyer_id를 지정하여 미팅 로그 생성 가능

**영향**: 데이터 무결성 위반 — 거래 A의 매수자가 거래 B의 미팅 로그에 연결될 수 있음

**검증 추적**: R3 에이전트 → Read로 create_meeting_log 확인 → update와 비교 → 누락 확인
**우선순위 점수**: 70 × 1.0 = **70** (P1)

**수정 제안**:
```python
# create_meeting_log에서 buyer_id 검증 추가 (update와 동일 패턴)
if body.buyer_id is not None:
    buyer_q = select(BuyerCandidate).where(
        BuyerCandidate.id == body.buyer_id,
        BuyerCandidate.transaction_id == txn_id,
    )
    if not (await db.execute(buyer_q)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="해당 거래에 속하지 않는 매수자입니다")
```

---

### [S-02] 호환 레이어 update_marketing_log에 auto_advance 누락 — [Major/HIGH] — Priority: P1

**파일**: `deal-mgmt/app/routers/buyer_marketing.py`
**위치**: `update_marketing_log` 함수

**증거**:
- `meeting_logs.py`의 `create_meeting_log`에는 auto_advance 로직 존재
- `meeting_logs.py`의 `update_meeting_log`에도 P1 수정으로 auto_advance 추가됨
- 그러나 호환 레이어 `buyer_marketing.py`의 `update_marketing_log`는 내부적으로 meeting_logs를 조작하지만 auto_advance를 호출하지 않음
- 호환 API를 통해 marketing_stage를 변경하면 buyer.status 자동 승격이 발생하지 않음

**영향**: 호환 API 경로와 신규 API 경로의 동작 불일치 — 동일 작업의 결과가 API 경로에 따라 다름

**교차 검증**: R3 에이전트 + R6 에이전트 독립 발견 (R3-11 = D5)
**우선순위 점수**: 70 × 1.0 + 10 (cross-agent) = **80** (P1)

**수정 제안**:
```python
# buyer_marketing.py update_marketing_log에 auto_advance 추가
if body.stage:
    target = buyer_status_service.get_advance_target(body.stage)
    if target and buyer:
        await buyer_status_service.auto_advance_buyer_status(db, buyer, target, claims.email)
```

---

### [S-03] auto_advance 실패 시 전체 미팅 로그 생성 롤백 — [Major/HIGH] — Priority: P1

**파일**: `deal-mgmt/app/routers/meeting_logs.py`
**위치**: `create_meeting_log` 함수 내 auto_advance 호출부

**증거**:
- auto_advance_buyer_status가 예외를 발생시키면 같은 트랜잭션 내이므로 미팅 로그 INSERT도 롤백됨
- 미팅 로그 기록은 성공해야 하고, buyer.status 승격은 부가 효과이므로 실패 격리가 필요
- 현재 try/except 없이 직접 호출

**영향**: buyer_status 테이블 무결성 문제 시 미팅 로그 자체도 저장 불가

**검증 추적**: R4+R5 에이전트 → create_meeting_log 코드 Read → auto_advance 호출부 확인 → 실패 격리 없음 확인
**우선순위 점수**: 70 × 1.0 = **70** (P1)

**수정 제안**:
```python
# auto_advance를 try/except로 감싸서 실패 격리
try:
    await buyer_status_service.auto_advance_buyer_status(db, buyer, target, claims.email)
except Exception:
    import logging
    logging.getLogger(__name__).warning("auto_advance failed for buyer %s", buyer.id, exc_info=True)
```

---

### [S-04] 마이그레이션 080 downgrade 시 통합 후 신규 데이터 손실 — [Major/HIGH] — Priority: P1

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`
**위치**: `downgrade()` 함수

**증거**:
- downgrade()에서 `marketing_stage IS NOT NULL`인 meeting_logs 레코드를 삭제
- 그러나 마이그레이션 이후 신규로 생성된 marketing_stage 미팅 로그도 함께 삭제됨
- 원본 buyer_marketing_logs 테이블에는 마이그레이션 이후 데이터가 없으므로 복구 불가
- 경고 주석은 이전 P2에서 추가되었지만, 실제 데이터 보호 메커니즘은 없음

**영향**: 롤백 시 마이그레이션 이후 생성된 마케팅 활동 기록 영구 손실

**검증 추적**: R4+R5 에이전트 → downgrade 코드 Read → 삭제 범위 분석
**우선순위 점수**: 70 × 1.0 = **70** (P1)

**수정 제안**:
```python
# downgrade에서 삭제 전 백업 테이블 생성
op.execute("""
    CREATE TABLE IF NOT EXISTS _backup_marketing_meeting_logs AS
    SELECT * FROM meeting_logs WHERE marketing_stage IS NOT NULL
""")
# 이후 기존 삭제 로직 수행
```

---

### [S-05] 이중 API 경로 — LogListPopover가 marketing-logs API 사용 — [Major/MEDIUM] — Priority: P2

**파일**: FE 컴포넌트 (LogListPopover 등)

**증거**:
- 신규 InlineLogInput은 meeting-logs API 사용 (통합 완료)
- 그러나 기존 LogListPopover 등 일부 컴포넌트는 여전히 marketing-logs API로 읽기/삭제 수행
- 호환 레이어가 중간에서 변환하므로 기능적으로는 동작하지만, 장기적으로 혼란 유발

**영향**: 기술 부채 — 두 API 경로가 공존하여 유지보수 복잡도 증가. 즉시 장애는 아님.

**검증 추적**: R6 에이전트 → Grep으로 marketing-logs API 호출처 확인
**우선순위 점수**: 70 × 0.6 = **42** (P2)

**수정 제안**: 호환 레이어를 deprecated로 표시하고, 점진적으로 FE를 meeting-logs API로 전환. 긴급 수정 불필요.

---

### [S-06] 마이그레이션 080에서 원본 ID 미보존 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**:
- buyer_marketing_logs → meeting_logs 복사 시 새 UUID 생성
- 원본 buyer_marketing_log의 ID를 meeting_log에 매핑하는 컬럼이 없음
- 감사 추적이나 데이터 정합성 검증 시 원본-복사 매핑 불가

**영향**: 마이그레이션 후 데이터 추적성 상실. 원본 로그와 복사본의 대응 관계 확인 불가.

**우선순위 점수**: 40 × 1.0 = **40** (P2)

**수정 제안**: 마이그레이션 복사 시 `original_marketing_log_id` 컬럼을 임시로 추가하여 매핑 보존. 또는 별도 매핑 테이블 생성.

---

### [S-07] QNA_COMPLETED 스테이지 매핑 미구현 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/app/services/buyer_status_service.py` (추정)

**증거**:
- MarketingStage Enum에 QNA_COMPLETED가 존재
- 그러나 auto_advance의 stage→target 매핑에서 QNA_COMPLETED에 대한 매핑이 명확하지 않을 수 있음
- QNA 완료 시 자동 승격이 발생하지 않을 수 있음

**영향**: QNA 완료 기록 시 buyer.status 자동 승격 누락 가능

**우선순위 점수**: 40 × 1.0 = **40** (P2)

---

### [S-08] FE/BE 자동 제목 라벨 불일치 — [Moderate/MEDIUM] — Priority: P3

**파일**: FE `InlineLogInput.tsx` vs BE `buyer_marketing.py`

**증거**:
- FE InlineLogInput에서 자동 생성하는 title에 약어 사용 ("NDA")
- BE 호환 레이어에서 생성하는 title에 전체 명칭 사용 ("NDA 체결")
- 같은 stage에 대해 입력 경로에 따라 제목 형식이 다름

**영향**: UI 일관성 저하 — 기능적 영향 없음

**우선순위 점수**: 40 × 0.6 = **24** (P3)

---

### [S-09] 배포 시 마이그레이션 순서 주의 필요 — [Moderate/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**:
- 마이그레이션 080은 buyer_marketing_logs 데이터를 meeting_logs로 복사
- 배포 시 마이그레이션이 먼저 실행되고 새 코드가 적용되는 순서가 보장되어야 함
- deploy.yml에서 마이그레이션 → 코드 적용 순서가 올바른지 확인 필요

**영향**: 잘못된 배포 순서 시 일시적 500 에러 가능

**우선순위 점수**: 40 × 0.6 = **24** (P3)

---

### [S-10] 통합 테스트 부재 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/tests/` (부재)

**증거**:
- meeting_log 라우터의 CRUD 통합 테스트가 존재하지 않음
- 특히 auto_advance, buyer_id 교차 검증, 호환 레이어 등 새로 추가된 로직의 테스트 없음
- 향후 리팩토링 시 회귀 버그 발견 불가

**영향**: 테스트 커버리지 부족 — 기술 부채

**우선순위 점수**: 40 × 1.0 = **40** (P2)

---

### [S-11] 마이그레이션에서 ix_meeting_logs_txn_phase 중복 생성 가능성 — [Minor/HIGH] — Priority: P3

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**:
- 모델에 `__table_args__`로 인덱스 정의 + 마이그레이션에서도 인덱스 생성
- Alembic이 모델의 인덱스를 자동 감지하면 다음 autogenerate에서 중복 생성 시도 가능
- 현재는 명시적 마이그레이션이므로 즉시 문제는 아님

**영향**: 향후 autogenerate 시 혼란 가능

**우선순위 점수**: 20 × 1.0 = **20** (P3)

---

### [S-12] meeting_log_summary 캐시 없음 — [Minor/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/app/routers/meeting_logs.py`

**증거**:
- summary 엔드포인트는 매 호출마다 SQL 집계 쿼리 실행
- 대시보드에서 자주 호출될 수 있으나 캐시 레이어 없음

**영향**: 고빈도 호출 시 DB 부하. 현재 규모에서는 문제 없음.

**우선순위 점수**: 20 × 0.6 = **12** (P3)

---

### [S-13] 호환 레이어에 deprecation 표시 없음 — [Minor/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/app/routers/buyer_marketing.py`

**증거**:
- 호환 레이어 엔드포인트들이 deprecation 주석이나 OpenAPI deprecated 태그 없음
- 향후 제거 시점이 불명확

**영향**: 기술 부채 관리 어려움

**우선순위 점수**: 20 × 0.6 = **12** (P3)

---

### [S-14] auto_advance 호출 시 로깅 없음 — [Minor/HIGH] — Priority: P3

**파일**: `deal-mgmt/app/routers/meeting_logs.py`

**증거**:
- auto_advance 성공/실패에 대한 로깅이 없음
- 운영 환경에서 buyer.status 자동 변경 추적 불가

**영향**: 운영 가시성 부족

**우선순위 점수**: 20 × 1.0 = **20** (P3)

---

### [S-15] 마이그레이션에서 channel 기본값 EMAIL 하드코딩 — [Minor/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**:
- buyer_marketing_logs → meeting_logs 복사 시 `channel = 'EMAIL'`로 하드코딩
- 실제로는 다른 채널(전화, 대면 등)로 기록된 마케팅 활동도 있을 수 있음
- 원본 테이블에 channel 필드가 없으므로 불가피한 선택이지만 정확도 저하

**영향**: 마이그레이션된 데이터의 channel 정보 부정확. 기존 데이터 한정.

**우선순위 점수**: 20 × 0.6 = **12** (P3)

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. **[S-02]** [Major/HIGH] 호환 레이어 auto_advance 누락 — buyer_marketing.py (점수: 80, 교차검증)
2. **[S-01]** [Major/HIGH] create_meeting_log buyer_id 교차 거래 검증 누락 — meeting_logs.py (점수: 70)
3. **[S-03]** [Major/HIGH] auto_advance 실패 시 전체 롤백 — meeting_logs.py (점수: 70)
4. **[S-04]** [Major/HIGH] downgrade 시 신규 데이터 손실 — migration 080 (점수: 70)

### P2 — 개선 권장 (점수: 30-59)
1. **[S-05]** [Major/MEDIUM] 이중 API 경로 (점수: 42)
2. **[S-06]** [Moderate/HIGH] 원본 ID 미보존 (점수: 40)
3. **[S-07]** [Moderate/HIGH] QNA_COMPLETED 매핑 확인 필요 (점수: 40)
4. **[S-10]** [Moderate/HIGH] 통합 테스트 부재 (점수: 40)

### P3 — 저우선 (점수: <30)
1. **[S-08]** [Moderate/MEDIUM] FE/BE 자동 제목 라벨 불일치 (점수: 24)
2. **[S-09]** [Moderate/MEDIUM] 배포 시 마이그레이션 순서 주의 (점수: 24)
3. **[S-11]** [Minor/HIGH] 인덱스 중복 생성 가능성 (점수: 20)
4. **[S-14]** [Minor/HIGH] auto_advance 로깅 없음 (점수: 20)
5. **[S-12]** [Minor/MEDIUM] summary 캐시 없음 (점수: 12)
6. **[S-13]** [Minor/MEDIUM] deprecation 표시 없음 (점수: 12)
7. **[S-15]** [Minor/MEDIUM] channel 기본값 하드코딩 (점수: 12)

---

## Methodology

- **Agents**: R3 (데이터 무결성 + API 계약), R6 (비즈니스/UX + 접근성 + 테스트), R4+R5 (회복성 + 운영)
- **Excluded Agents**: R1 (정합성), R2 (완전성) — 초기 리뷰에서 수행 완료
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: R3-11 = D5 (호환 레이어 auto_advance) 교차 확인
- **Already Fixed**: 7건 제외 (H-01, Perf-2, R1, R3, M-01, M-04, F1)

## 이전 리뷰 대비 변경

| 구분 | 초기 리뷰 | 보충 리뷰 |
|------|----------|----------|
| 관점 | 5개 (코드리뷰, 타입, API, 보안, 접근성) | 8개 (데이터무결성, API계약, 회복성, 운영, 비즈니스, UX, 접근성, 테스트) |
| P0 | 2건 (모두 수정 완료) | 0건 |
| P1 | 1건 (수정 완료) | 4건 (신규) |
| P2 | 3건 (수정 완료) | 4건 (신규) |
| P3 | 5건 | 7건 |
