# Code Review — 마케팅 스테이지 → 딜 파이프라인 자동 동기화

> **Review Date**: 2026-03-10 22:33
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 커밋 99af62d — 7개 파일, +250/-46
> **Method**: Quality Gates + Verified Multi-Agent Review (3 에이전트)
> **Quality Gates**: tsc(PASS) ruff-check(PASS) ruff-format(PASS)
> **Agents**: python-code-reviewer, code-reviewer, backend-security-reviewer

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 0 / MEDIUM: 1 / LOW: 0 | P1: 1 |
| Major    | 1     | HIGH: 0 / MEDIUM: 1 / LOW: 0 | P2: 1 |
| Moderate | 4     | HIGH: 3 / MEDIUM: 1 | P1: 1 / P2: 3 |
| Minor    | 3     | HIGH: 1 / MEDIUM: 2 | P3: 3 |
| **Total**| **9** | HIGH: **4** / MEDIUM: **4** / LOW: **1** | P0: **0** / P1: **2** / P2: **4** / P3: **3** |

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 Critical 1건 → P1 하향 (100×0.6=60)
- MEDIUM 신뢰도 Major 1건 → P2 하향 (70×0.6=42)

---

## Findings

### P1 — 스프린트 우선 (점수: 60-89)

#### [BE-1] _TERMINAL_STATUSES 가드가 데드 코드 — [Critical/MEDIUM] — Priority: P1 (60)

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:110-115`

```python
cur_ord = _STATUS_ORDER.get(buyer.status)     # REJECTED → None
tgt_ord = _STATUS_ORDER.get(target)
if cur_ord is None or tgt_ord is None or cur_ord >= tgt_ord:
    return                                     # ← 여기서 이미 return

if buyer.status in _TERMINAL_STATUSES:         # ← 도달 불가 (데드 코드)
    return
```

`_TERMINAL_STATUSES` (REJECTED, BID_DROPPED, BID_NOT_SUBMITTED)는 `_STATUS_ORDER`에 포함되지 않아 `cur_ord is None` 분기에서 이미 return됩니다. 현재 동작은 안전하지만:
- 의도와 구현이 불일치하여 코드 리더에게 잘못된 안전감을 줌
- 향후 터미널 상태가 `_STATUS_ORDER`에 실수로 추가되면 승격이 허용됨

**신뢰도 MEDIUM 사유**: 현재 실제 런타임 버그는 아니며, "데드 코드"의 위험도는 향후 유지보수 시 발현됨.

**수정 권장**: 터미널 상태 체크를 ordinal 확인 이전으로 이동:
```python
if buyer.status in _TERMINAL_STATUSES:
    return
cur_ord = _STATUS_ORDER.get(buyer.status)
...
```

---

#### [SEC-1] Race Condition — buyer.status 동시 갱신 충돌 — [Moderate/HIGH] — Priority: P1 (60)

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:103-132`

동일 buyer에 대해 두 요청이 동시에 들어오면 (EMAIL_SENT + NDA_SIGNED 빠르게 연속 POST), 두 세션이 같은 `buyer.status` 스냅샷을 읽고 Last-Write-Wins로 한 상태 변경이 유실될 수 있습니다.

`_get_buyer()` 쿼리에 `with_for_update()` 또는 CAS 방식 갱신이 없습니다. 실제 발생 빈도는 낮으나(단일 사용자 순차 조작이 대부분), M&A 플랫폼에서 상태 변경의 비즈니스 중요도를 감안하면 방어 코드가 권장됩니다.

---

### P2 — 개선 권장 (점수: 30-59)

#### [BE-2] _ADVANCE_PATH가 NDA_SENT를 건너뜀 — [Major/MEDIUM] — Priority: P2 (42)

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:67-68`

```python
_S.IDENTIFIED: _S.CONTACTED,
_S.CONTACTED: _S.NDA_SIGNED,    # NDA_SENT를 건너뜀
_S.NDA_SENT: _S.NDA_SIGNED,
```

`buyers.py:51-69`의 수동 전이 규칙에서는 `CONTACTED → NDA_SENT → NDA_SIGNED`가 유효 경로입니다. 자동 승격에서 NDA_SENT를 건너뛰는 것이 의도적 설계인지 확인 필요합니다.

**신뢰도 MEDIUM 사유**: 마케팅 스테이지에서 "NDA 발송"은 별도 추적하지 않으므로 의도적 스킵일 가능성이 높으나, 비즈니스 담당자 확인이 필요합니다.

---

#### [SEC-2] 감사 로그 AuditAction 타입 불일치 — [Moderate/HIGH] — Priority: P2 (40)

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:124`

```python
action=AuditAction.UPDATE,  # ← UPDATE 사용
```

`enums.py:479`에 `AuditAction.STATUS_CHANGE`가 별도 정의되어 있습니다. buyer.status 자동 승격은 명백한 상태 변경이므로 `STATUS_CHANGE`를 사용하면 감사 로그 필터링/추적이 용이합니다.

---

#### [SEC-3] 감사 로그 트리거 컨텍스트 누락 — [Moderate/HIGH] — Priority: P2 (40)

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:120-132`

감사 로그에 "왜 이 상태가 변경됐는지" (어떤 MarketingStage가 트리거했는지) 정보가 없습니다. `old_value`/`new_value`만 기록되어, 나중에 "이 상태 변경은 누가 어떤 근거로 했는가" 재구성이 어렵습니다.

---

#### [FE-1] 레이블 불일치: "CIM 발송" vs "IM 발송" — [Moderate/MEDIUM] — Priority: P2 (36)

**위치**: `amic-platform/src/modules/ma/constants/buyer.ts`

| 위치 | CIM_SENT 레이블 |
|------|----------------|
| MARKETING_STAGE_LABELS (L77) | "IM 발송" |
| MARKETING_STAGE_OPTIONS (L88) | "IM 발송" |
| BUYER_STATUS_OPTIONS (L134) | "CIM 발송" |
| FunnelNav (L56) | "IM 발송" |

같은 enum 값에 대해 마케팅 영역에서는 "IM 발송", Buyer Status 드롭다운에서는 "CIM 발송"으로 표시됩니다. 이번 커밋에서 발생한 것은 아니지만, CIM_SENT 스테이지가 마케팅 영역에 추가되면서 노출 빈도가 증가합니다.

---

### P3 — 저우선 (점수: <30)

#### [BE-3] while 루프 순환 방지 코드 부재 — [Minor/HIGH] — Priority: P3 (20)

**위치**: `deal-mgmt/app/routers/buyer_marketing.py:118`

현재 `_ADVANCE_PATH`는 단방향 선형이라 순환 없음이 확인되었으나, 향후 상태 추가 시 방어 코드가 없습니다. `visited: set` 추가로 무한 루프를 방지할 수 있습니다.

#### [FE-2] MILESTONE_STAGES에 CIM_SENT/DD_STARTED 미포함 — [Minor/MEDIUM] — Priority: P3 (12)

**위치**: `amic-platform/src/modules/ma/components/buyers/MarketingTimelineView.tsx:35-38`

타임라인 뷰에서 새 스테이지가 마일스톤으로 강조되지 않습니다. 의도적 설계일 가능성 있음.

#### [FE-3] MARKETING_STAGE_OPTIONS 타입 제약 부재 — [Minor/MEDIUM] — Priority: P3 (12)

**위치**: `amic-platform/src/modules/ma/constants/buyer.ts:81-90`

`SelectOption[]` 타입은 `value: string`이므로 오타가 컴파일 타임에 감지되지 않습니다. `MARKETING_STAGE_LABELS`에서 자동 생성하는 패턴이 더 안전합니다.

---

## Priority Matrix

### P0 — 즉시 수정 (0건)
없음

### P1 — 스프린트 우선 (2건)
1. [BE-1] [Critical/MEDIUM ⚠️]: _TERMINAL_STATUSES 가드 데드 코드 — buyer_marketing.py (60)
2. [SEC-1] [Moderate/HIGH]: Race condition buyer.status 동시 갱신 — buyer_marketing.py (60)

### P2 — 개선 권장 (4건)
1. [BE-2] [Major/MEDIUM ⚠️]: _ADVANCE_PATH NDA_SENT 건너뜀 — buyer_marketing.py (42)
2. [SEC-2] [Moderate/HIGH]: AuditAction 타입 불일치 — buyer_marketing.py (40)
3. [SEC-3] [Moderate/HIGH]: 감사 로그 트리거 컨텍스트 누락 — buyer_marketing.py (40)
4. [FE-1] [Moderate/MEDIUM]: 레이블 불일치 "CIM 발송" vs "IM 발송" — buyer.ts (36)

### P3 — 저우선 (3건)
1. [BE-3] [Minor/HIGH]: while 루프 순환 방지 부재 — buyer_marketing.py (20)
2. [FE-2] [Minor/MEDIUM]: MILESTONE_STAGES 미갱신 — MarketingTimelineView.tsx (12)
3. [FE-3] [Minor/MEDIUM]: SelectOption 타입 제약 부재 — buyer.ts (12)

---

## Methodology

- **Agents**: python-code-reviewer, code-reviewer (superpowers), backend-security-reviewer
- **Files scanned**: 7
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major — 2건 교차 검증 (BE-1 터미널 가드 = 보안 리뷰와 일치)

## Passed Checks

- [x] 하드코딩된 시크릿/토큰 없음
- [x] SQL injection 취약점 없음
- [x] 권한 체크 적용 (require_write_access + check_client_deal_access)
- [x] async/await 일관 사용
- [x] audit_service.record() 시그니처 정확
- [x] DB 세션 관리 — flush → 자동 승격 → 단일 commit
- [x] 마이그레이션 IF NOT EXISTS 멱등성 보장
- [x] BE-FE enum 완전 동기화 (8단계)
- [x] 3개 mutation 일관된 캐시 무효화
- [x] FunnelNav 갱신 경로 정확 (buyers 쿼리 → BuyersTab → FunnelNav)
- [x] Type hints 모든 public 함수 적용
- [x] IDOR 방어 — buyer_id + txn_id 복합 조건 쿼리
- [x] Pydantic enum 자동 검증
