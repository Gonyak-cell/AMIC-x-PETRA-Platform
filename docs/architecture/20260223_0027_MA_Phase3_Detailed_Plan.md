# MA Phase 3 상세 기획서

> 작성: 2026-02-23 00:27
> 기준 브랜치: `feat/ma-workflow`
> 참조: `docs/architecture/20260219_0210_MA_Phase3_Phase4_Remaining_Tasks.md`

---

## 1. 현재 구현 상태

### 완료된 항목 (Phase 0~2 + Phase 3 기반)

| 계층 | 항목 | 상태 |
|------|------|------|
| **백엔드 모델** | Contract, ContractVersion, ClosingChecklist | ✅ 완료 |
| **백엔드 Schema** | ContractOut/Create/Update, AIAnalysisResult, ClosingChecklistOut/Create/Update | ✅ 완료 |
| **백엔드 라우터** | contracts.py (8 EP), closing.py (5 EP) | ✅ 완료 |
| **마이그레이션** | 003_phase3_contracts_closing | ✅ 완료 |
| **프론트엔드 타입** | contract.ts, closing.ts | ✅ 완료 |
| **프론트엔드 훅** | useContracts (6훅), useClosing (5훅) | ✅ 완료 |
| **UI 탭** | contracts, closing 탭 (KPI + DataTable + 필터) | ✅ 완료 |
| **SPA 버전 관리** | ContractVersion 모델 + 버전 자동 증가 + 히스토리 API | ✅ 완료 |

### 미완료 항목 (Phase 3 잔여)

| 기능 | 현재 상태 | 구현 필요 | 복잡도 |
|------|-----------|-----------|--------|
| **AI 계약 분석** | MVP Stub (메시지만 반환) | LLM API 연동 + 문서 처리 | 🔴 HIGH |
| **전자서명 (DocuSign)** | 수동 상태 변경만 가능 | DocuSign API 통합 + 웹훅 | 🔴 HIGH |
| **Closing 자동 생성** | 수동 추가만 가능 | 거래 생성 시 표준 항목 자동 생성 | 🟢 LOW |

---

## 2. AI 계약 분석 구현 전략

### 2.1 현재 상태

```python
# deal-mgmt/app/services/contract_analysis_service.py
async def analyze_contract(contract_id, document_url) -> AIAnalysisResult:
    return AIAnalysisResult(status="PENDING", message="향후 업데이트에서 제공", clauses=[])
```

- API 엔드포인트: `POST /contracts/{id}/analyze` ✅
- DB 필드: `ai_analysis_summary` (Text), `ai_risk_flags` (JSONB) ✅
- 결과 스키마: `AIAnalysisResult`, `AIRiskFlag` ✅

### 2.2 구현 계획

**LLM 선택**: Claude 3.5 Sonnet (비용 효율적, 한국어 계약서 지원)

**파이프라인**:
```
1. document_url에서 계약서 다운로드 (S3/HTTP)
2. PDF → 텍스트 추출 (PyPDF2 또는 pdfplumber)
3. Claude API 호출 — 구조화된 분석 프롬프트
   - 핵심 조항 식별 (가격, 진술보증, 손해배상, 해제조건)
   - 리스크 플래깅 (비표준 조항, 누락 조항, 모호한 표현)
   - M&A SPA 체크리스트 대비 완성도 평가
4. 응답 파싱 → AIAnalysisResult 변환
5. DB 저장 (contract.ai_analysis_summary, contract.ai_risk_flags)
```

**신규 파일**:
- `deal-mgmt/app/services/llm_client.py` — Claude/OpenAI 통합 클라이언트
- `deal-mgmt/app/services/document_processor.py` — PDF 추출 유틸

**환경변수**:
```env
ANTHROPIC_API_KEY=sk-ant-...
AI_ANALYSIS_MODEL=claude-3-5-sonnet-20241022
AI_ANALYSIS_MAX_TOKENS=4096
```

**비동기 처리**: 분석이 5~30초 소요되므로:
- 옵션 A: 동기 처리 (timeout 60초) — 간단, 현재 라우터 구조 유지
- 옵션 B: Celery 비동기 + 폴링 — IM 모듈과 동일 패턴
- **권장**: 옵션 A (Phase 3는 단순하게 시작, 필요 시 B로 전환)

### 2.3 프롬프트 설계 (초안)

```
당신은 M&A 법률 전문가입니다. 다음 SPA(주식매매계약서)를 분석하세요.

분석 항목:
1. 핵심 조항 요약 (가격 조정, 진술보증, 손해배상, 선행조건)
2. 리스크 플래깅 (비표준 조항, 누락 사항, 매수자/매도자 불리 조항)
3. 완성도 평가 (표준 SPA 대비 %)

JSON 형식으로 응답:
{
  "status": "COMPLETED",
  "message": "분석 완료",
  "clauses": [
    { "clause": "가격 조정", "risk_level": "LOW", "description": "..." },
    ...
  ]
}
```

---

## 3. 전자서명 (DocuSign) 통합 전략

### 3.1 아키텍처

```
프론트엔드                        백엔드                         DocuSign
────────                        ──────                         ────────
[서명 요청 버튼] → POST /contracts/{id}/signature-request
                                → DocuSign API: Envelope 생성
                                  → signers: [seller, buyer]
                                  → document: contract PDF
                                ← envelope_id 반환
                                → contract.docusign_envelope_id 저장

                                ← DocuSign Webhook: envelope.completed
                                → signature_status 자동 업데이트
                                → audit_service 기록
```

### 3.2 필요 작업

**백엔드**:
1. `deal-mgmt/app/services/docusign_client.py` — DocuSign eSignature API 클라이언트
   - Envelope 생성 (문서 + 서명자 지정)
   - 서명 URL 생성 (embedded signing)
   - Envelope 상태 조회
2. 신규 라우터 엔드포인트:
   - `POST /contracts/{id}/signature-request` — 서명 요청 발송
   - `POST /webhooks/docusign` — DocuSign 완료 콜백 수신
3. Contract 모델 확장:
   - `docusign_envelope_id` (String, nullable) 필드 추가
   - 마이그레이션 추가 필요

**프론트엔드**:
1. 계약/SPA 탭에 "서명 요청" 버튼 추가
2. 서명 상태 실시간 반영 (polling 또는 React Query invalidation)

**환경변수**:
```env
DOCUSIGN_INTEGRATION_KEY=xxx
DOCUSIGN_SECRET_KEY=xxx
DOCUSIGN_ACCOUNT_ID=xxx
DOCUSIGN_BASE_URL=https://demo.docusign.net/restapi  # 또는 production
DOCUSIGN_WEBHOOK_SECRET=xxx
```

### 3.3 대안 검토

DocuSign 계정이 없는 경우의 대안:
- **Phase 3a**: 수동 서명 상태 관리 유지 (현재)
- **Phase 3b**: DocuSign 통합 (계정 확보 후)

---

## 4. Closing 체크리스트 자동 생성

### 4.1 구현 계획

거래 생성 시(`POST /transactions`) 표준 Closing 체크리스트를 자동 삽입.

**표준 체크리스트 (7개 카테고리별 기본 항목)**:

| 카테고리 | 기본 항목 |
|----------|----------|
| REGULATORY | 공정거래위원회 기업결합 신고, 금융위원회 승인 |
| LEGAL | 법률 의견서 (매도측/매수측), 이사회 결의 |
| FINANCIAL | 에스크로 계좌 개설, 가격 조정 계산서 |
| CORPORATE | 주주명부 이전, 임원 교체 |
| CONDITION_PRECEDENT | MAC 조항 미발생 확인, 진술보증 재확인 |
| FUND_FLOW | 자금 이체 스케줄, 은행 확인서 |
| OTHER | 직원 통보, 언론 보도 자료 |

**구현 위치**: `deal-mgmt/app/services/closing_service.py` (신규)
```python
async def create_default_checklist(db, transaction_id):
    for category, items in DEFAULT_CHECKLIST.items():
        for i, title in enumerate(items):
            item = ClosingChecklist(
                transaction_id=transaction_id,
                category=category,
                title=title,
                status="PENDING",
                sort_order=i,
            )
            db.add(item)
```

**연동**: `transactions.py` 라우터의 거래 생성 로직에서 호출

---

## 5. 실행 로드맵

| 순서 | 작업 | 예상 기간 | 외부 의존 |
|------|------|----------|----------|
| 1 | Closing 자동 생성 | 0.5일 | 없음 |
| 2 | AI 계약 분석 (LLM 연동) | 2~3일 | Anthropic API 키 |
| 3 | DocuSign 통합 | 3~4일 | DocuSign 계정 + API 키 |
| 4 | 통합 테스트 | 1~2일 | 없음 |

**총 예상**: 7~10일 (외부 의존 확보 후)

---

## 6. 외부 의존 체크리스트

- [ ] Anthropic API 키 (AI 계약 분석용) — `.env`에 `ANTHROPIC_API_KEY`
- [ ] DocuSign 개발자 계정 + API 키 — 4개 환경변수
- [ ] 문서 저장소 (S3/GCS) 설정 — 계약서 PDF 업로드/다운로드
- [ ] PDF 처리 라이브러리 추가 — `pip install pdfplumber` (or PyPDF2)
