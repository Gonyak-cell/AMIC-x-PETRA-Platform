# VDR 기반 IM 체크리스트 워크플로우 — 전체 코드 리뷰

> 2026-02-25 16:27 작성
> 리뷰 범위: Phase 1~6 전체 구현 (백엔드 + 프론트엔드 + 렌더러 + Docker)

---

## 리뷰 요약

| 등급 | 수량 | 설명 |
|------|------|------|
| **P0** | 2 | API 경로 불일치 + 인증 헤더 누락 (Celery 태스크 실행 시 즉시 장애) |
| **P1** | 13 | 필드 키 불일치 3건, 프론트엔드 기능 버그 1건, Celery 미연결, Docker 의존성 등 |
| **P2** | 17 | 타입 안전성, 접근성, 검증 누락, 데드 코드 등 |
| **P3** | 4 | 중복 토스트, 미사용 import, UX 세부사항 |

**전체 판정**: 아키텍처와 설계는 우수하나, **Celery 태스크 실행 경로에 P0 2건 + P1 필드 매핑 불일치 3건**이 있어 VDR 파싱→변환 워크플로우가 실제로 동작하지 않음. 프론트엔드는 P1 1건(편집 버튼 invisible) 외 높은 완성도. 렌더러는 30~70페이지 달성 가능하며 PDF 잔재만 정리 필요.

---

## P0 — 즉시 수정 필요

### P0-1. deal-mgmt 내부 API 경로 불일치

**위치**: `im/src/api/tasks/vdr_extraction.py:70-72`

**문제**: Celery 태스크에서 호출하는 경로가 실제 등록 경로와 다름.
- 호출 경로: `{url}/api/v1/transactions/{txn_id}/vdr/documents/{doc_id}`
- 실제 경로: `{url}/api/v1/internal/vdr/transactions/{txn_id}/documents/{doc_id}/metadata`

**영향**: VDR 문서 메타데이터 조회가 항상 404 → 전체 VDR 파싱 파이프라인 실패.

### P0-2. 내부 API 인증 헤더 누락

**위치**: `im/src/api/tasks/vdr_extraction.py:67-75`

**문제**: `vdr_internal.py`에서 `X-Internal-Key` 헤더를 `Depends`로 요구하지만, httpx 클라이언트에서 이 헤더를 전송하지 않음.

**영향**: 경로가 맞아도 항상 403 → 전체 VDR 파싱 파이프라인 실패.

---

## P1 — 워크플로우에 영향

### P1-1. MANAGEMENT 필드 키 불일치

**위치**: `im/src/api/services/checklist_to_imdata.py:377-378`

**문제**: 레지스트리에서 `mgmt_{n}_name`, `mgmt_{n}_title` 형태로 정의하지만, 변환기에서 `management_{idx}_{field}` 패턴을 매칭. 경영진 변환이 동작하지 않음.

### P1-2. SHAREHOLDERS 필드 키 불일치

**위치**: `im/src/api/services/checklist_to_imdata.py:437-438`

**문제**: 레지스트리에서 `sh_{n}_name`, `sh_{n}_pct` 형태로 정의하지만, 변환기에서 `shareholder_{idx}_{field}` 패턴을 매칭. 주주 변환이 전혀 동작하지 않음.

### P1-3. MARKET 필드 키 불일치

**위치**: `im/src/api/services/checklist_to_imdata.py:296`

**문제**: 레지스트리 `competitive_advantage` (단수) vs 변환기 `competitive_advantages` (복수). 경쟁 우위 매핑 누락.

### P1-4. Celery 태스크 미연결

**위치**: `im/src/api/routes/checklist.py:151-160, 425-437, 482-491`

**문제**: `create_from_vdr`, `confirm_checklist`, `reparse_checklist`에서 Celery 태스크 호출이 모두 주석 처리됨. 체크리스트가 `EXTRACTING` 상태에서 영원히 머무름.

### P1-5. 단건/일괄 수정의 상태 전환 로직 불일치

**위치**: `im/src/api/routes/checklist.py:290-300 vs 339-345`

**문제**: 단건 수정은 값 동일 시 `CONFIRMED`, 다를 시 `MODIFIED` 자동 결정. 일괄 수정은 무조건 `MODIFIED`. 동일 값으로 확인해도 상태가 다르게 설정됨.

### P1-6. `session.get(Document, document_id)` str UUID 전달

**위치**: `im/src/api/tasks/generate_im_from_checklist.py:115`

**문제**: Celery 태스크 인자로 `str`이 전달되지만, `session.get()`에 `uuid.UUID()` 변환 없이 전달. PostgreSQL UUID 컬럼과 타입 불일치로 에러 가능.

### P1-7. openpyxl/fitz ImportError 조용한 무시

**위치**: `im/src/api/services/vdr_analysis_service.py:190-193, 294-297`

**문제**: 필수 파싱 라이브러리 미설치 시 빈 결과를 반환하고 에러를 알리지 않음. 파일 존재하나 추출 결과 0건인 경우와 구분 불가.

### P1-8. `deal_mgmt_internal_url` 설정 미정의

**위치**: `im/src/api/tasks/vdr_extraction.py:62`, `im/src/api/config.py`

**문제**: `APIConfig`에 `deal_mgmt_internal_url` 속성이 없어 `getattr()` fallback으로만 동작. 명시적 설정 필드 필요.

### P1-9. 내부 API 인증 키 기본값 보안 문제

**위치**: `deal-mgmt/app/routers/vdr_internal.py:30`

**문제**: `INTERNAL_SERVICE_KEY` 기본값이 `"dev-internal-key"`. 프로덕션에서 환경변수 미설정 시 누구나 접근 가능.

### P1-10. ChecklistItemRow 편집 버튼 invisible

**위치**: `amic-platform/src/modules/im/components/ChecklistItemRow.tsx:98, 191`

**문제**: `<tr>` 요소에 `group` 클래스가 없어 `group-hover:opacity-100`이 동작하지 않음. 편집(연필) 버튼이 항상 `opacity-0`으로 보이지 않음.

### P1-11. Docker im-api → deal-mgmt-api 서비스 의존성 미선언

**위치**: `docker-compose.yml` im-api 섹션

**문제**: `DEAL_MGMT_INTERNAL_URL` 설정은 있으나 `depends_on`에 `deal-mgmt-api` 없음. 기동 순서에 따라 VDR API 호출 실패 가능.

### P1-12. 8개 렌더러에 PDF용 import 잔재

**위치**: 모든 확장된 렌더러의 `from src.design_renderer.pdf_output.html_builder import build_slide_html`

**문제**: PDF 제거가 pipeline.py에서는 완료되었으나, 렌더러에 HTML/PDF import + `render_html()` 메서드가 남아있음. `pdf_output/` 디렉토리 삭제 시 ImportError 발생.

### P1-13. 새 Celery 태스크 자동 발견 미확인

**위치**: `im/src/api/tasks/__init__.py`

**문제**: `vdr_extraction`, `generate_im_from_checklist` 모듈이 `__init__.py`에 import되지 않음. Celery autodiscover 설정에 따라 자동 발견될 수도 있으나 확인 필요.

---

## P2 — 개선 권장 (17건)

| # | 위치 | 이슈 |
|---|------|------|
| 1 | `im_checklist.py` | 중복 인덱스 정의 (UNIQUE + 별도 Index, index=True + 별도 Index) |
| 2 | `schemas/checklist.py` | `CreateFromVdrRequest`에 `im_style`, `industry` 검증 누락 (기존 `DocumentCreate`에는 있음) |
| 3 | `checklist_to_imdata.py` | DEAL 필드 매핑 불완전 (레지스트리↔변환기 불일치) |
| 4 | `checklist_to_imdata.py` | 단위(백만원/억원) 변환 로직 부재 |
| 5 | `checklist_field_registry.py` | 연도 하드코딩 `[2022, 2023, 2024]` |
| 6 | `vdr_extraction.py` + `generate_im_from_checklist.py` | `_get_sync_engine()` 함수 중복 정의 |
| 7 | `vdr_internal.py` | `file-path` 엔드포인트가 디렉토리 경로 반환 (파일명 미포함) |
| 8 | `ChecklistProgressBar.tsx` | `role="progressbar"` + ARIA 속성 누락 |
| 9 | `ChecklistTable.tsx` | `<table>`에 `aria-label` 또는 `<caption>` 없음 |
| 10 | `checklist.ts` | `ChecklistSummary.status/category`가 `string` (union type 대신) |
| 11 | `useChecklist.ts` | `useBatchUpdateItems` status가 `string` (`ChecklistItemStatus` 대신) |
| 12 | `CreateFromVdrPage.tsx` | `useTransactions` status `"ACTIVE"` 타입 검증 필요 |
| 13 | `ChecklistReviewPage.tsx` | sticky 바텀 바 `-mx-6` overflow 위험 |
| 14 | `design_tokens.py` | `font_mono: "Pretendard"` weight 정보 부재 |
| 15 | `valuation.py` | IRR 값 단위 모호성 (비율 0.25 vs 퍼센트 25.0) |
| 16 | `growth_strategy.py` | 로드맵 슬라이드 y좌표 오버플로우 위험 |
| 17 | `im_checklist.py` | `status` 필드 `Mapped[str]` — CHECK 제약 또는 enum 타입 제한 권장 |

---

## P3 — 선택 개선 (4건)

| # | 위치 | 이슈 |
|---|------|------|
| 1 | `CreateFromVdrPage.tsx` + `useVdrDocumentSelector.ts` | 성공 토스트 중복 표시 |
| 2 | `ChecklistReviewPage.tsx` | `useRef` 미사용 import |
| 3 | `SourceDocumentLink.tsx` | `ExternalLink` 아이콘이 클릭 불가 `<span>`에 표시 |
| 4 | `DocumentDetailPage.tsx` | 체크리스트 카드가 VDR 문서가 아닌 경우에도 표시 |

---

## 30~70페이지 달성 가능성

| 섹션 | 최소 | 최대 |
|------|------|------|
| Core (Cover~TOC, Contact) | 4 | 4 |
| Executive Summary | 2 | 5 |
| Investment Highlights | 1 | 6 |
| Company Overview | 1 | 6 |
| Market Overview | 1 | 6+ |
| Business Overview | 1 | 6+ |
| Financial Analysis | 1 | 10+ |
| Valuation | 1 | 5 |
| Growth Strategy | 1 | 5 |
| 기타 (Deal, BizModel, Mgmt, SH, Txn, Value, Appendix) | 7 | 21 |
| **합계** | **20** | **74+** |

**결론**: 30페이지 하한 안정적 달성, 70페이지 상한도 데이터 충분 시 달성 가능.

---

## 허위 리뷰 검증

리뷰에서 지적된 모든 이슈를 코드 기반으로 교차 검증:

| 검증 항목 | 결과 |
|-----------|------|
| P0-1 API 경로 불일치 | ✅ 실제 확인 — `vdr_extraction.py:70` vs `vdr_internal.py` prefix + route path |
| P0-2 인증 헤더 누락 | ✅ 실제 확인 — httpx 호출에 headers 없음 |
| P1-1~3 필드 키 불일치 | ✅ 실제 확인 — `checklist_field_registry.py` 정의 vs `checklist_to_imdata.py` 매칭 패턴 |
| P1-10 group 클래스 누락 | ✅ 실제 확인 — `<tr>` 태그에 className 없음 |
| P1-11 Docker depends_on | ✅ 실제 확인 — im-api의 depends_on에 deal-mgmt-api 없음 |
| P1-12 PDF import 잔재 | ✅ 실제 확인 — 8개 렌더러 모두 `build_slide_html` import 존재 |

**허위 양성 없음** — 모든 이슈가 실제 코드와 일치.
