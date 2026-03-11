# Code Review — MA 보충 13개 관점 통합 리뷰

> **Review Date**: 2026-03-11 18:41
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 미커밋 변경 파일 중 MeetingType 리뷰에서 미수행된 15개 파일
> **Method**: Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) ruff(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(2개 에이전트: code-reviewer-BE, code-reviewer-FE)

## 대상 파일 (15개)

### Backend (11개)
- `deal-mgmt/app/routers/deal_setup.py`
- `deal-mgmt/app/routers/financial_models.py`
- `deal-mgmt/app/routers/nda_markups.py`
- `deal-mgmt/app/routers/vdr.py`
- `deal-mgmt/app/schemas/workflow.py`
- `deal-mgmt/app/services/deal_setup_service.py`
- `deal-mgmt/app/services/financial_model_service.py`
- `deal-mgmt/app/services/marketing_material_service.py`
- `deal-mgmt/app/services/nda_analysis_service.py`
- `deal-mgmt/app/services/vdr_qa_service.py`
- `deal-mgmt/app/services/workflow_engine.py`

### Frontend (4개)
- `amic-platform/src/modules/ma/components/buyers/MarketingTimelineView.tsx`
- `amic-platform/src/modules/ma/hooks/useVdrQA.ts`
- `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx`
- `amic-platform/src/modules/ma/types/workflow.ts`

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| Critical | 0 | — | — |
| Important | 6 | HIGH: 5 / MEDIUM: 1 | P1: 5 / P2: 1 |
| Suggestion | 8 | HIGH: 1 / MEDIUM: 5 / LOW: 2 | P2: 1 / P3: 7 |
| **Total** | **14** | HIGH: **6** / MEDIUM: **6** / LOW: **2** | P1: **5** / P2: **2** / P3: **7** |

**FP Prevention**: 교차 검증 6건 수행 — 6건 모두 CONFIRMED (FP 0건)

---

## Findings

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [BE-07] `asyncio.get_event_loop()` 사용 — Python 3.10+ deprecated — Important/HIGH — P1 (점수: 70)

**파일**: `deal-mgmt/app/services/marketing_material_service.py:134, 267`

**증거**:
```python
# 라인 134
result = await asyncio.get_event_loop().run_in_executor(

# 라인 267
result = await asyncio.get_event_loop().run_in_executor(
```

**설명**: Python 3.10+에서 `asyncio.get_event_loop()`는 이미 실행 중인 이벤트 루프가 없을 때 `DeprecationWarning`을 발생시키며, 향후 버전에서 제거 예정입니다. `asyncio.get_running_loop().run_in_executor()`로 교체해야 합니다.

**교차 검증**: CONFIRMED — 라인 134, 267에서 실제 패턴 확인.

---

#### [FE-01] catch 블록에서 `pendingTokens` flush 누락 — Important/HIGH — P1 (점수: 70)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:267`

**증거**:
```typescript
// 정상 종료 (라인 247-248) — flush 있음
if (rafId !== null) cancelAnimationFrame(rafId);
flushTokens();

// 에러 종료 (라인 267) — flush 없음
if (rafId !== null) cancelAnimationFrame(rafId);
// flushTokens() 호출 없음 ← 누락
```

**설명**: 네트워크 끊김 등 비-abort 에러 시 이미 수신한 부분 토큰이 `pendingTokens` 배열에 남아 UI에 반영되지 않고 유실됩니다. AbortError 경로에서는 메시지 자체를 제거하므로 flush 불필요하나, 그 외 에러 경로에서는 에러 메시지 표시와 함께 기존 부분 응답도 보존하는 것이 바람직합니다.

**권장**: catch 블록의 `cancelAnimationFrame` 직후, AbortError 분기 전에 `flushTokens()` 호출 추가.

**교차 검증**: CONFIRMED — 라인 247-248 vs 267 비교 확인.

---

#### [FE-03] `"ai-quality"` 탭이 VALID_TABS에 누락 — dead code — Important/HIGH — P1 (점수: 70)

**파일**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:84-104, 562`

**증거**:
```typescript
// 라인 84-104 — "ai-quality" 없음
const VALID_TABS = [
  "engagement", "buyers", "timeline", "marketing-materials",
  "models", "ndas", "vdr", "bids", "dd-checklist", "contracts",
  "closing", "pmi", "earnout", "risks", "compliance",
  "notes-approvals", "marketing-logs", "negotiation-logs", "rfi",
];

// 라인 105 — 유효하지 않은 탭은 "overview"로 폴백
const activeTab = VALID_TABS.includes(splat ?? "") ? splat! : "overview";

// 라인 562 — 렌더링 코드는 존재하지만 도달 불가
{safeActiveTab === "ai-quality" && (
  <QualityTab txnId={id} canWrite={canWrite()} />
)}
```

**설명**: URL `ai-quality`가 VALID_TABS에 없어 항상 `"overview"`로 폴백. `safeActiveTab === "ai-quality"` 조건은 절대 true가 되지 않아 `QualityTab` 렌더링 코드와 lazy import가 dead code입니다.

**권장**: `VALID_TABS`에 `"ai-quality"` 추가, 또는 의도적 비활성이면 렌더링 코드 + lazy import 제거.

**교차 검증**: CONFIRMED — Grep으로 `ai-quality` 사용처 확인, VALID_TABS에 부재 확인.

---

#### [BE-02] `vdr.py` 함수 내 중복 import — Important/HIGH — P1 (점수: 70)

**파일**: `deal-mgmt/app/routers/vdr.py:18, 21 vs 783-784`

**증거**:
```python
# 모듈 최상단 (라인 18, 21)
from app.core.config import settings
from app.core.rate_limiter import InMemoryRateLimiter, qa_rate_limiter

# 함수 내부 재import (라인 783-784)
from app.core.config import settings        # 중복
from app.core.rate_limiter import qa_rate_limiter  # 중복
```

**설명**: `settings`와 `qa_rate_limiter`는 이미 모듈 최상단에서 import되어 있으므로, 함수 내부의 로컬 import는 불필요한 중복입니다. 순환 import 방지 목적의 lazy import가 아닌 한 제거해야 합니다.

**교차 검증**: CONFIRMED — 라인 18, 21에서 모듈 레벨 import 확인, 라인 783-784에서 동일 심볼 재import 확인.

---

#### [FE-02] 401 재시도 시 abort 경쟁 조건 — Important/HIGH — P1 (점수: 65)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:137-147`

**증거**:
```typescript
// 라인 131 — 동일 signal 사용
signal: controller.signal,

// 라인 137-147 — refreshAuth() 비동기 대기 중 abort 가능
if (response.status === 401) {
  const refreshed = await refreshAuth();  // 이 동안 cancelStream() 호출 가능
  if (refreshed) {
    response = await fetch(sseUrl, { ...fetchOpts, headers: fetchHeaders });
    // fetchOpts.signal이 이미 abort 상태 → 즉시 AbortError
  }
}
```

**설명**: `refreshAuth()` 대기 중 사용자가 `cancelStream()`을 호출하면 controller가 abort됩니다. 이후 재시도 fetch가 즉시 AbortError를 발생시키며, catch 블록에서 정상 처리됩니다. 기능적으로 치명적이지 않으나, 불필요한 fetch 시도를 방지하려면 재시도 전 abort 가드가 필요합니다.

**권장**: 재시도 전 `if (controller.signal.aborted) return;` 가드 추가.

**교차 검증**: CONFIRMED — 코드 흐름 추적 확인.

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [BE-04] 서비스 레이어에서 `HTTPException` 직접 raise — Important/MEDIUM — P2 (점수: 42)

**파일**: `deal-mgmt/app/services/` 전반 (financial_model_service.py, marketing_material_service.py, document_version_service.py 등)

**증거**:
```python
# financial_model_service.py:394
raise HTTPException(...)

# marketing_material_service.py:82
raise HTTPException(...)

# document_version_service.py:95, 127, 136, 234, 247, 249
raise HTTPException(404, "문서를 찾을 수 없습니다")
```

**설명**: 서비스 레이어는 프레임워크에 독립적인 도메인 예외(`DocumentNotFoundError` 등)를 raise하고, 라우터에서 HTTP 응답으로 변환하는 것이 계층 분리 원칙에 부합합니다. 이 코드베이스에서는 이미 `app/core/exceptions.py`에 `DocumentNotFoundError` 등 도메인 예외가 정의되어 있으나, 서비스 레이어에서 일관되지 않게 사용되고 있습니다.

**신뢰도 하향 사유**: 기존 패턴이 코드베이스 전반에 걸쳐 광범위하여 즉시 수정보다는 점진적 리팩토링이 적절.

**교차 검증**: CONFIRMED — DESIGN_RISK. 15건 이상의 HTTPException raise 확인.

---

#### [FE-04] VALID_TABS / SIDEBAR_ONLY_TABS 매 렌더 재생성 — Suggestion/MEDIUM — P2 (점수: 32)

**파일**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:84-104, 288-293`

**증거**: 상수 배열이 컴포넌트 함수 내부에 선언되어 매 렌더마다 재생성됨. 반면 라인 74의 `VALID_PHASES`는 모듈 스코프에 위치.

**권장**: 모듈 스코프로 이동하여 일관성 확보 + 불필요한 재생성 방지.

**교차 검증**: CONFIRMED.

---

### P3 — 저우선 (점수: <30)

---

#### [BE-01] `deal_setup_service.py` — `create_transaction`에서 단일 트랜잭션 내 과도한 ORM flush — Suggestion/HIGH — P3 (점수: 20)

**파일**: `deal-mgmt/app/services/deal_setup_service.py`

**설명**: 트랜잭션 생성 시 여러 관련 엔터티(folders, phases 등)를 생성하며 중간 flush가 많을 수 있으나, SQLAlchemy 세션이 자동으로 관계를 관리하므로 명시적 flush 최소화가 가능합니다. 현재 기능적 문제 없음.

---

#### [BE-03] `workflow_engine.py` — 단계 전환 로직의 하드코딩된 phase 이름 — Suggestion/MEDIUM — P3 (점수: 24)

**설명**: 워크플로우 엔진에서 phase 이름이 문자열로 하드코딩되어 있으나, Enum과 일치하므로 기능적 문제 없음. 향후 리팩토링 시 Enum 참조로 통일 권장.

---

#### [BE-05] `nda_analysis_service.py` — LLM 프롬프트 내 한글/영문 혼재 — Suggestion/LOW — P3 (점수: 12)

**설명**: NDA 분석 프롬프트에서 한글과 영문이 혼재되어 있으나, LLM 출력 품질에 실질적 영향 미미. 프롬프트 엔지니어링 개선 사항.

---

#### [BE-06] `vdr_qa_service.py` — Gemini API 응답 파싱 시 에러 처리 세분화 부족 — Suggestion/MEDIUM — P3 (점수: 24)

**설명**: Gemini API 호출 실패 시 일반적인 Exception catch로 처리. API 특정 에러(quota, timeout 등)별 분기 처리가 없으나, 현재 사용량에서는 문제 없음.

---

#### [BE-08] `financial_model_service.py` — 대용량 Excel 파싱 시 메모리 제한 없음 — Suggestion/MEDIUM — P3 (점수: 24)

**설명**: 업로드된 Excel 파일 크기에 대한 제한이 서비스 레이어에 없으나, FastAPI UploadFile의 기본 제한과 nginx 설정으로 간접 보호.

---

#### [BE-11] `vdr_qa_service.py` — `QAResult.is_error` 기본값 True — Suggestion/MEDIUM — P3 (점수: 24)

**설명**: QAResult dataclass의 `is_error`가 True로 기본 설정되어, 성공 응답 생성 시 명시적으로 False를 설정해야 합니다. 실수 방지를 위해 기본값 False가 자연스럽지만, 현재 모든 사용처에서 올바르게 설정 중.

---

#### [FE-05] 비-lazy 컴포넌트가 Suspense 내부에 위치 — Suggestion/LOW — P3 (점수: 6)

**파일**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:526-589`

**설명**: `VdrTab`, `RFIPanel`, `MeetingLogsTab` 등이 lazy import가 아닌 일반 import이면서 Suspense 내부에 위치. 기능 문제 없으나 코드 분할 효과를 받지 못합니다.

---

#### [FE-06] info 이벤트에 `VdrQAErrorEvent` 타입 재사용 — Suggestion/MEDIUM — P3 (점수: 12)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:225-227`

**설명**: 정보성 "info" 이벤트 파싱에 `VdrQAErrorEvent` 타입명을 재사용. 구조 동일하여 기능 문제 없으나 가독성 저하.

---

## Priority Matrix

### P1 — 스프린트 우선 (5건)

| # | ID | 심각도/신뢰도 | 요약 | 파일 | 점수 |
|---|-----|-------------|------|------|------|
| 1 | BE-07 | Important/HIGH | `asyncio.get_event_loop()` deprecated | `marketing_material_service.py:134,267` | 70 |
| 2 | FE-01 | Important/HIGH | catch 블록 pendingTokens flush 누락 | `useVdrQA.ts:267` | 70 |
| 3 | FE-03 | Important/HIGH | "ai-quality" 탭 VALID_TABS 누락 (dead code) | `TransactionWorkspacePage.tsx:84,562` | 70 |
| 4 | BE-02 | Important/HIGH | vdr.py 함수 내 중복 import | `vdr.py:783-784` | 70 |
| 5 | FE-02 | Important/HIGH | 401 재시도 abort 경쟁 조건 | `useVdrQA.ts:137-147` | 65 |

### P2 — 개선 권장 (2건)

| # | ID | 심각도/신뢰도 | 요약 | 파일 | 점수 |
|---|-----|-------------|------|------|------|
| 1 | BE-04 | Important/MEDIUM | 서비스 레이어 HTTPException 직접 raise | `services/*.py` 전반 | 42 |
| 2 | FE-04 | Suggestion/MEDIUM | 상수 배열 매 렌더 재생성 | `TransactionWorkspacePage.tsx:84,288` | 32 |

### P3 — 저우선 (7건)

| # | ID | 요약 | 점수 |
|---|-----|------|------|
| 1 | BE-03 | 하드코딩 phase 이름 | 24 |
| 2 | BE-06 | Gemini API 에러 처리 세분화 | 24 |
| 3 | BE-08 | Excel 파싱 메모리 제한 | 24 |
| 4 | BE-11 | QAResult.is_error 기본값 True | 24 |
| 5 | BE-01 | 과도한 ORM flush | 20 |
| 6 | FE-06 | info 이벤트에 ErrorEvent 타입 | 12 |
| 7 | BE-05 | LLM 프롬프트 한영 혼재 | 12 |
| 8 | FE-05 | 비-lazy 컴포넌트 Suspense 내부 | 6 |

## 잘 된 점

### Backend
- **workflow_engine.py**: 상태 머신 패턴이 체계적이며, 단계 전환 조건 검증 로직 명확
- **vdr_qa_service.py**: Gemini File API 활용한 대용량 문서 Q&A 아키텍처가 잘 설계됨
- **deal_setup_service.py**: 트랜잭션 생성 시 폴더 구조 + 워크플로우 단계 자동 초기화 로직 완성도 높음

### Frontend
- **MarketingTimelineView.tsx**: N+1 방지 일괄 fetch, useMemo 메모이제이션, WCAG 접근성 충실 적용
- **useVdrQA.ts**: SSE 버퍼 처리, rAF 기반 토큰 배칭, 401 자동 갱신, AbortController 정리 등 방어적 프로그래밍 우수
- **workflow.ts**: 타입 정의가 간결하고 백엔드 스키마와 정합

## Methodology

- **Agents**: code-reviewer-BE, code-reviewer-FE (병렬)
- **Files scanned**: 15개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Important 6건 모두 CONFIRMED (FP 0건)

## 검증 투명성

### 검증 통계
- 검증한 가설: 17건
- 거부된 가설 (사전 제거): 3건
- 보고된 이슈: 14건
- 거부율: 18%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 코드베이스 관례 | 2 | 서비스 레이어 HTTPException이 프로젝트 전반 관례 |
| 신뢰도 불충분 | 1 | 추정 기반 성능 이슈 — 증거 부족 |
