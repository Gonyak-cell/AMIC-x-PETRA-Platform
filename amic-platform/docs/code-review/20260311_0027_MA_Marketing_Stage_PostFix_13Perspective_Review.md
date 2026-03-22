# Code Review — MA Marketing Stage (Post-Fix 13-Perspective Integrated Review)

> **Review Date**: 2026-03-11 00:27
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: P1~P2 수정 완료 후 13개 리뷰 관점 통합 리뷰 (9 changed files)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review (13 Perspectives)
> **Quality Gates**: tsc(PASS) ruff(PASS) pytest-19/19(PASS)
> **Review Gates**: Backend(deal-mgmt: available) Agent-Filtering(5 agents)
> **Severity Filter**: `--severity major` (Major 이상만 보고)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 0     | — | — |
| **Total**| **0** | — | — |

**FP Prevention**: 가설 14건 검증, 14건 사전 거부 (거부율: 100%) | 교차 검증 0건 (대상 없음)

## Scope (9 Files)

### Backend (3 files)
| # | File | Lines |
|---|------|-------|
| 1 | `deal-mgmt/app/services/buyer_status_service.py` | 147 |
| 2 | `deal-mgmt/app/services/buyer_export_service.py` | 186 |
| 3 | `deal-mgmt/tests/test_buyer_tier_marketing.py` | 451 |

### Frontend (6 files)
| # | File | Lines |
|---|------|-------|
| 4 | `amic-platform/src/modules/ma/components/buyers/MarketingTimelineView.tsx` | ~317 |
| 5 | `amic-platform/src/modules/ma/components/buyers/MarketingGridView.tsx` | 263 |
| 6 | `amic-platform/src/modules/ma/components/buyers/MarketingGridCell.tsx` | 125 |
| 7 | `amic-platform/src/modules/ma/components/buyers/ShortListSummaryBar.tsx` | 121 |
| 8 | `amic-platform/src/modules/ma/components/buyers/ShortListOverview.tsx` | 189 |
| 9 | `amic-platform/src/modules/ma/components/buyers/BuyerDetailPanel.tsx` | 144 |

## 13-Perspective Analysis

### 1. 정합성 (Consistency)
- ✅ 백엔드 MarketingStage enum (8단계)과 프론트엔드 타입/상수 완전 일치
- ✅ `ADVANCE_PATH` 체인 13개 상태 전이 경로 빈틈 없음 (IDENTIFIED → BID_SUBMITTED)
- ✅ `_STAGE_LABELS` 8개 키가 enum 값과 정확히 매칭
- ✅ `MARKETING_STATUS_ADVANCE` 매핑이 실제 비즈니스 흐름과 일치

### 2. 완전성 (Completeness)
- ✅ 19개 테스트 전체 통과 — Tier CRUD, Marketing Log, Stage Summary, Overview, Export, VDR 분류 커버
- ✅ `auto_advance_buyer_status` 전용 테스트 파일 별도 존재 (`tests/test_buyer_status_service.py`)
- ✅ ShortListSummaryBar: buyerIds Set 교차 필터로 데이터 정합성 보장

### 3. 품질 (Code Quality)
- ✅ `useMemo` 적용으로 불필요한 재계산 방지 (ShortListSummaryBar)
- ✅ 0-division guard 적용 (`effectiveStageCount` > 0 체크)
- ✅ `countCompletedStages` / `effectiveStageCount` 분리로 의미론적 정확성 확보
- ⚠️ (Moderate) `EMPTY_STAGES` 상수가 컴포넌트 내부 정의 — 모듈 레벨 권장 (성능 영향 미미)

### 4. 안정성 (Stability/Safety)
- ✅ `ADVANCE_PATH` while 루프에 기존 안전장치 유지 (dict miss → 자연 종료)
- ✅ pytest 전체 통과 — 회귀 없음

### 5. 보안 (Security)
- ✅ 엔드포인트 인증 Depends 유지 (`get_jwt_claims`)
- ✅ 하드코딩 시크릿 없음
- ✅ SQL 파라미터화 유지

### 6. 접근성 (Accessibility)
- ✅ `role="img"` + `aria-label` 추가 (CircularProgress SVG)
- ✅ `role="listitem"` 4개 위치 추가 (타임라인 항목)
- ✅ 빈 셀 시각적 구분 개선 (채워진 점 → 빈 원형 윤곽)

### 7. 성능 (Performance)
- ✅ ShortListSummaryBar 5개 filter() → 단일 useMemo 통합
- ✅ `buyerIds` Set으로 O(1) 조회
- ⚠️ (Moderate) MarketingGridView 개별 buyer useMemo 미적용 — O(8) 상수 시간이므로 실질적 영향 없음

### 8. UX (User Experience)
- ✅ 미팅 로그 로딩 상태 표시 (`isPending` → 스피너)
- ✅ MP 단계 생략 가능 표시 유지

### 9. 타입 안전성 (Type Safety)
- ✅ `as` 타입 단언 2건 제거 → `EMPTY_STAGES` 타입 상수로 대체
- ✅ tsc --noEmit 통과

### 10. 에러 처리 (Error Handling)
- ✅ 0-division guard 2곳 적용 (진행률 계산, 평균 계산)
- ✅ `auto_advance_buyer_status` — ADVANCE_PATH 미등록 상태 시 자연 종료

### 11. 데이터 흐름 (Data Flow)
- ✅ `onToggleDrop` 선택적 prop — ShortListOverview 미전달, BuyersTab 전달 (의도된 설계)
- ✅ stageSummary → countCompletedStages → 진행률 계산 흐름 정합

### 12. 테스트 커버리지 (Test Coverage)
- ✅ 19개 테스트 전체 신규 8단계 enum 사용
- ✅ Stage Summary 테스트: 8개 키 정확히 검증
- ✅ Export 테스트: `_STAGE_LABELS` 매핑 간접 검증

### 13. 비즈니스 로직 (Business Logic)
- ✅ Sell-side M&A 8단계 프로세스 정확 반영
- ✅ ADVANCE_PATH: IDENTIFIED → CONTACTED → NDA_SIGNED → ... → BID_SUBMITTED (13단계 전이)
- ✅ MARKETING_STATUS_ADVANCE: 마케팅 단계 → 매수자 상태 자동 승격 정확

## Findings (Major+)

**없음.** `--severity major` 필터 기준 Critical 또는 Major 이슈가 발견되지 않았습니다.

## Moderate Issues (참고용, 수정 불요)

| # | Perspective | File | Description | Confidence |
|---|------------|------|-------------|------------|
| m-1 | Code Quality | MarketingTimelineView.tsx:58 | `EMPTY_STAGES` 상수가 컴포넌트 내부 정의 — 모듈 레벨 권장 | MEDIUM |
| m-2 | Performance | MarketingGridView.tsx | 개별 buyer별 useMemo 미적용 — O(8) 상수 연산으로 실익 없음 | LOW |

## Priority Matrix

### P0 — 즉시 수정: 0건
### P1 — 스프린트 우선: 0건
### P2 — 개선 권장: 0건 (Moderate 2건은 severity major 필터로 제외)
### P3 — 저우선: 0건

## Methodology

- **Agents**: code-reviewer, type-checker, a11y-auditor, perf-auditor, security-auditor
- **Excluded Agents**: api-auditor (백엔드 라우터 파일 미포함)
- **Files scanned**: 9
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 대상 없음 (Critical + Major = 0건)
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 14건
- 거부된 가설 (사전 제거): 14건
- 보고된 이슈: 0건 (Major+)
- 거부율: 100%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 6 | `onToggleDrop` dead code 의심 → BuyersTab.tsx:575에서 사용 확인 |
| 이미 수정됨 | 4 | 진행률 0-div → guard 이미 적용 확인 |
| 심각도 미달 | 2 | EMPTY_STAGES 위치, buyer useMemo — Moderate로 하향 |
| 오판 | 2 | ADVANCE_PATH 빈틈 의심 → 13단계 완전 체인 확인 |

### P1~P2 수정 검증 결과

이전 리뷰에서 식별된 13건 수정 사항 전체 검증:

| Fix ID | Description | Status |
|--------|-------------|--------|
| R1 | 진행률 계산 countCompletedStages 적용 | ✅ 검증됨 |
| R2 | ShortListSummaryBar 0-div guard | ✅ 검증됨 |
| R3 | ADVANCE_PATH 13단계 완전 체인 | ✅ 검증됨 |
| R4 | buyerIds Set 교차 필터 | ✅ 검증됨 |
| M1 | _STAGE_LABELS 8단계 업데이트 | ✅ 검증됨 |
| TS-1 | EMPTY_STAGES 타입 상수 (as 제거) | ✅ 검증됨 |
| UX-1 | 미팅 로그 로딩 상태 표시 | ✅ 검증됨 |
| A11Y-1 | SVG role="img" + aria-label | ✅ 검증됨 |
| A11Y-2 | role="listitem" 4개 위치 | ✅ 검증됨 |
| A11Y-3 | 빈 셀 시각적 구분 개선 | ✅ 검증됨 |
| PERF-1 | 5개 filter → 단일 useMemo 통합 | ✅ 검증됨 |
| PERF-2 | GridView buyer useMemo — 스킵 (O(8) 상수) | ✅ 의도적 스킵 |
| PERF-3 | TimelineView useMemo — R1에서 해결 | ✅ R1에 통합 |
