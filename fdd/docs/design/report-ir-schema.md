# Report IR (Intermediate Representation) 스키마 설계

> **Status**: Draft v1.0
> **관련 EPIC**: EPIC-8 (Report Schema IR + Block Library), EPIC-9 (PPT Renderer v1)
> **관련 Issue**: FDD-801 ~ FDD-805, FDD-901
> **Sprint**: Sprint 7에서 구현 예정
> **최종 수정**: 2026-02-05

---

## 1. 개요

### 1.1 목적

Report IR은 **엔진(engines) 출력물을 렌더러(PPT/Word)에 전달하는 포맷-중립 중간표현**이다.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Engines   │────▶│ report_builder.py│────▶│   Report IR     │────▶│  Renderers   │
│ (QoE/NWC/   │     │ (JSON IR 조립)   │     │   (JSON)        │     │ (PPT / Word) │
│  Net Debt)  │     └──────────────────┘     └─────────────────┘     └──────────────┘
│             │                                      │
│ return      │                              ┌───────┴───────┐
│ (Result,    │                              │ evidence_index│
│  Evidence[])│                              │ (전역 근거)    │
└─────────────┘                              └───────────────┘
```

### 1.2 설계 원칙

| 원칙 | 설명 |
|------|------|
| **포맷 독립** | 동일 IR로 PPT, Word, PDF 모두 생성 가능 |
| **자기완결적** | IR 안에 렌더링에 필요한 모든 데이터 포함. 렌더러가 DB 조회 금지 |
| **금액=문자열** | `DECIMAL(18,4)` 정밀도 유지를 위해 모든 금액은 `string`("10000.0000") |
| **근거 추적** | 모든 숫자·문장에 EvidenceLink ID 부착, evidence_index에서 일괄 관리 |
| **확장 가능** | 새 Block 타입 추가 시 기존 렌더러가 깨지지 않도록 `type` discriminator 사용 |
| **재현 가능** | snapshot_id + definition_hash로 동일 IR 재생성 보장 |

### 1.3 금액 값 규칙

- **IR 내 금액값은 `display_unit` 기준으로 이미 환산된 값**이다.
- 예: `display_unit = "MILLION_KRW"`이면, 10억원은 `"1000.0000"`으로 기록.
- 렌더러는 값을 그대로 포맷팅(천단위 콤마 등)만 한다.
- 원본 정밀도가 필요한 경우 `evidence_index`를 통해 원장까지 추적한다.

---

## 2. 최상위 구조 (Top-Level)

```jsonc
{
  "ir_version": "1.0",                   // IR 스키마 버전
  "meta": { /* ReportMeta */ },           // 보고서 메타정보
  "sections": [ /* Section[] */ ],        // 순서대로 나열된 섹션 배열
  "evidence_index": { /* EvidenceIndex */ } // 전역 근거 레지스트리
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `ir_version` | `string` | Y | IR 스키마 버전 (SemVer). 렌더러 호환성 체크용 |
| `meta` | `ReportMeta` | Y | 딜·보고서 메타정보 |
| `sections` | `Section[]` | Y | 보고서 섹션 배열 (순서 = 출력 순서) |
| `evidence_index` | `EvidenceIndex` | Y | 근거 링크 일괄 저장소 |

---

## 3. ReportMeta

```jsonc
{
  "deal_id": "550e8400-e29b-41d4-a716-446655440000",
  "deal_name": "Project Alpha",
  "deal_type": "COMPLETION_ACCOUNTS",       // "COMPLETION_ACCOUNTS" | "LOCKED_BOX"
  "base_currency": "KRW",
  "display_unit": "MILLION_KRW",            // 표시 단위 (아래 enum 참조)
  "reference_date": "2024-12-31",
  "period_start": "2024-01-01",
  "period_end": "2024-12-31",
  "periods": [                              // 비교 기간 목록 (컬럼 헤더 생성에 사용)
    { "key": "fy2022", "label": "FY2022", "start": "2022-01-01", "end": "2022-12-31" },
    { "key": "fy2023", "label": "FY2023", "start": "2023-01-01", "end": "2023-12-31" },
    { "key": "fy2024", "label": "FY2024", "start": "2024-01-01", "end": "2024-12-31" }
  ],
  "definition_version": 3,
  "definition_id": "660e8400-e29b-41d4-a716-446655440001",
  "definition_hash": "sha256:abc123...",
  "snapshot_id": "770e8400-e29b-41d4-a716-446655440002",
  "engine_version": "1.0.0",
  "generated_at": "2025-06-15T09:30:00Z",
  "generated_by": "system",
  "coverage": {
    "tb_months": 36,                        // TB 데이터 포함 월수
    "gl_available": true,                   // GL 데이터 존재 여부
    "contracts_reviewed": 12,               // 검토 계약 수
    "data_completeness": "0.95"             // 데이터 완전성 (0~1, string)
  }
}
```

### 3.1 DisplayUnit Enum

| 값 | 의미 | 변환 계수 |
|----|------|-----------|
| `"WON"` | 원 | ×1 |
| `"THOUSAND_KRW"` | 천원 | ×0.001 |
| `"MILLION_KRW"` | 백만원 | ×0.000001 |
| `"HUNDRED_MILLION_KRW"` | 억원 | ×0.00000001 |
| `"USD"` | 달러 | ×1 |
| `"THOUSAND_USD"` | 천달러 | ×0.001 |
| `"MILLION_USD"` | 백만달러 | ×0.000001 |

> `display_unit`은 보고서 전체 기본값이며, 개별 TableBlock에서 `unit` 필드로 오버라이드 가능.

---

## 4. Section

```jsonc
{
  "id": "qoe",                              // 섹션 고유 ID (snake_case)
  "section_type": "QOE",                    // SectionType enum
  "title": "Quality of Earnings Analysis",  // 표시 제목
  "subtitle": null,                         // 부제목 (optional)
  "order": 4,                               // 섹션 순서 (1-based)
  "blocks": [ /* Block[] */ ],              // 블록 배열 (순서 = 출력 순서)
  "page_break_before": true                 // Word용: 앞에 페이지 구분 삽입
}
```

### 4.1 SectionType Enum

| 값 | 설명 | PPT 최소 슬라이드 |
|----|------|--------------------|
| `"COVER"` | 표지 | 1장 |
| `"SCOPE_DEFINITIONS"` | 범위 및 정의 | 1장 |
| `"EXECUTIVE_SUMMARY"` | Executive Summary | 1~2장 |
| `"QOE"` | Quality of Earnings | 2~4장 |
| `"NWC"` | Net Working Capital | 2~3장 |
| `"NET_DEBT"` | Net Debt & debt-like | 2~3장 |
| `"ISSUE_LOG"` | 이슈 목록 | 1~2장 |
| `"REQUEST_LIST"` | 정보 요청 목록 | 1장 |
| `"APPENDIX"` | 부록 | 가변 |
| `"METHODOLOGY"` | 방법론 | 1장 |

---

## 5. Block 타입 상세

모든 Block은 공통 필드를 가진다:

```jsonc
{
  "type": "table",        // BlockType discriminator
  "id": "qoe-bridge",    // 블록 고유 ID (kebab-case, 섹션 내 유일)
  "title": "...",         // 블록 제목 (optional, null 가능)
  "visible": true         // false면 렌더링에서 제외 (숨김 모드)
}
```

### 5.1 TextBlock

**용도**: 본문 텍스트, 제목, 소제목, 각주, 방법론 설명 등

```jsonc
{
  "type": "text",
  "id": "exec-summary-overview",
  "title": null,
  "visible": true,
  "text_style": "body",                     // TextStyle enum
  "content": "본 FDD는 Project Alpha 인수 관련 재무 실사를 수행한 결과를 요약한 것입니다.",
  "content_html": null                       // 리치 텍스트가 필요할 경우 (optional)
}
```

| TextStyle 값 | 용도 | PPT 매핑 | Word 매핑 |
|---------------|------|----------|-----------|
| `"heading1"` | 섹션 대제목 | 타이틀 텍스트박스 | Heading 1 |
| `"heading2"` | 소제목 | 서브타이틀 텍스트박스 | Heading 2 |
| `"heading3"` | 하위 제목 | 굵은 본문 | Heading 3 |
| `"body"` | 본문 | 기본 텍스트 | Normal |
| `"footnote"` | 각주/주석 | 작은 텍스트 | Footnote |
| `"caption"` | 표/차트 캡션 | 캡션 스타일 | Caption |
| `"disclaimer"` | 면책 조항 | 이탤릭 소형 | 이탤릭 소형 |

---

### 5.2 TableBlock

**용도**: QoE Bridge, NWC Trend, Net Debt Schedule 등 모든 수치 표

```jsonc
{
  "type": "table",
  "id": "qoe-bridge",
  "title": "Quality of Earnings Bridge",
  "visible": true,
  "table_type": "QOE_BRIDGE",              // TableType enum
  "unit": "MILLION_KRW",                   // 이 테이블의 표시 단위 (meta.display_unit 오버라이드)
  "unit_label": "(단위: 백만원)",            // 표 상단에 표시할 단위 레이블
  "columns": [
    {
      "key": "item",                        // 데이터 키 (rows.values의 키와 매칭)
      "label": "항목",                       // 컬럼 헤더 텍스트
      "data_type": "text",                  // "text" | "number" | "percentage" | "date"
      "align": "left",                      // "left" | "center" | "right"
      "width_ratio": 0.3                    // 컬럼 너비 비율 (0~1, 합계 1.0)
    },
    {
      "key": "fy2022",
      "label": "FY2022",
      "data_type": "number",
      "align": "right",
      "width_ratio": 0.175
    },
    {
      "key": "fy2023",
      "label": "FY2023",
      "data_type": "number",
      "align": "right",
      "width_ratio": 0.175
    },
    {
      "key": "fy2024",
      "label": "FY2024",
      "data_type": "number",
      "align": "right",
      "width_ratio": 0.175
    },
    {
      "key": "comment",
      "label": "비고",
      "data_type": "text",
      "align": "left",
      "width_ratio": 0.175
    }
  ],
  "rows": [
    {
      "key": "reported_revenue",
      "values": {
        "item": "매출액",
        "fy2022": "150000.0000",
        "fy2023": "180000.0000",
        "fy2024": "210000.0000",
        "comment": ""
      },
      "row_style": "normal",                // RowStyle enum
      "indent": 0,                           // 들여쓰기 수준 (0, 1, 2)
      "evidence_ids": ["ev-001"]             // 이 행에 연결된 근거 ID 목록
    },
    {
      "key": "reported_cogs",
      "values": {
        "item": "매출원가",
        "fy2022": "-90000.0000",
        "fy2023": "-105000.0000",
        "fy2024": "-120000.0000",
        "comment": ""
      },
      "row_style": "normal",
      "indent": 0,
      "evidence_ids": ["ev-002"]
    },
    {
      "key": "reported_ebitda",
      "values": {
        "item": "Reported EBITDA",
        "fy2022": "30000.0000",
        "fy2023": "38000.0000",
        "fy2024": "45000.0000",
        "comment": ""
      },
      "row_style": "subtotal",
      "indent": 0,
      "evidence_ids": ["ev-003"]
    },
    {
      "key": "adj_one_off",
      "values": {
        "item": "일회성 비용 제거",
        "fy2022": "1200.0000",
        "fy2023": "0.0000",
        "fy2024": "3500.0000",
        "comment": "본사 이전 비용"
      },
      "row_style": "normal",
      "indent": 1,
      "evidence_ids": ["ev-004", "ev-005"]
    },
    {
      "key": "adjusted_ebitda",
      "values": {
        "item": "Adjusted EBITDA",
        "fy2022": "31200.0000",
        "fy2023": "38000.0000",
        "fy2024": "48500.0000",
        "comment": ""
      },
      "row_style": "total",
      "indent": 0,
      "evidence_ids": ["ev-006"]
    }
  ],
  "footnotes": [
    "주1: FY2024 일회성 비용은 본사 이전 관련 비용으로 경영진 확인 완료",
    "주2: Reported EBITDA는 관리회계 기준이며, IFRS 재무제표와 차이 존재"
  ],
  "validation": {                            // 선택적 검증 규칙 (QA에서 활용)
    "checksum_rule": "reported_ebitda + Σadj = adjusted_ebitda",
    "tolerance": "0.0000"
  }
}
```

### TableType Enum

| 값 | 설명 | 최소 지원 (v1) |
|----|------|-----------------|
| `"QOE_BRIDGE"` | QoE Bridge (Reported → Adjusted) | Y |
| `"QOE_ADJUSTMENTS_DETAIL"` | QoE 조정항목 상세 | Y |
| `"NWC_DEFINITION"` | NWC 구성 정의표 | Y |
| `"NWC_TREND"` | 월별 NWC 추이 | Y |
| `"NWC_PEG_SCENARIOS"` | NWC Peg 시나리오 비교 | Y |
| `"NET_DEBT_SCHEDULE"` | Net Debt & debt-like 스케줄 | Y |
| `"INCOME_STATEMENT"` | 손익계산서 요약 | — |
| `"BALANCE_SHEET"` | 재무상태표 요약 | — |
| `"COA_MAPPING"` | 계정과목 매핑표 (Appendix) | — |
| `"GENERIC"` | 범용 테이블 | — |

### RowStyle Enum

| 값 | 렌더링 | 설명 |
|----|--------|------|
| `"normal"` | 기본 스타일 | 일반 데이터 행 |
| `"header"` | 굵게 + 배경색 | 구간 헤더 (예: "매출 항목") |
| `"subtotal"` | 굵게 + 상단선 | 소계 행 |
| `"total"` | 굵게 + 이중선 | 합계 행 |
| `"separator"` | 빈 행 or 구분선 | 시각적 구분 |
| `"highlight"` | 배경 강조색 | 주요 항목 강조 |

---

### 5.3 ChartBlock

**용도**: 매출/마진 트렌드, NWC 트렌드, Net Debt 브리지 시각화

> **규칙**: 차트 데이터는 반드시 IR 내 TableBlock에서 파생. 직접 GL 참조 금지.

```jsonc
{
  "type": "chart",
  "id": "revenue-margin-trend",
  "title": "매출 및 EBITDA 마진 추이",
  "visible": true,
  "chart_type": "COMBO_BAR_LINE",            // ChartType enum
  "source_table_id": "qoe-bridge",           // 데이터 출처 테이블 블록 ID
  "data": {
    "categories": ["FY2022", "FY2023", "FY2024"],
    "series": [
      {
        "name": "매출액",
        "values": ["150000.0000", "180000.0000", "210000.0000"],
        "axis": "left",                       // "left" | "right"
        "render_as": "bar",                   // "bar" | "line" | "area"
        "color": "#4472C4"
      },
      {
        "name": "EBITDA 마진",
        "values": ["20.0", "21.1", "21.4"],
        "axis": "right",
        "render_as": "line",
        "color": "#ED7D31"
      }
    ]
  },
  "options": {
    "left_axis_label": "백만원",
    "right_axis_label": "%",
    "show_legend": true,
    "show_data_labels": false,
    "aspect_ratio": "16:9"                   // PPT 슬라이드 비율
  },
  "source_note": "Source: QoE Bridge Table, Definition v3"  // 차트 하단 출처 표기
}
```

### ChartType Enum

| 값 | 설명 | 최소 지원 (v1) |
|----|------|-----------------|
| `"BAR"` | 수직 막대 차트 | Y |
| `"STACKED_BAR"` | 누적 막대 차트 | Y |
| `"LINE"` | 꺾은선 차트 | Y |
| `"COMBO_BAR_LINE"` | 막대 + 꺾은선 복합 | — |
| `"WATERFALL"` | 폭포(워터폴) 차트 | — |
| `"PIE"` | 원형 차트 | — |
| `"AREA"` | 영역 차트 | — |

---

### 5.4 ClaimBlock

**용도**: 분석가가 작성하는 서술문(Claim). 각 문장마다 EvidenceLink 연결 필수.

> **규칙**: `evidence_ids`가 비어 있으면 `status`는 자동으로 `"unverified"` 처리.

```jsonc
{
  "type": "claim",
  "id": "claim-qoe-summary-01",
  "title": null,
  "visible": true,
  "claims": [
    {
      "claim_id": "c-001",
      "text": "FY2024 Adjusted EBITDA는 48,500백만원으로, 전년 대비 27.6% 증가하였습니다.",
      "evidence_ids": ["ev-006", "ev-003"],
      "status": "verified",                  // ClaimStatus enum
      "category": "finding"                  // ClaimCategory enum
    },
    {
      "claim_id": "c-002",
      "text": "동 증가의 주요 원인은 매출 성장(+16.7%)과 일회성 비용 조정(3,500백만원)입니다.",
      "evidence_ids": ["ev-004"],
      "status": "verified",
      "category": "finding"
    },
    {
      "claim_id": "c-003",
      "text": "경영진은 FY2025에도 유사한 성장률을 기대하고 있습니다.",
      "evidence_ids": [],
      "status": "unverified",
      "category": "management_representation"
    }
  ]
}
```

### ClaimStatus Enum

| 값 | 설명 |
|----|------|
| `"verified"` | 근거 1개 이상 확인됨 |
| `"unverified"` | 근거 없음 — Draft/Unverified 표기 필요 |
| `"user_approved"` | 사용자가 수동 승인 (근거 없이도 포함) |
| `"excluded"` | 보고서에서 제외 (visible=true이지만 렌더러가 제외 표시) |

### ClaimCategory Enum

| 값 | 설명 |
|----|------|
| `"finding"` | 분석 발견사항 |
| `"observation"` | 관찰사항 |
| `"management_representation"` | 경영진 진술 |
| `"recommendation"` | 권고사항 |
| `"limitation"` | 분석 제한사항 |

---

### 5.5 IssueBlock

**용도**: FDD 과정에서 발견된 이슈/리스크 항목 모음

```jsonc
{
  "type": "issue",
  "id": "issue-log",
  "title": "Key Issues & Observations",
  "visible": true,
  "items": [
    {
      "issue_id": "ISS-001",
      "category": "QOE",                    // IssueCategory enum
      "severity": "high",                   // "high" | "medium" | "low"
      "title": "비경상적 매출 인식",
      "description": "FY2024 Q4에 관계사 거래를 통한 매출 50억원이 인식되었으며, 실질 거래 여부 확인 필요",
      "impact_amount": "5000.0000",          // 영향 금액 (display_unit 기준, null 가능)
      "impact_direction": "negative",        // "positive" | "negative" | "neutral" | null
      "status": "open",                      // "open" | "resolved" | "acknowledged"
      "evidence_ids": ["ev-010", "ev-011"],
      "response": null                       // 경영진 답변 (optional)
    },
    {
      "issue_id": "ISS-002",
      "category": "NET_DEBT",
      "severity": "medium",
      "title": "미인식 리스부채",
      "description": "IFRS 16 적용 대상 리스 3건이 off-balance 처리되어 있음",
      "impact_amount": "2300.0000",
      "impact_direction": "negative",
      "status": "acknowledged",
      "evidence_ids": ["ev-012"],
      "response": "FY2025 Q1 재무제표에서 반영 예정 (CFO 확인)"
    }
  ]
}
```

### IssueCategory Enum

| 값 | 설명 |
|----|------|
| `"QOE"` | QoE 관련 |
| `"NWC"` | NWC 관련 |
| `"NET_DEBT"` | Net Debt 관련 |
| `"TAX"` | 세무 관련 |
| `"COMPLIANCE"` | 컴플라이언스 |
| `"OTHER"` | 기타 |

---

### 5.6 RequestListBlock

**용도**: 대상 회사에 요청한 자료 목록 및 수령 현황

```jsonc
{
  "type": "request_list",
  "id": "info-request-list",
  "title": "Information Request List",
  "visible": true,
  "items": [
    {
      "request_id": "REQ-001",
      "category": "Financial",
      "description": "FY2022~FY2024 월별 시산표 (TB)",
      "status": "received",                  // RequestStatus enum
      "requested_date": "2025-01-10",
      "received_date": "2025-01-15",
      "priority": "high",                    // "high" | "medium" | "low"
      "notes": null
    },
    {
      "request_id": "REQ-002",
      "category": "Legal",
      "description": "주요 거래처 계약서 (매출 상위 10개사)",
      "status": "partial",
      "requested_date": "2025-01-10",
      "received_date": null,
      "priority": "high",
      "notes": "3개사 계약서 미수령"
    }
  ],
  "summary": {
    "total": 25,
    "received": 18,
    "partial": 4,
    "pending": 2,
    "waived": 1
  }
}
```

### RequestStatus Enum

| 값 | 설명 |
|----|------|
| `"pending"` | 요청 중 |
| `"received"` | 수령 완료 |
| `"partial"` | 일부 수령 |
| `"waived"` | 면제/불필요 |
| `"overdue"` | 기한 초과 |

---

### 5.7 CoverBlock (표지 전용)

**용도**: 보고서 표지에 표시할 정보

```jsonc
{
  "type": "cover",
  "id": "report-cover",
  "title": null,
  "visible": true,
  "report_title": "Financial Due Diligence Report",
  "report_subtitle": "Project Alpha — Completion Accounts Basis",
  "target_company": "Alpha Holdings Co., Ltd.",
  "prepared_for": "Beta Capital Partners",
  "prepared_by": "FDD Advisory Team",
  "report_date": "2025-06-15",
  "confidentiality": "Confidential — For intended recipients only",
  "draft_label": "DRAFT"                     // null이면 최종본
}
```

---

### 5.8 KeyValueBlock (범위/정의 등 간단한 키-값 목록)

**용도**: Scope & Definitions 섹션의 key-value 나열

```jsonc
{
  "type": "key_value",
  "id": "scope-definitions",
  "title": "Scope of Work",
  "visible": true,
  "items": [
    { "key": "Target Company", "value": "Alpha Holdings Co., Ltd." },
    { "key": "Reference Date", "value": "2024년 12월 31일" },
    { "key": "Analysis Period", "value": "FY2022 ~ FY2024 (3개년)" },
    { "key": "Deal Type", "value": "Completion Accounts" },
    { "key": "Currency", "value": "KRW (백만원)" },
    { "key": "Base EBITDA Definition", "value": "영업이익 + 감가상각비 (관리회계 기준)" },
    { "key": "NWC Definition", "value": "유동자산 - 유동부채 (Cash/Debt 제외)" }
  ],
  "layout": "vertical"                       // "vertical" | "horizontal" | "two_column"
}
```

---

## 6. EvidenceIndex

모든 Block의 `evidence_ids`가 참조하는 전역 근거 저장소.

```jsonc
{
  "entries": {
    "ev-001": {
      "source_type": "tb",                   // EvidenceSourceType enum
      "source_id": "upload-001",             // 파일 업로드 ID 또는 경로
      "source_detail": {
        "sheet": "2024_12",                  // 엑셀 시트명
        "row": null,                         // 특정 행 (null이면 집계값)
        "page": null,                        // PDF 페이지
        "cell_range": "B2:B150",             // 셀 범위 (optional)
        "transaction_id": null,              // GL 전표번호
        "filter_hash": "sha256:def456..."    // 필터 조건 해시
      },
      "engine_version": "1.0.0",
      "description": "FY2024 12월 시산표 매출계정 합계",
      "created_at": "2025-06-15T09:30:00Z"
    },
    "ev-002": {
      "source_type": "gl",
      "source_id": "upload-002",
      "source_detail": {
        "sheet": null,
        "row": null,
        "page": null,
        "cell_range": null,
        "transaction_id": "JE-2024-00142",
        "filter_hash": "sha256:ghi789..."
      },
      "engine_version": "1.0.0",
      "description": "FY2024 12월 매출원가 전표 상세",
      "created_at": "2025-06-15T09:30:00Z"
    },
    "ev-010": {
      "source_type": "manual",
      "source_id": null,
      "source_detail": {
        "sheet": null,
        "row": null,
        "page": null,
        "cell_range": null,
        "transaction_id": null,
        "filter_hash": null
      },
      "engine_version": "1.0.0",
      "description": "경영진 인터뷰 (2025-01-20, CFO 김OO)",
      "created_at": "2025-06-15T09:30:00Z"
    }
  }
}
```

### EvidenceSourceType Enum

| 값 | 설명 |
|----|------|
| `"tb"` | 시산표 (Trial Balance) |
| `"gl"` | 총계정원장 (General Ledger) |
| `"file"` | 업로드 파일 (엑셀 등) |
| `"pdf"` | PDF 문서 |
| `"contract"` | 계약서 |
| `"manual"` | 수동 입력 (인터뷰, 메모 등) |
| `"computed"` | 엔진 계산 결과 (다른 근거의 파생) |

---

## 7. 표준 섹션 구성 (기본 보고서 10장)

아래는 PPT Renderer v1의 기본 섹션 구성이다. `report_builder.py`가 엔진 결과를 조립할 때 이 구조를 기본 템플릿으로 사용한다.

| 순서 | section_type | 포함 Block 타입 |
|------|-------------|----------------|
| 1 | `COVER` | CoverBlock ×1 |
| 2 | `SCOPE_DEFINITIONS` | KeyValueBlock ×1, TextBlock(disclaimer) ×1 |
| 3 | `EXECUTIVE_SUMMARY` | TextBlock(heading) ×1, ClaimBlock(핵심 findings) ×1, TableBlock(summary) ×1 |
| 4 | `QOE` | TextBlock ×1~2, TableBlock(QOE_BRIDGE) ×1, TableBlock(QOE_ADJUSTMENTS_DETAIL) ×1, ChartBlock(revenue trend) ×1, ClaimBlock ×1 |
| 5 | `NWC` | TextBlock ×1, TableBlock(NWC_DEFINITION) ×1, TableBlock(NWC_TREND) ×1, TableBlock(NWC_PEG_SCENARIOS) ×1, ChartBlock(NWC trend) ×1 |
| 6 | `NET_DEBT` | TextBlock ×1, TableBlock(NET_DEBT_SCHEDULE) ×1, ClaimBlock ×1 |
| 7 | `ISSUE_LOG` | IssueBlock ×1 |
| 8 | `REQUEST_LIST` | RequestListBlock ×1 |
| 9 | `APPENDIX` | TableBlock(COA_MAPPING) ×1, TableBlock(기타 상세) ×N |
| 10 | `METHODOLOGY` | TextBlock(body) ×1~2 |

---

## 8. PPT 슬라이드 매핑 규칙

IR → PPT 변환 시 렌더러가 따르는 규칙:

| 규칙 | 설명 |
|------|------|
| **1 Section = 1+ Slides** | 섹션 내 블록 수에 따라 슬라이드 자동 분할 |
| **Table 오버플로우** | 행이 슬라이드 높이 초과 시 자동 분할 (FDD-902) |
| **Text 오버플로우** | 폰트 축소 (최소 8pt) → 그래도 초과 시 말줄임 |
| **Chart 배치** | 슬라이드당 차트 1개, 16:9 비율 |
| **Evidence Summary** | 각 슬라이드 하단에 사용된 evidence 수/종류 소형 표 (FDD-904, 옵션) |
| **Draft 워터마크** | `meta`에 draft 상태이면 모든 슬라이드에 DRAFT 워터마크 |

---

## 9. 템플릿 Placeholder 매핑 (EPIC 10 Preview)

Sprint 7 이후 EPIC 10에서 템플릿 주입을 지원할 때, IR의 block ID가 placeholder 이름으로 매핑된다:

```
{{DEAL_NAME}}             → meta.deal_name
{{PERIOD}}                → meta.period_start ~ meta.period_end
{{DEFINITION_VERSION}}    → meta.definition_version
{{TABLE:QOE_BRIDGE}}      → sections[].blocks[id="qoe-bridge"]
{{TABLE:NWC_TREND}}       → sections[].blocks[id="nwc-trend"]
{{CHART:NWC_TREND}}       → sections[].blocks[id="nwc-trend-chart"]
```

> Block의 `id`를 `kebab-case`로 명명하는 이유: placeholder 매핑에서 대문자 변환(`QOE_BRIDGE`) 후 사용하기 위함.

---

## 10. 설계 결정 사항 요약

| # | 결정 | 근거 |
|---|------|------|
| D1 | 금액을 `string`으로 저장 | JSON에 decimal 타입 없음. float 정밀도 손실 방지. DECIMAL(18,4) 규칙 준수 |
| D2 | IR 내 값은 display_unit 기준 환산값 | 렌더러가 단위 변환 로직을 가질 필요 없음. report_builder가 환산 책임 |
| D3 | evidence를 블록 내 인라인이 아닌 전역 index | 동일 근거를 여러 블록에서 참조 가능. 중복 제거 |
| D4 | Block `type`으로 discriminated union | 렌더러가 unknown type을 skip 가능. 하위호환성 |
| D5 | Section `order`를 명시적 숫자로 | 배열 순서만으로 충분하나, 렌더러가 정렬 검증 가능 |
| D6 | `visible` 플래그 | 내부용/외부배포용에서 특정 블록 숨김 (예: evidence summary) |
| D7 | `validation` 필드를 TableBlock에 포함 | QA 게이트(Sprint 8)에서 IR만으로 검증 가능 |
| D8 | Chart는 source_table_id 참조 필수 | "차트는 표에서만 파생" 규칙 강제. GL 직접 참조 방지 |

---

## 11. Python 타입 정의 (Pydantic v2)

> Sprint 7 구현 시 `backend/app/schemas/report_ir.py`에 위치 예정.

```python
"""Report IR Schema — Pydantic v2 type definitions."""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────


class DisplayUnit(str, enum.Enum):
    WON = "WON"
    THOUSAND_KRW = "THOUSAND_KRW"
    MILLION_KRW = "MILLION_KRW"
    HUNDRED_MILLION_KRW = "HUNDRED_MILLION_KRW"
    USD = "USD"
    THOUSAND_USD = "THOUSAND_USD"
    MILLION_USD = "MILLION_USD"


class SectionType(str, enum.Enum):
    COVER = "COVER"
    SCOPE_DEFINITIONS = "SCOPE_DEFINITIONS"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    QOE = "QOE"
    NWC = "NWC"
    NET_DEBT = "NET_DEBT"
    ISSUE_LOG = "ISSUE_LOG"
    REQUEST_LIST = "REQUEST_LIST"
    APPENDIX = "APPENDIX"
    METHODOLOGY = "METHODOLOGY"


class TableType(str, enum.Enum):
    QOE_BRIDGE = "QOE_BRIDGE"
    QOE_ADJUSTMENTS_DETAIL = "QOE_ADJUSTMENTS_DETAIL"
    NWC_DEFINITION = "NWC_DEFINITION"
    NWC_TREND = "NWC_TREND"
    NWC_PEG_SCENARIOS = "NWC_PEG_SCENARIOS"
    NET_DEBT_SCHEDULE = "NET_DEBT_SCHEDULE"
    INCOME_STATEMENT = "INCOME_STATEMENT"
    BALANCE_SHEET = "BALANCE_SHEET"
    COA_MAPPING = "COA_MAPPING"
    GENERIC = "GENERIC"


class ChartType(str, enum.Enum):
    BAR = "BAR"
    STACKED_BAR = "STACKED_BAR"
    LINE = "LINE"
    COMBO_BAR_LINE = "COMBO_BAR_LINE"
    WATERFALL = "WATERFALL"
    PIE = "PIE"
    AREA = "AREA"


class TextStyle(str, enum.Enum):
    HEADING1 = "heading1"
    HEADING2 = "heading2"
    HEADING3 = "heading3"
    BODY = "body"
    FOOTNOTE = "footnote"
    CAPTION = "caption"
    DISCLAIMER = "disclaimer"


class RowStyle(str, enum.Enum):
    NORMAL = "normal"
    HEADER = "header"
    SUBTOTAL = "subtotal"
    TOTAL = "total"
    SEPARATOR = "separator"
    HIGHLIGHT = "highlight"


class ColumnDataType(str, enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    PERCENTAGE = "percentage"
    DATE = "date"


class ClaimStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    USER_APPROVED = "user_approved"
    EXCLUDED = "excluded"


class ClaimCategory(str, enum.Enum):
    FINDING = "finding"
    OBSERVATION = "observation"
    MANAGEMENT_REPRESENTATION = "management_representation"
    RECOMMENDATION = "recommendation"
    LIMITATION = "limitation"


class IssueSeverity(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueCategory(str, enum.Enum):
    QOE = "QOE"
    NWC = "NWC"
    NET_DEBT = "NET_DEBT"
    TAX = "TAX"
    COMPLIANCE = "COMPLIANCE"
    OTHER = "OTHER"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    RECEIVED = "received"
    PARTIAL = "partial"
    WAIVED = "waived"
    OVERDUE = "overdue"


class EvidenceSourceType(str, enum.Enum):
    TB = "tb"
    GL = "gl"
    FILE = "file"
    PDF = "pdf"
    CONTRACT = "contract"
    MANUAL = "manual"
    COMPUTED = "computed"


# ── ReportMeta ─────────────────────────────────────────────


class Period(BaseModel):
    key: str
    label: str
    start: date
    end: date


class Coverage(BaseModel):
    tb_months: int
    gl_available: bool
    contracts_reviewed: int
    data_completeness: str = Field(description="0~1 string representation")


class ReportMeta(BaseModel):
    deal_id: str
    deal_name: str
    deal_type: str  # "COMPLETION_ACCOUNTS" | "LOCKED_BOX"
    base_currency: str
    display_unit: DisplayUnit
    reference_date: date
    period_start: date
    period_end: date
    periods: list[Period]
    definition_version: int
    definition_id: str
    definition_hash: str
    snapshot_id: str
    engine_version: str
    generated_at: datetime
    generated_by: str
    coverage: Coverage


# ── Evidence ───────────────────────────────────────────────


class EvidenceSourceDetail(BaseModel):
    sheet: str | None = None
    row: int | None = None
    page: int | None = None
    cell_range: str | None = None
    transaction_id: str | None = None
    filter_hash: str | None = None


class EvidenceEntry(BaseModel):
    source_type: EvidenceSourceType
    source_id: str | None = None
    source_detail: EvidenceSourceDetail
    engine_version: str
    description: str
    created_at: datetime


class EvidenceIndex(BaseModel):
    entries: dict[str, EvidenceEntry]  # key = evidence ID (e.g. "ev-001")


# ── Blocks ─────────────────────────────────────────────────


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    id: str
    title: str | None = None
    visible: bool = True
    text_style: TextStyle = TextStyle.BODY
    content: str
    content_html: str | None = None


class ColumnDef(BaseModel):
    key: str
    label: str
    data_type: ColumnDataType = ColumnDataType.TEXT
    align: str = "left"  # "left" | "center" | "right"
    width_ratio: float | None = None


class TableRow(BaseModel):
    key: str
    values: dict[str, str | None]  # column key → display value (string)
    row_style: RowStyle = RowStyle.NORMAL
    indent: int = 0
    evidence_ids: list[str] = Field(default_factory=list)


class TableValidation(BaseModel):
    checksum_rule: str
    tolerance: str = "0.0000"


class TableBlock(BaseModel):
    type: Literal["table"] = "table"
    id: str
    title: str | None = None
    visible: bool = True
    table_type: TableType = TableType.GENERIC
    unit: DisplayUnit | None = None  # overrides meta.display_unit
    unit_label: str | None = None
    columns: list[ColumnDef]
    rows: list[TableRow]
    footnotes: list[str] = Field(default_factory=list)
    validation: TableValidation | None = None


class ChartSeries(BaseModel):
    name: str
    values: list[str]  # string decimals
    axis: str = "left"  # "left" | "right"
    render_as: str = "bar"  # "bar" | "line" | "area"
    color: str | None = None


class ChartData(BaseModel):
    categories: list[str]
    series: list[ChartSeries]


class ChartOptions(BaseModel):
    left_axis_label: str | None = None
    right_axis_label: str | None = None
    show_legend: bool = True
    show_data_labels: bool = False
    aspect_ratio: str = "16:9"


class ChartBlock(BaseModel):
    type: Literal["chart"] = "chart"
    id: str
    title: str | None = None
    visible: bool = True
    chart_type: ChartType
    source_table_id: str  # references a TableBlock.id
    data: ChartData
    options: ChartOptions = Field(default_factory=ChartOptions)
    source_note: str | None = None


class ClaimItem(BaseModel):
    claim_id: str
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    category: ClaimCategory = ClaimCategory.FINDING


class ClaimBlock(BaseModel):
    type: Literal["claim"] = "claim"
    id: str
    title: str | None = None
    visible: bool = True
    claims: list[ClaimItem]


class IssueItem(BaseModel):
    issue_id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    impact_amount: str | None = None  # string decimal
    impact_direction: str | None = None  # "positive" | "negative" | "neutral"
    status: IssueStatus = IssueStatus.OPEN
    evidence_ids: list[str] = Field(default_factory=list)
    response: str | None = None


class IssueBlock(BaseModel):
    type: Literal["issue"] = "issue"
    id: str
    title: str | None = None
    visible: bool = True
    items: list[IssueItem]


class RequestItem(BaseModel):
    request_id: str
    category: str
    description: str
    status: RequestStatus = RequestStatus.PENDING
    requested_date: date | None = None
    received_date: date | None = None
    priority: str = "medium"  # "high" | "medium" | "low"
    notes: str | None = None


class RequestSummary(BaseModel):
    total: int
    received: int
    partial: int
    pending: int
    waived: int


class RequestListBlock(BaseModel):
    type: Literal["request_list"] = "request_list"
    id: str
    title: str | None = None
    visible: bool = True
    items: list[RequestItem]
    summary: RequestSummary | None = None


class CoverBlock(BaseModel):
    type: Literal["cover"] = "cover"
    id: str
    title: str | None = None
    visible: bool = True
    report_title: str
    report_subtitle: str | None = None
    target_company: str
    prepared_for: str
    prepared_by: str
    report_date: date
    confidentiality: str | None = None
    draft_label: str | None = None  # "DRAFT" or None for final


class KeyValueItem(BaseModel):
    key: str
    value: str


class KeyValueBlock(BaseModel):
    type: Literal["key_value"] = "key_value"
    id: str
    title: str | None = None
    visible: bool = True
    items: list[KeyValueItem]
    layout: str = "vertical"  # "vertical" | "horizontal" | "two_column"


# ── Discriminated Union ────────────────────────────────────

from typing import Annotated, Union
from pydantic import Discriminator, Tag

Block = Annotated[
    Union[
        Annotated[TextBlock, Tag("text")],
        Annotated[TableBlock, Tag("table")],
        Annotated[ChartBlock, Tag("chart")],
        Annotated[ClaimBlock, Tag("claim")],
        Annotated[IssueBlock, Tag("issue")],
        Annotated[RequestListBlock, Tag("request_list")],
        Annotated[CoverBlock, Tag("cover")],
        Annotated[KeyValueBlock, Tag("key_value")],
    ],
    Discriminator("type"),
]


# ── Section & Top-level ────────────────────────────────────


class Section(BaseModel):
    id: str
    section_type: SectionType
    title: str
    subtitle: str | None = None
    order: int
    blocks: list[Block]
    page_break_before: bool = True


class ReportIR(BaseModel):
    """Report Intermediate Representation — 최상위 스키마."""

    ir_version: str = "1.0"
    meta: ReportMeta
    sections: list[Section]
    evidence_index: EvidenceIndex
```

---

## 12. TypeScript 타입 정의

> Sprint 7 구현 시 `pptx-service/src/types/report-ir.ts`에 위치 예정.

```typescript
// ── Enums ──────────────────────────────────────────────────

type DisplayUnit =
  | "WON"
  | "THOUSAND_KRW"
  | "MILLION_KRW"
  | "HUNDRED_MILLION_KRW"
  | "USD"
  | "THOUSAND_USD"
  | "MILLION_USD";

type SectionType =
  | "COVER"
  | "SCOPE_DEFINITIONS"
  | "EXECUTIVE_SUMMARY"
  | "QOE"
  | "NWC"
  | "NET_DEBT"
  | "ISSUE_LOG"
  | "REQUEST_LIST"
  | "APPENDIX"
  | "METHODOLOGY";

type TableType =
  | "QOE_BRIDGE"
  | "QOE_ADJUSTMENTS_DETAIL"
  | "NWC_DEFINITION"
  | "NWC_TREND"
  | "NWC_PEG_SCENARIOS"
  | "NET_DEBT_SCHEDULE"
  | "INCOME_STATEMENT"
  | "BALANCE_SHEET"
  | "COA_MAPPING"
  | "GENERIC";

type ChartType =
  | "BAR"
  | "STACKED_BAR"
  | "LINE"
  | "COMBO_BAR_LINE"
  | "WATERFALL"
  | "PIE"
  | "AREA";

type TextStyle =
  | "heading1"
  | "heading2"
  | "heading3"
  | "body"
  | "footnote"
  | "caption"
  | "disclaimer";

type RowStyle =
  | "normal"
  | "header"
  | "subtotal"
  | "total"
  | "separator"
  | "highlight";

type ColumnDataType = "text" | "number" | "percentage" | "date";

type ClaimStatus = "verified" | "unverified" | "user_approved" | "excluded";

type ClaimCategory =
  | "finding"
  | "observation"
  | "management_representation"
  | "recommendation"
  | "limitation";

type IssueSeverity = "high" | "medium" | "low";

type IssueCategory = "QOE" | "NWC" | "NET_DEBT" | "TAX" | "COMPLIANCE" | "OTHER";

type IssueStatus = "open" | "resolved" | "acknowledged";

type RequestStatus = "pending" | "received" | "partial" | "waived" | "overdue";

type EvidenceSourceType =
  | "tb"
  | "gl"
  | "file"
  | "pdf"
  | "contract"
  | "manual"
  | "computed";

// ── ReportMeta ─────────────────────────────────────────────

interface Period {
  key: string;
  label: string;
  start: string; // ISO date
  end: string;
}

interface Coverage {
  tb_months: number;
  gl_available: boolean;
  contracts_reviewed: number;
  data_completeness: string; // "0.95"
}

interface ReportMeta {
  deal_id: string;
  deal_name: string;
  deal_type: "COMPLETION_ACCOUNTS" | "LOCKED_BOX";
  base_currency: string;
  display_unit: DisplayUnit;
  reference_date: string;
  period_start: string;
  period_end: string;
  periods: Period[];
  definition_version: number;
  definition_id: string;
  definition_hash: string;
  snapshot_id: string;
  engine_version: string;
  generated_at: string; // ISO datetime
  generated_by: string;
  coverage: Coverage;
}

// ── Evidence ───────────────────────────────────────────────

interface EvidenceSourceDetail {
  sheet?: string | null;
  row?: number | null;
  page?: number | null;
  cell_range?: string | null;
  transaction_id?: string | null;
  filter_hash?: string | null;
}

interface EvidenceEntry {
  source_type: EvidenceSourceType;
  source_id: string | null;
  source_detail: EvidenceSourceDetail;
  engine_version: string;
  description: string;
  created_at: string;
}

interface EvidenceIndex {
  entries: Record<string, EvidenceEntry>; // key = "ev-001"
}

// ── Blocks ─────────────────────────────────────────────────

interface BlockBase {
  type: string;
  id: string;
  title?: string | null;
  visible: boolean;
}

interface TextBlock extends BlockBase {
  type: "text";
  text_style: TextStyle;
  content: string;
  content_html?: string | null;
}

interface ColumnDef {
  key: string;
  label: string;
  data_type: ColumnDataType;
  align: "left" | "center" | "right";
  width_ratio?: number | null;
}

interface TableRow {
  key: string;
  values: Record<string, string | null>;
  row_style: RowStyle;
  indent: number;
  evidence_ids: string[];
}

interface TableValidation {
  checksum_rule: string;
  tolerance: string;
}

interface TableBlock extends BlockBase {
  type: "table";
  table_type: TableType;
  unit?: DisplayUnit | null;
  unit_label?: string | null;
  columns: ColumnDef[];
  rows: TableRow[];
  footnotes: string[];
  validation?: TableValidation | null;
}

interface ChartSeries {
  name: string;
  values: string[];
  axis: "left" | "right";
  render_as: "bar" | "line" | "area";
  color?: string | null;
}

interface ChartData {
  categories: string[];
  series: ChartSeries[];
}

interface ChartOptions {
  left_axis_label?: string | null;
  right_axis_label?: string | null;
  show_legend: boolean;
  show_data_labels: boolean;
  aspect_ratio: string;
}

interface ChartBlock extends BlockBase {
  type: "chart";
  chart_type: ChartType;
  source_table_id: string;
  data: ChartData;
  options: ChartOptions;
  source_note?: string | null;
}

interface ClaimItem {
  claim_id: string;
  text: string;
  evidence_ids: string[];
  status: ClaimStatus;
  category: ClaimCategory;
}

interface ClaimBlock extends BlockBase {
  type: "claim";
  claims: ClaimItem[];
}

interface IssueItem {
  issue_id: string;
  category: IssueCategory;
  severity: IssueSeverity;
  title: string;
  description: string;
  impact_amount?: string | null;
  impact_direction?: "positive" | "negative" | "neutral" | null;
  status: IssueStatus;
  evidence_ids: string[];
  response?: string | null;
}

interface IssueBlock extends BlockBase {
  type: "issue";
  items: IssueItem[];
}

interface RequestItem {
  request_id: string;
  category: string;
  description: string;
  status: RequestStatus;
  requested_date?: string | null;
  received_date?: string | null;
  priority: "high" | "medium" | "low";
  notes?: string | null;
}

interface RequestSummary {
  total: number;
  received: number;
  partial: number;
  pending: number;
  waived: number;
}

interface RequestListBlock extends BlockBase {
  type: "request_list";
  items: RequestItem[];
  summary?: RequestSummary | null;
}

interface CoverBlock extends BlockBase {
  type: "cover";
  report_title: string;
  report_subtitle?: string | null;
  target_company: string;
  prepared_for: string;
  prepared_by: string;
  report_date: string;
  confidentiality?: string | null;
  draft_label?: string | null;
}

interface KeyValueItem {
  key: string;
  value: string;
}

interface KeyValueBlock extends BlockBase {
  type: "key_value";
  items: KeyValueItem[];
  layout: "vertical" | "horizontal" | "two_column";
}

type Block =
  | TextBlock
  | TableBlock
  | ChartBlock
  | ClaimBlock
  | IssueBlock
  | RequestListBlock
  | CoverBlock
  | KeyValueBlock;

// ── Section & Top-level ────────────────────────────────────

interface Section {
  id: string;
  section_type: SectionType;
  title: string;
  subtitle?: string | null;
  order: number;
  blocks: Block[];
  page_break_before: boolean;
}

interface ReportIR {
  ir_version: string;
  meta: ReportMeta;
  sections: Section[];
  evidence_index: EvidenceIndex;
}

export type {
  ReportIR,
  ReportMeta,
  Section,
  Block,
  TextBlock,
  TableBlock,
  ChartBlock,
  ClaimBlock,
  IssueBlock,
  RequestListBlock,
  CoverBlock,
  KeyValueBlock,
  EvidenceIndex,
  EvidenceEntry,
  TableRow,
  ColumnDef,
  ChartSeries,
  ChartData,
  ClaimItem,
  IssueItem,
  RequestItem,
};
```

---

## Appendix A: 최소 예제 IR (Cover + Executive Summary + QoE)

> 전체 예제는 `docs/design/report-ir-example.json` 참조.

```jsonc
{
  "ir_version": "1.0",
  "meta": {
    "deal_id": "550e8400-e29b-41d4-a716-446655440000",
    "deal_name": "Project Alpha",
    "deal_type": "COMPLETION_ACCOUNTS",
    "base_currency": "KRW",
    "display_unit": "MILLION_KRW",
    "reference_date": "2024-12-31",
    "period_start": "2022-01-01",
    "period_end": "2024-12-31",
    "periods": [
      { "key": "fy2022", "label": "FY2022", "start": "2022-01-01", "end": "2022-12-31" },
      { "key": "fy2023", "label": "FY2023", "start": "2023-01-01", "end": "2023-12-31" },
      { "key": "fy2024", "label": "FY2024", "start": "2024-01-01", "end": "2024-12-31" }
    ],
    "definition_version": 3,
    "definition_id": "660e8400-e29b-41d4-a716-446655440001",
    "definition_hash": "sha256:abc123def456",
    "snapshot_id": "770e8400-e29b-41d4-a716-446655440002",
    "engine_version": "1.0.0",
    "generated_at": "2025-06-15T09:30:00Z",
    "generated_by": "system",
    "coverage": {
      "tb_months": 36,
      "gl_available": true,
      "contracts_reviewed": 12,
      "data_completeness": "0.95"
    }
  },
  "sections": [
    {
      "id": "cover",
      "section_type": "COVER",
      "title": "Cover",
      "subtitle": null,
      "order": 1,
      "page_break_before": false,
      "blocks": [
        {
          "type": "cover",
          "id": "report-cover",
          "title": null,
          "visible": true,
          "report_title": "Financial Due Diligence Report",
          "report_subtitle": "Project Alpha — Completion Accounts Basis",
          "target_company": "Alpha Holdings Co., Ltd.",
          "prepared_for": "Beta Capital Partners",
          "prepared_by": "FDD Advisory Team",
          "report_date": "2025-06-15",
          "confidentiality": "Confidential",
          "draft_label": "DRAFT"
        }
      ]
    },
    {
      "id": "executive-summary",
      "section_type": "EXECUTIVE_SUMMARY",
      "title": "Executive Summary",
      "subtitle": null,
      "order": 3,
      "page_break_before": true,
      "blocks": [
        {
          "type": "text",
          "id": "exec-intro",
          "title": null,
          "visible": true,
          "text_style": "body",
          "content": "본 보고서는 Alpha Holdings의 FY2022~FY2024 재무 실사 결과를 요약합니다.",
          "content_html": null
        },
        {
          "type": "claim",
          "id": "exec-key-findings",
          "title": "Key Findings",
          "visible": true,
          "claims": [
            {
              "claim_id": "c-001",
              "text": "Adjusted EBITDA는 FY2024 기준 48,500백만원으로, 3개년 CAGR 24.7%를 기록하였습니다.",
              "evidence_ids": ["ev-006"],
              "status": "verified",
              "category": "finding"
            }
          ]
        }
      ]
    },
    {
      "id": "qoe",
      "section_type": "QOE",
      "title": "Quality of Earnings Analysis",
      "subtitle": null,
      "order": 4,
      "page_break_before": true,
      "blocks": [
        {
          "type": "table",
          "id": "qoe-bridge",
          "title": "QoE Bridge: Reported → Adjusted EBITDA",
          "visible": true,
          "table_type": "QOE_BRIDGE",
          "unit": "MILLION_KRW",
          "unit_label": "(단위: 백만원)",
          "columns": [
            { "key": "item", "label": "항목", "data_type": "text", "align": "left", "width_ratio": 0.3 },
            { "key": "fy2022", "label": "FY2022", "data_type": "number", "align": "right", "width_ratio": 0.175 },
            { "key": "fy2023", "label": "FY2023", "data_type": "number", "align": "right", "width_ratio": 0.175 },
            { "key": "fy2024", "label": "FY2024", "data_type": "number", "align": "right", "width_ratio": 0.175 },
            { "key": "comment", "label": "비고", "data_type": "text", "align": "left", "width_ratio": 0.175 }
          ],
          "rows": [
            {
              "key": "reported_ebitda",
              "values": { "item": "Reported EBITDA", "fy2022": "30000.0000", "fy2023": "38000.0000", "fy2024": "45000.0000", "comment": "" },
              "row_style": "subtotal",
              "indent": 0,
              "evidence_ids": ["ev-003"]
            },
            {
              "key": "adj_one_off",
              "values": { "item": "일회성 비용 제거", "fy2022": "1200.0000", "fy2023": "0.0000", "fy2024": "3500.0000", "comment": "본사 이전 비용" },
              "row_style": "normal",
              "indent": 1,
              "evidence_ids": ["ev-004"]
            },
            {
              "key": "adjusted_ebitda",
              "values": { "item": "Adjusted EBITDA", "fy2022": "31200.0000", "fy2023": "38000.0000", "fy2024": "48500.0000", "comment": "" },
              "row_style": "total",
              "indent": 0,
              "evidence_ids": ["ev-006"]
            }
          ],
          "footnotes": ["주1: Reported EBITDA는 관리회계 기준"],
          "validation": {
            "checksum_rule": "reported_ebitda + Σadj = adjusted_ebitda",
            "tolerance": "0.0000"
          }
        }
      ]
    }
  ],
  "evidence_index": {
    "entries": {
      "ev-003": {
        "source_type": "tb",
        "source_id": "upload-001",
        "source_detail": { "sheet": "2024_12", "row": null, "page": null, "cell_range": "B2:B150", "transaction_id": null, "filter_hash": "sha256:aaa" },
        "engine_version": "1.0.0",
        "description": "FY2022~FY2024 시산표 기반 Reported EBITDA 산출",
        "created_at": "2025-06-15T09:30:00Z"
      },
      "ev-004": {
        "source_type": "gl",
        "source_id": "upload-002",
        "source_detail": { "sheet": null, "row": null, "page": null, "cell_range": null, "transaction_id": "JE-2024-00142", "filter_hash": "sha256:bbb" },
        "engine_version": "1.0.0",
        "description": "FY2024 본사 이전 관련 일회성 비용 전표",
        "created_at": "2025-06-15T09:30:00Z"
      },
      "ev-006": {
        "source_type": "computed",
        "source_id": null,
        "source_detail": { "sheet": null, "row": null, "page": null, "cell_range": null, "transaction_id": null, "filter_hash": "sha256:ccc" },
        "engine_version": "1.0.0",
        "description": "Adjusted EBITDA = Reported EBITDA + Σ조정항목 (엔진 계산)",
        "created_at": "2025-06-15T09:30:00Z"
      }
    }
  }
}
```

---

## Appendix B: report_builder.py 파이프라인 (구현 가이드)

Sprint 7 구현 시 `report_builder.py`의 책임:

```
1. Snapshot 로드 (definition + engine results)
2. Engine 결과를 Block으로 변환
   - qoe_engine.Result → TableBlock(QOE_BRIDGE) + ClaimBlock
   - nwc_engine.Result → TableBlock(NWC_DEFINITION, NWC_TREND, NWC_PEG) + ChartBlock
   - debt_engine.Result → TableBlock(NET_DEBT_SCHEDULE) + ClaimBlock
3. EvidenceLink 수집 → EvidenceIndex 조립
4. Section 순서에 따라 조립
5. ReportMeta 생성 (Deal 정보 + Definition + Snapshot)
6. ReportIR 직렬화 (JSON)
7. PPT Renderer 호출 (POST /render)
```

```python
# 구현 시 시그니처 (예시)
async def build_report_ir(
    deal: Deal,
    definition: DealDefinition,
    snapshot: DealSnapshot,
    engine_results: dict[str, tuple[Any, list[EvidenceLink]]],
) -> ReportIR:
    """엔진 결과를 받아 Report IR을 조립한다."""
    ...
```

---

## Appendix C: 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2026-02-05 | 초안 작성 — 8 Block 타입, 10 Section, Python/TS 타입 정의 |
