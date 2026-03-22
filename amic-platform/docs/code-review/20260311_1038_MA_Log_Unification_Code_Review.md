# Code Review — MA 마케팅 로그 + 미팅 로그 통합

> **Review Date**: 2026-03-11 10:38
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Marketing Log + Meeting Log Unification (BE migration, API, FE components)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(N/A) build(N/A)
> **Review Gates**: Backend(available) Agent-Filtering(5개 에이전트 호출, 0개 제외)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 3     | HIGH: 3 / MEDIUM: 0 / LOW: 0 | P0: 2 / P1: 1 |
| Moderate | 4     | HIGH: 3 / MEDIUM: 1 / LOW: 0 | P2: 3 / P3: 1 |
| Minor    | 4     | HIGH: 2 / MEDIUM: 2 / LOW: 0 | P3: 4 |
| **Total**| **11**| HIGH: **8** / MEDIUM: **3** / LOW: **0** | P0: **2** / P1: **1** / P2: **3** / P3: **5** |

**FP Prevention**: 가설 15건 검증, 2건 사전 거부 (거부율: 13%) | 교차 검증 6건 수행
- R2 (stage-summary invalidation 누락): TanStack Query prefix matching이 `buyers` 키로 커버됨 → **FP 제거**
- Py-1 (stage_map type safety): `meeting_date`가 `String(10)` 컬럼이므로 `func.max()`도 문자열 반환 → **FP 제거**

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 3건 하향 조정

---

## Findings

### [H-01/R7] create/update/delete_meeting_log에 check_client_deal_access 누락 — [Major/HIGH] — Priority: P0

**파일**: `deal-mgmt/app/routers/meeting_logs.py`
**위치**: create(L137-183), update(L186-210), delete(L213-239)

**증거**:
- `list_meeting_logs`(L57), `get_meeting_log`(L118), `meeting_log_summary`(L94)는 모두 `check_client_deal_access` 호출
- 반면 `create_meeting_log`는 `require_write_access()` JWT 권한만 검증, deal-level 접근 제어 없음
- `update_meeting_log`, `delete_meeting_log`도 동일하게 누락
- 비교: `buyer_marketing.py`의 `create_marketing_log`(L138)는 `check_client_deal_access` 호출함

**영향**: 쓰기 권한이 있는 사용자가 접근 권한 없는 다른 딜의 미팅 로그를 생성/수정/삭제 가능

**교차 검증**: security-auditor + code-reviewer + python-reviewer 3개 에이전트 독립 발견, review-verifier 확인
**우선순위 점수**: 70 × 1.0 + 15 (verifier) + 10 (cross-agent) = **95**

**수정 제안**:
```python
# create_meeting_log 함수 시작부에 추가
await check_client_deal_access(db, txn_id, claims)

# update_meeting_log, delete_meeting_log에도 동일 추가
txn = await _get_log_or_404(db, txn_id, log_id)
await check_client_deal_access(db, txn_id, claims)  # 추가
```

---

### [Perf-2/Py-3] meeting_log_summary가 전체 ORM 객체를 로드하여 Python에서 카운팅 — [Major/HIGH] — Priority: P0

**파일**: `deal-mgmt/app/routers/meeting_logs.py`
**위치**: L86-108

**증거**:
```python
# 현재 코드: 전체 MeetingLog 객체 로드 (minutes, summary 텍스트 + JSON 필드 포함)
result = await db.execute(q)
logs = result.scalars().all()
for log in logs:
    by_status[log.status.value] = by_status.get(log.status.value, 0) + 1
    by_channel[log.channel.value] = by_channel.get(log.channel.value, 0) + 1
```

- 비교: `buyer_marketing.py`(L291-300)의 `marketing_stage_summary`는 올바르게 SQL `GROUP BY` + `func.max()` 사용

**영향**: 미팅 로그가 많은 거래에서 불필요한 메모리 소비 및 응답 지연

**교차 검증**: performance-profiler + python-reviewer 독립 발견, review-verifier 확인
**우선순위 점수**: 70 × 1.0 + 15 (verifier) + 10 (cross-agent) = **95**

**수정 제안**:
```python
# SQL GROUP BY 방식으로 전환
from sqlalchemy import func
status_q = select(MeetingLog.status, func.count()).where(...).group_by(MeetingLog.status)
channel_q = select(MeetingLog.channel, func.count()).where(...).group_by(MeetingLog.channel)
```

---

### [R4] update_meeting_log에 marketing_stage 변경 시 auto-advance 누락 — [Major/HIGH] — Priority: P1

**파일**: `deal-mgmt/app/routers/meeting_logs.py`
**위치**: L186-210

**증거**:
- `create_meeting_log`(L167-179): `body.marketing_stage` + `body.buyer_id` 존재 시 `auto_advance_buyer_status()` 호출
- `update_meeting_log`: `setattr` 루프로 필드 업데이트 후 커밋만 수행, auto-advance 로직 없음
- `delete_meeting_log`(L229-238): 삭제 시 `check_status_after_delete` 호출 (역방향 처리)

**영향**: 미팅 로그 수정으로 marketing_stage를 변경해도 buyer.status가 자동 승격되지 않음

**교차 검증**: review-verifier 확인
**우선순위 점수**: 70 × 1.0 + 15 (verifier) = **85**

**수정 제안**:
```python
# update 함수에서 marketing_stage 변경 감지 시 auto-advance 호출
if "marketing_stage" in update_data and log.buyer_id:
    from app.services import buyer_status_service
    await buyer_status_service.auto_advance_buyer_status(db, txn_id, log.buyer_id)
```

---

### [R1/M-05] downgrade에서 마이그레이션 후 생성된 marketing_stage 로그도 삭제됨 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**:
- `downgrade()`에서 `marketing_stage` 컬럼 DROP 시, 마이그레이션 이후 직접 생성된 meeting log의 marketing_stage 정보가 소실됨
- 원본 `buyer_marketing_logs` 테이블은 보존되지만, 통합 후 새로 입력된 데이터는 복구 불가

**영향**: 롤백 시 마이그레이션 이후 입력된 마케팅 활동 데이터 소실 가능

**교차 검증**: migration-validator + security-auditor + code-reviewer 독립 발견
**우선순위 점수**: 40 × 1.0 + 10 (cross-agent) = **50**

**참고**: 이는 마이그레이션의 본질적 한계. downgrade 주석에 경고 추가 권장.

---

### [M-02] MeetingLogUpdate에서 buyer_id 변경 시 cross-txn 검증 누락 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/app/schemas/meeting_log.py` + `deal-mgmt/app/routers/meeting_logs.py`

**증거**:
- `MeetingLogUpdate` 스키마에 `buyer_id: str | None` 필드 존재
- `update_meeting_log`에서 buyer_id 값을 검증 없이 `setattr`로 적용
- 다른 거래의 buyer_id로 변경 가능

**영향**: 미팅 로그가 잘못된 매수자에게 연결될 수 있음

**우선순위 점수**: 40 × 1.0 = **40**

---

### [Perf-1] (transaction_id, meeting_phase) 복합 인덱스 누락 — [Moderate/HIGH → DESIGN_RISK] — Priority: P2

**파일**: `deal-mgmt/app/models/meeting_log.py`

**증거**:
- `transaction_id`: 개별 `index=True` (L29)
- `meeting_phase`: 인덱스 없음 (L33)
- `list_meeting_logs`, `meeting_log_summary`에서 둘 다 필터 조건으로 사용

**영향**: 현재 데이터 규모에서는 개별 인덱스로 충분하나, 규모 성장 시 성능 저하 가능

**교차 검증**: review-verifier → DESIGN_RISK로 하향 (현재 규모에서 비임계)
**우선순위 점수**: 40 × 1.0 + 15 (verifier) = **55**

---

### [R5] MeetingLogForm에서 marketing_stage를 null로 리셋 불가 — [Moderate/HIGH] — Priority: P2 (미검증)

**파일**: `amic-platform/src/modules/ma/components/meetings/MeetingLogForm.tsx`
**위치**: L76, L90

**증거**:
```typescript
marketing_stage: (marketingStage as MarketingStage) || undefined,
```
- `""` (빈 문자열 = "선택 안 함")이 `||` 연산자에 의해 `undefined`로 변환됨
- 기존에 설정된 `marketing_stage`를 "선택 안 함"으로 변경하면 서버에 필드가 전송되지 않아 기존 값 유지

**영향**: 사용자가 마케팅 단계를 제거(초기화)할 수 없음

**우선순위 점수**: 40 × 1.0 = **40**

**수정 제안**: `|| undefined` → 명시적 null 처리
```typescript
marketing_stage: marketingStage ? (marketingStage as MarketingStage) : null,
```

---

### [R6] 마이그레이션에서 buyer_marketing_logs 테이블 미존재 시 실패 — [Moderate/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**: `INSERT INTO...SELECT FROM buyer_marketing_logs` 구문이 테이블 존재 여부를 확인하지 않음

**영향**: 신규 환경(테이블 미존재)에서 마이그레이션 실패 가능

⚠️ MEDIUM 신뢰도로 인해 P2에서 P3로 하향
**우선순위 점수**: 40 × 0.6 = **24**

---

### [R8] _to_marketing_out에서 stage=None 레코드 처리 — [Minor/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/app/routers/buyer_marketing.py`

**증거**: `_to_marketing_out()` 함수에서 `marketing_stage=None`인 MeetingLog가 전달되면 `stage` 필드가 None이 됨

**영향**: 호환 API 응답에 `stage: null` 레코드 포함 가능 (기존 FE 코드가 처리 못할 수 있음)

**우선순위 점수**: 20 × 0.6 = **12**

---

### [Py-2] buyer_marketing.py에서 중복 get_transaction 호출 — [Minor/HIGH] — Priority: P3

**파일**: `deal-mgmt/app/routers/buyer_marketing.py`

**증거**: `check_client_deal_access` 내부에서 이미 transaction을 조회하는데, 이후 다시 `get_transaction` 호출

**영향**: 불필요한 DB 쿼리 1회 추가 (성능 영향 미미)

**우선순위 점수**: 20 × 1.0 = **20**

---

### [Mig-INFO1] 마이그레이션 데이터 복사 시 channel='EMAIL' 하드코딩 — [Minor/MEDIUM] — Priority: P3 (정보)

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**: 기존 마케팅 로그 → 미팅 로그 복사 시 `channel='EMAIL'`로 고정, 실제 접촉 채널과 다를 수 있음

**영향**: 복사된 레코드의 channel 정보 부정확 가능 (히스토리 데이터)

**우선순위 점수**: 20 × 0.6 = **12**

---

### [Mig-INFO2] 마이그레이션 row-by-row INSERT 성능 — [Minor/HIGH] — Priority: P3 (정보)

**파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`

**증거**: 대량 데이터 시 row-by-row INSERT 방식이 느릴 수 있음

**영향**: 마이그레이션 실행 시간 증가 (일회성, 데이터 규모 의존)

**우선순위 점수**: 20 × 1.0 = **20**

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)
1. [H-01/R7] [Major/HIGH]: meeting_logs 라우터 write 엔드포인트에 check_client_deal_access 누락 — meeting_logs.py (점수: 95, 교차 검증)
2. [Perf-2/Py-3] [Major/HIGH]: meeting_log_summary가 전체 ORM 로드 후 Python 카운팅 — meeting_logs.py (점수: 95, 교차 검증)

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)
1. [R4] [Major/HIGH]: update_meeting_log에 marketing_stage 변경 시 auto-advance 누락 — meeting_logs.py (점수: 85, 교차 검증)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [Perf-1] [Moderate/HIGH]: (transaction_id, meeting_phase) 복합 인덱스 누락 — meeting_log.py (점수: 55, DESIGN_RISK)
2. [R1/M-05] [Moderate/HIGH]: downgrade에서 신규 marketing_stage 로그 데이터 소실 — migration (점수: 50)
3. [R5] [Moderate/HIGH]: MeetingLogForm에서 marketing_stage null 리셋 불가 — MeetingLogForm.tsx (점수: 40)
4. [M-02] [Moderate/HIGH]: buyer_id 변경 시 cross-txn 검증 누락 — meeting_logs.py (점수: 40)

### P3 — 저우선 (점수: <30, 개선 가능)
1. [R6] [Moderate/MEDIUM ⚠️]: 마이그레이션 buyer_marketing_logs 미존재 시 실패 — migration (점수: 24, 신뢰도 하향)
2. [Py-2] [Minor/HIGH]: 중복 get_transaction 호출 — buyer_marketing.py (점수: 20)
3. [Mig-INFO2] [Minor/HIGH]: row-by-row INSERT 성능 — migration (점수: 20)
4. [R8] [Minor/MEDIUM ⚠️]: _to_marketing_out stage=None 처리 — buyer_marketing.py (점수: 12)
5. [Mig-INFO1] [Minor/MEDIUM]: channel='EMAIL' 하드코딩 — migration (점수: 12)

---

## 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1-1 | BE 모델에 marketing_stage 컬럼 추가 | ✅ | meeting_log.py:72 |
| 1-2 | BE 스키마 3곳에 marketing_stage 추가 | ✅ | meeting_log.py schemas |
| 1-3 | Alembic 마이그레이션 + 데이터 복사 | ✅ | 080_unify_marketing_meeting_logs.py |
| 2-1 | create_meeting_log에 auto-advance 추가 | ✅ | meeting_logs.py:167-179 |
| 2-1 | 목록 조회에 marketing_stage 필터 추가 | ✅ | meeting_logs.py:73-74 |
| 2-2 | buyer_marketing.py 호환 레이어 전환 | ✅ | buyer_marketing.py 전체 리라이트 |
| 3-1 | FE MeetingLog 타입에 marketing_stage 추가 | ✅ | meeting_log.ts:108 |
| 3-2 | useCreateMeetingLog invalidation 추가 | ✅ | useMeetingLogs.ts:85-95 |
| 4-1 | InlineLogInput → useCreateMeetingLog 전환 | ✅ | InlineLogInput.tsx |
| 4-2 | MeetingLogForm에 marketing_stage 셀렉트 | ✅ | MeetingLogForm.tsx:146-158 |
| 4-3 | BuyerMeetingTimeline에 stage 뱃지 | ✅ | BuyerMeetingTimeline.tsx:70-74 |

---

## 품질 게이트 상태

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| tsc --noEmit | ✅ PASS | §1 정합성 자동 검증됨 |
| eslint | ✅ PASS | §1 정합성 자동 검증됨 |
| ruff check (BE) | ✅ PASS | §1 정합성 자동 검증됨 |

---

## Methodology

- **Agents**: code-reviewer, security-auditor, migration-validator, performance-profiler, python-reviewer
- **Excluded Agents**: 없음
- **Files scanned**: ~15개 (BE 모델/스키마/라우터/마이그레이션 + FE 타입/훅/컴포넌트)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 6건 → 4건 확인, 2건 FP 제거
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 15건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 11건
- 거부율: 13%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | R2: TanStack Query prefix matching이 stage-summary 커버 |
| 오판 | 1 | Py-1: String(10) 컬럼의 func.max()는 문자열 반환 |
| 범위 외 | 4+ | H-03(proxy), M-01(rate limiter) 등 기존 이슈 |

### 기존 이슈 (본 변경과 무관)

아래 이슈는 기존 코드에 존재하며 본 통합 작업과 직접 관련 없음:
- H-03: proxy.py DART 라이선스 키 평문 노출
- M-01: meeting_logs 라우터에 rate limiter 미적용
- M-03: attachments URL 무검증
- M-04: Excel 파일명 인젝션
- Py-6: DART search 에러 핸들링
- L-01~L-04: 기타 저위험 보안 항목
