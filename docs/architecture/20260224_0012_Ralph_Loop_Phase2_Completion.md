# Ralph Loop Phase 2 구현 완료 보고서

**작성일**: 2026-02-24 00:12
**범위**: LLM 연결 + Vision Gate + 학습 패턴 + 프론트엔드 AI 모드
**테스트**: Phase 0~2 전체 79개 통과

---

## Phase 2 구현 요약

Phase 0(코어 엔진, 25 tests)과 Phase 1(파서/생성기)에 이어, Phase 2에서는 실제 LLM 연결과 고급 품질 게이트를 구현하여 Ralph Loop을 **동작 가능한 시스템**으로 완성했다.

---

## Step 1: LLM 클라이언트 모듈

**신규**: `deal-mgmt/app/ralph/llm_client.py` (326줄)

| 클래스 | 역할 |
|--------|------|
| `CostTracker` | 모델별 토큰 비용 누적 추적 (COST_PER_1K 사전 기반) |
| `_AnthropicAdapter` | Claude Sonnet 4 기본, `anthropic.AsyncAnthropic` |
| `_OpenAIAdapter` | GPT-4o 기본, `openai.AsyncOpenAI` |
| `_GoogleAdapter` | Gemini 2.0 Flash, `asyncio.to_thread` 래핑 |
| `RalphLLMClient` | 폴백 체인 (Anthropic→OpenAI→Google), `call(system, user) -> str` |

**핵심 설계**:
- `call()` 시그니처가 `async (str, str) -> str`로 통일 → `LDDSectionAnalyzer(llm_call=...)`, `LLMJudgeGate(llm_provider=...)` 등 기존 코드와 즉시 호환
- `from_settings(settings)` 팩토리 메서드로 Settings 객체에서 자동 생성
- 비용 추적 내장: 모델별 input/output 토큰 비용 자동 계산

**수정 파일**:
- `deal-mgmt/app/core/config.py` — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `RALPH_PRIMARY_MODEL`, `RALPH_JUDGE_MODEL`, `RALPH_MAX_COST_PER_DOC` 추가
- `deal-mgmt/pyproject.toml` — `anthropic>=0.40.0`, `openai>=1.50.0`, `google-generativeai>=0.8.0` 의존성

**테스트**: 18개 (`test_ralph_llm_client.py`)

---

## Step 2: 기존 코드 연결 (6개 미연결 지점)

| 위치 | 수정 내용 |
|------|----------|
| `orchestrator.py:LoopResult` | `final_artifact: str \| None` 필드 추가 |
| `models/ralph_session.py` | `final_artifact`, `learned_patterns` JSONB 컬럼 추가 |
| `routers/ralph.py` | `_run_ralph_loop()` + `_build_pipeline()` 구현, TODO 해소 |
| `services/ldd_report_service.py` | `RalphLLMClient.from_settings()` + `[DOCXProgrammaticGate()]` 실제 주입 |
| `docker-compose.prod.yml` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` env var |

**마이그레이션**: `012_ralph_phase2_columns.py` — `final_artifact(JSONB)`, `learned_patterns(JSONB)` 추가

---

## Step 3: Vision Gate

**신규**: `deal-mgmt/app/ralph/gates/vision_gate.py` (272줄)

PPTX 전용 시각 품질 평가 게이트:
1. PPTX → PDF (LibreOffice headless)
2. PDF → PNG (PyMuPDF, 전략적 샘플링: 표지 + 중간 + 끝 = max 5장)
3. GPT-4o Vision API (5차원 평가)

| 차원 | 가중치 | 설명 |
|------|--------|------|
| layout_balance | 25% | 레이아웃 균형/여백 |
| typography | 20% | 타이포그래피 가독성 |
| data_viz | 20% | 데이터 시각화 품질 |
| professionalism | 20% | IB 수준 전문성 |
| color_harmony | 15% | 색상 조화/브랜드 일관성 |

**Fallback**: Vision API 미연결 시 모든 차원 3.0점 규칙 기반 평가
**비용**: ~$0.015/문서 (5장 × $0.003)

**테스트**: 20개 (`test_ralph_vision_gate.py`)

---

## Step 4: 학습 패턴

**신규 패키지**: `deal-mgmt/app/ralph/learning/`

| 파일 | 역할 |
|------|------|
| `pattern_aggregator.py` | DB에서 과거 세션 패턴 집계 (이슈 빈도순 + 고점수 세션 베스트 프랙티스) |
| `prompt_injector.py` | 학습 패턴을 LLM 시스템 프롬프트/피드백에 주입 |

**핵심 로직**:
- `get_common_issues(doc_type, section_id)` — `ralph_sessions.progress` JSONB에서 gate_results → issues 추출, 빈도순 정렬
- `get_best_practices(doc_type, min_score=4.5)` — 고점수 세션의 suggestions 추출
- `enrich_system_prompt(base, patterns)` — "과거 반복에서 학습된 패턴" 섹션 추가

**테스트**: 16개 (`test_ralph_learning.py`) — DB 시드 데이터 기반 통합 테스트 포함

---

## Step 5: CreateLDDReportPage AI 모드 통합

**수정**: `amic-platform/src/modules/docs/pages/CreateLDDReportPage.tsx`

기존 3단계 수동 마법사에 "AI 자동 분석" 모드 추가:

```
Step 0: 모드 선택
├── "수동 작성" (PenTool) → 기존 Step 1~3
└── "AI 자동 분석" (Brain, emerald) → Step A~C
    ├── Step A: 실사자료 폴더 경로 입력
    ├── Step B: 진행 상황 (로딩 스피너)
    └── Step C: 결과 확인/다운로드
```

**수정 훅**: `useLDDReports.ts` — `useCreateLDDReportAuto(txnId)` mutation 추가

---

## 테스트 결과 요약

```
tests/test_ralph_parsers.py      — 25 passed  (Phase 0~1)
tests/test_ralph_llm_client.py   — 18 passed  (Phase 2 Step 1)
tests/test_ralph_vision_gate.py  — 20 passed  (Phase 2 Step 3)
tests/test_ralph_learning.py     — 16 passed  (Phase 2 Step 4)
────────────────────────────────────────────────
Total Ralph Loop tests           — 79 passed ✅
```

---

## Phase 2 신규/수정 파일 목록

### 신규 (6개)
```
deal-mgmt/app/ralph/llm_client.py
deal-mgmt/app/ralph/gates/vision_gate.py
deal-mgmt/app/ralph/learning/__init__.py
deal-mgmt/app/ralph/learning/pattern_aggregator.py
deal-mgmt/app/ralph/learning/prompt_injector.py
deal-mgmt/migrations/versions/012_ralph_phase2_columns.py
```

### 수정 (7개)
```
deal-mgmt/app/core/config.py
deal-mgmt/pyproject.toml
deal-mgmt/app/ralph/orchestrator.py
deal-mgmt/app/models/ralph_session.py
deal-mgmt/app/routers/ralph.py
deal-mgmt/app/services/ldd_report_service.py
docker-compose.prod.yml
```

### 프론트엔드 수정 (2개)
```
amic-platform/src/modules/docs/pages/CreateLDDReportPage.tsx
amic-platform/src/modules/docs/hooks/useLDDReports.ts
```

### 테스트 (3개)
```
deal-mgmt/tests/test_ralph_llm_client.py
deal-mgmt/tests/test_ralph_vision_gate.py
deal-mgmt/tests/test_ralph_learning.py
```
