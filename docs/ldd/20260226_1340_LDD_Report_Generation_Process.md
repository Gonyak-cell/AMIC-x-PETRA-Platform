# LDD 보고서 작성 로직 — 상세 프로세스 설명

> 현재 Azure 배포 버전 (feat/ma-workflow 브랜치) 기준
> 작성일: 2026-02-26 13:40

---

## 1. 전체 아키텍처 개요

LDD(법률실사) 보고서 생성은 **deal-mgmt** 백엔드 서비스에서 처리된다.
크게 **3가지 생성 모드**와 **Ralph Loop 2회 적용 워크플로우**로 구성된다.

### 3가지 생성 모드

| 모드 | API 엔드포인트 | 설명 |
|------|--------------|------|
| **수동 작성** | `POST /transactions/{txn_id}/ldd-reports` | 사용자가 체크리스트 직접 기입 → 즉시 DOCX 렌더링 |
| **AI 자동 (폴더 경로)** | `POST /transactions/{txn_id}/ldd-reports/auto` | 서버 로컬 폴더의 실사자료를 파싱 → Ralph Loop → DOCX |
| **VDR 기반 AI (★ 메인 워크플로우)** | `POST /transactions/{txn_id}/ldd-reports/from-vdr` | VDR에 업로드된 문서를 소스로 → Ralph Loop #1 (초안) → 사용자 리뷰 → Ralph Loop #2 (최종) → DOCX |

### 보고서 유형

| 유형 | 설명 |
|------|------|
| **FULL** (정식 LDD) | 10개 섹션 × 52개 항목 전체 분석, Executive Summary + 본문 + 별첨 |
| **REDFLAG** (Redflag DD) | Executive Summary + Critical/High 이슈만 추출 |

---

## 2. DDRL 체크리스트 구조 (10개 섹션, 52개 항목)

기본 템플릿 `DEFAULT_LDD_SECTIONS` — 한국 대형 로펌(김앤장, 세종, 태평양, 광장)급 기재례 표준:

| # | 섹션 (section_type) | 제목 | 항목 예시 |
|---|-------------------|------|---------|
| 1 | GOVERNANCE | 기업 일반 및 지배구조 | CORP-01~06: 설립/등기/정관, 이사회, 주주명부, 임원, 자기거래, 자회사 |
| 2 | CAPITAL | 자본 및 주식 | CAP-01~05: 주식발행, 전환사채, 스톡옵션, 배당이력, 증자이력 |
| 3 | CONTRACTS | 계약 관계 | CONTRACT-01~06: 주요계약, CoC 조항, 보증/담보, 공급계약, 리스, 금융계약 |
| 4 | LITIGATION | 소송 및 분쟁 | LIT-01~05: 계류소송, 잠재분쟁, 규제조사, 중재, 전과이력 |
| 5 | LABOR | 노동/인사 | LABOR-01~06: 근로계약, 단체협약, 퇴직금, 산재, 핵심인력, 파견/도급 |
| 6 | IP | 지식재산권 | IP-01~05: 특허, 상표, 영업비밀, 라이선스, 오픈소스 |
| 7 | REAL_ESTATE | 부동산 | RE-01~04: 등기, 임대차, 환경오염, 공장등록 |
| 8 | PERMITS | 인허가/규제 | PERMIT-01~05: 사업허가, 환경규제, 산업안전, 개인정보, 공정거래 |
| 9 | TAX | 세무 | TAX-01~05: 법인세, 부가세, 이전가격, 세무조사, 조세특례 |
| 10 | DATA_IT | 데이터/IT | IT-01~05: IT인프라, 정보보안, 개인정보처리, 클라우드, 라이선스 |

### 거래유형별 특화 템플릿

`deal_type` 파라미터로 거래유형을 지정하면, `TemplateRegistry`에서 특화 템플릿을 로드한다:

- `STOCK_ACQUISITION` — 주식양수도
- `REAL_ESTATE` — 부동산 거래
- `IPO` — 기업공개
- `CORPORATE_SPLIT` — 분할
- `PREFERRED_STOCK` — 우선주 투자
- `ASSET_ACQUISITION` — 사업양수도

지정하지 않으면 기본 10개 섹션 사용.

### 각 항목의 데이터 구조

```python
{
    "item_id": "CORP-01",           # 고유 식별자
    "name": "설립/등기/정관 검토",    # 항목명
    "status": "OK|ISSUE|NA|PENDING", # 상태
    "issue_level": "CRITICAL|HIGH|MEDIUM|LOW|null",  # 이슈 레벨
    "risk_color": "RED|AMBER|GREEN", # 신호등 색상 (자동 계산)
    "description": "사실관계 서술",   # 발견사항
    "deal_impact": "거래 영향",       # 가격/구조/일정 영향
    "recommendation": "권고사항",     # 구체적 행동 권고
    "rfi_required": true/false,      # 추가 자료 요청 여부
    "rfi_number": "CORP-001",        # RFI 번호
    "confidence": 0.85,              # AI 신뢰도 (0.0~1.0)
    "evidence_refs": ["파일명1"],     # 근거 문서 목록
    "user_comment": "",              # 리뷰어 코멘트
    "user_approved": null,           # 승인/반려/미검토
    "user_override_status": null,    # 사용자 직접 변경한 status
    "user_override_level": null,     # 사용자 직접 변경한 issue_level
}
```

---

## 3. VDR 기반 LDD 메인 워크플로우 (전체 흐름)

```
[사용자] 프론트엔드에서 "VDR 기반 LDD 생성" 클릭
   │
   ▼
POST /transactions/{txn_id}/ldd-reports/from-vdr
   │  body: { title, report_type, deal_type, industry, is_cross_border,
   │          folder_ids, draft_max_iterations, max_cost_usd, use_multi_llm }
   │
   ▼
┌─── Ralph Loop #1: 초안 생성 (ANALYZING) ───────────────────┐
│                                                              │
│  1. LDDReport 레코드 생성 (status=ANALYZING)                 │
│  2. VDR 문서 텍스트 추출 (TextExtractionService)             │
│  3. 섹션별 소스 매핑 (build_source_map)                      │
│  4. [분기] 멀티 LLM 파이프라인 or 단일 LLM Ralph Loop        │
│  5. AI 분석 결과 → sections JSONB 병합                       │
│  6. evidence_refs → VDR 참조 링크 생성                       │
│  7. status → REVIEW                                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌─── 사용자 리뷰 단계 (REVIEW) ──────────────────────────────┐
│                                                              │
│  GET  /{report_id}/review-progress   → 진행률 조회           │
│  PUT  /{report_id}/items/{id}/review → 개별 승인/반려/코멘트 │
│  PUT  /{report_id}/items/bulk-review → 일괄 리뷰             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
POST /{report_id}/finalize
   │  body: { max_iterations, max_cost_usd }
   │
   ▼
┌─── Ralph Loop #2: 최종 Refine (FINALIZING) ────────────────┐
│                                                              │
│  1. 사용자 피드백 수집 (approved_items, user_feedback)        │
│  2. VDR 소스 재로딩                                          │
│  3. LDDFinalizeGenerator (승인 항목 스킵, 반려 항목만 재분석) │
│  4. 품질 게이트 + Ralph Loop 실행                            │
│  5. 결과 병합 (approved=원본 유지, rejected=재분석 반영)      │
│  6. DOCX 렌더링 (docxtpl)                                    │
│  7. status → READY                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
GET /{report_id}/download → .docx 파일 다운로드
```

---

## 4. 단계별 상세 프로세스

### 4-1. VDR 문서 텍스트 추출 (Step 2)

**파일**: `app/services/text_extraction_service.py`

1. VDR DB에서 `transaction_id`에 속한 문서 목록 조회
2. `folder_ids`가 지정되면 해당 폴더만 필터링
3. 각 문서의 실제 파일을 파싱:
   - **PDF** → `pdf_parser.py` (pdfplumber)
   - **DOCX** → `docx_parser.py` (python-docx)
   - **HWPX** → `hwp_parser.py` (XML 파싱)
   - **XLS/XLSX** → `excel_parser.py` (openpyxl)
4. 파싱 결과: `ParsedFile(source_path, text, tables, is_valid, ddrl_sections)`
5. `build_source_map()`: 파싱된 파일을 DDRL 섹션 유형별로 분류
   - `file_classifier.py`가 문서 내용/키워드로 관련 섹션을 추론

### 4-2. 멀티 LLM 10단계 파이프라인 (Step 4 — 멀티 LLM 모드)

**파일**: `app/ralph/generators/ldd/pipeline.py` → `LDDMultiLLMPipeline`

`use_multi_llm=True`이고 LLM 클라이언트가 사용 가능하면 이 경로로 진입.

#### Stage 1+2: 문서 분류 + 조항 추출 (단일 LLM)

**파일**: `app/ralph/generators/ldd/section_analyzer.py` → `LDDSectionAnalyzer`

- 10개 섹션 × N개 항목(총 52개)을 순회하며 **항목당 1회 LLM 호출**
- 각 항목에 대해:
  1. 관련 소스 파일(source_files)을 `format_source_materials()`로 텍스트 변환 (파일당 최대 2,000자, 전체 최대 15,000자)
  2. `SYSTEM_PROMPT` (한국 M&A LDD 전문가 역할) + `ITEM_ANALYSIS_PROMPT` (항목별 분석 지시)를 LLM에 전달
  3. LLM이 JSON으로 응답: `{status, issue_level, risk_color, description, deal_impact, recommendation, rfi_required, rfi_number, confidence, evidence_refs}`
  4. `extract_json()`으로 JSON 추출 (파싱 실패 시 fallback 딕셔너리 반환)
- LLM 라우팅: `LDDModelRouter`가 `section_type`에 따라 프로바이더 결정
  - 법률 분석: Anthropic (Claude Sonnet 4)
  - 리스크 분석: OpenAI (GPT-4o)
  - 사실 추출: Google (Gemini 2.0 Flash)

#### Stage 3: 듀얼 리스크 분석 (멀티 LLM, opt-in)

**파일**: `app/ralph/generators/ldd/dual_risk_analyzer.py` → `DualRiskAnalyzer`

- **조건**: `stage3_risk_dual=True` (기본값 True) + 비용 한도 미초과
- `status=ISSUE`인 항목만 대상
- 2개 LLM을 **병렬 호출** (`call_parallel`):
  - LLM A (Anthropic): **매수인 관점** — 인수가 보호 중심 분석
  - LLM B (OpenAI): **독립 평가** — 중립적 시각 분석
- 비교 로직:
  - 리스크 등급을 수치화: CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1
  - `gap = |level_A - level_B|`
  - `gap ≤ 1` (설정값 `risk_gap_auto_resolve`): 자동 해결 — 높은 쪽 채택 + 양측 근거 병기
  - `gap ≥ 2` (설정값 `risk_gap_human_review`): `needs_human_review=True` — 변호사 필수 검토

#### Stage 4: 누락 탐지 (멀티 LLM, opt-in)

**파일**: `app/ralph/generators/ldd/gap_detector.py` → `GapDetector`

- **조건**: `stage4_gap_detection=True` (기본값 True) + 비용 한도 미초과
- 2개 LLM **병렬 호출**:
  - LLM A (Anthropic): **DDRL 체크리스트 기반** — 52개 항목 대비 누락 식별
  - LLM B (OpenAI): **자유 탐색** — 체크리스트 외 추가 이슈 발굴
- 병합 로직:
  - Jaccard similarity > `gap_similarity_threshold` (기본 0.6) → 중복 제거
  - 결과: `merged_gaps[]` (gap_id, section_type, description, priority, rationale, source)

#### Stage 5: 관할권 교차 분석 (크로스보더 시만)

**파일**: `app/ralph/generators/ldd/jurisdiction_analyzer.py` → `JurisdictionAnalyzer`

- **조건**: `stage5_jurisdiction=True` + `is_cross_border=True` + 비용 한도 미초과
- ISSUE 항목의 조항 요약을 생성한 후 LLM 분석
- 결과: `cross_points[]` (한국법-외국법 교차점), `conflict_points[]` (충돌점)

#### Stage 6: 6블록 서술 생성 (opt-in, 기본 OFF)

**파일**: `app/ralph/generators/ldd/narrative_generator.py` → `NarrativeGenerator`

- **조건**: `stage6_narrative=True` (기본값 **False** — 비용 ~$2-4 추가) + 비용 한도 미초과
- ISSUE 항목에 대해 **6블록 체인 방식**으로 순차 생성:

| 블록 | 제목 | 설명 | 선행 입력 |
|------|------|------|---------|
| FACTS | 사실관계 | 관련 사실을 시간순 정리 | 소스 자료 |
| LEGAL_REVIEW | 법률 검토 | 관련 법률/판례 분석 | FACTS + 법률 컨텍스트 |
| ANALYSIS | 분석 | 법적 리스크 종합 분석 | FACTS + LEGAL_REVIEW |
| DEAL_IMPACT | 거래 영향 | 가격/구조/일정 영향 | FACTS + LEGAL_REVIEW + ANALYSIS |
| PENALTY | 불이익 검토 | 위반 시 제재/벌칙 | FACTS + LEGAL_REVIEW + ANALYSIS + DEAL_IMPACT |
| RECOMMENDATION | 권고 | 구체적 행동 방안 | 위 모든 블록 |

- 체인 구조: 이전 블록의 출력이 다음 블록의 입력에 포함됨
- `CitationPromptInjector`: 섹션별 관련 한국 법률/판례 컨텍스트를 프롬프트에 주입
- 블록 수 결정: `get_blocks_for_item(status, issue_level)` — status/level에 따라 1~6개

#### Stage 7: 법률 인용 검증 (규칙 기반)

**파일**: `app/ralph/generators/ldd/citation_verifier.py` → `CitationVerifier`

- **조건**: Stage 6의 narrative_sections가 존재할 때
- LLM 호출 **없음** — 규칙 기반 검증
- 서술에 포함된 법률 인용(조문 번호, 판례 번호)을 `korean_statutes.py`, `korean_precedents.py` DB와 대조
- 유효하지 않은 인용에 경고 태그 추가

#### Stage 8: 별첨 데이터 수집 (규칙 기반)

**파일**: `app/ralph/generators/ldd/appendix_generator.py` → `AppendixGenerator`

- LLM 호출 **없음** — 체크리스트 분석 결과에서 데이터 추출
- 6종 테이블 자동 생성:

| 테이블 유형 | 소스 섹션 |
|------------|---------|
| LITIGATION_SUMMARY | LITIGATION 이슈 항목 |
| IP_ASSETS | IP 항목 |
| REAL_ESTATE | REAL_ESTATE 항목 |
| CONTRACTS_SUMMARY | CONTRACTS 이슈 항목 |
| INSURANCE | CONTRACTS 내 보험 관련 |
| PERMITS_LICENSES | PERMITS 항목 |

#### Guardrails 검증 (동기)

**파일**: `app/ralph/generators/ldd/guardrails.py` → `LDDGuardrails`

- 데이터 완전성, 일관성 규칙 검증
- 에러/경고 카운트 및 이슈 목록 반환

#### Stage 9: Executive Summary 생성 (단일 LLM)

- `LDDSectionAnalyzer.generate_executive_summary(section_results)`
- 10개 섹션 분석 결과를 요약하여 Executive Summary 마크다운 생성
- 내용: 거래 개요, 핵심 이슈(Top 5), Red Flag, 조건선행 요건, 전체 의견

#### Stage 10: 최종 QA (멀티 LLM, opt-in)

**파일**: `app/ralph/generators/ldd/report_qa.py` → `LDDReportQA`

- **조건**: `stage7_qa=True` (기본값 True) + 비용 한도 미초과
- 전체 보고서에 대한 독립적 팩트체킹
- 결과: `overall_score` (0.0-5.0), `issues[]`, `passed_checks`, `summary`

#### 서술 품질 게이트 (선택)

**파일**: `app/ralph/gates/narrative_gate.py` → `NarrativeQualityGate`

- narrative_sections가 있을 때만 실행
- LLM 없이 밀리초 단위 동작
- 서술 품질 점수 (passed_items / total_items, overall_score)

### 4-3. 단일 LLM Ralph Loop 워크플로우 (Step 4 — 대안 경로)

`use_multi_llm=False`이거나 서버 설정 `LDD_MULTI_LLM_ENABLED=False`일 때:

1. `LDDDocumentGenerator`를 `RalphLoopOrchestrator`에 연결
2. Ralph Loop 반복 구조:
   - `generate_outline()` → 10개 섹션 구조
   - 섹션별 `generate_section()` → 항목 분석 (Claude Sonnet 4)
   - 품질 게이트: `DOCXProgrammaticGate` + `LLMJudgeGate` (GPT-4o)
   - 게이트 통과 실패 시 → 피드백 반영하여 재분석 (최대 N회 반복)
   - `assemble_document()` → 전체 조립 + Executive Summary + 교차 검증
3. 결과를 `_merge_ai_results()`로 섹션 데이터에 병합

### 4-4. 결과 저장 (Step 5-7)

1. AI 분석 결과를 `_merge_ai_results()`로 기본 섹션에 병합
   - 각 항목의 status, issue_level, description, deal_impact, recommendation 등 업데이트
2. `_compute_risk_colors()`: issue_level → risk_color 자동 계산
   - CRITICAL → RED, HIGH/MEDIUM → AMBER, LOW → GREEN
3. `_compute_counts()`: 집계 (total_items, issue_count, red/amber/green/ok/na/pending/rfi 카운트)
4. `_insert_vdr_references()`: evidence_refs에 포함된 파일명을 VDR 문서 UUID와 매칭하여 `LddVdrReference` 테이블에 저장
5. 멀티 LLM 결과 저장 (JSONB 컬럼):
   - `dual_risk_summary`, `gap_detection`, `jurisdiction_analysis`
   - `narrative_sections`, `legal_citations`, `appendices`
   - `qa_result`, `pipeline_stages`
6. `status → REVIEW`, `analysis_completed_at` 기록

---

## 5. 사용자 리뷰 단계

**파일**: `app/services/ldd_review_service.py` → `LDDReviewService`

### 리뷰 진행률 조회

```
GET /transactions/{txn_id}/ldd-reports/{report_id}/review-progress
→ { total: 52, approved: 30, rejected: 5, pending: 17, progress_pct: 67.3 }
```

### 개별 항목 리뷰

```
PUT /transactions/{txn_id}/ldd-reports/{report_id}/items/CORP-01/review
body: {
    "item_id": "CORP-01",
    "user_approved": true,            // 또는 false (반려)
    "user_comment": "정관 제15조 확인 필요",
    "user_override_status": "ISSUE",  // 사용자가 status 직접 변경
    "user_override_level": "HIGH"     // 사용자가 level 직접 변경
}
```

### 일괄 리뷰

```
PUT /transactions/{txn_id}/ldd-reports/{report_id}/items/bulk-review
body: { "items": [ { item_id, user_approved, ... }, ... ] }
```

---

## 6. Ralph Loop #2: 최종 Refine (Finalize)

**파일**: `app/services/ldd_report_service.py` → `finalize_ldd_report()`

### 전제조건

- 보고서 status가 `REVIEW`일 때만 호출 가능

### 프로세스

1. **사용자 피드백 수집**
   - `user_approved=True` 항목 → `approved_items` 집합
   - `user_approved=False` 항목 → `user_feedback` 딕셔너리 (코멘트, override 정보 포함)

2. **VDR 소스 재로딩** (VDR 기반인 경우)
   - TextExtractionService로 원본 문서 다시 추출

3. **LDDFinalizeGenerator 생성**
   - `approved_items`에 포함된 항목은 **스킵** (기존 분석 유지)
   - `user_feedback`이 있는 항목만 **재분석** (피드백 내용을 LLM 프롬프트에 주입)

4. **Ralph Loop #2 실행**
   - 동일한 품질 게이트 적용 (DOCXProgrammaticGate + LLMJudgeGate)
   - 예산: `max_cost_usd`의 40% (초안에 60% 배정)

5. **결과 병합**
   - 승인 항목: 원본 유지 (AI 결과 무시, user_override만 적용)
   - 반려/수정 항목: 재분석 결과로 업데이트

6. **DOCX 렌더링**
   - `generate_ldd_report()` → docxtpl 기반 렌더링

7. **상태 업데이트**
   - `status → READY`
   - `finalize_completed_at`, `final_ralph_session_id`, `final_score` 기록

---

## 7. DOCX 렌더링

**파일**: `app/services/ldd_report_service.py` → `generate_ldd_report()`

### 템플릿 선택

| narrative 유무 | report_type | 템플릿 파일 |
|---------------|-------------|-----------|
| 없음 | FULL | `ldd_full_template.docx` |
| 없음 | REDFLAG | `ldd_redflag_template.docx` |
| 있음 | FULL | `ldd_narrative_full_template.docx` |
| 있음 | REDFLAG | `ldd_narrative_redflag_template.docx` |

### 컨텍스트 빌드 (`_build_context()`)

docxtpl에 전달되는 변수:

```python
{
    "title": "보고서 제목",
    "target_company": "대상회사명",
    "dd_period": "2025.01.01 ~ 2025.03.31",
    "law_firm": "법무법인 세종",
    "prepared_by": "홍길동 변호사",
    "report_date": "2026년 02월 26일",
    "total_items": 52,
    "issue_count": 12,
    "red_count": 3,        # CRITICAL
    "amber_count": 5,      # HIGH + MEDIUM
    "green_count": 4,      # LOW
    "ok_count": 30,
    "na_count": 5,
    "pending_count": 5,
    "rfi_count": 8,
    "sections": [...],           # 10개 섹션 전체 데이터
    "all_issues": [...],         # ISSUE 항목만 추출
    "red_issues": [...],         # CRITICAL 항목만 추출
    "sections_with_issues": [...],  # 이슈 있는 섹션만
    "vdr_source": true,
    "draft_score": 3.8,
    "final_score": 4.2,
    "narrative_items": [...],    # (narrative 있을 때) 6블록 서술 데이터
    "appendix_tables": [...],    # (appendix 있을 때) 6종 별첨 테이블
}
```

### 렌더링 프로세스

1. `status → GENERATING`으로 변경 + DB 커밋
2. `asyncio.to_thread()`로 별도 스레드에서 동기 렌더링:
   - `DocxTemplate(template_path)` 로드
   - `tpl.render(context)` 실행
   - `tpl.save(output_path)` 저장
3. 파일 정보 기록: `file_name`, `file_path`, `file_size_bytes`
4. `status → READY` 또는 `FAILED` (예외 발생 시)

---

## 8. LLM 클라이언트 아키텍처

**파일**: `app/ralph/llm_client.py` → `RalphLLMClient`

### 프로바이더 폴백 체인

```
Anthropic (Claude Sonnet 4) → OpenAI (GPT-4o) → Google (Gemini 2.5 Flash)
```

- 각 프로바이더에 API 키가 없거나 호출 실패 시 다음으로 폴백
- `call()`: 기본 호출 (폴백 체인 순서)
- `call_for_provider()`: 특정 프로바이더 지정 (Stage 3/4 라우터용)
- `call_parallel()`: 여러 프로바이더 병렬 호출 (듀얼 분석용)
- `call_with_model()`: 특정 모델 지정 (Judge Panel용)

### 비용 추적

```python
COST_PER_1K = {
    "claude-sonnet-4-20250514":  {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
    "gpt-4o":                    {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini":               {"input": 0.00015, "output": 0.0006},
    "gemini-2.0-flash":          {"input": 0.0001, "output": 0.0004},
}
```

- `CostTracker`: 호출마다 비용 누적 (USD)
- 파이프라인에서 `_is_cost_exceeded()`: 누적 비용이 `max_cost_usd` 초과 시 이후 Stage 스킵

### Stage별 모델 라우팅

**파일**: `app/ralph/routing/ldd_router.py` → `LDDModelRouter`

| 용도 | 프로바이더 | 이유 |
|------|----------|------|
| 법률 분석 (Stage 1+2) | Anthropic | 법률 이해도 우수 |
| 리스크 분석 - 매수인 (Stage 3) | Anthropic | 보수적 관점 |
| 리스크 분석 - 독립 (Stage 3) | OpenAI | 다양한 시각 |
| 누락 탐지 - 체크리스트 (Stage 4) | Anthropic | 체계적 분석 |
| 누락 탐지 - 자유 탐색 (Stage 4) | OpenAI | 창의적 탐색 |
| 서술 생성 (Stage 6) | Anthropic | 톤 일관성 |
| 최종 QA (Stage 10) | Google | 독립 검증 |

---

## 9. 학습 패턴 시스템

- `PatternAggregator.get_learned_patterns("LDD")`: 과거 세션의 학습 패턴 조회
- `LearningPromptInjector.enrich_system_prompt()`: 학습 패턴을 시스템 프롬프트에 주입
- 효과: 이전 세션에서 발견된 패턴/실수를 다음 분석에 반영

---

## 10. 보고서 상태 흐름

```
DRAFT → ANALYZING → REVIEW → FINALIZING → GENERATING → READY
                                                    └→ FAILED
```

| 상태 | 의미 |
|------|------|
| DRAFT | 초기 생성, 섹션 데이터만 존재 |
| ANALYZING | Ralph Loop #1 실행 중 |
| REVIEW | 초안 완성, 사용자 리뷰 대기 |
| FINALIZING | Ralph Loop #2 실행 중 |
| GENERATING | DOCX 렌더링 중 |
| READY | 최종 보고서 다운로드 가능 |
| FAILED | 에러 발생 (error_message 참조) |

---

## 11. 프론트엔드 연동

### 진입점

1. **MA 거래 워크스페이스**: `/ma/transactions/{txn_id}?tab=ldd` → LDDReportsTab
2. **Docs Studio**: `/docs/dd/ldd` → DDReportListPage

### 폴링

- 프론트엔드 훅 `useLDDReports()`는 status가 `ANALYZING|FINALIZING|GENERATING`일 때 **5초 간격 자동 폴링**

### 다운로드

- `getLDDReportDownloadUrl()` → `GET /api/ma/transactions/{txn_id}/ldd-reports/{report_id}/download`
- Path Traversal 방어: `file_path`가 `generated/ldd/` 디렉터리 내에 있는지 검증

---

## 12. 파이프라인 설정 기본값 (현재 배포)

```python
# deal-mgmt/app/core/config.py
LDD_MULTI_LLM_ENABLED = False     # 멀티 LLM 기본 OFF
LDD_STAGE3_DUAL_RISK = True       # 듀얼 리스크 분석 ON
LDD_STAGE4_GAP_DETECTION = True   # 누락 탐지 ON
LDD_STAGE5_JURISDICTION = False   # 관할권 분석 OFF (크로스보더만)
LDD_STAGE6_NARRATIVE = False      # 6블록 서술 OFF (비용 절약)
LDD_STAGE7_QA = True              # 최종 QA ON
LDD_RISK_GAP_AUTO_RESOLVE = 1     # gap≤1 자동 해결
LDD_MAX_COST_USD = 15.0           # 세션당 최대 $15
```

> 현재 기본 설정으로는 **단일 LLM Ralph Loop** 모드로 동작.
> `use_multi_llm=True`를 요청 body에 명시하거나 서버 설정을 변경하면 멀티 LLM 파이프라인 활성화.

---

## 13. 핵심 파일 경로 요약

| 카테고리 | 파일 |
|---------|------|
| **라우터** | `deal-mgmt/app/routers/ldd_reports.py` |
| **서비스** | `deal-mgmt/app/services/ldd_report_service.py` |
| **리뷰 서비스** | `deal-mgmt/app/services/ldd_review_service.py` |
| **스키마** | `deal-mgmt/app/schemas/ldd_report.py` |
| **DB 모델** | `deal-mgmt/app/models/ldd_report.py` |
| **파이프라인 오케스트레이터** | `deal-mgmt/app/ralph/generators/ldd/pipeline.py` |
| **파이프라인 설정** | `deal-mgmt/app/ralph/generators/ldd/pipeline_config.py` |
| **섹션 분석기** | `deal-mgmt/app/ralph/generators/ldd/section_analyzer.py` |
| **듀얼 리스크** | `deal-mgmt/app/ralph/generators/ldd/dual_risk_analyzer.py` |
| **누락 탐지** | `deal-mgmt/app/ralph/generators/ldd/gap_detector.py` |
| **관할권 분석** | `deal-mgmt/app/ralph/generators/ldd/jurisdiction_analyzer.py` |
| **서술 생성** | `deal-mgmt/app/ralph/generators/ldd/narrative_generator.py` |
| **법률 인용 검증** | `deal-mgmt/app/ralph/generators/ldd/citation_verifier.py` |
| **별첨 생성** | `deal-mgmt/app/ralph/generators/ldd/appendix_generator.py` |
| **최종 QA** | `deal-mgmt/app/ralph/generators/ldd/report_qa.py` |
| **Finalize 생성기** | `deal-mgmt/app/ralph/generators/ldd/finalize_generator.py` |
| **프롬프트** | `deal-mgmt/app/ralph/generators/ldd/prompts.py` |
| **서술 프롬프트** | `deal-mgmt/app/ralph/generators/ldd/narrative_prompts.py` |
| **LLM 클라이언트** | `deal-mgmt/app/ralph/llm_client.py` |
| **모델 라우터** | `deal-mgmt/app/ralph/routing/ldd_router.py` |
| **프론트 훅** | `amic-platform/src/modules/docs/hooks/useLDDReports.ts` |
| **프론트 페이지** | `amic-platform/src/modules/docs/pages/CreateLDDReportPage.tsx` |
