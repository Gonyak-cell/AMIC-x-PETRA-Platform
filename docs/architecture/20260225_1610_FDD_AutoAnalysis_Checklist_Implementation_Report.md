# FDD 자동 분석 & 체크리스트 시스템 구현 보고서

> 작성: 2026-02-25 16:10
> Phase 1~6 전체 구현 완료 + 코드 리뷰 + 버그 수정

---

## 1. 개요

FDD (Financial Due Diligence) 모듈에 **자동 분석 파이프라인**과 **체크리스트 워크플로우**를 구현했다.

### 핵심 워크플로우
```
VDR 업로드 → 파일 인제스트 → COA 매핑 → 분석 엔진(QoE/NWC/Debt)
    → Report IR 생성 → 렌더러(PPTX/DOCX/XLSX/JSON)
    → 체크리스트 자동 생성 → 사용자 리뷰/수정 → Finalize → Refined Report
```

---

## 2. Phase 별 구현 내역

### Phase 1: 데이터 모델
- `FddChecklist`, `FddChecklistItem`, `ChecklistItemVdrLink` — 3개 ORM 모델
- `AnalysisRun` — 분석 실행 추적 모델
- 18개 `ChecklistCategory` enum (Revenue Recognition ~ Tax Compliance)
- 상태 머신: GENERATING → PENDING_REVIEW → REVIEWED → FINALIZED
- Alembic 마이그레이션 2개 (`011_fdd_checklist.py`, `012_analysis_runs.py`)

### Phase 2: 분석 오케스트레이터
- `AnalysisOrchestrator` — VDR 파일 기반 3대 엔진 순차 실행
- QoE 엔진: 수익 인식, 일회성 항목, 원가 비용 분석
- NWC 엔진: 운전자본, 유동성, 계절성 분석
- Debt 엔진: 차입금, 우발채무, 리스 분석
- 체크리스트 자동 생성 (엔진 결과 → 18개 카테고리)

### Phase 3: API 엔드포인트
- 분석 API: `POST /run`, `GET /runs`, `GET /runs/{id}`
- 체크리스트 API: `GET`, `GET /{id}`, `PUT /items/{id}`, `PUT /bulk-update`, `POST /finalize`, `GET /items/{id}/vdr-links`
- RBAC 권한 체크 (`require_permission`)

### Phase 4: Excel 렌더러 확장
- `_render_checklist_sheet()` — 체크리스트 시트 자동 생성
- 카테고리별 그룹핑, 상태/심각도 색상 코딩
- 요약 통계 (총 항목, 확인/수정/플래그 수)

### Phase 5: 프론트엔드 컴포넌트
- `ChecklistReviewPage` — 전체 체크리스트 리뷰 페이지
- `ChecklistSummaryBar` — 요약 통계 바
- `ChecklistCategorySection` — 카테고리별 섹션
- `ChecklistItemCard` — 개별 항목 카드 (상태 변경, 수정, VDR 링크)
- `VdrSourceLinks` — VDR 소스 링크 표시
- React Query 훅: `useChecklist`, `useUpdateChecklistItem`, `useFinalizeChecklist`, `useRunAnalysis`

### Phase 6: 통합 테스트
- `test_checklist.py` — 16개 테스트 (CRUD, 상태 머신, Finalize, Bulk)
- `test_analysis.py` — 11개 테스트 (오케스트레이터, 동시 실행 방지, 엔진)
- `test_excel_renderer.py` — 20개 테스트 (기본, 섹션별, 체크리스트 시트)
- **47/47 전체 통과**

---

## 3. 구현 중 발견/수정된 이슈

| # | 이슈 | 원인 | 수정 |
|---|------|------|------|
| 1 | SQLAlchemy `metadata` 예약어 충돌 | `FddChecklistItem.metadata` → Base 클래스 예약 속성 | `extra_metadata`로 rename + `Column("metadata")` |
| 2 | `Permission.DEAL_VIEW/DEAL_EDIT` 미존재 | API 코드에서 잘못된 enum 멤버 참조 | `DEAL_READ`/`DEAL_UPDATE`으로 수정 (9곳) |
| 3 | 테스트 401 Unauthorized | `auth_enabled` 기본값 True, .env 파일 부재 | `AUTH_ENABLED=false` 환경변수로 테스트 실행 |
| 4 | `user_amount` Decimal 형식 불일치 | `Numeric(18,4)` → `"5000000.0000"` 반환 | `startswith()` 단언으로 수정 |

---

## 4. 코드 리뷰 후 추가 수정 (P0~P1)

| # | 이슈 | 심각도 | 파일 | 수정 내용 |
|---|------|--------|------|----------|
| 1 | Excel 렌더러 checklist_data 구조 불일치 | P0 | `reports.py` | `checklist_data["items"]` 전달 |
| 2 | vdr-links IDOR 보안 취약점 | P0 | `checklist.py` | deal_id 소속 검증 추가 |
| 3 | 보고서 버전 API 권한 미적용 | P1 | `reports.py` | `require_permission()` 4곳 추가 |
| 4 | ReportPage checklist_id 미전달 | P1 | `ReportPage.tsx` | checklist 연동 + UI 토글 |
| 5 | ChecklistReviewPage 쿼리 무효화 누락 | Low | `ChecklistReviewPage.tsx` | `invalidateQueries` 추가 |

---

## 5. 파일 목록

### 신규 파일 (백엔드)
- `fdd/backend/app/models/fdd_checklist.py`
- `fdd/backend/app/models/analysis_run.py`
- `fdd/backend/app/schemas/fdd_checklist.py`
- `fdd/backend/app/services/analysis/orchestrator.py`
- `fdd/backend/app/services/analysis/engines/qoe_engine.py`
- `fdd/backend/app/services/analysis/engines/nwc_engine.py`
- `fdd/backend/app/services/analysis/engines/debt_engine.py`
- `fdd/backend/app/services/checklist_service.py`
- `fdd/backend/app/api/analysis.py`
- `fdd/backend/app/api/checklist.py`
- `fdd/backend/alembic/versions/011_fdd_checklist.py`
- `fdd/backend/alembic/versions/012_analysis_runs.py`
- `fdd/backend/tests/test_checklist.py`
- `fdd/backend/tests/test_analysis.py`
- `fdd/backend/tests/test_excel_renderer.py`

### 신규 파일 (프론트엔드)
- `amic-platform/src/modules/fdd/pages/ChecklistReviewPage.tsx`
- `amic-platform/src/modules/fdd/components/checklist/ChecklistSummaryBar.tsx`
- `amic-platform/src/modules/fdd/components/checklist/ChecklistCategorySection.tsx`
- `amic-platform/src/modules/fdd/components/checklist/ChecklistItemCard.tsx`
- `amic-platform/src/modules/fdd/components/checklist/VdrSourceLinks.tsx`
- `amic-platform/src/modules/fdd/hooks/useChecklist.ts`
- `amic-platform/src/modules/fdd/hooks/useAnalysis.ts`

### 수정 파일
- `fdd/backend/app/renderers/excel_renderer.py` — 체크리스트 시트 추가
- `fdd/backend/app/api/reports.py` — Excel 체크리스트 데이터 전달 + 권한 체크
- `fdd/backend/app/models/__init__.py` — 모델 import 추가
- `amic-platform/src/modules/fdd/pages/ReportPage.tsx` — checklist_id 전달

---

## 6. 테스트 실행 방법

```bash
cd fdd/backend
TESTING=true AUTH_ENABLED=false python -m pytest \
  tests/test_checklist.py \
  tests/test_analysis.py \
  tests/test_excel_renderer.py \
  -v
```

결과: **47/47 passed**
