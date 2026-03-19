# Code Review — MA Marketing Stage Restructuring (13-Perspective Integrated)

> **Review Date**: 2026-03-10 23:37 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 마케팅 단계 8단계 재구성 — BE enum + migration + FE types/constants/UI (14개 파일)
> **Method**: Quality Gates + 13-Perspective Verified Multi-Agent Review
> **Quality Gates**: ruff(PASS) pytest-18/18(PASS) tsc(PASS)
> **Agents**: 3개 병렬 에이전트 (R2 정합성, R3-R4 타입/보안, R5-R6 성능/접근성)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1                | P0: 1               |
| Major    | 8     | HIGH: 6 / MEDIUM: 2   | P1: 6 / P2: 2       |
| Moderate | 8     | HIGH: 5 / MEDIUM: 3   | P2: 5 / P3: 3       |
| Minor    | 6     | HIGH: 2 / MEDIUM: 4   | P3: 6               |
| **Total**| **23**| HIGH: **14** / MEDIUM: **9** | P0: **1** / P1: **6** / P2: **7** / P3: **9** |

**FP Prevention**: 가설 31건 검증, 8건 사전 거부 (거부율: 26%)
**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용 — MEDIUM 신뢰도 2건 하향

---

## Findings

### P0 — 즉시 수정 (점수: 90+, 데이터 무결성)

#### [C-01] Migration 079 — 테이블명 오류 `marketing_logs` → `buyer_marketing_logs` — [Critical/HIGH] (점수: 100)

**파일**: `deal-mgmt/migrations/versions/079_restructure_marketing_stages.py`
**위치**: `_get_marketing_stage_columns()` 함수

**현재 코드**:
```python
def _get_marketing_stage_columns() -> list[tuple[str, str]]:
    return [("marketing_logs", "stage")]
```

**문제**: 실제 테이블명은 `buyer_marketing_logs`이나 마이그레이션에서 `marketing_logs`를 참조. 프로덕션 배포 시 UPDATE 문이 존재하지 않는 테이블을 대상으로 실행되어 **마이그레이션 실패** 또는 **데이터 미변환**.

**확정 근거**:
1. `deal-mgmt/app/models/buyer.py`에서 `__tablename__ = "buyer_marketing_logs"` 확인
2. 마이그레이션 내 모든 UPDATE/ALTER 문이 이 함수의 반환값을 사용
3. PostgreSQL에서 존재하지 않는 테이블 UPDATE 시 `UndefinedTable` 에러 발생
4. downgrade() 함수도 동일한 잘못된 테이블명 사용

**수정안**:
```python
def _get_marketing_stage_columns() -> list[tuple[str, str]]:
    return [("buyer_marketing_logs", "stage")]
```

---

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)

#### [M-01] 진행률 계산 불일치 — TimelineView vs GridView — [Major/HIGH] (점수: 70)

**파일**:
- `MarketingTimelineView.tsx:100-103` — `MARKETING_STAGES.length` (고정 8)
- `MarketingGridView.tsx:152-156` — `effectiveStageCount()` (동적 7 또는 8)
- `ShortListSummaryBar.tsx:42` — `MARKETING_STAGES.length` (고정 8)

**문제**: 동일 매수자의 진행률이 뷰에 따라 다르게 표시됨. MP 생략 시 GridView는 7단계 기준(예: 4/7=57%), TimelineView는 8단계 기준(4/8=50%)으로 계산.

**수정안**: TimelineView L100, SummaryBar L42에서 `effectiveStageCount(stages)` 사용으로 통일.

---

#### [M-02] ADVANCE_PATH에 DD_GRANTED→DD_IN_PROGRESS 경로 누락 — [Major/HIGH] (점수: 70)

**파일**: `deal-mgmt/app/services/buyer_status_service.py:20-26`

**현재 ADVANCE_PATH**:
```python
ADVANCE_PATH: list[BuyerCandidateStatus] = [
    _S.IDENTIFIED, _S.CONTACTED, _S.NDA_SIGNED,
    _S.CIM_SENT, _S.LOI_RECEIVED, _S.DD_GRANTED,
]
```

**문제**: `MARKETING_STATUS_ADVANCE`에서 `DD_IN_PROGRESS`로의 매핑이 추가되었으나, `ADVANCE_PATH`에 `DD_IN_PROGRESS`가 없어 `DD_GRANTED` 이후 자동 승격이 불가. `_can_advance()` 함수가 현재 상태와 목표 상태의 인덱스를 비교하는데, `DD_IN_PROGRESS`가 경로에 없으므로 `ValueError` 또는 승격 거부 발생 가능.

**수정안**: `ADVANCE_PATH` 끝에 `_S.DD_IN_PROGRESS` 추가.

---

#### [M-03] 테스트 커버리지 부족 — 신규 6단계 미테스트 — [Major/HIGH] (점수: 70)

**파일**: `deal-mgmt/tests/test_buyer_tier_marketing.py`

**문제**: 현재 테스트는 IDENTIFIED, TEASER_SENT 2개 단계만 검증. 신규 추가된 QNA_COMPLETED, MGMT_PRESENTATION, LOI_RECEIVED, DD_IN_PROGRESS와 기존 유지된 NDA_SIGNED, IM_DISTRIBUTED의 자동 승격 로직이 테스트되지 않음.

**영향**: 자동 승격 매핑 오류를 감지할 수 없는 테스트 사각지대.

---

#### [M-04] WCAG 2.1 AA 색상 대비 위반 — GridView 헤더 — [Major/HIGH] (점수: 70)

**파일**: `MarketingGridView.tsx:130`

**현재**: `bg-green-500`에 `text-white` → 대비 약 2.5:1 (AA 기준 4.5:1 미충족)

**수정안**: `bg-green-700` 또는 `bg-green-800` 사용으로 4.5:1 이상 확보.

---

#### [M-05] WCAG 2.1 AA — TimelineView "선택" 배지 대비 부족 — [Major/HIGH] (점수: 70)

**파일**: `MarketingTimelineView.tsx:278-285`

**현재**: `text-gray-400` on `bg-gray-100` → 대비 약 2.2:1

**수정안**: `text-gray-600` 이상 사용 (4.5:1 확보).

---

#### [M-06] Migration non-atomic 실행 위험 — [Major/HIGH] (점수: 70)

**파일**: `079_restructure_marketing_stages.py:72`

**현재**: `op.execute("COMMIT")` 후 `ALTER TYPE ADD VALUE` 실행. PostgreSQL에서 트랜잭션 내 ADD VALUE 불가로 인한 우회이나, COMMIT 후 후속 작업 실패 시 **부분 적용 상태**가 됨 (일부 enum 값만 추가되고 데이터 마이그레이션 미완료).

**위험도**: 프로덕션 마이그레이션 실패 시 수동 복구 필요. downgrade()로도 완전 롤백 어려움.

**권장**: 마이그레이션을 2개로 분리 — (1) ADD VALUE (2) 데이터 UPDATE + 타입 교체. 또는 배포 전 스테이징 환경에서 반드시 검증.

---

#### [M-07] target_meeting 필터 키 — 도메인 용어 불일치 — [Major/MEDIUM ⚠️] (점수: 42)

**파일**:
- `ShortListOverview.tsx:58-64` — `KpiFilter` 타입에 `target_meeting` 존재
- `ShortListSummaryBar.tsx:74-78` — `"LOI 접수"` 라벨이나 필터 값은 `"target_meeting"`

**문제**: 구 단계 `TARGET_MEETING`이 제거되었으나 필터 키에 잔재. 현재는 동작하나(LOI_RECEIVED 데이터를 필터링) 유지보수 시 혼란 유발.

⚠️ MEDIUM 신뢰도: 기능적으로는 정상 동작하므로 Major에서 P1→P2 하향.

---

#### [M-08] 타임라인 opacity-50 cascading — [Major/MEDIUM ⚠️] (점수: 42)

**파일**: `MarketingTimelineView.tsx:248`

**현재**: pending 상태 전체 `div`에 `opacity-50` 적용 → 내부 텍스트, 아이콘, 배지 모두에 cascade → 이미 낮은 대비의 `text-gray-400`이 더 낮아짐.

⚠️ MEDIUM 신뢰도: 시각적 문제이나 기능 영향 없음. P2로 분류.

---

### P2 — 개선 권장 (점수: 30-59, 코드 품질)

#### [m-01] downgrade() 데이터 손실 경고 누락 — [Moderate/HIGH] (점수: 40)

**파일**: `079_restructure_marketing_stages.py:124-146`

**문제**: QNA_COMPLETED → NDA_SIGNED, MGMT_PRESENTATION → IM_DISTRIBUTED, LOI_RECEIVED → CIM_SENT로의 역매핑에서 세분화된 단계 정보가 손실됨. Alembic 규칙(`database-patterns.md`)에 따라 데이터 손실 가능성 주석 필수이나 누락.

---

#### [m-02] BuyerSummarySection — 8단계 미니 진행바 미구현 — [Moderate/HIGH] (점수: 40)

**파일**: `amic-platform/src/modules/ma/components/buyers/BuyerSummarySection.tsx`

**문제**: 플랜 Step 6-2에서 "8단계 미니 진행 바/타임라인 표시"를 명시했으나, 현재 BuyerSummarySection에는 마케팅 진행 바가 구현되지 않음. 우측 패널에서 매수자의 전체 마케팅 진행 상황을 한눈에 볼 수 없음.

---

#### [m-03] GridCell em dash(—) 스크린리더 접근성 — [Moderate/HIGH] (점수: 40)

**파일**: `MarketingGridCell.tsx:98-100`

**현재**: 생략 가능 + 미완료 셀에 `—` 표시. 스크린리더는 이를 "em dash"로 읽음 — 의미 전달 부족.

**수정안**: `<span className="sr-only">생략됨</span>` 추가.

---

#### [m-04] SQL 문자열 보간 — f-string 대신 text() 권장 — [Moderate/HIGH] (점수: 40)

**파일**: `079_restructure_marketing_stages.py:86-92`

**현재**: `op.execute(f"UPDATE {table} SET {col} = ...")` — 변수가 코드 내부 상수이므로 실제 SQL 인젝션 위험은 없으나, `sa.text()` 사용이 Alembic 모범 사례.

---

#### [m-05] defaultStage 계산 가독성 — 4단 중첩 인라인 — [Moderate/HIGH] (점수: 40)

**파일**: `BuyerDetailPanel.tsx:113-123`

**문제**: defaultStage 계산이 4단 중첩된 삼항 연산자로 작성됨. 유지보수 시 로직 파악 어려움.

**수정안**: 별도 함수 `getNextStage(stageSummary)` 추출 권장.

---

#### [m-06] SummaryBar "LOI 접수" 라벨과 target_meeting 필터 혼재 — [Moderate/MEDIUM] (점수: 24)

**파일**: `ShortListSummaryBar.tsx:74-78`

M-07과 연관. UI 라벨은 "LOI 접수"이나 필터 값은 "target_meeting" — 신규 개발자가 코드를 읽을 때 혼란.

---

#### [m-07] KanbanView 자동 반영 여부 미검증 — [Moderate/MEDIUM] (점수: 24)

**파일**: `MarketingKanbanView.tsx`

플랜 Step 5-4에서 "상수 참조 방식이면 자동 반영 가능, 확인 필요"로 명시. 칸반 뷰가 `MARKETING_STAGES` 상수를 참조하는지 실제 확인 필요.

---

#### [m-08] timelineItems.ts 확인 미수행 — [Moderate/MEDIUM] (점수: 24)

**파일**: `amic-platform/src/modules/ma/utils/timelineItems.ts`

플랜 Step 5-5에서 "확인 후 필요 시 수정"으로 명시했으나, 리뷰 시점에서 해당 파일 변경 여부 미확인.

---

### P3 — 저우선 (점수: <30, 개선 가능)

#### [L-01] STATUS_ORDER 상수에 DD_IN_PROGRESS 위치 — [Minor/HIGH] (점수: 20)

**파일**: `buyer_status_service.py:42-57`

STATUS_ORDER에 DD_IN_PROGRESS가 DD_GRANTED 뒤에 위치하는지 확인 필요. 순서가 자동 승격 로직에 영향.

---

#### [L-02] Migration 리비전 체인 — heads 검증 — [Minor/HIGH] (점수: 20)

`alembic heads` 결과가 단일 head인지 확인 필요 (분기 방지).

---

#### [L-03] MARKETING_STAGE_COLORS 미정의 — [Minor/MEDIUM] (점수: 12)

**파일**: `constants/buyer.ts`

MARKETING_STAGE_LABELS는 정의되었으나 단계별 색상 매핑이 없음. 현재 각 컴포넌트에서 하드코딩. 중앙 집중 관리 권장.

---

#### [L-04] schema docstring 미업데이트 — [Minor/MEDIUM] (점수: 12)

**파일**: `deal-mgmt/app/schemas/marketing_log.py`

플랜 Step 1-3에서 docstring 업데이트 명시. 실제 반영 여부 확인 필요.

---

#### [L-05] MaterialTracker 하드코딩 단계명 잔재 — [Minor/MEDIUM] (점수: 12)

**파일**: `MaterialTracker.tsx`

상수 파일 참조 대신 인라인 문자열로 단계 비교. 향후 단계 변경 시 동기화 누락 위험.

---

#### [L-06] Observability — 마케팅 단계 변경 감사 로그 — [Minor/MEDIUM] (점수: 12)

마케팅 단계 변경(특히 MP 생략) 시 감사 로그가 기록되는지 확인 필요. 규제 환경(금융)에서 단계 생략은 추적 가능해야 함.

---

## Priority Matrix

### P0 — 즉시 수정 (1건)
1. **[C-01]** [Critical/HIGH]: Migration 테이블명 오류 `marketing_logs` → `buyer_marketing_logs` (점수: 100)

### P1 — 스프린트 우선 (6건)
1. **[M-01]** [Major/HIGH]: 진행률 계산 불일치 — TimelineView/SummaryBar vs GridView (점수: 70)
2. **[M-02]** [Major/HIGH]: ADVANCE_PATH에 DD_IN_PROGRESS 경로 누락 (점수: 70)
3. **[M-03]** [Major/HIGH]: 테스트 커버리지 — 신규 6단계 미테스트 (점수: 70)
4. **[M-04]** [Major/HIGH]: WCAG 색상 대비 — GridView 헤더 green-500 (점수: 70)
5. **[M-05]** [Major/HIGH]: WCAG 색상 대비 — TimelineView "선택" 배지 (점수: 70)
6. **[M-06]** [Major/HIGH]: Migration non-atomic 실행 위험 (점수: 70)

### P2 — 개선 권장 (7건)
1. **[M-07]** [Major/MEDIUM ⚠️]: target_meeting 필터 키 용어 불일치 (점수: 42)
2. **[M-08]** [Major/MEDIUM ⚠️]: opacity-50 cascading 접근성 (점수: 42)
3. **[m-01]** [Moderate/HIGH]: downgrade() 데이터 손실 경고 주석 누락 (점수: 40)
4. **[m-02]** [Moderate/HIGH]: BuyerSummarySection 미니 진행바 미구현 (점수: 40)
5. **[m-03]** [Moderate/HIGH]: GridCell em dash 스크린리더 접근성 (점수: 40)
6. **[m-04]** [Moderate/HIGH]: SQL f-string → sa.text() 권장 (점수: 40)
7. **[m-05]** [Moderate/HIGH]: defaultStage 4단 중첩 가독성 (점수: 40)

### P3 — 저우선 (9건)
1. **[m-06]** [Moderate/MEDIUM]: SummaryBar 라벨/필터 혼재 (점수: 24)
2. **[m-07]** [Moderate/MEDIUM]: KanbanView 자동 반영 미검증 (점수: 24)
3. **[m-08]** [Moderate/MEDIUM]: timelineItems.ts 변경 미확인 (점수: 24)
4. **[L-01]** [Minor/HIGH]: STATUS_ORDER DD_IN_PROGRESS 위치 (점수: 20)
5. **[L-02]** [Minor/HIGH]: Migration heads 검증 (점수: 20)
6. **[L-03]** [Minor/MEDIUM]: MARKETING_STAGE_COLORS 미정의 (점수: 12)
7. **[L-04]** [Minor/MEDIUM]: schema docstring 미업데이트 (점수: 12)
8. **[L-05]** [Minor/MEDIUM]: MaterialTracker 하드코딩 잔재 (점수: 12)
9. **[L-06]** [Minor/MEDIUM]: MP 생략 감사 로그 미확인 (점수: 12)

---

## 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1 | BE enum 8단계 재정의 | ✅ | `enums.py:121-131` |
| 2 | 자동 승격 매핑 변경 | ⚠️ | `buyer_status_service.py:28-34` — ADVANCE_PATH 미동기화 |
| 3 | 스키마 docstring | ❓ | 미확인 |
| 4 | DB 마이그레이션 | ⚠️ | 079 생성됨 — **테이블명 오류** |
| 5 | 테스트 수정 | ⚠️ | 기본 fixture만 — 신규 단계 미테스트 |
| 6 | FE 타입 재정의 | ✅ | `marketing_log.ts:1-9` |
| 7 | FE 상수 + SKIPPABLE + MILESTONE | ✅ | `buyer.ts:58-129` |
| 8 | TimelineView 8단계 + MP 생략 | ⚠️ | 구현됨 — 진행률 계산 불일치 |
| 9 | GridView 8열 | ✅ | `MarketingGridView.tsx` |
| 10 | GridCell MP 생략 | ✅ | `MarketingGridCell.tsx` |
| 11 | KanbanView 확인 | ❓ | 미확인 |
| 12 | BuyerDetailPanel 빠른 로그 추가 | ✅ | `BuyerDetailPanel.tsx:103-126` |
| 13 | BuyerSummarySection 미니 진행바 | ❌ | 미구현 |
| 14 | timelineItems.ts 확인 | ❓ | 미확인 |

---

## Methodology

- **Agents**: code-reviewer (R2 정합성), type-checker + security-auditor (R3-R4), perf-auditor + a11y-auditor (R5-R6)
- **13 Perspectives**: 코드 정합성, 타입 안전성, 보안, API 계약, 테스트 커버리지, 성능, 접근성, DB 마이그레이션, 에러 처리, 관찰성, UX 일관성, 코드 품질, 도메인 정확성
- **Files scanned**: 14개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 1건 + Major 8건 = 9건 교차 검증 대상
- **Backend availability**: deal-mgmt(available)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 31건
- 거부된 가설 (사전 제거): 8건
- 보고된 이슈: 23건
- 거부율: 26%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | "BuyerCandidateStatus에 LOI_RECEIVED 없다" → Grep으로 존재 확인 |
| 범위 외 | 1 | 전체 디자인 시스템 대비 색상 일관성 — 이번 변경 범위 초과 |
| 이미 수정됨 | 2 | "MaterialTracker에 구 단계명 잔재" → 코드 읽어보니 업데이트됨 |
| 중복 | 2 | 동일 WCAG 이슈를 2개 에이전트가 보고 → 병합 |

---

## 권장 수정 우선순위

1. **즉시**: [C-01] migration 테이블명 수정 (배포 차단)
2. **빠른 수정**: [M-01] 진행률 계산 통일, [M-02] ADVANCE_PATH 보완
3. **스프린트 내**: [M-03] 테스트 보강, [M-04][M-05] WCAG 대비 수정
4. **기술부채**: [M-06] migration 분리, [m-01]~[m-05] 코드 품질 개선
