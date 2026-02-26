# FDD 보고서 생성기 — 로컬 vs Azure 배포 비교 분석 리포트

> 2026-02-26 12:32 작성

## 1. 개요

FDD 보고서 생성기의 로컬 코드와 Azure 프로덕션 배포 간 기능 일치 여부를 점검하고, 에이전트 보고의 허위 여부까지 검증한 리포트.

## 2. 보고서 생성 파이프라인

### 전체 플로우
```
API 요청 → build_report_ir() → [Ralph Loop] → [QA Agent] → 포맷 렌더링 → 다운로드
```

### 핵심 수치
- **15개 include 플래그** (report_service.py:1434-1451)
- **18개+ 섹션 그룹**: Cover → Scope → KPI → QoE → NWC → Debt → FS → Multiperiod → Revenue Deepdive → Trends → Sales/Cost → Cost Structure → FCF/CAPEX → Backlog → Consolidation → Korea Overlay → Issues → Narratives → Methodology → Reconciliation
- **13개 분석 엔진**: qoe, nwc, debt, anomaly, delta, multiperiod, revenue, cost, fcf, backlog, qualitative, consolidation
- **10가지 BlockType**: cover, kpi, table, chart, text, claim, issue, methodology, scope, appendix
- **4가지 출력 포맷**: JSON, DOCX, XLSX, PPTX

### 고급 기능
- **Ralph Loop**: 2-pass LLM 기반 품질 개선 (Draft → Final)
- **QA Agent**: 독립 LLM 팩트체크
- **Template SlotFill**: 구조화된 내러티브 자동 생성
- **Industry Context**: 산업별 KPI 벤치마크 + Korea Overlay (K-IFRS, 규제, 세무)

## 3. 기능 일치/불일치 매트릭스

### 엔드포인트별 동작 상태

| 엔드포인트 | 로컬 | Azure Docker | 상태 |
|-----------|------|-------------|------|
| `POST /generate` format=json | OK | OK | MATCH |
| `POST /generate` format=docx | OK | OK | MATCH |
| `POST /generate` format=xlsx | OK | OK | MATCH |
| `POST /generate` format=pptx | OK | **FAIL** | **BUG-1 (수정 완료)** |
| `POST /generate-word` | OK | OK | MATCH |
| `GET /preview` | OK | OK | MATCH |
| `GET /ir` | OK | OK | MATCH |
| `POST /versions` format=pptx | OK | **FAIL** | **BUG-1 (수정 완료)** |
| `GET /versions/{v}/download` | OK | OK | MATCH |

### pptx-service 블록 렌더러 (10/10 완전 구현)

| BlockType | 렌더러 함수 | PPTX | DOCX | XLSX |
|-----------|-----------|------|------|------|
| cover | `renderCoverSlide()` | O | O | - |
| kpi | `renderKPISlide()` | O | O | O |
| table | `renderTableSlide()` (오버플로우 분할) | O | O | O |
| chart | `renderChartSlide()` (bar/line/pie + base64) | O | O | O |
| text | `renderTextSlide()` (risk badge) | O | O | O |
| claim | `renderClaimSlide()` (verified + evidence) | O | O | O |
| issue | `renderIssueSlide()` (severity 색상) | O | O | O |
| methodology | `renderMethodologySlide()` | O | O | - |
| scope | `renderScopeSlide()` | O | O | - |
| appendix | `renderAppendixSlide()` | O | O | - |

## 4. 발견된 버그 및 수정

### BUG-1 (P0-CRITICAL): pptx_service_url 미전달 — Docker PPTX 100% 실패

**원인**:
- `generate_pptx()` 함수의 기본값이 `"http://localhost:3100"` 하드코딩
- 호출자가 `settings.pptx_service_url`을 전달하지 않음
- Docker 환경에서 `localhost`는 fdd-api 컨테이너 자신 → ConnectionRefusedError

**수정 (완료)**:
- `reports.py:15` — `from app.config import settings` 추가
- `reports.py:199` — `generate_pptx(report_ir, pptx_service_url=settings.pptx_service_url)`
- `reports.py:466` — 동일 수정 (버전 생성 경로)

### BUG-2 (P2-MEDIUM): Include 플래그 API 미노출

**원인**: `ReportGenerateRequest`에 7개 필드만 정의, `build_report_ir()`의 15개 파라미터 중 8개 미노출

**수정 (완료)**:
- `schemas/report.py` — 8개 필드 추가 (multiperiod, revenue_deepdive, cost_structure, fcf, backlog, consolidation_enhanced, use_llm_narratives, use_template_slotfill)
- `reports.py:69-76` — `build_report_ir()` 호출에 새 필드 전달

## 5. 에이전트 허위 보고

### 보고 내용
> "pptx-service POST /render가 501 Not Implemented 스텁 상태"

### 실제 상태
`fdd/pptx-service/src/index.ts:1249-1282`에 POST /render **완전 구현** (10가지 블록 렌더러, 1306줄)

### 원인
`fdd/pptx-service/CLAUDE.md:12`에 오래된 문구 잔존:
```
POST /render — returns 501 (stub)
DO NOT implement /render until Sprint 7
```
에이전트가 코드 대신 CLAUDE.md를 신뢰하여 허위 보고 생성.

### 수정 (완료)
`fdd/pptx-service/CLAUDE.md` 전체 재작성 — 실제 구현 상태 반영

## 6. Auto FDD vs 모노레포 FDD

| 항목 | Auto FDD | 모노레포 FDD |
|------|---------|------------|
| Python 파일 | 308개 | 390개 (+82) |
| 마이그레이션 | 12개 | 18개 (+6) |
| API 라우터 | 26개 | 29개 (+3) |
| 렌더러 | 5개 | 7개 (+2) |
| 테스트 | 77개 | 96개 (+19) |

**결론**: 모노레포 FDD가 상위 집합. Auto FDD 아카이브 권장 기록 **정확**.

## 7. 설계 장점

1. **IR 패턴**: Engine → Report IR → Renderer 분리
2. **Pure Engine**: 모든 엔진이 순수 함수 (부작용 없음)
3. **선택적 섹션**: include 플래그로 모듈식 구성
4. **4중 렌더러**: PPTX/DOCX/XLSX/JSON
5. **3중 AI**: Ralph Loop + QA Agent + SlotFill
6. **산업 컨텍스트**: 산업별 KPI + K-IFRS/규제/세무 오버레이
7. **버전 관리**: DRAFT → FINAL + 감사 로그
8. **테이블 오버플로우**: 슬라이드 자동 분할

## 8. 수정된 파일

| 파일 | 변경 내용 |
|------|---------|
| `fdd/backend/app/api/reports.py` | P0: settings.pptx_service_url 전달 + P2: 8개 include 전달 |
| `fdd/backend/app/schemas/report.py` | P2: 8개 include 필드 추가 |
| `fdd/pptx-service/CLAUDE.md` | P1: 오래된 "501 stub" → 실제 구현 상태 반영 |
