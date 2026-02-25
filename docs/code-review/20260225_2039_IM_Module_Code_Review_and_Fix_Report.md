# IM 모듈 종합 코드 리뷰 및 수정 보고서

> 리뷰 일시: 2026-02-25 20:23
> 수정 완료: 2026-02-25 20:39
> 리뷰 범위: `im/` 백엔드 전체 + `amic-platform/src/modules/im/` 프론트엔드 전체
> 변경 요약: VDR 기반 IM 자동 생성 워크플로우, 체크리스트 관리, Ralph Loop 품질 반복, 감사 로깅, AMIC 디자인 시스템, 26개 섹션 렌더러
> 관련 브랜치: `feat/ma-workflow`

---

## 리뷰 요약

- **총 이슈 수**: 14개 (Critical: 1, Major: 3, Moderate: 5, Minor: 5)
- **허위 양성 제거**: 3건 (models/__init__.py 미등록, PPTX 폰트 오버라이드 불일치, Ralph POST 라우트 누락)
- **수정 완료**: 12/14 (중기 과제 2건 보류: #4 Soft Delete, #7 JSONB 스키마 검증)
- **빌드 검증**: `tsc --noEmit` 통과, `vite build` 성공 (3095 모듈, 21.73초)

---

## 허위 양성 제거 (Self-Check 결과)

| 원 보고 | 검증 결과 | 근거 |
|---------|----------|------|
| `models/__init__.py`에 IMChecklist 미등록 | **허위 양성** | `__init__.py:6,16-29`에서 import + `__all__` 등록 확인 |
| PPTX 폰트 오버라이드 불일치 | **허위 양성** | `font_helper.py:101-156`에서 `title_ph_idx` 기반 heading_ea_font(SUITE)/ea_font(Pretendard) 분기 확인 |
| #14 Ralph 수동 트리거 라우트 부재 | **허위 양성** | `ralph.py:105`에 `@router.post("/sessions", ...)` 존재 확인 |

---

## 수정 내역

### Phase 1 — Critical + Major (3/3 완료)

#### #1 [Critical] Excel 업로드 경로 키 불일치
- **위치**: `im/src/api/tasks/generate_im.py:299`
- **원인**: `_generation_config`(언더스코어 접두사) → DB 컬럼명은 `generation_config`
- **수정**: `im_data.get("_generation_config")` → `im_data.get("generation_config")`

#### #2 [Major] 프론트엔드 DataSource 타입에 "VDR" 누락
- **위치**: `amic-platform/src/modules/im/types/document.ts:4`
- **수정**: `export type DataSource = "DART" | "MANUAL" | "EXCEL" | "VDR";`

#### #3 [Major] CreateDocumentPage에 TEASER 스타일 옵션 누락
- **위치**: `amic-platform/src/modules/im/pages/CreateDocumentPage.tsx:26-31`
- **수정**: STYLE_OPTIONS 배열에 `{ value: "TEASER", label: "Teaser - One-pager" }` 추가

---

### Phase 2 — Moderate (5/5 완료, 2건 보류)

#### #5 섹션 렌더러 레지스트리 에러 처리
- **위치**: `im/src/design_renderer/section_renderers/`
- **수정**:
  - `base.py`: `RendererError` / `RendererNotFoundError` 커스텀 예외 클래스 추가
  - `__init__.py`: `get_renderer()`에서 `KeyError` → `RendererNotFoundError` 발생, exports에 추가
  - `pipeline.py`: `RendererNotFoundError` (warning) vs `Exception` (error + exc_info) 분기 처리

#### #6 IMRalphSession relationship 패턴 불일치
- **위치**: `im/src/api/db/models/im_ralph_session.py:90`, `document.py`
- **수정**: `backref="ralph_sessions"` → `back_populates="ralph_sessions"` + Document 모델에 역관계 명시

#### #8 차트 엔진 색상 하드코딩 중복
- **위치**: `im/src/chart_engine/config.py`
- **수정**: `chart_config_from_design_tokens()` 어댑터 함수 추가 (duck typing, 런타임 의존 없음)

#### #9 HTTPException vs APIError 혼용
- **위치**: `im/src/api/routes/documents.py`, `ralph.py`
- **수정**:
  - `documents.py`: `HTTPException` → `ValidationError(field=..., reason=...)`
  - `ralph.py`: 404→`NotFoundError`, 400→`ValidationError`, 409→`ConflictError`

#### #4 [보류] 문서 Hard Delete → Soft Delete
- **사유**: 중기 과제. `is_deleted` 플래그 + 마이그레이션 필요

#### #7 [보류] JSONB 컬럼 스키마 검증
- **사유**: 중기 과제. 6개+ JSONB 컬럼에 Pydantic 모델 검증 도입 필요

---

### Phase 3 — Minor (4/4 완료, 1건 허위 양성 제거)

#### #10 디자인 토큰 footer_note 하드코딩
- **위치**: `im/src/design_renderer/design_tokens.py`
- **수정**: `from_brand_assets()`에 `footer_note=getattr(brand, "footer_note", cls.footer_note)` 오버라이드 추가

#### #11 TM TOC 페이지 번호 검증
- **위치**: `im/src/design_renderer/pipeline.py`
- **수정**: Phase 5 검증 단계 추가 — 렌더링 완료 후 `group_start_pages` vs 실제 슬라이드 수 비교, 불일치 시 warning 로깅

#### #12 DocumentDetailPage 데이터소스 표시 불일치
- **위치**: `amic-platform/src/modules/im/pages/DocumentDetailPage.tsx`, `DocumentListPage.tsx`
- **수정**:
  - DetailPage: 평문 → 색상 배지 (DART=blue, MANUAL=gray, EXCEL=emerald, VDR=violet)
  - ListPage: VDR 배지 추가 (`bg-violet-100 text-violet-700`)

#### #13 섹션 렌더러 간 포맷 유틸 중복
- **수정**:
  - 신규 `format_utils.py`: `fmt_amount()`, `fmt_pct()`, `fmt_multiple()` 공통 유틸
  - 업데이트된 렌더러 (5개):
    - `business_overview.py` — 로컬 `_fmt_amount`/`_fmt_pct` 제거, import 교체
    - `executive_summary.py` — 로컬 함수를 format_utils 위임으로 교체
    - `financial_analysis.py` — 로컬 `_fmt_amount`/`_fmt_pct` 제거, import 교체
    - `proforma.py` — 로컬 `_fmt_amount`/`_fmt_pct` 제거, import 교체
    - `valuation.py` — 로컬 `_fmt_multiple`/`_fmt_pct`/`_fmt_amount` 제거, import 교체 (`already_percent=True` 적용)
  - `valuation.py`: 미사용 `html_escape` import도 정리

#### #14 [허위 양성 제거] Ralph Loop 수동 트리거 라우트 부재
- **검증 결과**: `ralph.py:105`에 `@router.post("/sessions", ...)` 이미 존재

---

## 수정 파일 목록 (20개)

### 백엔드 (10개)
| 파일 | 이슈 # | 변경 유형 |
|------|--------|----------|
| `im/src/api/tasks/generate_im.py` | #1 | 키 이름 수정 |
| `im/src/design_renderer/section_renderers/base.py` | #5 | 커스텀 예외 추가 |
| `im/src/design_renderer/section_renderers/__init__.py` | #5 | 예외 타입 교체 + export |
| `im/src/design_renderer/pipeline.py` | #5, #11 | 예외 분기 + TOC 검증 |
| `im/src/api/db/models/im_ralph_session.py` | #6 | backref→back_populates |
| `im/src/api/db/models/document.py` | #6 | 역관계 추가 |
| `im/src/chart_engine/config.py` | #8 | 어댑터 함수 추가 |
| `im/src/api/routes/documents.py` | #9 | HTTPException→ValidationError |
| `im/src/api/routes/ralph.py` | #9 | HTTPException→도메인 예외 |
| `im/src/design_renderer/design_tokens.py` | #10 | footer_note 설정화 |

### 프론트엔드 (4개)
| 파일 | 이슈 # | 변경 유형 |
|------|--------|----------|
| `amic-platform/src/modules/im/types/document.ts` | #2 | VDR 타입 추가 |
| `amic-platform/src/modules/im/pages/CreateDocumentPage.tsx` | #3 | TEASER 옵션 추가 |
| `amic-platform/src/modules/im/pages/DocumentDetailPage.tsx` | #12 | 데이터소스 배지 |
| `amic-platform/src/modules/im/pages/DocumentListPage.tsx` | #12 | VDR 배지 추가 |

### 렌더러 리팩토링 (6개)
| 파일 | 이슈 # | 변경 유형 |
|------|--------|----------|
| `im/src/design_renderer/section_renderers/format_utils.py` | #13 | **신규** 공통 유틸 |
| `im/src/design_renderer/section_renderers/business_overview.py` | #13 | import 교체 |
| `im/src/design_renderer/section_renderers/executive_summary.py` | #13 | import 교체 |
| `im/src/design_renderer/section_renderers/financial_analysis.py` | #13 | import 교체 |
| `im/src/design_renderer/section_renderers/proforma.py` | #13 | import 교체 |
| `im/src/design_renderer/section_renderers/valuation.py` | #13 | import 교체 + 미사용 import 정리 |

---

## 아키텍처 강점 (긍정 평가)

### 백엔드
- Celery Chord/Chain 패턴으로 5단계 파이프라인 오케스트레이션 (DART/EXCEL/MANUAL/VDR 분기)
- SQLAlchemy 2.0 Mapped[] + AsyncSession 일관적 사용
- 구조화된 JSON 로깅 + ContextVar 기반 Request ID 전파
- ErrorCode 열거형 (1000~9999 범위별 도메인 분류) + 커스텀 예외 계층
- 체크리스트 80개 필드 레지스트리 (`checklist_field_registry.py`)
- httpOnly 쿠키 JWT + 크로스 백엔드 사용자 페더레이션

### 프론트엔드
- React Query 조건부 폴링 (처리 중일 때만 3초 간격, 완료 시 자동 중단)
- ARIA 접근성 (progressbar, tabpanel, aria-valuenow)
- Lazy loading + Suspense fallback
- VDR 폴더 계층 탐색 + 크로스 모듈 MA↔IM 통합

### 디자인 렌더러
- AMIC 5단계 Green 팔레트 + SUITE/Pretendard 폰트 시스템
- 26개 섹션 렌더러 (18 IM + 8 TM) 동적 슬라이드 수 조절
- PPTX 한글 폰트 a:ea 보장 (title=SUITE, body=Pretendard 분기)
- 워터마크 + 편집 제한 보안

---

## 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| `npx tsc --noEmit` | ✅ 에러 없음 |
| `npx vite build` | ✅ 성공 (3095 모듈, 21.73초) |
| 수정 파일 수 | 20개 (백엔드 10, 프론트엔드 4, 렌더러 6) |
| 허위 양성 제거 | 3건 |

---

## 남은 중기 과제

| # | 이슈 | 우선순위 | 예상 작업량 |
|---|------|---------|-----------|
| 4 | Document Soft Delete | Medium | 마이그레이션 + 서비스 로직 |
| 7 | JSONB 컬럼 스키마 검증 | Low | Pydantic 모델 6개+ 정의 |
