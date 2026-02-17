# FDD 보고서 부동문자 템플릿 + LLM 슬롯 채우기 시스템 구현 계획

> 작성일: 2026-02-17 13:31

---

## Context

**문제**: FDD 백엔드의 `FDDNarrativeGenerator`는 4개 메서드가 각각 system_prompt + user_prompt를 직접 조립하여 LLM에 전체 섹션 텍스트를 자유 생성시킨다. IM 모듈에서 이미 검증된 **YAML 부동문자 템플릿 + L1~L4 슬롯 채우기 방식**을 FDD에도 적용하여 일관성, 비용 효율, 품질을 개선한다.

**IM에서 이미 구현된 시스템**: `loader.py`, `registry.py`, `renderer.py`, `slot_fill.py`, `slot_parser.py` + 15개 YAML 템플릿 + 13개 산업 변형 YAML

**FDD 적용 전략**: IM 핵심 모듈을 FDD 내부에 복사-적응 (Phase 1), 향후 공통 패키지 추출 (Phase 5)

---

## 현재 FDD 내러티브 구조

**파일**: [narrative_generator.py](fdd/backend/app/services/report/narrative_generator.py)

| 메서드 | LLM | temp | 용도 |
|--------|-----|------|------|
| `generate_executive_summary()` | Anthropic | 0.3 | 종합 FDD 요약 |
| `generate_qoe_commentary()` | OpenAI | 0.2 | QoE 분석 코멘터리 |
| `generate_methodology()` | Gemini | 0.1 | 방법론 설명 |
| `generate_risk_narrative()` | Anthropic | 0.3 | 리스크 평가 |

**통합 지점**: [report_service.py:518-554](fdd/backend/app/services/report/report_service.py#L518-L554) — `use_llm_narratives=True`일 때 `narrator.generate_*()` 호출 → `build_text_block()` 삽입

---

## 구현 파일 구조

### 신규 파일 (14개)

```
fdd/backend/app/services/report/
├── slot_fill/                           # 신규 패키지
│   ├── __init__.py                      # re-exports
│   ├── loader.py                        # IM loader.py 복사-적응 (IMDocumentData 참조 제거)
│   ├── registry.py                      # IM registry.py 복사 (변경 없음)
│   ├── renderer.py                      # FDDTemplateRenderer (IM 상속, L2/조건부 오버라이드)
│   ├── prompt_builder.py                # FDDSlotFillPromptBuilder (FDD 전용)
│   └── slot_parser.py                   # IM slot_parser.py 복사 (변경 없음)
└── templates/                           # 신규 YAML 디렉터리
    ├── _base.yaml                       # FDD 공통 부동문자
    ├── executive_summary.yaml           # L2 7개 + L3 4개 + L4 4개
    ├── qoe_analysis.yaml                # L2 5개 + L3 3개 + L4 2개
    ├── nwc_analysis.yaml                # L2 5개 + L3 3개 + L4 2개
    ├── debt_analysis.yaml               # L2 5개 + L3 2개 + L4 2개
    ├── risk_narrative.yaml              # L2 1개 + L3 3개 + L4 1개
    ├── methodology.yaml                 # L1 + L2 5개 (LLM 불필요)
    └── industry_variants/
        └── (Phase 4에서 추가)
```

### 수정 파일 (2개)

| 파일 | 변경 |
|------|------|
| [report_service.py](fdd/backend/app/services/report/report_service.py) | `use_template_slotfill` 파라미터 추가, `_build_slotfill_narratives()` 헬퍼 함수 추가 |
| [narrative_generator.py](fdd/backend/app/services/report/narrative_generator.py) | 변경 없음 — 레거시 폴백으로 유지 |

### 변경 없는 파일 (호환성 유지)

- `fdd/backend/app/renderers/report_builder.py` — ReportIR/TextBlock 인터페이스 동일
- `fdd/backend/app/industry/*` — 산업 모듈 그대로 활용
- `fdd/backend/app/agents/guardrails.py` — `validate_narrative_claims()` 그대로 적용
- `fdd/pptx-service/` — PPTX 렌더러 변경 없음

---

## Phase 1: 기반 구축 — slot_fill 패키지

### 1-1. IM에서 복사-적응할 파일 (3개)

**loader.py** — IM [loader.py](im/src/narrative_generator/templates/loader.py) 복사
- `SlotDefinition`, `ConditionalBlock`, `SectionTemplate`, `BaseBlocks`, `TemplateLoader` 그대로
- 유일한 변경: docstring에서 "IM" → "FDD" 참조 수정
- `IMDocumentData` import 없음 (loader는 데이터 모델 비의존)

**registry.py** — IM [registry.py](im/src/narrative_generator/templates/registry.py) 복사
- `TemplateRegistry` 그대로 (캐시 + has/get/invalidate)
- 변경 없음

**slot_parser.py** — IM [slot_parser.py](im/src/narrative_generator/engine/slot_parser.py) 복사
- `SlotResponseParser`, `SlotFillResult`, `parse_slot_response()` 그대로
- 변경 없음 (JSON 파싱은 범용적)

### 1-2. FDD 전용 구현 (2개)

**renderer.py** — `FDDTemplateRenderer`

IM의 [renderer.py](im/src/narrative_generator/templates/renderer.py)를 기반으로 하되, 핵심 3개 메서드를 FDD용으로 재구현:

```python
class FDDTemplateRenderer:
    """FDD 전용 렌더러.

    IM TemplateRenderer와 동일한 6단계 파이프라인이나,
    데이터 경로 해석과 포맷/조건 평가가 FDD 모델에 맞춤.
    """

    def render(self, template, data: dict, llm_slots, *, industry, base_blocks) -> str:
        # 동일한 6단계: base_refs → L4 → L2 → L3 → cleanup → normalize

    def _resolve_data_path(self, data: dict, path: str) -> Any:
        # dict 기반 dotted path 탐색 (FDD 데이터는 dict로 전달)

    def _format_l2_value(self, value, format_spec) -> str:
        # FDD 전용 포맷:
        #   "currency_million" → "1,234" (백만원 단위, 숫자만)
        #   "currency_display" → "1,234백만원"
        #   "count" → "5"
        #   "count_items" → len(list) 반환
        #   "ratio" → "15.2%"

    def _evaluate_condition(self, condition, industry, data) -> bool:
        # IM 조건 + FDD 전용 조건:
        #   "has_qoe" → data.get("qoe") is not None
        #   "has_nwc" → data.get("nwc") is not None
        #   "has_debt" → data.get("debt") is not None
        #   "has_issues" → len(data.get("issues", [])) > 0
        #   "adjustment_ratio_high" → qoe.total_adj / qoe.reported > 0.15
```

**핵심 결정**: FDD 데이터를 `dict`로 전달 (별도 FDDReportData 클래스 불필요). `report_service.py`에서 이미 `qoe_calc`, `nwc_calc`, `debt_calc` 등의 ORM 객체를 직접 사용하므로, 렌더러에는 필요한 필드만 dict로 추출하여 전달한다.

```python
# report_service.py에서 구성
fdd_data = {
    "deal_name": deal.name,
    "industry_name": industry_module.industry_name_en,
    "industry_name_kr": industry_module.industry_name_kr,
    "qoe": {
        "reported_ebitda": _format_currency(qoe_calc.reported_ebitda),
        "adjusted_ebitda": _format_currency(qoe_calc.adjusted_ebitda),
        "total_adjustments": _format_currency(qoe_calc.total_adjustments),
        "adjustment_count": len(qoe_calc.adjustment_items),
        # ...
    } if qoe_calc else None,
    "nwc": { ... } if nwc_calc else None,
    "debt": { ... } if debt_calc else None,
    "issues": [ ... ],
}
```

**prompt_builder.py** — `FDDSlotFillPromptBuilder`

IM의 [slot_fill.py](im/src/narrative_generator/prompts/slot_fill.py) 패턴을 따르되, FDD 도메인 프롬프트:

```python
FDD_SLOT_FILL_SYSTEM = (
    "## Role\n"
    "You fill empty slots in a pre-written Financial Due Diligence report.\n\n"
    "## Rules\n"
    "1. Respond ONLY in JSON format.\n"
    "2. Reference ONLY the provided data — NEVER invent or calculate numbers.\n"
    "3. Write in English. Use 'million KRW' for currency.\n"
    "4. Maintain professional FDD tone: objective, concise, data-driven.\n"
    "5. Follow slot type constraints (sentence/paragraph/bullet_list).\n"
    "6. Match the surrounding boilerplate tone and style.\n"
)
```

`build_user_prompt(template, fdd_data)`:
1. 딜 기본 정보 (deal_name, industry)
2. 부동문자 맥락 (body 미리보기)
3. 각 L3 슬롯별: 힌트 + 관련 데이터 + max_tokens
4. JSON 응답 형식 예시

---

## Phase 2: 파일럿 YAML (2개 섹션)

### _base.yaml — FDD 공통 부동문자

```yaml
version: "1.0"
blocks:
  - name: fdd_disclaimer
    text: >-
      This analysis is based on information provided by management
      and does not constitute an independent audit.
  - name: fdd_currency_note
    text: "(Note: All amounts in million KRW unless otherwise stated)"
  - name: transition_qoe
    text: >-
      The following section presents the Quality of Earnings analysis.
  - name: transition_nwc
    text: >-
      The following section presents the Net Working Capital analysis.
  - name: transition_debt
    text: >-
      The following section presents the Net Debt analysis.
  - name: transition_risk
    text: >-
      The following section summarizes key risks identified during the analysis.
```

### executive_summary.yaml

L2 슬롯 7개 (deal_name, industry, reported_ebitda, adjusted_ebitda, total_adjustments, net_working_capital, net_debt) + L3 슬롯 4개 (qoe_summary, nwc_debt_summary, key_risks, overall_assessment) + L4 조건부 4개 (tech, healthcare, manufacturing, financial_services)

### methodology.yaml

대부분 L1 부동문자 + L2 슬롯 5개 (deal_name, industry, scope_items). LLM 호출 불필요 — 순수 템플릿.

---

## Phase 3: 핵심 분석 섹션 YAML (4개)

| 섹션 | L2 | L3 | L4 | 프로바이더 |
|------|-----|-----|-----|-----------|
| `qoe_analysis.yaml` | 5 (수치) | 3 (분류, 품질 평가, 매출 노트) | 2 (tech: R&D/SBC, manufacturing: CAPEX) | OpenAI |
| `nwc_analysis.yaml` | 5 (수치) | 3 (구성 분석, peg 평가, 계절성) | 2 (tech: 음의 NWC, manufacturing: 재고) | OpenAI |
| `debt_analysis.yaml` | 5 (수치) | 2 (구조 분석, 레버리지 평가) | 2 (tech: CB/SAFE, financial_services: 규제자본) | OpenAI |
| `risk_narrative.yaml` | 1 (issue_count) | 3 (분류, 완화 제안, 딜 영향) | 1 (고위험 이슈 경고) | Anthropic |

---

## Phase 4: 산업 변형 YAML

```
templates/industry_variants/
├── tech/
│   ├── executive_summary.yaml    # SaaS 특화 슬롯 (ARR, NRR)
│   └── qoe_analysis.yaml         # R&D 자본화, SBC 조건부 블록 강화
├── healthcare/
│   └── executive_summary.yaml    # 파이프라인, 임상시험 특화
├── manufacturing/
│   └── qoe_analysis.yaml         # CAPEX, 설비 가동률 특화
├── financial_services/
│   └── debt_analysis.yaml        # 규제자본, 충당금 특화
└── logistics/
    └── executive_summary.yaml    # 플릿, 네트워크 특화
```

---

## Phase 5 (향후): IM-FDD 공통 패키지 추출

`loader.py`, `registry.py`, `slot_parser.py`는 IM/FDD 동일 — 향후 `shared/narrative_templates/`로 추출 가능. Phase 1~4 완료 후 검토.

---

## report_service.py 통합 설계

### 시그니처 변경

```python
def build_report_ir(
    db, deal_id,
    include_qoe=True, include_nwc=True, include_debt=True, include_issues=True,
    use_llm_narratives=False,
    use_template_slotfill=False,   # ← 신규 파라미터
) -> ReportIR:
```

### 통합 로직 (기존 라인 518 부근에 추가)

```python
# 8.5a Template SlotFill 내러티브 (신규)
if use_template_slotfill:
    _build_slotfill_narratives(
        sections, deal, qoe_calc, nwc_calc, debt_calc, issues,
        industry_module, industry_id,
    )

# 8.5b LLM 자유 생성 내러티브 (레거시 — 기존 그대로)
elif narrator:
    # ... 기존 코드 유지 ...
```

### `_build_slotfill_narratives()` 헬퍼

```python
def _build_slotfill_narratives(sections, deal, qoe_calc, nwc_calc, debt_calc, issues,
                                industry_module, industry_id):
    """템플릿 슬롯 채우기 방식으로 내러티브 생성."""
    from app.services.report.slot_fill import (
        TemplateLoader, TemplateRegistry, FDDTemplateRenderer,
        FDDSlotFillPromptBuilder, parse_slot_response,
    )
    from app.services.llm.routing import create_fdd_model_router

    # 1. 인프라 초기화
    templates_dir = Path(__file__).parent / "templates"
    loader = TemplateLoader(templates_dir)
    registry = TemplateRegistry(loader)
    renderer = FDDTemplateRenderer()
    prompt_builder = FDDSlotFillPromptBuilder()
    base_blocks = loader.load_base()

    # 2. FDD 데이터 dict 구성
    fdd_data = _build_fdd_data_dict(deal, qoe_calc, nwc_calc, debt_calc, issues)

    # 3. LLM 라우터 (L3 슬롯용)
    router = None
    try:
        router = create_fdd_model_router()
    except Exception:
        pass

    # 4. 섹션별 렌더링
    section_order = ["executive_summary", "qoe_analysis", "nwc_analysis",
                     "debt_analysis", "risk_narrative", "methodology"]

    for section_id in section_order:
        if not registry.has(section_id):
            continue

        template = registry.get(section_id, industry=industry_id)

        # L3 슬롯이 있고 라우터가 있으면 LLM 호출
        llm_slots = {}
        if template.l3_slots and router:
            system = prompt_builder.build_system_prompt(
                industry_context=industry_module.format_narrative_context()
            )
            user = prompt_builder.build_user_prompt(template, fdd_data)
            response = router.generate(
                section_id, system_prompt=system, user_prompt=user,
                temperature=0.2, max_tokens=512,
            )
            result = parse_slot_response(response.text, list(template.l3_slots.keys()))
            llm_slots = result.filled_slots

        # 렌더링
        text = renderer.render(
            template, fdd_data, llm_slots,
            industry=industry_id, base_blocks=base_blocks,
        )

        # Guardrail (기존 validate_narrative_claims 활용)
        known_values = _extract_known_values(fdd_data)
        warnings = validate_narrative_claims(text, known_values)
        if warnings:
            logger.warning("SlotFill guardrail warnings [%s]: %s", section_id, warnings)

        sections.append(build_text_block(text, title=_SECTION_TITLES[section_id]))
```

---

## 멀티 LLM 라우팅 전략

슬롯 채우기에서도 기존 `FDDModelRouter`의 섹션별 라우팅을 유지:

| 섹션 | 라우팅 | 이유 |
|------|--------|------|
| executive_summary | Anthropic | 종합 평가, 장문 일관성 |
| qoe_analysis | OpenAI | 수치 정확도 |
| nwc_analysis | OpenAI | 수치 정확도 |
| debt_analysis | OpenAI | 수치 정확도 |
| risk_narrative | Anthropic | 전략적 서술 |
| methodology | (LLM 불필요) | 순수 L1+L2 |

`router.generate(section_id, ...)` 호출 시 `section_id`로 자동 라우팅됨.

---

## 호환성 보장

1. **`use_template_slotfill=False` (기본값)**: 기존 코드 100% 유지
2. **`use_template_slotfill=True` + `use_llm_narratives=False`**: 슬롯 채우기 모드
3. **`use_llm_narratives=True` (레거시)**: 기존 자유 생성 방식 그대로
4. **Guardrail**: `validate_narrative_claims()` 슬롯 채우기 결과에도 동일 적용
5. **PPTX/DOCX 렌더러**: TextBlock 인터페이스 동일 → 변경 없음

---

## 구현 순서 요약

| Phase | 범위 | 파일 수 | 핵심 작업 |
|-------|------|---------|----------|
| **1** | slot_fill 패키지 | 6개 (신규) | loader/registry/parser 복사, renderer/prompt_builder FDD 전용 구현 |
| **2** | 파일럿 YAML | 3개 (신규) | `_base.yaml`, `executive_summary.yaml`, `methodology.yaml` |
| **2** | report_service 통합 | 1개 (수정) | `use_template_slotfill` 파라미터 + `_build_slotfill_narratives()` |
| **3** | 분석 섹션 YAML | 4개 (신규) | qoe/nwc/debt/risk YAML |
| **4** | 산업 변형 | ~6개 (신규) | 5개 산업별 오버라이드 YAML |

---

## 검증 방법

1. **단위 테스트**: `FDDTemplateRenderer._resolve_data_path`, `_format_l2_value`, `_evaluate_condition`
2. **YAML 파싱 테스트**: 각 YAML이 `TemplateLoader.load_section()`으로 정상 로드되는지
3. **A/B 비교**: 동일 딜 데이터로 레거시 vs 슬롯 채우기 결과 비교
4. **Guardrail 통합**: `validate_narrative_claims()`가 슬롯 채우기 결과에서 false positive 없는지
5. **회귀 테스트**: `use_template_slotfill=False`일 때 기존 테스트 100% 통과
6. **E2E**: 실제 딜 데이터로 Report IR 생성 → PPTX 출력 확인
