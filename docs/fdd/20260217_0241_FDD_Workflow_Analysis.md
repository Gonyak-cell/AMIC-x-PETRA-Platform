# FDD (Financial Due Diligence) 리포트 생성 워크플로우 분석

> 2026-02-17 02:34 | FDD 모듈 백엔드 파이프라인 + 프론트엔드 UI 구현 현황

---

## 1. 시스템 개요

FDD 모듈은 **재무실사 자동화 플랫폼**으로, 기업 인수합병 시 재무 건전성을 분석하고 최종 FDD 리포트(PPTX/DOCX/JSON)를 자동 생성합니다. IM과 달리 **단계별 사용자 주도(interactive) 워크플로우**로, 분석가가 각 단계를 직접 실행·검토·승인합니다.

**핵심 특징:**
- 멀티-LLM 라우팅: Anthropic(장문), OpenAI(정량), Gemini(효율) 자동 선택
- 산업별 8개 맞춤형 모듈 + 한국 규제/K-IFRS/세무 오버레이
- 순수 함수 기반 엔진: 계산은 rule-based, LLM은 텍스트 분석만
- Decimal 기반 정확성: 모든 금액 NUMERIC(18,4)

---

## 2. 전체 파이프라인 개요

```
[1] Deal 생성 & 설정
[2] 정의(Definition) 설정 & 승인
[3] 데이터 업로드 (Trial Balance)
[4] 계정과목 매핑 (Auto-Suggest → Approve)
[5] 분석 엔진 실행 (병렬 3개)
    ├─ QoE: Reported EBITDA → 조정항목 감지 → Adjusted EBITDA
    ├─ NWC: 계정 분류 → 정상범위 → Peg 시나리오
    └─ Net Debt: 부채 분류 → 현금 조정 → 순부채
[6] 이슈 관리 (이상 탐지 + 수동 추가)
[7] LLM 내러티브 생성 (선택사항)
[8] 보고서 IR 구축 → PPTX/DOCX/JSON 렌더링
[9] 버전 관리 & 최종 승인
```

---

## 3. Stage 1: Deal 생성 & 설정

**엔드포인트:** `POST /deals`

| 항목 | 설명 | 필수 |
|------|------|------|
| `name` | 딜 이름 | O |
| `deal_type` | COMPLETION_ACCOUNTS / LOCKED_BOX | O |
| `base_currency` | KRW (기본) | O |
| `industry` | GENERAL / TECH_SAAS / HEALTHCARE / MANUFACTURING / FINANCIAL_SERVICES / LOGISTICS | O |
| `reference_date` | 재무 기준일 | O |
| `period_start/end` | 분석 기간 | O |
| `client_name` | 고객사명 | X |
| `target_company_name` | 대상사명 | X |
| `scope_qoe/nwc/debt` | 분석 범위 플래그 | X |

**UI:** `DealListPage.tsx` (목록 + "New Deal" 모달), `DealSetupWizardPage.tsx` (마법사), `WorkflowOverviewPage.tsx` (5단계 시각화), `DealSetupPage.tsx` (상세 설정)

---

## 4. Stage 2: 정의(Definition) 설정

**엔드포인트:** `POST /deals/{deal_id}/definitions`

Cash/Debt/NWC Include/Exclude 패턴, Target NWC 계산 방법 (LTM Average, TTM, Last Month, Max, Min, Custom), IFRS 16 리스 부채 포함 여부.

**승인 워크플로우:** DRAFT → APPROVED → LOCKED

**UI:** `DefinitionPage.tsx` — DefinitionForm + DefinitionCard + TagInput

---

## 5. Stage 3: 데이터 업로드

**엔드포인트:** `POST /deals/{deal_id}/uploads`

```
파일 업로드 (.xlsx/.xls) → 타입 자동 감지 (TB, GL, AR, AP, BANK, DEBT, LEASE)
→ 검증 (Validation) → Ingest → Snapshot 생성
```

**파일 상태:** PENDING → DETECTING → VALIDATING → INGESTING → COMPLETED

**UI:** `UploadPage.tsx` — 드래그&드롭, KPI 카드, UploadCard, ValidationErrors

---

## 6. Stage 4: 계정과목 매핑

**엔드포인트:** `POST /deals/{deal_id}/mappings/suggest` → `POST /deals/{deal_id}/mappings`

```
"Auto-Suggest" → 자동 매핑 (Confidence: HIGH/MEDIUM/LOW)
→ "Save All as Proposed" → "Approve" (개별/전체)
→ Tie-out 검증 (TB Total = Reconstructed Total)
```

**UI:** `MappingPage.tsx` — SuggestionsTable, MappingsTable, TieOutSection

---

## 7. Stage 5: 분석 엔진 실행 (3개 독립 엔진)

### 5-1. QoE (Quality of Earnings) 엔진

**엔드포인트:** `POST /deals/{deal_id}/qoe/calculate`

```
Trial Balance → 카테고리별 합계 → Reported EBITDA 계산
→ 조정항목 자동 감지 (산업별 규칙):
    NON_RECURRING, NON_OPERATING, NORMALIZATION, OWNER_RELATED
→ CANDIDATE → PROPOSED → APPROVED / REJECTED
→ Bridge 재계산: Reported EBITDA + Adjustments = Adjusted EBITDA
```

**모든 금액:** `NUMERIC(18,4)` Decimal 기반

**UI:** `QoEPage.tsx` — EBITDASummaryCard, BridgeTable, AdjustmentCandidatesTable

### 5-2. NWC (Net Working Capital) 엔진

**엔드포인트:** `POST /deals/{deal_id}/nwc/calculate`

```
Balance Sheet 계정 분류 → NWC = Current Assets(포함) - Current Liabilities(포함)
→ NWC Days 계산 → 산업별 정상범위 비교
→ Peg 시나리오 6종: LTM Average, TTM, Last Month, Max, Min, Custom
```

**UI:** `NWCPage.tsx` — NWCSummaryCard, LineItemsTable, PegSimulationPanel, MonthlyTrendTable

### 5-3. Net Debt 엔진

**엔드포인트:** `POST /deals/{deal_id}/debt/calculate`

```
부채 분류 → Gross Debt + Debt-Like - Cash - Cash-Like = Net Debt
→ 수동 Item 추가 → Item별 Approve
```

**UI:** `NetDebtPage.tsx` — KPI 카드, BridgeTable, DebtItemsTable, AddItemForm

---

## 8. Stage 6: 이슈 관리

**엔드포인트:** `POST /deals/{deal_id}/issues/detect`

```
"Run Anomaly Detection" → 자동 이상 탐지
→ Severity: Critical/High/Medium/Low
→ Status: Open → Under Review → Resolved / False Positive
→ 댓글 스레드 (CommentThread)
```

**UI:** `IssuesPage.tsx` — KPI 카드, 필터, IssueRow (확장 가능), CommentThread

---

## 9. Stage 7: LLM 내러티브 생성 (선택사항)

**조건:** `use_llm_narratives=True`

### 멀티-LLM 라우팅

| 태스크 | 프로바이더 | 이유 |
|--------|-----------|------|
| executive_summary | **Anthropic** | 장문 일관성 |
| overall_assessment | **Anthropic** | 전략/정성 분석 |
| risk_narrative | **Anthropic** | 장문 위험 서술 |
| qoe_analysis_narrative | **OpenAI** | 수치 정확도 |
| nwc_analysis_narrative | **OpenAI** | 정량 분석 |
| debt_analysis_narrative | **OpenAI** | 정량 분석 |
| methodology_description | **Gemini** | 비용 효율 |
| scope_description | **Gemini** | 비용 효율 |

**폴백 체인:** primary 불가 시 자동 전환 (openai → anthropic → gemini)

**Guardrails:** `validate_narrative_claims()` — 수치 정합성 검증

**핵심 파일:**
- `fdd/backend/app/services/llm/routing/model_router.py`
- `fdd/backend/app/services/report/narrative_generator.py`

---

## 10. Stage 8: 보고서 IR 구축 & 렌더링

**엔드포인트:** `POST /deals/{deal_id}/reports/generate`

### Report IR 구조

```
ReportIR
├── CoverBlock (표지)
├── ScopeBlock (범위, 정의)
├── KPIBlock (Executive Summary: EBITDA, NWC, Net Debt)
├── TextBlock (Industry KPI Benchmarks)
├── TableBlock (QoE Bridge)
├── TableBlock (QoE Adjustments Detail)
├── TableBlock (NWC Definition)
├── TableBlock (NWC Peg Scenarios)
├── TableBlock (Net Debt Schedule)
├── TableBlock (Entity Structure — 멀티엔티티)
├── TableBlock (Exchange Rates — 멀티엔티티)
├── TextBlock (Korea Regulatory & Accounting Overlay)
│   ├── K-IFRS 조정 사항
│   ├── 규제 검토 (공정거래법 등)
│   └── 세무 검토 (이전가격세제 등)
├── IssueBlock (Issue Log)
├── TableBlock (Issue Summary — Top 10)
├── TextBlock (LLM Executive Summary — 선택 시)
└── MethodologyBlock (방법론 & 한계)
```

### 출력 형식 3종

| 형식 | 렌더러 | 특징 |
|------|--------|------|
| JSON | `report_ir_to_dict()` | IR 구조 그대로 |
| PPTX | `pptx-service` (Node.js, port 3100) | IR JSON → PowerPoint XML |
| DOCX | `word_renderer` (python-docx) | IR → Word 테이블/텍스트 |

**UI:** `ReportPage.tsx` — 섹션 선택, 형식 선택, Preview, Generate, ReportVersionList

---

## 11. Stage 9: 버전 관리

```
v1 (DRAFT) → [검토] → v2 (DRAFT) → [최종 승인] → v2 (FINAL)
```

**UI:** ReportPage 내 ReportVersionList 컴포넌트

---

## 12. 산업별 맞춤형 로직

### 산업 모듈 구조 (`FDDIndustryModule`)

```python
class FDDIndustryModule(ABC):
    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:      # EBITDA 조정 규칙
    def get_nwc_norms(self) -> list[FDDNWCNorm]:                    # NWC 정상범위
    def get_debt_classifications(self) -> list[FDDDebtClassification]: # 부채 분류
    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:          # 산업 벤치마크
    def get_narrative_templates(self) -> list[FDDNarrativeTemplate]: # LLM 프롬프트
    def get_korea_overlay(self) -> FDDKoreaOverlayData | None:      # 한국 오버레이
```

### 산업별 차이점

| 산업 | QoE 조정규칙 | NWC 정상범위 | Debt 특수처리 | KPI 벤치마크 |
|------|-------------|-------------|-------------|-------------|
| **Tech/SaaS** | R&D 자본화, SBC, CAC | -30~+15일 (음의 NWC 정상) | 전환사채, SAFE | ARR 성장률, NRR, Rule of 40, LTV/CAC |
| **Healthcare** | 임상시험비, 라이선스 | 30~60일 | 마일스톤 부채 | 파이프라인 가치, R&D 비율 |
| **Manufacturing** | 설비투자, 재고평가 | 45~90일 | 리스(IFRS 16) | 설비가동률, 재고회전율 |
| **Logistics** | 차량감가, 유류비 | 15~45일 | 차량리스 | 배송효율, 차량가동률 |
| **Financial Services** | 대손충당금, 수수료 | 특수 (규제자본) | 후순위채, 규제자본 | CAR, NIM, NPL |

### 한국 오버레이 (Korea Overlay)

| 범주 | 내용 |
|------|------|
| **K-IFRS** | 수익인식(1115), 리스(1116), 금융상품(1109) 등 |
| **규제** | 공정거래법 M&A 신고, 산업별 규제 |
| **세무** | 이전가격세제, 세무조사 이력, 합병 세무 |

**핵심 파일:**
- `fdd/backend/app/industry/base.py`
- `fdd/backend/app/industry/tech_saas.py` (외 7개)
- `fdd/backend/app/industry/korea/`

---

## 13. UI 페이지 구현 현황

| 워크플로우 단계 | UI 페이지 | 구현 상태 |
|---------------|----------|----------|
| 거래 목록 | `DealListPage.tsx` | ✅ 완전 구현 |
| 신규 거래 마법사 | `DealSetupWizardPage.tsx` | ✅ 완전 구현 |
| 워크플로우 개요 | `WorkflowOverviewPage.tsx` | ✅ 완전 구현 |
| 거래 설정 | `DealSetupPage.tsx` | ✅ 완전 구현 |
| 가상 데이터룸 | `VdrPage.tsx` | ⚠️ 부분 구현 (파일 목록 미완) |
| 정의 설정 | `DefinitionPage.tsx` | ✅ 완전 구현 |
| 데이터 업로드 | `UploadPage.tsx` | ✅ 완전 구현 |
| 계정과목 매핑 | `MappingPage.tsx` | ✅ 완전 구현 |
| QoE 분석 | `QoEPage.tsx` | ✅ 완전 구현 |
| NWC 분석 | `NWCPage.tsx` | ✅ 완전 구현 |
| Net Debt 분석 | `NetDebtPage.tsx` | ✅ 완전 구현 |
| 이슈 관리 | `IssuesPage.tsx` | ✅ 완전 구현 |
| 보고서 생성 | `ReportPage.tsx` | ✅ 완전 구현 |

**13/14 페이지 완전 구현** — VdrPage만 부분 구현 (폴더 트리 O, 파일 목록 X)

---

## 14. IM vs FDD 아키텍처 비교

| 항목 | IM | FDD |
|------|----|----|
| 워크플로우 방식 | 비동기 Celery 파이프라인 (자동) | 단계별 사용자 주도 (대화형) |
| 데이터 소스 | DART API + 웹 크롤링 (자동 수집) | 사용자가 직접 Excel 업로드 |
| LLM 역할 | **핵심** — 14개 섹션 내러티브 전체 생성 | **보조** — 선택사항, 코멘터리만 |
| 계산 엔진 | 재무지표 산출 (파생지표) | 3개 독립 엔진 (QoE/NWC/Debt) |
| 승인 워크플로우 | 없음 (자동 생성) | 다단계 (CANDIDATE → PROPOSED → APPROVED) |
| 출력 형식 | PPTX + PDF | PPTX + DOCX + JSON |
| 산업 맞춤 | 프롬프트 컨텍스트 수준 | 분석 규칙 전체 커스터마이즈 |
| 진행 추적 | 폴링 (3초 간격) | 페이지별 직접 확인 |
