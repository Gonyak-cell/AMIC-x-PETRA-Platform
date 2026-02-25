# FDD 멀티 LLM 교차검증 구현 프롬프트

> 이 문서는 AI에 그대로 입력하여 구현을 지시하는 프롬프트입니다.

---

## 프롬프트 시작

너는 `fdd/backend/` 디렉토리의 FDD(Financial Due Diligence) 백엔드에 **멀티 LLM 교차검증 시스템**을 구현해야 한다.

### 현재 구조 요약

현재 파이프라인은 **분석 엔진 1회 실행 → 체크리스트 생성 → 레포트**로 끝난다. 교차검증이 없어서 LLM이 잘못 분류해도 그대로 레포트에 반영된다.

핵심 파일과 현재 역할:

| 파일 | 역할 |
|------|------|
| `app/agents/base.py` | `BaseAgent` 추상 클래스. `build_prompt()` → LLM 호출 → `parse_response()` → `validate_output()`. `AgentConfig`(provider, model, temperature, max_tokens, max_retries), `AgentResponse`(success, result, raw_output, token_usage, validation_errors, confidence, warnings). `FDDModelRouter`를 주입받아 `section_id` 기반으로 프로바이더를 자동 선택한다. |
| `app/agents/qoe_analyzer.py` | `QoEAnalyzerAgent(BaseAgent)`. `section_id="qoe_adjustment_classification"`. GL 전표를 NON_RECURRING/NORMALIZATION/OPERATING/UNCLEAR로 분류. 가드레일: entry_id 존재 확인, 금액 검증, 환각 탐지, 계산 시도 방지. |
| `app/agents/guardrails.py` | `validate_entry_ids_exist()`, `validate_amounts_exist()`, `check_hallucination_patterns()`, `enforce_confidence_threshold()`, `validate_no_calculations()` |
| `app/services/llm/client.py` | `LLMClient` ABC + `AnthropicClient`(claude-sonnet-4-5), `OpenAIClient`(gpt-4o), `GeminiClient`(gemini-2.0-flash). 공통 인터페이스: `chat(system_prompt, user_prompt, model, temperature, max_tokens, json_schema, timeout_seconds) → LLMResponse(content, model, provider, token_usage, finish_reason)`. `create_llm_client(provider)`, `get_available_provider()` 팩토리. |
| `app/services/llm/routing/model_router.py` | `FDDModelRouter`. `DEFAULT_FDD_ROUTING`: 정량(qoe/nwc/debt)→openai, 정성(executive_summary/risk)→anthropic, 지원(methodology/industry)→gemini. `FALLBACK_CHAIN`. `resolve(section_id)→RoutingDecision`, `generate(section_id, ...)→FDDLLMResponse`. |
| `app/services/analysis/orchestrator.py` | `AnalysisOrchestrator`. `run_analysis(deal_id)`: VDR 파일 수집 → 스냅샷 → `_run_qoe()` → `_run_nwc()` → `_run_debt()` → `_build_checklist()`. 각 엔진은 deterministic 계산이고, LLM Agent(QoEAnalyzerAgent 등)는 별도로 호출한다. |
| `app/models/analysis_run.py` | `AnalysisRun` SQLAlchemy 모델. status(RUNNING/COMPLETED/FAILED), progress_percent, input_file_ids, output_checklist_id, error_message. |
| `app/models/fdd_checklist.py` | `FddChecklist`, `FddChecklistItem`(18개 카테고리), `ChecklistItemVdrLink`. 상태: AUTO_GENERATED/CONFIRMED/CORRECTED/FLAGGED/NOT_APPLICABLE. |

### 구현할 것: 3개 모듈

---

#### 모듈 1: `app/agents/cross_verifier.py` (신규 파일)

**목적**: Writer(기존 분석 에이전트)의 결과를 **다른 LLM 프로바이더**로 독립 검증하고, 불일치를 탐지한다.

**설계 원칙**:
- Writer와 Reviewer는 반드시 **다른 프로바이더**를 사용 (같은 모델 2번 호출은 의미 없음)
- BLIND 모드: Reviewer가 Writer 결과를 모른 채 독립 분석 → 결과를 코드로 비교
- INFORMED 모드: Reviewer가 Writer 결과를 보고 검증/반박
- 비교는 LLM이 아니라 **deterministic 코드**로 수행

**구현 상세**:

1. `ReviewMode` enum: `BLIND`, `INFORMED`
2. `DisagreementLevel` enum: `NONE`, `MINOR`, `MODERATE`, `MAJOR`, `CRITICAL`
3. `DisagreementItem` dataclass: entry_id, field, writer_value, reviewer_value, level, writer_rationale, reviewer_rationale, resolution, resolved
4. `CrossVerificationResult` dataclass: writer_provider, reviewer_provider, review_mode, total_items, agreed_items, disagreements, reviewer_only_items, writer_only_items, agreement_rate, auto_resolved, needs_human_review, total_cost_usd, token_usage

5. `CrossVerificationAgent` 클래스:
   - `BaseAgent`를 상속하지 않는다 (별도 클래스). 이유: Writer 에이전트의 결과를 받아서 다른 에이전트의 결과와 비교하는 오케스트레이터 역할이므로.
   - `__init__(writer_provider, reviewer_provider, reviewer_client: LLMClient, review_mode, analysis_type)`
   - `run_cross_verification(writer_result: AgentResponse, source_data: dict, context: dict) → CrossVerificationResult`: 메인 실행 메서드
   - 내부에서 `_build_reviewer_prompt()`, `_call_reviewer()`, `_compare_results()`, `_auto_resolve()` 를 순서대로 호출

6. 비교 로직 (`_compare_results`):
   - QoE: assessment 불일치 → MODERATE (NON_RECURRING↔OPERATING이면 MAJOR), 금액 5%+ → MODERATE, 15%+ → MAJOR
   - NWC: classification(ABOVE/BELOW LINE) 불일치 → MODERATE, 금액 3%+ → MODERATE
   - Debt: debt_like 판단 불일치 → MAJOR

7. 자동 해결 (`_auto_resolve`):
   - 한쪽이 UNCLEAR이고 다른 쪽이 명확 → 명확한 쪽 채택
   - 금액 MINOR이고 한쪽이 원본과 정확히 일치 → 일치하는 쪽 채택
   - 양쪽 confidence 차이 0.4+ → 높은 쪽 채택
   - 그 외 → 미해결 (needs_human_review)

8. Reviewer 프롬프트:
   - BLIND system prompt: "You are an independent QoE reviewer. Classify these GL entries independently. Output JSON with analysis_results array matching the QoE analyzer output schema."
   - INFORMED system prompt: "You are a senior reviewer. A junior analyst classified these entries. Verify each classification, challenge disagreements with counter-rationale, identify missed entries."
   - user prompt는 QoEAnalyzerAgent와 동일한 컨텍스트를 전달하되, INFORMED 모드에서만 writer_results_json을 추가

---

#### 모듈 2: `app/services/analysis/orchestrator.py` 수정

**변경 내용**: `run_analysis()` 내에서 QoE/NWC 엔진 실행 직후 교차검증 단계를 삽입한다.

1. `__init__`에 `cross_verify_enabled: bool = False`와 `cross_verify_config` 추가. config는 dataclass로: `review_mode`, `qoe_enabled`, `nwc_enabled`, `debt_enabled`, `max_cost_usd`

2. `run_analysis()` 흐름 변경:
   ```
   기존: _run_qoe → _run_nwc → _run_debt → _build_checklist
   변경: _run_qoe → (교차검증) → _run_nwc → (교차검증) → _run_debt → _build_checklist(검증결과 포함)
   ```

3. `_cross_verify()` 메서드 추가: `CrossVerificationAgent`를 생성하고 실행. Writer 프로바이더와 다른 프로바이더를 자동 선택. 사용 가능한 프로바이더가 없으면 skip + 경고 로그.

4. `_build_checklist()` 수정: 교차검증 결과를 받아서:
   - 불일치 항목 → `ChecklistItemStatus.FLAGGED` + notes에 양측 근거 기록
   - Reviewer만 발견한 항목 → 새 `FddChecklistItem` 추가 (FLAGGED)
   - 자동 해결된 항목 → notes에 해결 근거 기록

5. `AnalysisRun` 모델에 `cross_verify_summary: JSON` 컬럼 추가 (결과 저장)

---

#### 모듈 3: `app/agents/report_qa.py` (신규 파일)

**목적**: 완성된 레포트 IR을 분석/서술에 사용하지 않은 다른 LLM으로 팩트체크한다.

1. `ReportQAAgent(BaseAgent)`:
   - `section_id = "report_qa"` → Gemini로 라우팅 (분석=OpenAI, 서술=Anthropic이므로)
   - `build_prompt(context)`: report_ir JSON + source QoE/NWC/Debt 결과를 포함
   - `parse_response()`: JSON 출력 파싱 (overall_score, issues[], passed_checks[], summary)
   - `validate_output()`: issues 배열의 각 항목이 location, description을 포함하는지 확인

2. 검증 항목 (system prompt에 명시):
   - NUMBER_ACCURACY: 레포트 수치 ↔ 원본 데이터 일치
   - LOGICAL_CONSISTENCY: 결론이 분석 내용과 모순 없는지
   - CROSS_REFERENCE: 섹션 간 수치 일관성
   - COMPLETENESS: 중요 발견사항 누락 여부 (confidence > 0.7, amount > revenue 1%)
   - TERMINOLOGY: 재무/회계 용어 정확성

3. QA 결과 구조:
   ```json
   {
     "overall_score": 4,
     "issues": [
       {
         "severity": "major",
         "category": "number_accuracy",
         "location": "Executive Summary",
         "description": "Adjusted EBITDA 불일치",
         "expected": "2,450,000,000",
         "found": "2,540,000,000"
       }
     ],
     "passed_checks": ["cross_reference", "terminology"],
     "summary": "수치 1건 불일치 외 전반적으로 양호"
   }
   ```

---

### 라우팅 맵 확장

`app/services/llm/routing/model_router.py`의 `DEFAULT_FDD_ROUTING`에 추가:

```python
# 교차검증 (Writer와 반드시 다른 프로바이더)
"cross_verify_qoe": "anthropic",      # Writer=openai → Reviewer=anthropic
"cross_verify_nwc": "anthropic",
"cross_verify_debt": "gemini",

# 레포트 QA (분석+서술 모두에 안 쓴 프로바이더)
"report_qa": "gemini",
```

---

### DB 마이그레이션

`app/models/analysis_run.py`에 컬럼 2개 추가:

```python
cross_verify_summary = Column(JSON, nullable=True)  # 교차검증 결과 요약
qa_result = Column(JSON, nullable=True)              # QA 결과
```

Alembic 마이그레이션 파일 생성: `alembic/versions/018_add_cross_verification.py`

---

### API 변경

`app/api/analysis.py`:
- `AnalysisRunRequest`에 `cross_verify_enabled: bool = False` 추가
- GET `/deals/{deal_id}/analysis/cross-verification` 엔드포인트 추가 (최근 분석의 교차검증 결과 조회)

`app/api/reports.py`:
- `ReportGenerateRequest`에 `qa_enabled: bool = False` 추가
- QA 실행 시 `ReportQAAgent`를 호출하고, 점수가 3 미만이면 응답에 warnings 포함

---

### 테스트

`tests/test_cross_verifier.py` (신규):

1. `test_blind_mode_independent` — BLIND 모드에서 Reviewer 프롬프트에 Writer 결과가 포함되지 않는지
2. `test_assessment_mismatch_detected` — NON_RECURRING↔OPERATING 불일치 → MAJOR
3. `test_amount_variance_thresholds` — 5% MODERATE, 15% MAJOR
4. `test_auto_resolve_unclear` — UNCLEAR vs 명확 → 자동 해결
5. `test_reviewer_only_items` — Reviewer만 발견한 항목이 결과에 포함되는지
6. `test_fallback_provider` — 지정 Reviewer 불가 시 다른 프로바이더로 폴백
7. `test_cost_limit` — max_cost_usd 초과 시 skip

`tests/test_report_qa.py` (신규):

1. `test_number_accuracy_detection` — 수치 불일치 탐지
2. `test_uses_different_provider` — QA가 분석/서술과 다른 프로바이더 사용

테스트에서 LLM 호출은 mock으로 대체한다. `unittest.mock.patch`로 `LLMClient.chat()`을 모킹하여 미리 정의된 JSON 응답을 반환하게 한다.

---

### 제약 조건

1. 기존 코드의 인터페이스를 변경하지 않는다. `BaseAgent`, `LLMClient`, `FDDModelRouter`의 기존 public API는 그대로 유지.
2. 교차검증은 `cross_verify_enabled=True`일 때만 실행. 기본값은 False이므로 기존 동작에 영향 없음.
3. Reviewer 프로바이더가 사용 불가하면 교차검증을 건너뛰고 경고 로그만 남긴다 (기존 파이프라인 중단 금지).
4. 비용 제어: `max_cost_usd` 초과 시 남은 교차검증을 skip.
5. 모든 새 코드는 기존 코드 스타일을 따른다: `from __future__ import annotations`, `get_logger(__name__)`, `dataclass` 사용, docstring은 한국어.

### 구현 순서

1. `app/agents/cross_verifier.py` — CrossVerificationAgent + 비교/자동해결 로직
2. `app/agents/report_qa.py` — ReportQAAgent
3. `app/services/llm/routing/model_router.py` — DEFAULT_FDD_ROUTING 확장
4. `app/models/analysis_run.py` + Alembic 마이그레이션 — 컬럼 추가
5. `app/services/analysis/orchestrator.py` — 교차검증 통합
6. `app/api/analysis.py`, `app/api/reports.py` — API 확장
7. `tests/test_cross_verifier.py`, `tests/test_report_qa.py` — 테스트

이 순서대로 하나씩 구현하라. 각 파일을 완성한 후 다음 파일로 넘어가라.

## 프롬프트 끝
