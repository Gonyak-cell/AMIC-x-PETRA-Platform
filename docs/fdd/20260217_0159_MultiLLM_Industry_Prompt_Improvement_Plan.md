# FDD/IM 멀티LLM 및 산업별 프롬프트 개선 계획

> 작성: 2026-02-17 01:20

## Context

FDD와 IM 백엔드의 멀티LLM 시스템을 점검한 결과 5개 이슈가 발견됨:

| # | 이슈 | 영향 |
|---|------|------|
| 1 | FDD 산업별 프롬프트 변형 미사용 — `FDDNarrativeTemplate` 정의만 되고 `narrative_generator`에서 미사용 | 산업 컨텍스트가 엔진(계산)에만 반영, LLM 내러티브에는 미반영 |
| 2 | FDD 라우팅 맵 하드코딩 — `DEFAULT_FDD_ROUTING`만 존재, 환경변수 커스텀 불가 | IM은 `LLM_ROUTING_MAP` 환경변수로 런타임 변경 가능 |
| 3 | FDD 한국 특수성 오버레이 없음 — IM은 K-IFRS, 규제, 노동법, ESG 데이터 구현 | FDD 보고서에 한국 회계/규제 맥락 부재 |
| 4 | Anthropic 모델 버전 불일치 — FDD: `claude-sonnet-4-5-20250929`, IM: `claude-sonnet-4-20250514` | 품질/비용 차이 가능 |
| 5 | 산업별 LLM 라우팅 양쪽 모두 미구현 — 같은 섹션은 산업 무관하게 동일 LLM 사용 | 특정 산업에서 더 나은 LLM이 있어도 반영 불가 |

IM은 이미 환경변수 라우팅, 산업별 프롬프트 변형, 한국 오버레이를 구현했으므로, **IM 패턴을 참조하여 FDD에 동일 수준 적용** + 양쪽에 산업별 LLM 라우팅 추가.

### 모노레포 디렉토리 구조

```
AMIC x PETRA Platform/          <- 루트 (현재 작업 디렉토리)
├── fdd/backend/app/            <- FDD 백엔드
├── im/src/                     <- IM 백엔드
├── kiis/app/                   <- KIIS 백엔드
├── amic-platform/src/          <- 프론트엔드
└── docker-compose.yml
```

---

## 구현 순서

의존성을 고려한 순서: **이슈4 -> 이슈2 -> 이슈1 -> 이슈3 -> 이슈5**

---

## Step 1: Anthropic 모델 버전 통일 + 환경변수화 (이슈 4)

**목적**: 모델명을 하드코딩에서 환경변수로 전환하고, FDD/IM 간 버전 통일

### 수정 파일

**1-A. `fdd/backend/app/services/llm/client.py`** (라인 89, ~165, ~236)

각 클라이언트의 `DEFAULT_MODEL`을 유지하되, `__init__`에서 환경변수 우선 적용:

```python
class AnthropicClient(LLMClient):
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self) -> None:
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("ANTHROPIC_MODEL_NAME", self.DEFAULT_MODEL)  # 추가

class OpenAIClient(LLMClient):
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._model = os.getenv("OPENAI_MODEL_NAME", self.DEFAULT_MODEL)  # 추가

class GeminiClient(LLMClient):
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self) -> None:
        self._api_key = os.getenv("GOOGLE_API_KEY", "")
        self._model = os.getenv("GOOGLE_MODEL_NAME", self.DEFAULT_MODEL)  # 추가
```

각 `chat()` 메서드에서 `model = model or self._model` 로 변경 (기존: `model or self.DEFAULT_MODEL`)

**1-B. `im/src/narrative_generator/config.py`** (라인 47)

Anthropic 모델 기본값 업데이트:
```python
# 변경 전
anthropic_model_name: str = Field(default="claude-sonnet-4-20250514", ...)
# 변경 후
anthropic_model_name: str = Field(default="claude-sonnet-4-5-20250929", ...)
```

**1-C. `fdd/.env.example`** — 새 환경변수 문서화 추가:
```bash
# LLM 모델명 (선택, 기본값 사용 가능)
ANTHROPIC_MODEL_NAME=claude-sonnet-4-5-20250929
OPENAI_MODEL_NAME=gpt-4o
GOOGLE_MODEL_NAME=gemini-2.0-flash
```

---

## Step 2: FDD 라우팅 맵 환경변수 지원 (이슈 2)

**목적**: IM의 `LLM_ROUTING_MAP`, `LLM_FALLBACK_ORDER` 패턴을 FDD에 적용

### 수정 파일

**2-A. `fdd/backend/app/services/llm/routing/router_factory.py`**

`create_fdd_model_router()`에 환경변수 파싱 로직 추가:

```python
import json
import os

def create_fdd_model_router(
    routing_map: dict[str, str] | None = None,
) -> FDDModelRouter:
    providers: dict[str, LLMClient] = {
        "openai": OpenAIClient(),
        "anthropic": AnthropicClient(),
        "gemini": GeminiClient(),
    }

    # 환경변수에서 라우팅 맵 파싱 (신규)
    if routing_map is None:
        raw_map = os.getenv("FDD_LLM_ROUTING_MAP", "")
        if raw_map:
            try:
                routing_map = json.loads(raw_map)
            except json.JSONDecodeError:
                logger.warning("FDD_LLM_ROUTING_MAP 파싱 실패: %s", raw_map)

    # 환경변수에서 폴백 순서 파싱 (신규)
    fallback_order_str = os.getenv("FDD_LLM_FALLBACK_ORDER", "")
    fallback_order = None
    if fallback_order_str:
        fallback_order = [p.strip() for p in fallback_order_str.split(",") if p.strip()]

    available = [name for name, client in providers.items() if client.is_available()]
    logger.info("FDD ModelRouter created", extra={"ctx": {"available_providers": available}})

    return FDDModelRouter(
        providers=providers,
        routing_map=routing_map,
        fallback_order=fallback_order,
    )
```

**2-B. `fdd/backend/app/services/llm/routing/model_router.py`**

`FDDModelRouter.__init__`에 `fallback_order` 파라미터 추가:

```python
def __init__(
    self,
    providers: dict[str, LLMClient],
    routing_map: dict[str, str] | None = None,
    fallback_order: list[str] | None = None,  # 추가
):
    self._providers = providers
    self._routing_map = routing_map or DEFAULT_FDD_ROUTING
    self._fallback_order = fallback_order  # 추가 (None이면 FALLBACK_CHAIN 사용)
```

`resolve()` 메서드의 폴백 로직 업데이트:
```python
# 기존: fallbacks = FALLBACK_CHAIN.get(primary, [])
# 변경: 커스텀 폴백 -> 기본 폴백 체인
if self._fallback_order:
    fallbacks = [f for f in self._fallback_order if f != primary]
else:
    fallbacks = FALLBACK_CHAIN.get(primary, [])
```

**2-C. `fdd/.env.example`** — 라우팅 환경변수 추가:
```bash
# 라우팅 커스텀 (선택, JSON 형식)
FDD_LLM_ROUTING_MAP=
FDD_LLM_FALLBACK_ORDER=openai,anthropic,gemini
```

---

## Step 3: FDD 산업별 프롬프트 변형 활성화 (이슈 1)

**목적**: 기존 `FDDNarrativeTemplate`을 활용하여 산업별 프롬프트 강화

### 설계 결정

기존 `FDDNarrativeTemplate` 데이터 클래스(section_id, template_text, emphasis_areas, terminology_overrides)는 IM의 `IndustryVariant`와 필드가 거의 동일하므로, **별도 variant 시스템을 만들지 않고 기존 데이터 클래스를 활성화**.

### 수정 파일

**3-A. `fdd/backend/app/industry/base.py`** — `format_narrative_context()` 메서드 추가:

```python
def format_narrative_context(self, section_id: str | None = None) -> str:
    """산업별 프롬프트 컨텍스트를 포맷팅된 문자열로 반환한다."""
    templates = self.get_narrative_templates()
    if not templates:
        return ""
    if section_id:
        templates = [t for t in templates if t.section_id == section_id]

    parts = [f"### {self.industry_name_en} ({self.industry_name_kr}) 산업 분석 가이드\n"]
    for tmpl in templates:
        if tmpl.emphasis_areas:
            parts.append("#### 핵심 분석 영역")
            for area in tmpl.emphasis_areas:
                parts.append(f"- {area}")
        if tmpl.terminology_overrides:
            parts.append("\n#### 산업 특화 용어")
            for general, specific in tmpl.terminology_overrides.items():
                parts.append(f"- {general} -> {specific}")
        if tmpl.template_text:
            parts.append(f"\n#### 추가 지침\n{tmpl.template_text}")
    return "\n".join(parts)
```

**3-B. 각 산업 모듈에 `get_narrative_templates()` 오버라이드** (5개 파일)

- `fdd/backend/app/industry/tech_saas.py` — ARR/MRR, R&D 자본화, SBC, 음의 NWC
- `fdd/backend/app/industry/manufacturing.py` — CAPEX/가동률, 재고, 감가상각
- `fdd/backend/app/industry/healthcare.py` — 파이프라인, 규제, 특허, R&D 자산화
- `fdd/backend/app/industry/financial_services.py` — 대손, 자본비율, Trading P&L
- `fdd/backend/app/industry/logistics.py` — 유류비, 리스부채, 가동률
- `fdd/backend/app/industry/general.py` — 빈 리스트 유지 (변경 없음)

예시 — `tech_saas.py`:
```python
def get_narrative_templates(self) -> list[FDDNarrativeTemplate]:
    return [
        FDDNarrativeTemplate(
            section_id="executive_summary",
            template_text=(
                "SaaS/구독 모델 특성을 반영한 FDD 분석:\n"
                "- ARR/MRR 기반 수익 지속성 평가\n"
                "- 높은 R&D 비중의 EBITDA 정상화 관점\n"
                "- 음의 NWC 구조(선수수익)의 긍정적 해석"
            ),
            emphasis_areas=[
                "ARR/MRR 성장률 및 NRR (순매출유지율)",
                "R&D 자본화/SBC 조정의 EBITDA 영향",
                "CAC 회수 기간 및 LTV/CAC 비율",
                "이탈률(Churn Rate) 추세와 수익 지속성",
            ],
            terminology_overrides={
                "매출액": "ARR 또는 매출액",
                "재고": "해당 없음 (소프트웨어/서비스)",
                "설비투자": "R&D 투자 및 클라우드 인프라",
            },
        ),
    ]
```

**3-C. `fdd/backend/app/services/report/narrative_generator.py`** — 산업 컨텍스트 주입

`FDDNarrativeGenerator.__init__`에 `industry_context` 파라미터 추가:
```python
def __init__(self, router: FDDModelRouter, industry_context: str = ""):
    self._router = router
    self._industry_context = industry_context
```

각 `generate_*` 메서드의 `system_prompt`에 산업 컨텍스트 추가:
```python
if self._industry_context:
    system_prompt += f"\n\n## Industry Context\n{self._industry_context}"
```

적용 대상: `generate_executive_summary`, `generate_qoe_commentary`, `generate_methodology`, `generate_risk_narrative` (4개 메서드)

**3-D. `fdd/backend/app/services/report/report_service.py`** (~라인 176-187)

narrator 생성 시 산업 컨텍스트 전달:
```python
industry_narrative_ctx = industry_module.format_narrative_context()
narrator = FDDNarrativeGenerator(router, industry_context=industry_narrative_ctx)
```

---

## Step 4: FDD 한국 특수성 오버레이 (이슈 3)

**목적**: IM의 `im/src/industry/korea/` 패턴을 참조하여 FDD 전용 한국 오버레이 추가

### 참조 파일 (IM 기존 구현)

- `im/src/industry/korea/models.py` — KoreaOverlayData, RegulatoryItem 등
- `im/src/industry/korea/regulatory.py` — 규제 데이터
- `im/src/industry/korea/kifrs.py` — K-IFRS 항목
- `im/src/industry/korea/labor_esg.py` — 노동법/ESG
- `im/src/industry/korea/__init__.py` — get_korea_overlay_data()
- `im/src/industry/base.py:103-118` — get_korea_overlay() 메서드

### 신규 파일

**4-A. `fdd/backend/app/industry/korea/models.py`** — FDD 특화 데이터 모델

```python
@dataclass(frozen=True)
class FDDRegulatoryItem:
    regulation_id: str
    law_name_kr: str
    authority: str
    fdd_impact: str              # FDD 분석 영향
    applicable_industries: list[str]

@dataclass(frozen=True)
class FDDKIFRSNote:
    standard_number: str         # "1115", "1116" 등
    topic_kr: str
    ebitda_impact: str           # EBITDA 조정 관련성 (FDD 특화)
    nwc_impact: str              # NWC 산정 관련성 (FDD 특화)
    applicable_industries: list[str]

@dataclass(frozen=True)
class FDDTaxItem:
    item_id: str
    description_kr: str
    fdd_consideration: str       # FDD 세무 검토 사항
    applicable_industries: list[str]

@dataclass(frozen=True)
class FDDKoreaOverlayData:
    industry_id: str
    regulatory_items: list[FDDRegulatoryItem]
    kifrs_notes: list[FDDKIFRSNote]
    tax_items: list[FDDTaxItem]
```

**4-B. `fdd/backend/app/industry/korea/regulatory.py`** — FDD 관점 규제
- 기업결합 심사 (공정위) — EBITDA 영향
- 세무조사 이력 — 우발채무
- 산업별 인허가 — 사업 지속성 리스크

**4-C. `fdd/backend/app/industry/korea/kifrs.py`** — FDD 관점 K-IFRS
- 1115 수익인식 -> EBITDA 조정 영향
- 1116 리스 -> NWC/Net Debt 분류
- 1019 종업원급여 -> 퇴직급여충당부채
- 산업별 특화 (Tech: 1038 R&D, Manufacturing: 1036 손상)

**4-D. `fdd/backend/app/industry/korea/tax.py`** — 세무 검토
- 이전가격 세제 (Transfer Pricing)
- 비정상적 접대비/기부금 한도
- R&D 세액공제 영속성

**4-E. `fdd/backend/app/industry/korea/__init__.py`** — 집계 함수

```python
def get_fdd_korea_overlay_data(industry_id: str) -> FDDKoreaOverlayData | None:
    reg = [r for r in REGULATORY_ITEMS if industry_id in r.applicable_industries]
    kifrs = [k for k in KIFRS_NOTES if industry_id in k.applicable_industries]
    tax = [t for t in TAX_ITEMS if industry_id in t.applicable_industries]
    if not (reg or kifrs or tax):
        return None
    return FDDKoreaOverlayData(
        industry_id=industry_id, regulatory_items=reg,
        kifrs_notes=kifrs, tax_items=tax,
    )
```

**4-F. `fdd/backend/app/industry/base.py`** — `get_korea_overlay()` 메서드 추가
```python
def get_korea_overlay(self) -> FDDKoreaOverlayData | None:
    """한국 PE FDD 특수성 오버레이 데이터를 반환한다."""
    try:
        from app.industry.korea import get_fdd_korea_overlay_data
        return get_fdd_korea_overlay_data(self.industry_id)
    except ImportError:
        return None
```

**4-G. `fdd/backend/app/services/report/report_service.py`** — 한국 오버레이 보고서 섹션 추가

```python
korea_overlay = industry_module.get_korea_overlay()
if korea_overlay:
    # K-IFRS 조정 사항 섹션
    # 규제/세무 검토 사항 섹션
    # narrative_generator에도 전달
```

---

## Step 5: 산업별 LLM 라우팅 (이슈 5)

**목적**: 같은 섹션도 산업에 따라 다른 LLM으로 라우팅 가능

### 설계: 복합 키 패턴

`routing_map`에 `{industry}:{section_id}` 형식의 복합 키 지원:

```python
# 예시: healthcare 산업의 executive_summary만 다른 프로바이더 사용
{
    "healthcare:executive_summary": "openai",   # 복합 키 (산업별)
    "executive_summary": "anthropic",           # 기본 키 (전체 산업)
}
```

### 수정 파일

**5-A. `fdd/backend/app/services/llm/routing/model_router.py`**

`resolve()` + `generate()`에 `industry` 파라미터 추가:

```python
def resolve(self, section_id: str, *, industry: str = "") -> RoutingDecision:
    # 1차: 복합 키 (industry:section_id) 조회
    if industry:
        compound_key = f"{industry}:{section_id}"
        if compound_key in self._routing_map:
            primary = self._routing_map[compound_key]
            # ... 가용성 확인 후 반환

    # 2차: 기본 키 (section_id) 조회 -- 기존 로직
    primary = self._routing_map.get(section_id, "openai")
    # ... 기존 로직 동일

def generate(self, section_id: str, *, industry: str = "", ...):
    decision = self.resolve(section_id, industry=industry)
    # ... 나머지 동일
```

**5-B. `fdd/backend/app/services/report/narrative_generator.py`**

`FDDNarrativeGenerator.__init__`에 `industry_id` 추가, 각 generate 호출 시 전달:

```python
def __init__(self, router, industry_context="", industry_id=""):
    self._router = router
    self._industry_context = industry_context
    self._industry_id = industry_id

def generate_executive_summary(self, ...):
    response = self._router.generate(
        "executive_summary", industry=self._industry_id, ...
    )
```

**5-C. `im/src/narrative_generator/engine/model_router.py`** — 동일 복합 키 패턴 적용

`ModelRouter.resolve()` + `generate()`에 `industry` 파라미터 추가 (FDD와 동일 패턴)

**5-D. `im/src/narrative_generator/engine/orchestrator.py`**

`_call_llm()` -> `_generate_section()` -> `generate()` 체인에서 `industry` 전달

---

## 수정 파일 요약

| # | 파일 (모노레포 상대 경로) | Step | 변경 유형 |
|---|------|------|----------|
| 1 | `fdd/backend/app/services/llm/client.py` | 1 | 모델명 환경변수화 |
| 2 | `im/src/narrative_generator/config.py` | 1 | Anthropic 모델 버전 업데이트 |
| 3 | `fdd/backend/app/services/llm/routing/router_factory.py` | 2 | 환경변수 파싱 추가 |
| 4 | `fdd/backend/app/services/llm/routing/model_router.py` | 2, 5 | fallback_order + 복합 키 |
| 5 | `fdd/backend/app/industry/base.py` | 3, 4 | format_narrative_context + get_korea_overlay |
| 6 | `fdd/backend/app/industry/tech_saas.py` | 3 | get_narrative_templates 오버라이드 |
| 7 | `fdd/backend/app/industry/manufacturing.py` | 3 | get_narrative_templates 오버라이드 |
| 8 | `fdd/backend/app/industry/healthcare.py` | 3 | get_narrative_templates 오버라이드 |
| 9 | `fdd/backend/app/industry/financial_services.py` | 3 | get_narrative_templates 오버라이드 |
| 10 | `fdd/backend/app/industry/logistics.py` | 3 | get_narrative_templates 오버라이드 |
| 11 | `fdd/backend/app/services/report/narrative_generator.py` | 3, 5 | 산업 컨텍스트 + industry_id |
| 12 | `fdd/backend/app/services/report/report_service.py` | 3, 4 | 컨텍스트/오버레이 전달 |
| 13 | `fdd/backend/app/industry/korea/models.py` | 4 | **신규** |
| 14 | `fdd/backend/app/industry/korea/regulatory.py` | 4 | **신규** |
| 15 | `fdd/backend/app/industry/korea/kifrs.py` | 4 | **신규** |
| 16 | `fdd/backend/app/industry/korea/tax.py` | 4 | **신규** |
| 17 | `fdd/backend/app/industry/korea/__init__.py` | 4 | **신규** |
| 18 | `im/src/narrative_generator/engine/model_router.py` | 5 | 복합 키 라우팅 |
| 19 | `im/src/narrative_generator/engine/orchestrator.py` | 5 | industry 파라미터 전달 |

---

## 검증 방법

1. **Step 1 검증**: 환경변수 `ANTHROPIC_MODEL_NAME=test-model` 설정 후 `AnthropicClient()._model` 확인
2. **Step 2 검증**: `FDD_LLM_ROUTING_MAP='{"executive_summary":"openai"}'` 설정 후 `create_fdd_model_router().routing_summary` 확인
3. **Step 3 검증**: `FDDTechSaaSModule().format_narrative_context()` 호출 -> 비어있지 않은 문자열 반환 확인
4. **Step 4 검증**: `FDDTechSaaSModule().get_korea_overlay()` 호출 -> FDDKoreaOverlayData 반환 확인
5. **Step 5 검증**: `router.resolve("executive_summary", industry="healthcare")` -> 복합 키 매핑 확인
6. **통합 테스트**: `pytest` 실행 -> 기존 테스트 통과 확인 (하위 호환성)

---

## 구현 후 검증 결과 (2026-02-17 01:50)

### Step별 검증 결과

| Step | 결과 | 검증 내용 |
|------|------|----------|
| 1. 모델명 환경변수화 | ✅ 통과 | 3개 프로바이더 모두 `os.getenv()` + `DEFAULT_MODEL` 폴백 정상 |
| 2. 라우팅 환경변수 | ✅ 통과 | `FDD_LLM_ROUTING_MAP` JSON 파싱 + `FDD_LLM_FALLBACK_ORDER` 파싱 정상 |
| 3. 산업별 프롬프트 | ✅ 통과 | 5개 산업 `get_narrative_templates()` + 4개 generate 메서드에 `industry_context` 삽입 |
| 4. 한국 오버레이 | ✅ 통과 | 37개 데이터 항목 (규제13 + K-IFRS13 + 세무11), 보고서 섹션 + LLM 컨텍스트 전달 |
| 5. 복합 키 라우팅 | ✅ 통과 | FDD: 복합 키 unavailable 시 기본 키로 정상 폴백. IM: 동일 패턴 구현 확인 |

### 발견 및 수정된 버그

#### BUG-1 (HIGH): `report_service.py:313-316` — FDDKPIBenchmark 속성명 불일치

`FDDKPIBenchmark` 클래스에 존재하지 않는 속성을 참조하여 런타임 `AttributeError` 발생.

| 속성 (수정 전) | 실제 속성 (수정 후) |
|---------------|-------------------|
| `bm.range_low` | `bm.benchmark_range[0]` |
| `bm.range_high` | `bm.benchmark_range[1]` |
| `bm.kpi_name` | `bm.name_en` |
| `bm.description` | `bm.formula` |

**영향 범위**: `industry_id != "general"` && `kpi_benchmarks` 비어있지 않을 때 보고서 생성 크래시.

**수정 완료**: 2026-02-17 01:50

#### BUG-2 (LOW): `narrative_generator.py:16` — 중복 import 제거

```python
# 수정 전
from app.services.llm.routing import FDDModelRouter, FDDModelRouter as _
# 수정 후
from app.services.llm.routing import FDDModelRouter
```

**수정 완료**: 2026-02-17 01:50

### 잔여 확인 사항 (2026-02-17 01:59 전체 완료)

| # | 항목 | 상태 | 결과 |
|---|------|------|------|
| 1 | IM `model_router.py` 복합 키 폴백 | ✅ 정상 | 코드 직접 확인: 복합 키 unavailable 시 라인 127로 정상 폴백. 초기 서브에이전트 분석 오류 |
| 2 | `pytest` 통합 테스트 | ✅ 통과 | **137/137 관련 테스트 통과** (0.29s). 전체 1353건 중 1157 passed, 196 failed (API 인증 fixture 이슈, 변경과 무관) |
| 3 | `.env.example` 업데이트 | ✅ 완료 | `fdd/.env.example` 정상 확인. `im/.env.example` 모델 버전 불일치 수정 (`claude-sonnet-4-20250514` → `claude-sonnet-4-5-20250929`) |

#### pytest 상세 결과

| 테스트 파일 | 대상 Step | 결과 |
|------------|----------|------|
| `test_llm_client.py` | Step 1 (환경변수화) | ✅ 19/19 |
| `test_model_router.py` | Step 2+5 (라우팅+복합 키) | ✅ 13/13 |
| `test_industry_registry.py` | Step 3 (산업별 모듈) | ✅ 31/31 |
| `test_narrative_engine.py` | Step 3 (내러티브 생성) | ✅ 26/26 |
| `test_report_builder.py` | Step 4 (보고서 빌더) | ✅ 31/31 |
| `test_guardrails.py` | Step 3 (가드레일) | ✅ 17/17 |
| **합계** | | **137/137 (100%)** |

#### 추가 수정: `im/.env.example` 모델 버전 통일

```bash
# 수정 전
ANTHROPIC_MODEL_NAME=claude-sonnet-4-20250514
# 수정 후
ANTHROPIC_MODEL_NAME=claude-sonnet-4-5-20250929
```
