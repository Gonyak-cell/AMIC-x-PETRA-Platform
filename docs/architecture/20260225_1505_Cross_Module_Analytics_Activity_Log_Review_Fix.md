# Cross-Module Analytics & Activity Log — 구현 리뷰 및 버그 수정 보고서

> **작성일**: 2026-02-25 15:05:00
> **세션**: Session 36 (이전 세션 연속)
> **브랜치**: `feat/ma-workflow`

---

## 1. 배경

### 이전 세션 (Session 35) 완료 작업

Cross-Module Analytics와 Activity Log가 전체 프로젝트의 실제 기능과 부합하지 않아 전면 개편을 수행함.

**백엔드 (4개 모듈 audit log 통합)**:
- `deal-mgmt/app/routers/audit.py` — MA 감사 로그 API (검색 + CSV 내보내기)
- `deal-mgmt/app/models/audit.py` — AuditLog 모델 + AuditAction enum
- `deal-mgmt/app/services/audit_service.py` — 감사 로그 서비스 계층
- `deal-mgmt/app/schemas/audit.py` — Pydantic 스키마
- `fdd/backend/app/routers/audit.py` — FDD 감사 로그 API
- `kiis/app/routers/audit.py` — KIIS 감사 로그 API
- `im/src/api/routes/audit.py` — IM 감사 로그 API
- 각 모듈 `main.py`에 라우터 등록

**프론트엔드 (Activity Log 전면 재작성)**:
- `amic-platform/src/hooks/useActivityLog.ts` — 4개 백엔드 통합 쿼리 (244줄)
- `amic-platform/src/types/activity.ts` — 통합 타입 정의
- Activity Log 관련 컴포넌트 전면 교체

### 현재 세션 (Session 36) 작업 범위

1. **useAnalytics.ts 확장** — Docs KPI 쿼리 + Pipeline Funnel 계산 추가
2. **Analytics 컴포넌트 업데이트** — FilterBar, ModuleKpiSection, ChartPanel, AnalyticsPage
3. **3-에이전트 병렬 리뷰** — 백엔드/프론트 Activity/프론트 Analytics 검증
4. **교차 검증 (수동)** — Agent 주장을 실제 코드 대조로 확인
5. **확인된 버그 수정** — P0 2건, P1 2건

---

## 2. 구현 완료 목록

### 2-1. Analytics 프론트엔드 확장

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/hooks/useAnalytics.ts` | DocsAnalytics 타입 추가, `docs-counts` 쿼리, Pipeline Funnel 계산 (`buildPipelineFunnel`), PHASE_ORDER/PHASE_LABELS 상수 |
| `amic-platform/src/components/analytics/AnalyticsFilterBar.tsx` | MODULES 배열에 `{ value: "docs", label: "Docs" }` 추가 |
| `amic-platform/src/components/analytics/ModuleKpiSection.tsx` | Docs KPI 섹션 추가 (Legal Documents, Marketing Materials, LDD Reports, Total Documents) |
| `amic-platform/src/components/analytics/AnalyticsChartPanel.tsx` | Pipeline Funnel 차트 추가 (7-phase 수평 막대 차트, FUNNEL_COLORS) |
| `amic-platform/src/pages/analytics/AnalyticsPage.tsx` | subtitle 업데이트, `pipelineFunnel` prop 전달 |

### 2-2. Activity Log (이전 세션 완료, 이번 세션 검증)

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/hooks/useActivityLog.ts` | 4개 백엔드 병렬 쿼리 (fdd/kiis/im/ma), 통합 정렬, 필터링 |
| `amic-platform/src/types/activity.ts` | UnifiedAuditEntry, AuditSource, ActivityFilter 타입 |

---

## 3. 리뷰 및 교차 검증

### 3-1. 리뷰 방법론

1. **3개 병렬 Explore 에이전트 실행**:
   - Agent 1: 백엔드 audit 코드 검증 (4개 모듈)
   - Agent 2: 프론트엔드 Activity Log 검증
   - Agent 3: 프론트엔드 Analytics 검증

2. **수동 교차 검증**:
   - 각 Agent 주장을 실제 소스코드 `Read`로 대조
   - 특히 Vite proxy rewrite 규칙을 핵심 기준으로 경로 검증

### 3-2. 핵심 발견: Vite Proxy Rewrite 규칙

```javascript
// amic-platform/vite.config.ts:64-83
"/api/fdd":  { rewrite: (path) => path.replace(/^\/api\/fdd/, "/api/v1") },  // → FDD (8000)
"/api/kiis": { rewrite: (path) => path.replace(/^\/api\/kiis/, "/api/v1") }, // → KIIS (8001)
"/api/im":   { rewrite: (path) => path.replace(/^\/api\/im/, "/api/v1") },   // → IM (8002)
"/api/ma":   { rewrite: (path) => path.replace(/^\/api\/ma/, "/api/v1") },   // → deal-mgmt (8003)
```

이 규칙이 모든 API 경로 검증의 기준점. Agent 허위 주장 4건 중 3건이 이 규칙을 고려하지 않은 오판.

### 3-3. Agent 허위 주장 (False Positive) — 4건 기각

| Agent | 주장 | 검증 결과 | 근거 |
|-------|------|-----------|------|
| Agent 2 | "KIIS AUDIT_PATH `/audit/audit-logs` 오류, `/api/v1/audit/audit-logs`로 수정 필요" | **❌ 허위** | Proxy가 `/api/kiis/audit/audit-logs` → `/api/v1/audit/audit-logs`로 rewrite. KIIS `main.py` `prefix="/api/v1/audit"` + route `"/audit-logs"` = `/api/v1/audit/audit-logs`. 경로 일치 |
| Agent 3 | "Card className prop 미지원 → 레이아웃 깨짐" | **❌ 허위** | `Card.tsx:16`에 `className?: string`, `:54`에 `cn(..., className)` 전달. 완벽 지원 |
| Agent 1 | "deal-mgmt audit 마이그레이션 누락" | **❌ 허위** | `001_initial_schema.py:159-183`에서 `audit_logs` 테이블 이미 생성 |
| Agent 1 | "deal-mgmt export 인증 누락" | **❌ 허위** | `audit.py:57`에 `claims: JWTClaims = Depends(get_jwt_claims)` 이미 존재 |

### 3-4. 확인된 실제 버그 — 4건

#### P0-1: IM audit 라우터 prefix 불일치 → 404

- **위치**: `im/src/api/routes/audit.py:18`
- **원인**: IM 라우터들은 자체 prefix에 `/api/v1` 포함 (예: `documents.py` → `prefix="/api/v1/documents"`). audit 라우터만 `prefix="/audit-logs"`로 설정되어, proxy rewrite 후 `/api/v1/audit-logs` → 백엔드의 `/audit-logs` 불일치
- **수정**: `prefix="/audit-logs"` → `prefix="/api/v1/audit-logs"`

#### P0-2: Docs KPI API 경로 미존재 → 항상 0 표시

- **위치**: `amic-platform/src/hooks/useAnalytics.ts:266-301`
- **원인**: 프론트엔드가 `maApi.get("/legal-documents")` 호출하지만, 백엔드 실제 경로는 `/transactions/{txn_id}/legal-documents` (트랜잭션 하위 리소스). 전역 리스팅 엔드포인트 없음. `.catch()` 핸들러로 크래시는 방지되나 KPI 항상 0
- **수정**:
  - 백엔드: `deal-mgmt/app/routers/dashboard.py`에 `GET /docs-stats` 엔드포인트 추가 (LegalDocument, MarketingMaterial, LDDReport 전역 카운팅)
  - 프론트: docs-counts 쿼리를 `/dashboard/docs-stats` 단일 호출로 교체

#### P1-1: deal-mgmt export 인증 누락 (Agent 주장 → 검증 결과 이미 존재)

- **위치**: `deal-mgmt/app/routers/audit.py:57`
- **결론**: `claims: JWTClaims = Depends(get_jwt_claims)` 이미 존재. **수정 불필요 (False Positive)**

#### P1-2: KIIS/IM audit 모델 created_at 타입 힌트 오류

- **위치**: `kiis/app/models/audit.py:37`, `im/src/api/db/models/audit.py:37`
- **원인**: `created_at: Mapped[str]` → 실제 컬럼은 `DateTime(timezone=True)`. 런타임 동작에는 영향 없으나 타입 안전성 위반
- **수정**: `from datetime import datetime` 추가 + `Mapped[datetime]`으로 변경

---

## 4. 수정 상세

### 4-1. `im/src/api/routes/audit.py` (P0-1)

```python
# Before
router = APIRouter(prefix="/audit-logs", tags=["Audit"])

# After
router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit"])
```

### 4-2. `deal-mgmt/app/routers/dashboard.py` (P0-2 백엔드)

```python
# 추가된 import
from app.models.ldd_report import LDDReport
from app.models.legal_document import LegalDocument
from app.models.marketing_material import MarketingMaterial

# 추가된 엔드포인트
@router.get("/docs-stats")
async def get_docs_stats(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """Deal Document Studio 전체 문서 통계."""
    legal = await db.scalar(select(func.count()).select_from(LegalDocument))
    marketing = await db.scalar(select(func.count()).select_from(MarketingMaterial))
    ldd = await db.scalar(select(func.count()).select_from(LDDReport))
    return {
        "total_legal": legal or 0,
        "total_marketing": marketing or 0,
        "total_ldd": ldd or 0,
    }
```

### 4-3. `amic-platform/src/hooks/useAnalytics.ts` (P0-2 프론트)

```typescript
// Before: 3개 존재하지 않는 엔드포인트 병렬 호출
const [legal, marketing, ldd] = await Promise.all([
  maApi.get("/legal-documents", ...).catch(...),
  maApi.get("/marketing-materials", ...).catch(...),
  maApi.get("/ldd-reports", ...).catch(...),
]);

// After: 단일 전역 카운팅 엔드포인트 호출
const { data } = await maApi.get<{
  total_legal: number;
  total_marketing: number;
  total_ldd: number;
}>("/dashboard/docs-stats");
return {
  totalLegal: data.total_legal,
  totalMarketing: data.total_marketing,
  totalLdd: data.total_ldd,
};
```

### 4-4. `kiis/app/models/audit.py` + `im/src/api/db/models/audit.py` (P1-2)

```python
# Before
created_at: Mapped[str] = mapped_column(
    DateTime(timezone=True), server_default=func.now()
)

# After
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now()
)
```

---

## 5. 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| `tsc --noEmit` | 통과 (타입 에러 0) |
| `vite build` | 통과 (22.7초, 3070 모듈) |
| Agent 허위 주장 기각 | 4건 모두 코드 대조로 확인 |
| 수정 범위 최소화 | 확인된 원인의 정확한 위치만 수정 |

---

## 6. API 경로 전체 검증 매트릭스

### Activity Log (useActivityLog.ts)

| 모듈 | 프론트 호출 | Proxy 후 | 백엔드 라우트 | 상태 |
|------|-----------|---------|-------------|------|
| FDD | `api.get("/audit-logs")` | `/api/v1/audit-logs` | `main.py prefix="/api/v1"` + `router(tags=["Audit"])` → `/api/v1/audit-logs` | ✅ |
| KIIS | `kiisApi.get("/audit/audit-logs")` | `/api/v1/audit/audit-logs` | `main.py prefix="/api/v1/audit"` + `route "/audit-logs"` → `/api/v1/audit/audit-logs` | ✅ |
| IM | `imApi.get("/audit-logs")` | `/api/v1/audit-logs` | `router prefix="/api/v1/audit-logs"` → `/api/v1/audit-logs` | ✅ (수정 후) |
| MA | `maApi.get("/audit-logs")` | `/api/v1/audit-logs` | `main.py prefix="/api/v1"` + `router(tags=["Audit"])` → `/api/v1/audit-logs` | ✅ |

### Analytics KPI

| 쿼리 | 프론트 호출 | Proxy 후 | 백엔드 라우트 | 상태 |
|------|-----------|---------|-------------|------|
| FDD deals | `api.get("/deals")` | `/api/v1/deals` | FDD `/api/v1/deals` | ✅ |
| KIIS summary | `kiisApi.get("/dashboard/summary")` | `/api/v1/dashboard/summary` | KIIS `/api/v1/dashboard/summary` | ✅ |
| IM documents | `imApi.get("/documents")` | `/api/v1/documents` | IM `/api/v1/documents` | ✅ |
| MA stats | `maApi.get("/dashboard/stats")` | `/api/v1/dashboard/stats` | deal-mgmt `/api/v1/dashboard/stats` | ✅ |
| Docs counts | `maApi.get("/dashboard/docs-stats")` | `/api/v1/dashboard/docs-stats` | deal-mgmt `/api/v1/dashboard/docs-stats` | ✅ (신규) |

---

## 7. 변경 파일 목록

| 파일 | 변경 유형 | 줄 수 |
|------|----------|------|
| `im/src/api/routes/audit.py` | 수정 | 1줄 |
| `deal-mgmt/app/routers/dashboard.py` | 추가 | ~20줄 |
| `amic-platform/src/hooks/useAnalytics.ts` | 수정 | ~15줄 |
| `kiis/app/models/audit.py` | 수정 | 2줄 |
| `im/src/api/db/models/audit.py` | 수정 | 2줄 |
| `amic-platform/src/components/analytics/AnalyticsFilterBar.tsx` | 추가 | 1줄 |
| `amic-platform/src/components/analytics/ModuleKpiSection.tsx` | 추가 | ~40줄 |
| `amic-platform/src/components/analytics/AnalyticsChartPanel.tsx` | 추가 | ~30줄 |
| `amic-platform/src/pages/analytics/AnalyticsPage.tsx` | 수정 | 2줄 |
