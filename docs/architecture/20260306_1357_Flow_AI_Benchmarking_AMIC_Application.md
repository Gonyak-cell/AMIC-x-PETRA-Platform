# Flow AI 상품구조 분석 및 AMIC 플랫폼 적용 방안

> 작성: 2026-03-06 13:57 KST
> 목적: SaaS 협업툴 '플로우(Flow)'의 AI 에이전트 상품구조를 분석하고, AMIC x PETRA Platform에 적용 가능한 3가지 방향의 설계안 제시

---

## Context: 왜 이 분석이 필요한가

마드라스체크가 2026.02.24 출시한 Flow AI 에이전트는 **"엑셀 + 자연어 → 프로젝트 자동 생성"**과 **"문서 기반 폐쇄형 챗봇"** 두 가지 핵심 기능을 통해, 기존 협업툴 AI가 "사후 보조"에 머물던 한계를 넘어 **"초기 설계 단계부터 AI가 개입"**하는 패러다임 전환을 시도했다.

AMIC x PETRA Platform은 이미 **멀티 LLM 통합(3사), RAG 파이프라인, 문서 자동 분류/추출, 9단계 M&A 워크플로우**를 보유하고 있어, Flow의 접근법을 M&A 도메인에 특화 적용할 기술적 토대가 충분하다.

---

## 1. 현재 AMIC 플랫폼 AI 역량 (As-Is)

| 역량 | 현황 | 핵심 파일 |
|------|------|----------|
| **멀티 LLM** | OpenAI + Anthropic + Google 3중 통합, 폴백 체인 | `im/src/narrative_generator/engine/providers/` |
| **RAG** | OpenAI embedding + Pinecone + MMR 리랭킹 | `im/src/narrative_generator/rag/` |
| **문서 파싱** | DOCX, PDF, Excel, HWP 4종 파서 | `deal-mgmt/app/ralph/parsers/` |
| **문서 자동 분류** | 2단계 (메타데이터 스코어링 + LLM 본문 분석) | `deal-mgmt/app/services/vdr_service.py` |
| **문서 데이터 추출** | 9개 카테고리별 LLM 추출 (NDA, LOI, SPA 등) | `deal-mgmt/app/services/document_extraction_service.py` |
| **엑셀 처리** | RFI import/export (한/영 이중 헤더 매핑) | `deal-mgmt/app/excel/rfi_excel.py` |
| **자동 보고서** | IM 투자설명서 + LDD 법률실사 보고서 자동 생성 | `im/src/narrative_generator/`, `deal-mgmt/app/ralph/generators/ldd/` |
| **비용 추적** | 프로바이더별 토큰 비용 실시간 집계 | `deal-mgmt/app/ralph/llm_client.py` |

---

## 2. Flow AI 상품구조 벤치마킹

### 2.1 Flow 상품구조 해부

```
┌─────────────────────────────────────────────────────┐
│                   Flow AI Agent OS                   │
├─────────────────┬──────────────────┬────────────────┤
│  프로젝트 설계   │  문서 기반 챗봇   │  멀티 LLM 허브  │
│  AI 에이전트     │  (RAG 기반)      │  (GPT+Gemini   │
│                 │                  │   +Claude)     │
├─────────────────┼──────────────────┼────────────────┤
│ • 엑셀 WBS 업로드│ • 내부 문서 연동  │ • 단일 환경     │
│ • 자연어 명령    │ • 지침 기반 통제  │ • 별도 도구 불필요│
│ • 태스크 자동생성 │ • 폐쇄형 답변    │ • 프롬프트 가드  │
│ • 일정 자동배치  │ • 환각 방지      │ • 민감정보 마스킹│
│ • 담당자 배정    │                  │                │
└─────────────────┴──────────────────┴────────────────┘
        ↓                  ↓                ↓
   온보딩 장벽 80%↓    사내 지식 접근성↑    AI 도구 파편화↓
```

### 2.2 확인된 사실 (출처 기반)

| 항목 | 내용 | 출처 |
|------|------|------|
| 기능명 | 프로젝트 설계 AI 에이전트 | 마드라스체크 공식 발표 (2026.02.24) |
| 자동 기획 스펙 | 프로젝트 목적 + 엑셀 WBS → 전체 업무 구조/태스크/일정/담당자 자동 설계 | 지티티코리아 보도 (2026.02.24) |
| 사내 챗봇 스펙 | 문서/엑셀/프로젝트 연동 → 해당 범위 내에서만 답변하는 폐쇄형 봇 | 제품 안내 이미지 |
| 생산성 향상 | 프로젝트 초기 계획 시간 80% 이상 단축 | 플래텀 보도 (2026.02.24) |
| 보안 | 민감정보 자동 마스킹 + 프롬프트 가드 + 어드민 통제 | 플래텀 보도 (2026.02.24) |
| 기술 기반 | 챗GPT + 제미나이 + 클로드 통합, RAG 기반 환각 제어 | 마드라스체크 발표 |

### 2.3 Flow vs AMIC 갭 분석

| Flow 기능 | AMIC 현황 | 갭 수준 | 구현 난이도 |
|----------|----------|---------|-----------|
| 엑셀 → 프로젝트 자동 생성 | RFI 엑셀 import만 존재 | **HIGH** | 중 |
| 자연어 → 구조화된 태스크 | 없음 | **HIGH** | 중 |
| 문서 기반 폐쇄형 챗봇 | RAG 인프라 보유, 챗봇 UI 없음 | **MEDIUM** | 중 |
| 멀티 LLM 통합 | ✅ 이미 구현 완료 | **NONE** | - |
| 민감정보 마스킹 | 없음 | **MEDIUM** | 하 |
| 프롬프트 가드 | 없음 | **LOW** | 하 |
| 관리자 AI 대시보드 | 없음 | **MEDIUM** | 중 |

### 2.4 핵심 인사이트

1. **기술 갭은 작고, UX 갭이 크다** — AMIC은 멀티 LLM, RAG, 문서 파싱을 모두 보유. 진짜 차이는 "비전문가가 자연어/엑셀로 복잡한 구조를 만들 수 있는 인터페이스"에 있음
2. **재사용률 70% 이상** — 기존 엑셀 파서, LLM 클라이언트, RAG 코드를 조합하면 핵심 로직 구현 가능
3. **M&A 도메인 특화가 차별점** — Flow는 범용 "프로젝트"를 다루지만, AMIC은 9단계 M&A 워크플로우라는 구조화된 도메인에서 도메인 정밀도 압도적 우위

---

## 3. 적용 방향 A: 딜 셋업 AI 에이전트

### 3.1 개념

사용자가 기존 엑셀(딜 리스트, WBS, 거래조건)과 자연어 설명을 입력하면, AI가 Transaction + DD Checklist + Timeline + Buyer Pipeline을 자동으로 구성.

### 3.2 사용자 시나리오

```
시나리오 1: 자연어만 입력
─────────────────────
사용자: "삼성전자 자회사 하만 매각 딜. 예상 거래금액 600억, Sell-side.
        6개월 일정, FDD+LDD 필요. 매수 후보 3~5개사 타겟."

AI 응답:
├── Transaction 자동 생성
│   ├── code_name: "MA-2026-XXXX"
│   ├── target: "하만", deal_type: MA, side: SELL
│   ├── estimated_value: 60,000,000,000 KRW
│   └── phase: ENGAGEMENT
├── DD Checklist (FDD + LDD 워크스트림)
├── Timeline (6개월 마일스톤)
└── Buyer Pipeline 스켈레톤 (3~5개 슬롯)

시나리오 2: 엑셀 + 자연어
─────────────────────
사용자: "이 딜 리스트 엑셀을 참고해서 거래를 생성해줘" [엑셀 업로드]

AI: 엑셀 파싱 → LLM 분석 → Transaction 자동 생성 (사용자 확인 후)
```

### 3.3 기술 아키텍처

```
[사용자 입력]
  ├── 자연어 텍스트 ───┐
  └── 엑셀 파일 ───────┤
                       ▼
              ┌─────────────────┐
              │  Deal Setup     │
              │  AI Agent       │
              └────────┬────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  [엑셀 파서]    [LLM 구조화]    [유효성 검증]
  openpyxl       Claude/GPT      스키마 매칭
  헤더 매핑       JSON 스키마      필수 필드 체크
                  강제 출력
        └──────────────┼──────────────┘
                       ▼
              ┌─────────────────┐
              │  Preview &      │
              │  Confirmation   │
              └────────┬────────┘
                       ▼
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
  Transaction    DD Checklist    Timeline     Buyer Slots
```

### 3.4 재사용 코드 / 신규 파일

**재사용**: `rfi_excel.py` (헤더 매핑 패턴), `ralph/llm_client.py` (LLM 호출), `extraction_prompts.py` (JSON 스키마 패턴), 기존 CRUD 서비스들

**신규 BE**: `deal_setup_agent.py`, `deal_setup_service.py`, `deal_setup_prompts.py`, `deal_setup_excel.py`
**신규 FE**: `DealSetupWizard.tsx`, `useDealSetup.ts`

---

## 4. 적용 방향 B: VDR 지식 챗봇

### 4.1 개념

딜별 VDR 문서를 RAG로 인덱싱하여, 해당 문서 범위 내에서만 답변하는 폐쇄형 Q&A 챗봇 제공.

### 4.2 사용자 시나리오

```
[VDR 탭 → 챗봇 패널]

Q: "이 거래의 NDA에서 비밀유지 기간은?"
A: "NDA-2026-하만.pdf (3p)에 따르면, 계약 종료 후 3년입니다. [📎 소스]"

Q: "SPA 초안에서 선행조건(CP) 목록을 정리해줘"
A: "SPA_Draft_v2.docx (12-15p) 기재 선행조건: 1. 공정위 승인... [📎 소스]"
```

### 4.3 기술 아키텍처

```
VDR 문서 업로드 → Document Indexer (BackgroundTask)
→ Chunker + Embedder (IM RAG 코드 재사용)
→ Pinecone 벡터 스토어 (네임스페이스: "vdr-{transaction_id}")
→ 사용자 질문 → RAG Retriever (MMR) → LLM Answer + Source Citation
```

### 4.4 환각 방지 원칙

| 원칙 | 구현 |
|------|------|
| 네임스페이스 격리 | 딜별 Pinecone 네임스페이스 |
| 출처 강제 | 소스 문서명 + 페이지 번호 첨부 |
| 답변 불가 선언 | relevance < 임계값 → "관련 내용 없음" |
| 시스템 프롬프트 | "업로드된 문서 범위 내에서만 답변" |
| 프롬프트 가드 | 시스템 프롬프트 우회 시도 차단 |

### 4.5 재사용 코드 / 신규 파일

**재사용**: `ralph/parsers/` (문서 파서 4종), `rag/embedder.py`, `rag/chunker.py`, `rag/vector_store.py`, `rag/retriever.py`, `ralph/llm_client.py`

**신규 BE**: `vdr_chatbot.py`, `vdr_chatbot_service.py`, `vdr_indexer_service.py`, `vdr_chatbot_prompts.py`
**신규 FE**: `VdrChatPanel.tsx`, `useVdrChat.ts`

---

## 5. 차세대 AI 전략 로드맵

```
Phase 1 (단기: 1-2개월)
├── A. 딜 셋업 AI 에이전트 MVP
│   └── 자연어 + 엑셀 → Transaction + DD Checklist 자동 생성
└── 보안 기초 (프롬프트 가드, 입력 검증)

Phase 2 (중기: 2-3개월)
├── B. VDR 지식 챗봇
│   └── 딜별 문서 RAG 인덱싱 → 폐쇄형 Q&A
└── AI 사용량 대시보드 (비용/토큰 모니터링)

Phase 3 (장기: 3-6개월)
├── 크로스 딜 인텔리전스
│   └── 과거 딜 데이터 → 유사 딜 추천, 벤치마크
├── 민감정보 자동 마스킹
└── 관리자 AI 통제 대시보드
```

## 6. 구현 우선순위

| 순위 | 방향 | 이유 | 예상 규모 |
|------|------|------|----------|
| **1** | A: 딜 셋업 AI 에이전트 | 온보딩 효과 최대, 코드 재사용률 높음 | BE 4 + FE 2 파일 |
| **2** | B: VDR 지식 챗봇 | RAG 인프라 보유, 딜 관리 핵심 부가가치 | BE 4 + FE 2 파일 |
| **3** | C: 전략 로드맵 확장 | A/B 데이터 축적 후 크로스 딜 인텔리전스 | 문서 산출물 |
