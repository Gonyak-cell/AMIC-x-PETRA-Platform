# IM 보고서 부동문자 템플릿 + LLM 슬롯 채우기 시스템 구현 계획

> 작성일: 2026-02-17 12:04
> 최종 수정: 2026-02-17 13:29
> 목적: IM 보고서의 공통 문구(부동문자)를 고정 프레임으로 관리하고, LLM이 업로드 자료 + 리서치 기반으로 슬롯만 채우는 방식으로 전환

---

## Context

**문제**: 현재 IM 시스템은 12~19개 섹션 전부를 LLM이 자유 생성 → 매번 미묘하게 다른 문체/구조, 비용 높음, 실제 보고서에서 반복되는 공통 문구까지 매번 재생성.

**목표**: 외부 참조 보고서에서 추출한 부동문자를 고정 프레임으로 관리하고, `{{slot}}` 위치만 LLM이 업로드된 자료와 리서치 내용을 토대로 채우는 방식으로 전환.

**적용 범위**: IM 먼저 (FDD는 후속)

---

## 현재 vs 목표 비교

### 현재 방식
```
System Prompt (IB 전문가 역할 + 규칙) + User Prompt (전체 재무 데이터)
  → LLM이 섹션 전체 텍스트 자유 생성 (600토큰/섹션)
  → 매번 다른 구조/문체
```

### 목표 방식
```
YAML 템플릿 (부동문자 프레임 + {{slot}} 마커)
  → L2 슬롯: IMDocumentData에서 직접 치환 (기업명, 날짜 등)
  → L4 조건부: 산업군에 따라 부동문자 블록 선택
  → L3 슬롯: LLM이 업로드 자료 + 리서치 기반으로 채움 (JSON 출력)
  → TemplateRenderer가 부동문자 + 채워진 슬롯 조합
  → 최종 텍스트 (data.narratives에 저장 — 렌더러 변경 불필요)
```

---

## 슬롯 레벨 분류

| 레벨 | 처리 방식 | 예시 |
|------|----------|------|
| **L1 완전 고정** | 변환 없이 그대로 | 면책조항, "본 자료는...", 프로토콜 문구 |
| **L2 단순 치환** | `IMDocumentData` 필드 직접 참조 | `{{company_name}}`, `{{report_date}}` |
| **L3 LLM 슬롯** | LLM이 업로드 자료/리서치 기반 작성 | `{{revenue_highlight}}`, `{{market_opportunity}}` |
| **L4 조건부 블록** | 산업군/조건에 따라 부동문자 블록 삽입 | Tech→ARR 블록, 제조→설비가동률 블록 |

---

## YAML 템플릿 구조 예시

```yaml
# im/src/narrative_generator/templates/executive_summary.yaml
section_id: executive_summary
version: "1.0"
source_reference: "참조 IM 보고서"

slots:
  company_name:
    level: L2
    source: company_name_kr

  company_intro:
    level: L3
    type: paragraph
    hint: "기업의 핵심 사업과 시장 포지션을 1-2문장으로 소개"
    max_tokens: 80
    data_keys: [company_name_kr, company_overview.business_model]

  revenue_highlight:
    level: L3
    type: sentence
    hint: "최근 연도 매출액과 성장률을 포함한 재무 하이라이트"
    max_tokens: 60
    data_keys: [financial_statements.revenue, derived_metrics.revenue_cagr_3y]

body: |
  {{company_name}}(이하 "대상회사")은 {{company_intro}}

  재무적 측면에서, 대상회사는 {{revenue_highlight}} {{ebitda_comment}}
  이러한 재무 성과는 대상회사의 사업 모델의 견고함을 입증하고 있습니다.

  시장 환경 측면에서, {{market_opportunity}}
  이러한 시장 동향은 대상회사에게 유의미한 성장 기회를 제공하고 있습니다.

conditional_blocks:
  - condition: "industry == 'tech'"
    insert_after: "revenue_highlight"
    text: "특히, SaaS 기반 반복 매출 구조의 안정성이 돋보이며, {{arr_highlight}}"
```

---

## 구현 구조 (신규/수정 파일)

### 신규 파일

```
im/src/narrative_generator/
  templates/                          # 신규 디렉터리
    __init__.py
    loader.py                         # TemplateLoader, SlotDefinition, SectionTemplate
    registry.py                       # TemplateRegistry (캐시 + 산업별 오버라이드)
    renderer.py                       # TemplateRenderer (L1/L2/L3/L4 조합 엔진)
    extractor.py                      # TemplateExtractor (참조 보고서 → YAML 초안) [Phase 6]
    cli.py                            # 템플릿 추출 CLI 커맨드 [Phase 6]
    _base.yaml                        # 공통 부동문자 (면책조항, 연결 문구 등)
    executive_summary.yaml            # 파일럿 섹션 1 [Phase 2]
    contact.yaml                      # 파일럿 섹션 2 [Phase 2]
    ...                               # 추가 섹션 (Phase 3~4에서 추가)
    industry_variants/                # 산업별 오버라이드
      tech/
      healthcare/
      manufacturing/
      financial_services/
      logistics/
      general/
  prompts/
    slot_fill.py                      # SlotFillPromptBuilder (슬롯 채우기 전용 프롬프트)
  engine/
    slot_parser.py                    # SlotResponseParser (JSON 파싱 + 검증)
```

### 수정 파일

| 파일 | 변경 내용 |
|------|---------|
| `orchestrator.py` | `_generate_section()`에 템플릿/레거시 분기 추가 |
| `config.py` | `template_enabled`, `template_dir`, `slot_fill_temperature` 추가 |

### 변경 없는 파일 (호환성 유지)

- `im/src/narrative_generator/prompts/base.py` — 기존 프롬프트 그대로 유지 (레거시 모드)
- `im/src/design_renderer/` — 렌더러 21개 전부 변경 없음 (`data.narratives` 인터페이스 동일)
- `im/src/api/tasks/` — Celery 태스크 변경 없음 (`orchestrator.generate()` 시그니처 유지)
- `im/src/design_renderer/im_document.py` — `IMDocumentData` SSoT 구조 유지

---

## 핵심 로직: Orchestrator 분기

```python
# orchestrator.py — _generate_section() 수정
def _generate_section(self, section_id, data, industry, ...):
    # 템플릿이 있으면 → 슬롯 채우기 방식
    if self._template_registry and self._template_registry.has(section_id):
        return self._generate_section_template(section_id, data, ...)
    # 없으면 → 기존 자유 생성 방식 (레거시)
    return self._generate_section_legacy(section_id, data, ...)
```

이로써 **섹션 단위 점진적 마이그레이션**이 가능. 템플릿이 준비된 섹션만 새 방식, 나머지는 기존 방식 유지.

---

## 프롬프트 전략 변경

### 기존 (자유 생성)
```
System: "당신은 IB 전문가입니다. Executive Summary를 작성하세요."
User: "기업명: X, 매출: 1500억, EBITDA: 300억, ..."
→ LLM이 3~5문단 전체 자유 생성
```

### 새로운 (슬롯 채우기)
```
System: "이미 작성된 IM 문서의 빈 슬롯을 채우는 역할입니다. JSON으로 응답하세요."
User: "다음 슬롯을 채워주세요:
  1. company_intro (문단, 80토큰): [힌트] + [관련 데이터] + [주변 부동문자 맥락]
  2. revenue_highlight (문장, 60토큰): [힌트] + [관련 데이터]
  응답: { 'company_intro': '...', 'revenue_highlight': '...' }"
→ LLM이 슬롯별 짧은 텍스트만 JSON으로 생성
```

---

## 마이그레이션 단계

| Phase | 범위 | 내용 | 상태 |
|-------|------|------|------|
| **1. 인프라** | 신규 모듈 | `TemplateLoader`, `TemplateRegistry`, `TemplateRenderer`, `SlotFillPromptBuilder`, `SlotResponseParser` 구현 | ✅ 완료 |
| **2. 파일럿** | 2개 섹션 | `_base.yaml` + `executive_summary.yaml` + `contact.yaml` 템플릿 작성 | ✅ 완료 |
| **3. Core** | +4개 섹션 | `company_overview`, `business_overview`, `deal_overview`, `financial_analysis` | ✅ 완료 |
| **4. Strategy** | +7개 섹션 | `investment_highlights`, `market_overview`, `value_creation`, `growth_strategy`, `management_team`, `business_model`, `appendix` | ✅ 완료 |
| **5. 산업 변형** | L4 조건부 | 6개 산업 × 핵심 섹션 2~3개의 오버라이드 YAML | ✅ 완료 |
| **6. 추출 도구** | TemplateExtractor | 참조 보고서 PDF/PPTX → YAML 초안 자동 변환 CLI | ✅ 완료 |

---

## 구현 완료 파일 목록 (Phase 1~4)

### Phase 1: 인프라 (신규 6개 + 수정 2개) — ✅ 2026-02-17 12:50 구현

| 파일 | 역할 |
|------|------|
| `templates/__init__.py` | 패키지 초기화, 클래스 re-export |
| `templates/loader.py` | TemplateLoader, SlotDefinition, SectionTemplate, ConditionalBlock, BaseBlocks |
| `templates/registry.py` | TemplateRegistry (캐시 + 산업별 오버라이드 + 병합) |
| `templates/renderer.py` | TemplateRenderer (L1/L2/L3/L4 조합 + 베이스 블록 참조 + 리스트 인덱싱) |
| `prompts/slot_fill.py` | SlotFillPromptBuilder (슬롯 채우기 전용 프롬프트, JSON 응답 지시) |
| `engine/slot_parser.py` | SlotResponseParser (JSON 파싱 + 코드블록 추출 + regex 폴백 3단계) |
| `config.py` | template_enabled, template_dir, slot_fill_temperature 추가 |
| `engine/orchestrator.py` | 템플릿/레거시 분기, _generate_section_template(), TemplateRegistry 통합 |

### Phase 2: 파일럿 YAML (신규 3개) — ✅ 2026-02-17 12:50 구현

| 파일 | 역할 |
|------|------|
| `templates/_base.yaml` | 공통 부동문자 10개 블록 (면책조항, 비밀유지, 연결 문구, 마무리 문구, 수치 주석) |
| `templates/executive_summary.yaml` | Executive Summary 템플릿 (L2 5개 + L3 5개 슬롯, L4 조건부 4개) |
| `templates/contact.yaml` | Contact 템플릿 (L2 10개 슬롯, LLM 호출 불필요, 베이스 블록 참조) |

### Phase 3: Core YAML (신규 4개) — ✅ 2026-02-17 12:50 구현

| 파일 | 슬롯 구성 | 역할 |
|------|----------|------|
| `templates/company_overview.yaml` | L2 7개 + L3 4개 + L4 3개 | 회사 개요 (설립 배경, 비즈니스 모델, 성장 스토리, 가치사슬) |
| `templates/business_overview.yaml` | L2 4개 + L3 4개 + L4 3개 | 사업 현황 (매출 구성, 사업부별 분석, 고객 관계, 수익성) |
| `templates/deal_overview.yaml` | L2 8개 + L3 3개 + L4 2개 | 거래 개요 (거래 배경, 거래 구조, 타임라인) |
| `templates/financial_analysis.yaml` | L2 10개 + L3 5개 + L4 4개 | 재무 분석 (매출/수익성, 재무건전성, 현금흐름, 핵심지표, 전망) |

### Phase 4: Strategy YAML (신규 7개 + _base.yaml 수정) — ✅ 2026-02-17 12:57 구현

| 파일 | 슬롯 구성 | 역할 |
|------|----------|------|
| `templates/investment_highlights.yaml` | L2 3개 + L3 5개 + L4 4개 | 투자 하이라이트 (시장 포지션, 재무 강점, 성장 잠재력, 리스크 완화) |
| `templates/market_overview.yaml` | L2 5개 + L3 4개 + L4 4개 | 시장 분석 (TAM/SAM/SOM, 경쟁 구도, 산업 트렌드, 시장 포지션) |
| `templates/value_creation.yaml` | L2 2개 + L3 5개 + L4 4개 | 가치 창출 방안 (매출 성장, 운영 효율화, 전략적 이니셔티브) |
| `templates/growth_strategy.yaml` | L2 2개 + L3 5개 + L4 4개 | 성장 전략 (유기적 성장, 신규 시장, M&A, 로드맵) |
| `templates/management_team.yaml` | L2 10개 + L3 3개 + L4 2개 | 경영진 (팀 개요, CEO 프로필, 핵심 임원 요약) |
| `templates/business_model.yaml` | L2 4개 + L3 5개 + L4 4개 | 비즈니스 모델 (수익 구조, 경쟁 해자, 가치사슬, 확장성) |
| `templates/appendix.yaml` | L2 4개 + L3 2개 + L4 2개 | 부록 (데이터 출처, 핵심 전제, 용어 정의, 면책조항) |
| `templates/_base.yaml` (수정) | +4개 블록 | 신규 전환 문구 (value_creation, management, business_model, appendix) |

### Phase 5: 산업 변형 YAML (신규 13개) — ✅ 2026-02-17 13:07 구현

6개 산업별 `industry_variants/{industry}/` 디렉터리에 오버라이드 YAML 배치.
TemplateRegistry의 `_merge_templates()` 병합 로직으로 기본 템플릿 + 산업 특화 슬롯/본문이 조합됨.

#### Tech/SaaS (3개 파일)

| 파일 | 신규 L3 슬롯 | 역할 |
|------|-------------|------|
| `industry_variants/tech/financial_analysis.yaml` | `saas_metrics_analysis`, `unit_economics_analysis` | SaaS 핵심 지표(ARR/NRR/Churn) + 유닛 이코노믹스(CAC/LTV) 분석 |
| `industry_variants/tech/business_model.yaml` | `platform_dynamics`, `saas_pricing_model` | 플랫폼 역학(네트워크 효과) + SaaS 가격 모델 분석 |
| `industry_variants/tech/market_overview.yaml` | `tech_disruption_analysis` | 기술 패러다임 전환(AI/Cloud/DX) 영향 분석 |

#### Healthcare/Biotech (3개 파일)

| 파일 | 신규 L3 슬롯 | 역할 |
|------|-------------|------|
| `industry_variants/healthcare/financial_analysis.yaml` | `rnd_pipeline_analysis`, `regulatory_cost_analysis` | R&D 파이프라인(rNPV) + 규제 비용 영향 분석 |
| `industry_variants/healthcare/investment_highlights.yaml` | `pipeline_value_assessment`, `regulatory_moat_assessment` | 파이프라인 가치 평가 + 규제 해자 분석 |
| `industry_variants/healthcare/business_model.yaml` | `ip_portfolio_analysis`, `regulatory_structure` | IP 포트폴리오(특허/데이터독점) + 규제 구조 분석 |

#### Manufacturing (2개 파일)

| 파일 | 신규 L3 슬롯 | 역할 |
|------|-------------|------|
| `industry_variants/manufacturing/financial_analysis.yaml` | `capex_structure_analysis`, `inventory_cost_analysis` | CAPEX 구분(유지/성장) + 재고/원가 관리 분석 |
| `industry_variants/manufacturing/business_model.yaml` | `production_capability`, `supply_chain_structure` | 생산 역량(OEE/CAPA) + 공급망 구조 분석 |

#### Financial Services (2개 파일)

| 파일 | 신규 L3 슬롯 | 역할 |
|------|-------------|------|
| `industry_variants/financial_services/financial_analysis.yaml` | `capital_adequacy_analysis`, `credit_quality_analysis` | 규제자본(BIS/CET1) + 자산건전성(NPL/ECL) 분석 |
| `industry_variants/financial_services/business_model.yaml` | `regulatory_framework`, `fee_income_structure` | 규제 프레임워크(라이선스) + 수수료 수익 구조 분석 |

#### Logistics (2개 파일)

| 파일 | 신규 L3 슬롯 | 역할 |
|------|-------------|------|
| `industry_variants/logistics/financial_analysis.yaml` | `fleet_economics_analysis`, `network_efficiency_analysis` | 플릿 경제성(가동률/유류비) + 네트워크 효율성 분석 |
| `industry_variants/logistics/business_model.yaml` | `logistics_network`, `automation_technology` | 물류 네트워크(Hub-Spoke) + 자동화 기술 분석 |

#### General (1개 파일)

| 파일 | 신규 L3 슬롯 | 역할 |
|------|-------------|------|
| `industry_variants/general/financial_analysis.yaml` | `peer_comparison_analysis` | 동종업계 비교 분석(Peer Comparison) |

### Phase 6: 추출 도구 (신규 2개 + 수정 1개) — ✅ 2026-02-17 13:16 구현

| 파일 | 역할 |
|------|------|
| `templates/extractor.py` | TemplateExtractor — 참조 보고서(PDF/PPTX)에서 YAML 템플릿 초안 자동 생성. LLM 분석 + 휴리스틱 폴백 이중 경로. 텍스트 추출(pymupdf/python-pptx), 섹션 분할(LLM/휴리스틱), 부동문자/슬롯 분류, YAML 생성 파이프라인 |
| `templates/cli.py` | CLI 커맨드 — `extract`(단일 섹션), `extract-all`(전체 분할+추출), `text`(텍스트 추출 디버깅), `list-sections`(섹션 ID 목록) 4개 서브커맨드 |
| `templates/__init__.py` (수정) | `TemplateExtractor`, `ExtractionResult` re-export 추가 |

#### 핵심 기능

**TemplateExtractor 파이프라인**:
1. **텍스트 추출**: PDF(pymupdf) / PPTX(python-pptx) / TXT → 원문 텍스트
2. **섹션 분할**: LLM 기반 자동 분할 또는 휴리스틱(헤더 패턴) 폴백
3. **LLM 분석**: 고정 텍스트(L1) vs 가변 텍스트(L2/L3) 분류, JSON 구조화
4. **YAML 생성**: SectionTemplate 구조에 맞는 YAML 초안 출력

**이중 경로 설계**:
- LLM 경로: OpenAI API로 부동문자/슬롯 분류 (정확도 높음)
- 휴리스틱 경로: 수치 패턴 기반 자동 분류 (`--no-llm` 옵션, LLM 미사용 시 자동 폴백)

**CLI 사용 예시**:
```bash
# 단일 섹션 추출
python -m src.narrative_generator.templates.cli extract \
    --file reference_im.pdf --section executive_summary

# 전체 보고서 추출
python -m src.narrative_generator.templates.cli extract-all \
    --file reference_im.pdf --output-dir templates/

# 휴리스틱 모드 (LLM 없이)
python -m src.narrative_generator.templates.cli extract \
    --file reference_im.pdf --no-llm
```

---

## 검증 방법

1. **단위 테스트**: 각 신규 클래스별 (loader, renderer, parser) — ✅ **93/93 통과** (2026-02-17 13:29)
2. **A/B 비교**: 동일 입력 → 기존 출력 vs 템플릿 출력 품질 비교 — ✅ **10/10 통과** (2026-02-17 13:29)
3. **회귀 테스트**: `template_enabled=False`일 때 기존 테스트 100% 통과 확인 — ✅ **144/144 통과** (2026-02-17 13:29)
4. **비용 벤치마크**: 섹션당 토큰 사용량 비교 (예상: 30~50% 절감)
5. **E2E**: 실제 기업 데이터로 IM 생성 → PPTX/PDF 출력 확인

### 테스트 파일 목록 (2026-02-17 13:29 신규)

| 파일 | 테스트 수 | 대상 모듈 |
|------|----------|----------|
| `tests/test_narrative_generator/test_template_infra.py` | 52개 | SlotDefinition, TemplateLoader, TemplateRegistry, TemplateRenderer, SlotResponseParser, SlotFillPromptBuilder |
| `tests/test_narrative_generator/test_template_extractor.py` | 21개 | ExtractionResult, TemplateExtractor (텍스트 추출, 섹션 식별, 휴리스틱 분석, LLM 응답 파싱, YAML 생성) |
| `tests/test_narrative_generator/test_template_ab.py` | 10개 | Orchestrator A/B 비교 (template_enabled=True vs False, 산업별 오버라이드, 슬롯 파싱 실패 graceful degradation) |

### 테스트 커버리지 요약

- **TemplateLoader**: YAML 로딩, base blocks, 섹션, 산업 오버라이드, 조건부 블록
- **TemplateRegistry**: 캐시, 산업별 병합 (`_merge_templates`), `has`/`get`
- **TemplateRenderer**: L1/L2/L3/L4 렌더링, base block 참조, 조건 평가, 포맷팅 (currency/percent/count), dotted notation 경로 조회, 미해결 슬롯 처리, 공백 정규화
- **SlotResponseParser**: 3단계 폴백 (JSON → code block → regex), 단일 슬롯 폴백, 리스트 변환, 부분 매치
- **SlotFillPromptBuilder**: 시스템/유저 프롬프트 조립, L3 슬롯 없을 때 빈 반환, 데이터 포함 검증
- **TemplateExtractor**: TXT 추출, 섹션 ID 자동 추정, 휴리스틱 분석, LLM 응답 파싱, YAML 생성, 폴백 YAML, 전체 보고서 분할 추출
- **A/B 비교**: 템플릿 모드 부동문자 포함, contact L2 전용 (LLM 호출 0회), 산업별 조건부 블록, 레거시 회귀, 멀티 섹션 혼합 모드, 슬롯 파싱 실패 graceful degradation

---

## 리스크 대응

| 리스크 | 대응 |
|--------|------|
| LLM이 JSON 형식 미준수 | `slot_parser.py`에 regex 폴백 + 1회 재시도 |
| 부동문자와 슬롯 톤 불일치 | 주변 맥락(surrounding_text)을 프롬프트에 포함 |
| 참조 보고서 저작권 | 일반적 금융 문구로 재작성, 직접 복사 금지 |
| 기존 테스트 파손 | `template_enabled=False` 기본값 (opt-in) |
