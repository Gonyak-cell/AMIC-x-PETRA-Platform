# FDD 모듈 전체 리뷰 작업 내역 통합

> 최종 업데이트: 2026-02-25 20:54:00
> 대상: FDD 백엔드 + 프론트엔드 전체 리뷰/수정 이력 (2026-02-17 ~ 2026-02-25)
> 총 리뷰 건수: 8건 (Critical 4 + Major 5 + Moderate 6 + Minor 3)

---

## 요약 통계

| 지표 | 값 |
|------|-----|
| 총 발견 이슈 | 32건 |
| 수정 완료 | 29건 |
| 허위 양성(False Positive) | 3건 (#3, #4, #9 — 자동 분석 리뷰) |
| 후속 개선 보류 | 3건 (Moderate 이하) |
| 수정 파일 수 (백엔드) | ~40파일 |
| 수정 파일 수 (프론트엔드) | ~12파일 |
| 테스트 최종 상태 | **1439 passed, 0 failed** |
| TypeScript 빌드 | **tsc --noEmit + vite build 통과** |

---

## 리뷰 1: FDD Deal 생성 500 에러 수정 + 폼 리디자인

> 날짜: 2026-02-17 21:40
> 카테고리: bugfix (Critical)
> 문서: `review/bugfix/20260217_2142_FDD_Deal_Creation_500_Fix.md`

### 근본 원인

`IndustryType` enum의 name(대문자 `TECH_SAAS`)과 value(소문자 `tech`)가 불일치. SQLAlchemy가 name을 DB에 전송 → PostgreSQL ENUM 거부 → 500 에러.

### 수정 내역 (7건)

| # | 수정 | 파일 |
|---|------|------|
| 1 | `values_callable` 추가 — `.value` 사용 강제 | `app/models/deal.py:96-103` |
| 2 | 새 Enum 3종 (`DealStructure`, `InvestmentType`, `SellerType`) | `app/models/deal.py:54-83` |
| 3 | Deal 모델 컬럼 추가 + 날짜 nullable 변경 | `app/models/deal.py` |
| 4 | Pydantic 스키마 수정 (새 필드 + Optional) | `app/schemas/deal.py` |
| 5 | API _UPDATABLE_FIELDS 업데이트 | `app/api/deals.py:106-113` |
| 6 | Alembic 마이그레이션 012 | `alembic/versions/012_*.py` |
| 7 | 프론트엔드 타입 + 상수 + 폼 리디자인 | `types/deal.ts`, `constants.ts`, `DealListPage.tsx` |

---

## 리뷰 2: FDD 딜 생성 폼 리디자인

> 날짜: 2026-02-17 21:53
> 카테고리: UI/UX (P2)
> 문서: `review/ui/20260217_2154_FDD_Deal_Form_Redesign.md`

### 변경 요약

- **필수/선택 분리**: 딜 이름 + 대상회사명만 필수, 나머지 접이식
- **"선택 안함" 기본값**: 모든 Select 옵션 배열에 `{ value: "", label: "선택 안함" }` 추가
- **Docker HMR**: `vite.config.ts`에 `usePolling: true`, `host: true` 추가

### 수정 파일

| 파일 | 변경 |
|------|------|
| `DealListPage.tsx` | 폼 구조 리디자인 (필수/접이식) |
| `constants.ts` | 5개 Select 옵션에 "선택 안함" 추가 |
| `vite.config.ts` | Docker HMR 수정 |

---

## 리뷰 3: FDD industry 타입 단언 제거

> 날짜: 2026-02-23 12:15
> 카테고리: type (Moderate/P2)
> 문서: `review/type/20260223_1215_FDD_industry_type_assertion.md`

### 문제

`useFDDDocuments.ts:30`에서 `industry: body.industry as Deal["industry"]` 타입 단언 → 런타임 안전성 미보장.

### 수정

```typescript
// Before
industry: body.industry as Deal["industry"],
// After
industry: body.industry && isIndustryId(body.industry) ? body.industry : undefined,
```

기존 `isIndustryId()` 타입 가드 재사용으로 런타임 검증 추가.

---

## 리뷰 4: FDD → DD/Checklist 탭 연동

> 날짜: 2026-02-24 15:39
> 카테고리: UI (P3)
> 문서: `review/ui/20260224_1539_FDD_DD_Report_Integration.md`

### 문제

DD/Checklist 탭의 FDD 카드가 `available: false` → "COMING SOON" 표시. FDD 모듈은 이미 완성 상태.

### 수정 내역

| # | 수정 | 파일 |
|---|------|------|
| 1 | FDD `available` → `true`, view 분기 추가 | `DDReportSection.tsx` |
| 2 | **신규** `FDDReportsTab.tsx` 컴포넌트 | `modules/ma/components/FDDReportsTab.tsx` |

FDDReportsTab: `fdd_deal_id` 연결 여부에 따라 빈 상태 / 보고서 버전 목록+KPI 표시.

---

## 리뷰 5: FDD 자동 분석 & 체크리스트 전체 코드 리뷰

> 날짜: 2026-02-25 16:10
> 카테고리: review (P0~P2)
> 문서: `review/review/20260225_1610_FDD_AutoAnalysis_Checklist_Code_Review.md`

### 발견 이슈 10건 → 수정 5건 + 허위 양성 3건 + 후속 2건

| # | 문제 | 판정 | 심각도 | 상태 |
|---|------|------|--------|------|
| 1 | `build_refined_report_ir()` 미구현 | PARTIAL | Medium | 향후 Phase |
| 2 | **Excel 렌더러 checklist_data dict vs list[dict]** | **TRUE** | **P0** | **✅ 수정** |
| 3 | ChecklistRead 계산 필드가 항상 0 | FALSE (허위) | — | — |
| 4 | VdrLinkRead upload_filename DB 부재 | FALSE (허위) | — | — |
| 5 | **vdr-links IDOR 보안 취약점** | **TRUE** | **P0** | **✅ 수정** |
| 6 | **보고서 버전 API 권한 체크 부재** | **TRUE** | **P1** | **✅ 수정** |
| 7 | **ReportPage checklist_id 미전달** | **TRUE** | **P1** | **✅ 수정** |
| 8 | ChecklistReviewPage 쿼리 무효화 누락 | PARTIAL | Low | **✅ 수정** |
| 9 | ChecklistItemCard correction 유실 | FALSE (허위) | — | — |
| 10 | test_excel_renderer 포맷 불일치 | TRUE | Medium | #2 수정으로 해결 |

### 허위 양성 분석

- **#3**: `**summary` unpacking으로 계산 필드 정상 주입 — Pydantic `default=0`은 fallback
- **#4**: 의도적 확장 필드 (`Optional[str] = None`) — 향후 VDR 조인용
- **#9**: 로컬 state `correction/amount`가 `onUpdate()`에 정상 전달

### 핵심 수정

1. **P0 Excel 렌더러**: `checklist_data["items"]` 추출 후 전달
2. **P0 IDOR**: `item.checklist.deal_id != deal_id` 검증 추가
3. **P1 권한**: 4개 버전 엔드포인트에 `require_permission()` 적용
4. **P1 checklist_id**: ReportPage에 FINALIZED 체크리스트 토글 + body 전달

---

## 리뷰 6: FDD Ralph Loop 2-Pass 코드 리뷰

> 날짜: 2026-02-25 17:50
> 카테고리: review (Critical+Medium)
> 문서: `review/review/20260225_1750_FDD_Ralph_Loop_Code_Review.md`

### 리뷰 범위

| 영역 | 파일 수 |
|------|--------|
| 코어 모듈 (ralph/) | 10 |
| API/스키마/서비스 | 4 |
| DB 모델/마이그레이션 | 2 |
| 프론트엔드 훅/타입 | 2 |
| 테스트 | 3 (39 tests) |

### 정상 확인 항목 (13개 영역)

코어 포팅 정합성, DocumentGenerator Protocol, Convergence 5개 종료 조건, Gate 1 (5차원 가중치 합 1.0), Gate 2 (6차원 가중치 합 1.0), Learning 모듈, PRD JSON, DB 모델↔마이그레이션, API URL↔FE 훅, 스키마↔FE 타입, 서비스→Orchestrator 통합, import 경로, LoopStatus StrEnum

### 발견 버그 3건 → 전체 수정 완료

| # | 문제 | 심각도 | 수정 |
|---|------|--------|------|
| BUG-1 | **Refined IR이 docx/xlsx/pptx에 미적용** | Critical | `_patch_report_ir()` 함수 추가 |
| BUG-2 | 테스트 픽스처 `"body"` → `"content"` 불일치 | Medium | 4곳 필드명 수정 |
| MINOR-1 | mock 반환값도 `"body"` 사용 | Low | 2곳 수정 |

### 핵심 수정: `_patch_report_ir()`

```python
# reports.py:79-81
if ir_dict:
    _patch_report_ir(report_ir, ir_dict)
```

Ralph refined IR dict의 텍스트 필드를 원본 ReportIR 객체에 in-place 패치:
- `TextBlock`: `content`, `bullet_points`
- `ClaimBlock`: `claim_text`
- `IssueBlock`: 각 issue의 `description`, `recommendation`

---

## 리뷰 7: FDD 테스트 스위트 70건 실패 수정

> 날짜: 2026-02-25 18:23
> 카테고리: bugfix (Medium)
> 문서: `review/bugfix/20260225_1823_FDD_Test_Suite_70_Failures_Fix.md`

### 결과: 70건 실패 → **0 failed, 1439 passed**

### Phase 1: `target_company_name` 필수 필드 누락 (63건)

6개 테스트 파일의 SAMPLE_DEAL에 `"target_company_name"` 필드 추가:

| 파일 | 추가 값 |
|------|---------|
| `test_uploads.py` | `"Upload Test Corp"` |
| `test_deals.py` | `"Alpha Corp"` |
| `test_vdr.py` | `"VDR Test Corp"` |
| `test_api_entities.py` | `"Entity Test Corp"` |
| `test_api_exchange_rates.py` | `"FX Rate Test Corp"` |
| `security/conftest.py` | `"Security Test Corp"` |

### Phase 2: 코드 진화에 따른 테스트 갱신 (7건)

| # | 파일 | 원인 | 수정 |
|---|------|------|------|
| 1 | `test_deals.py` | 페이지네이션 응답 구조 변경 | `len(resp.json())` → `len(resp.json()["items"])` |
| 2 | `test_auth_api.py` | httpOnly 쿠키 전환 | body 토큰 → 쿠키+메시지 검증 |
| 3 | `test_auth_api.py` | refresh 쿠키 기반 전환 | JSON body → TestClient 쿠키 |
| 4 | `test_password.py` | bcrypt 전환 | SHA-256 → `$2b$` 검증 |
| 5 | `test_rbac.py` | VIEWER 권한 확장 | 기대값 set에 2개 추가 |
| 6 | `test_job_api.py` | 필수 필드 누락 | `target_company_name` + `base_currency` 추가 |
| 7 | `test_industries_api.py` | ORM 날짜 타입 불일치 | 문자열 → `date()` 객체 |

---

## 리뷰 8: FDD 보고서 품질 개선 (Excel/Ralph Gate/스키마)

> 날짜: 2026-02-25 20:54
> 카테고리: review (Critical 1 + Major 2 + Moderate 3 + Minor 1)
> 대상: P0~P2 + 잔여 3건 수정 전체 검증

### 변경 범위

| 파일 | 수정 항목 | 라인 수 |
|------|----------|--------|
| `report_service.py` | NWC 속성 수정, `_derive_cash_flow` enum 전환 | ~1500 |
| `report.py` (스키마) | 3개 신규 파라미터 | 70 |
| `excel_renderer.py` | `_auto_row_height` + 차트 연결 + import 정리 | 1084 |
| `excel_charts.py` | DataPoint 버그 수정 + import 정리 | 215 |
| `report_builder.py` | 빈 리스트 가드 + 11개 신규 빌더 | ~1550 |
| `fdd_programmatic_gate.py` | 7차원 게이트 (소계검증+산업별계정) | 493 |
| `fdd_report.json` (PRD) | PRD 스펙 확장 | 145 |

### 최초 계획 대비 구현 검증: **12/12 (100%)**

| # | 항목 | 상태 |
|---|------|------|
| 1 | waterfall DataPoint (P0) | ✅ `excel_charts.py:92` |
| 2 | 미사용 import (P0) | ✅ 3개 import 제거 |
| 3 | PrintPageSetup (P0) | ✅ import 제거 확인 |
| 4 | `total_nwc`→`net_working_capital` (P1) | ✅ `report_service.py:887,1158,1285` |
| 5 | `peg_scenarios` 가드 (P1) | ✅ `report_service.py:1000,1290` |
| 6 | 빈 리스트 가드 (P1) | ✅ `report_builder.py` 4함수 |
| 7 | 스키마 3개 파라미터 (P2) | ✅ 스키마 + API 핸들러 5곳 전달 |
| 8 | `_derive_cash_flow` enum (P2) | ✅ `report_service.py:254,256,279` |
| 9 | 차트→시트 연결 (P2) | ✅ `excel_renderer.py` 3곳 |
| 10 | 행 높이 자동 조정 | ✅ `excel_renderer.py:169-225` |
| 11 | Ralph Gate 합계 검증 | ✅ `fdd_programmatic_gate.py:346-361` |
| 12 | Ralph Gate 산업별 계정 | ✅ `fdd_programmatic_gate.py:365-456` |

### 이슈 목록 (7건)

| # | 이슈 | 심각도 | 신뢰도 | 상태 |
|---|------|--------|--------|------|
| 1 | reports.py 신규 3개 파라미터 미전달 | **Critical** | HIGH | **✅ 수정 완료** |
| 2 | 산업별 계정 substring 매칭 오류 | **Major** | HIGH | **✅ 수정 완료** |
| 3 | `_auto_row_height` 한글 전각 너비 미반영 | **Major** | MEDIUM | **✅ 수정 완료** |
| 4 | 소계→합계 절대 오차만 사용 | Moderate | MEDIUM | **✅ 수정 완료** (상대 0.1% 추가) |
| 5 | 체크리스트 correction 부분 매칭 | Moderate | LOW | 후속 개선 |
| 6 | 수치 정합성 비금액 숫자 포함 | Moderate | LOW | 후속 개선 |
| 7 | FE 토글 UI 미구현 | Minor | HIGH | **✅ 수정 완료** |

### 검증 결과

| 항목 | 결과 |
|------|------|
| pytest (리포트 관련 51건) | ✅ 51/51 passed |
| tsc --noEmit | ✅ 에러 없음 |

---

## 전체 타임라인

```
2026-02-17  FDD Deal 생성 500 에러 수정 + 폼 리디자인 (bugfix/Critical)
2026-02-17  FDD 딜 생성 폼 필수/선택 분리 UX (ui/P2)
2026-02-23  FDD industry 타입 단언 → 타입 가드 전환 (type/P2)
2026-02-24  FDD → DD/Checklist 탭 연동 COMING SOON 제거 (ui/P3)
2026-02-25  FDD 자동 분석 & 체크리스트 전체 코드 리뷰 — P0 IDOR + Excel 구조 (review/P0)
2026-02-25  FDD Ralph Loop 2-Pass 전체 코드 리뷰 — Refined IR 미적용 (review/Critical)
2026-02-25  FDD 테스트 스위트 70건 → 0건 수정 (bugfix/Medium)
2026-02-25  FDD 보고서 품질 개선 검증 — P0~P2 + 잔여 3건 100% 완료 (review/Critical)
```

---

## 보안 수정 요약

| # | 취약점 | 심각도 | 수정 |
|---|--------|--------|------|
| SEC-1 | vdr-links IDOR — deal_id 소속 미검증 | **P0** | `deal_id` 검증 추가 |
| SEC-2 | 보고서 버전 API 권한 체크 부재 | **P1** | 4개 엔드포인트 `require_permission()` 적용 |
| SEC-3 | IndustryType enum DB 불일치 (500 → 데이터 노출 위험) | **Critical** | `values_callable` 추가 |

---

## 후속 개선 목록 (미완료)

| # | 이슈 | 우선순위 | 설명 |
|---|------|---------|------|
| 1 | `build_refined_report_ir()` 미구현 | Medium | 체크리스트 결과를 IR에 직접 반영하는 함수 (향후 Phase) |
| 2 | correction 부분 매칭 정규식 | Low | 기존 코드, 문장 수준이므로 실질 영향 낮음 |
| 3 | 수치 정합성 비금액 숫자 필터링 | Low | `abs(val) < 10` 필터 존재하지만 불완전 |
| 4 | FDD 멀티 LLM 교차검증 | High | 구현 프롬프트 작성 완료 (`docs/architecture/20260225_2000_FDD_MultiLLM_CrossVerification_Implementation_Prompt.md`) |

---

## 관련 문서 색인

| 분류 | 문서 |
|------|------|
| 버그 수정 | `review/bugfix/20260217_2142_FDD_Deal_Creation_500_Fix.md` |
| UI 개선 | `review/ui/20260217_2154_FDD_Deal_Form_Redesign.md` |
| 타입 안전성 | `review/type/20260223_1215_FDD_industry_type_assertion.md` |
| UI 연동 | `review/ui/20260224_1539_FDD_DD_Report_Integration.md` |
| 코드 리뷰 | `review/review/20260225_1610_FDD_AutoAnalysis_Checklist_Code_Review.md` |
| 코드 리뷰 | `review/review/20260225_1750_FDD_Ralph_Loop_Code_Review.md` |
| 테스트 수정 | `review/bugfix/20260225_1823_FDD_Test_Suite_70_Failures_Fix.md` |
| 아키텍처 | `docs/architecture/20260225_2000_FDD_MultiLLM_CrossVerification_Implementation_Prompt.md` |
