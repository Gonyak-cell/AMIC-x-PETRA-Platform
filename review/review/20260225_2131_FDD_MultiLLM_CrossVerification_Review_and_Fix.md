# FDD 멀티 LLM 교차검증 시스템 — 코드 리뷰 및 수정 보고서

> **작성**: 2026-02-25 21:31
> **브랜치**: `feat/ma-workflow`
> **범위**: FDD 파이프라인 멀티 LLM 교차검증(Cross-Verification) + 레포트 QA 시스템

---

## 1. 변경 범위

| # | 파일 | 액션 | 역할 |
|---|------|------|------|
| 1 | `fdd/backend/app/agents/cross_verifier.py` | NEW (670줄) | 멀티 LLM 교차검증 에이전트 |
| 2 | `fdd/backend/app/agents/report_qa.py` | NEW (163줄) | 레포트 QA 팩트체크 에이전트 |
| 3 | `fdd/backend/app/agents/prompts/report_qa_v1_0.yaml` | NEW | QA 시스템 프롬프트 |
| 4 | `fdd/backend/app/agents/schemas/report_qa_schema.json` | NEW | QA 출력 JSON 스키마 |
| 5 | `fdd/backend/app/services/llm/routing/model_router.py` | MODIFY | 라우팅 맵 4개 항목 추가 |
| 6 | `fdd/backend/app/models/analysis_run.py` | MODIFY | JSONB 컬럼 2개 추가 |
| 7 | `fdd/backend/alembic/versions/018_add_cross_verification.py` | NEW | Alembic 마이그레이션 |
| 8 | `fdd/backend/app/services/analysis/orchestrator.py` | MODIFY | 교차검증 오케스트레이션 |
| 9 | `fdd/backend/app/schemas/fdd_checklist.py` | MODIFY | API 스키마 확장 |
| 10 | `fdd/backend/app/api/analysis.py` | MODIFY | 교차검증 엔드포인트 |
| 11 | `fdd/backend/app/schemas/report.py` | MODIFY | qa_enabled 파라미터 |
| 12 | `fdd/backend/app/api/reports.py` | MODIFY | QA 통합 |
| 13 | `fdd/backend/tests/test_cross_verifier.py` | NEW (8 tests) | 교차검증 테스트 |
| 14 | `fdd/backend/tests/test_report_qa_agent.py` | NEW (2 tests) | QA 테스트 |
| 15 | `amic-platform/src/modules/fdd/hooks/useAnalysis.ts` | MODIFY | FE 타입 동기화 |

---

## 2. 리뷰 요약

- **발견 이슈**: 10개 (Critical: 2, Major: 4, Moderate: 3, Minor: 1)
- **전체 수정 완료**: 10/10 (100%)
- **테스트 결과**: 10/10 PASSED (0.24s)

---

## 3. 발견 이슈 및 수정 내역

### P0 — Critical (런타임 에러)

#### 이슈 #1: reports.py — AnalysisRun 미import로 NameError
- **위치**: `fdd/backend/app/api/reports.py:115`
- **원인**: `qa_enabled=True`로 레포트 생성 시 `AnalysisRun`이 import 되지 않아 `NameError` 발생
- **수정**: 파일 상단에 `from app.models.analysis_run import AnalysisRun` 추가

#### 이슈 #2: reports.py — 도달 불가능 코드 (Dead Code)
- **위치**: `fdd/backend/app/api/reports.py:133-134`
- **원인**: L132에서 `return result` 후 L134에서 다시 `return` → 절대 실행 안 됨
- **수정**: dead code 2줄 삭제

#### 이슈 #7 (병합): reports.py — 로깅 패턴 불일치
- **원인**: `import logging` 직접 사용 → 구조화 JSON 로깅 누락
- **수정**: `from app.core.logging import get_logger` + `logger = get_logger(__name__)` 패턴으로 교체

### P1 — Major (핵심 로직 미완성)

#### 이슈 #3: orchestrator._calc_to_items() — NWC/Debt 미구현
- **위치**: `fdd/backend/app/services/analysis/orchestrator.py:642-685`
- **원인**: QoE만 변환하고 NWC/Debt는 빈 리스트 반환 → 교차검증 건너뜀
- **수정**: NWC `calc.line_items` (NWCLineItem), Debt `calc.items` (DebtItem) 변환 로직 추가

#### 이슈 #4: orchestrator._apply_cv_flags() — 첫 항목만 FLAGGED
- **위치**: `fdd/backend/app/services/analysis/orchestrator.py:694-704`
- **원인**: `break`로 분석 유형당 첫 번째 매칭 항목에만 플래그
- **수정**: `break` 제거, 모든 관련 카테고리 항목에 동일 플래그 적용

#### 이슈 #5: orchestrator._apply_cv_flags() — reviewer_only_items 미처리
- **위치**: `fdd/backend/app/services/analysis/orchestrator.py:706-732`
- **원인**: `reviewer_only` 변수를 로드만 하고 새 ChecklistItem 생성 로직 없음
- **수정**: `reviewer_only` 항목별로 `FddChecklistItem(status=FLAGGED, severity=HIGH)` 생성 로직 추가

#### 이슈 #6: orchestrator._run_cross_verification() — source_data/context 비어있음
- **위치**: `fdd/backend/app/services/analysis/orchestrator.py:605-610`
- **원인**: `source_data = {"gl_entries": []}` 하드코딩 → 자동 해결 규칙 2 작동 불가
- **수정**:
  - `_extract_gl_entries()` 신규 메서드 추가 — VDR 파일의 `parsed_metadata`에서 GL/TB 데이터 추출
  - `completed_files`를 `_run_cross_verification`에 전달
  - `context`에 deal_name, gl_entries, adjustment_candidates 포함

### P2 — Moderate/Minor (품질 개선)

#### 이슈 #8: FE 타입 불일치
- **위치**: `amic-platform/src/modules/fdd/hooks/useAnalysis.ts`
- **수정**: `AnalysisRun` 인터페이스에 `cross_verify_summary`, `qa_result` 추가. `useRunAnalysis` mutation에 `cross_verify_enabled` 파라미터 추가.

#### 이슈 #9: confidence 하드코딩
- **위치**: `fdd/backend/app/services/analysis/orchestrator.py:653`
- **수정**: QoE는 `getattr(adj, "confidence", 0.8)`, Debt는 `confidence_score / 100`으로 동적 추출

#### 이슈 #10: 자동 해결 규칙 3 미구현
- **위치**: `fdd/backend/app/agents/cross_verifier.py:632-646`
- **수정**:
  - `DisagreementItem`에 `writer_confidence`, `reviewer_confidence` 필드 추가
  - `_compare_qoe_item`, `_compare_nwc_item`, `_compare_debt_item`에서 confidence 전달
  - `_auto_resolve()`에 규칙 3 구현: confidence 차이 0.4+ → 높은 쪽 채택
  - `test_auto_resolve_confidence_gap` 테스트 추가

---

## 4. 테스트 결과

```
tests/test_cross_verifier.py::test_blind_mode_independent PASSED
tests/test_cross_verifier.py::test_assessment_mismatch_detected PASSED
tests/test_cross_verifier.py::test_amount_variance_thresholds PASSED
tests/test_cross_verifier.py::test_auto_resolve_unclear PASSED
tests/test_cross_verifier.py::test_reviewer_only_items PASSED
tests/test_cross_verifier.py::test_fallback_provider PASSED
tests/test_cross_verifier.py::test_cost_limit PASSED
tests/test_cross_verifier.py::test_auto_resolve_confidence_gap PASSED   ← 신규
tests/test_report_qa_agent.py::test_number_accuracy_detection PASSED
tests/test_report_qa_agent.py::test_uses_different_provider PASSED

10 passed in 0.24s
```

Python syntax check: reports.py, orchestrator.py, cross_verifier.py 모두 OK.

---

## 5. 수정된 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `fdd/backend/app/api/reports.py` | AnalysisRun import, get_logger, dead code 삭제 |
| `fdd/backend/app/services/analysis/orchestrator.py` | NWC/Debt 변환, break 제거, reviewer_only 처리, GL 추출, source_data 채우기 |
| `fdd/backend/app/agents/cross_verifier.py` | DisagreementItem confidence 필드, 규칙 3 구현 |
| `amic-platform/src/modules/fdd/hooks/useAnalysis.ts` | 타입 동기화, mutation 파라미터 |
| `fdd/backend/tests/test_cross_verifier.py` | test_auto_resolve_confidence_gap 추가 |
