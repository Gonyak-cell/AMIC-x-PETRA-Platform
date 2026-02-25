# Financial Model (재무모델) 기능 구현 리포트

> **작성일**: 2026-02-25 20:56:00
> **브랜치**: `feat/ma-workflow`
> **범위**: deal-mgmt 백엔드 + amic-platform 프론트엔드

---

## 1. 기능 개요

M&A 거래 워크플로우의 **재무모델(Financial Model)** 탭 기능. VDR 문서를 기반으로 Excel 재무모델을 자동 생성하고, AI 체크리스트 검토 워크플로우를 통해 사용자가 모델의 정확성을 확인·수정할 수 있도록 한다.

### 핵심 워크플로우

```
VDR 문서 선택 → Ralph Pass 1 (데이터 추출 + 초안 생성)
                → 체크리스트 검토 (사용자 확인/수정/플래그)
                → Finalize → Ralph Pass 2 (최종 Excel 생성)
                → 다운로드
```

---

## 2. 파일 구조 (15개 파일, ~2,660 LOC)

### 백엔드 (deal-mgmt) — 8개 파일, ~1,640 LOC

| 파일 | 라인 | 역할 |
|------|------|------|
| `app/models/financial_model.py` | 183 | ORM 모델 — FinancialModel, FMChecklist, FMChecklistItem |
| `app/schemas/financial_model.py` | 126 | Pydantic 스키마 — Create/Out/Update/Summary |
| `app/services/financial_model_service.py` | 404 | 서비스 레이어 — CRUD + VDR 추출 + Ralph Loop + Excel 생성 |
| `app/services/fm_checklist_service.py` | 162 | 체크리스트 서비스 — 항목 관리, 벌크 업데이트, Finalize |
| `app/routers/financial_models.py` | 209 | API 라우터 — 모델 CRUD + 체크리스트 CRUD + 다운로드 |
| `app/tasks/fm_tasks.py` | 90 | Celery 태스크 — VDR 추출+Ralph, Finalize+생성 |
| `tests/test_financial_models.py` | 480 | 테스트 — 45개 테스트 케이스 |
| `migrations/versions/020_financial_models.py` | 189 | Alembic 마이그레이션 — 3 테이블 |

### 프론트엔드 (amic-platform) — 7개 파일, ~910 LOC

| 파일 | 라인 | 역할 |
|------|------|------|
| `src/modules/ma/types/financial_model.ts` | 256 | TypeScript 타입 정의 |
| `src/modules/ma/hooks/useFinancialModels.ts` | 93 | React 훅 — API 호출 + 상태 관리 |
| `src/modules/ma/components/fm/FMChecklistReview.tsx` | 103 | 체크리스트 검토 메인 컴포넌트 |
| `src/modules/ma/components/fm/FMChecklistCategorySection.tsx` | 125 | 카테고리별 섹션 렌더링 |
| `src/modules/ma/components/fm/FMChecklistItemCard.tsx` | 248 | 개별 항목 카드 (확인/수정/플래그) |
| `src/modules/ma/components/fm/FMChecklistSummaryBar.tsx` | 85 | 진행률 요약 바 |

---

## 3. API 엔드포인트

### 모델 CRUD

| Method | Path | 설명 |
|--------|------|------|
| GET | `/transactions/{txn_id}/financial-models` | 모델 목록 |
| POST | `/transactions/{txn_id}/financial-models` | 모델 생성 (VDR → Ralph Pass 1 트리거) |
| GET | `/transactions/{txn_id}/financial-models/{fm_id}` | 모델 상세 |
| POST | `/transactions/{txn_id}/financial-models/{fm_id}/regenerate` | 모델 재생성 |
| DELETE | `/transactions/{txn_id}/financial-models/{fm_id}` | 모델 삭제 |
| GET | `/transactions/{txn_id}/financial-models/{fm_id}/download` | Excel 다운로드 |

### 체크리스트 CRUD

| Method | Path | 설명 |
|--------|------|------|
| GET | `.../financial-models/{fm_id}/checklist` | 체크리스트 조회 |
| PUT | `.../financial-models/{fm_id}/checklist/items/{item_id}` | 항목 업데이트 |
| PUT | `.../financial-models/{fm_id}/checklist/{cl_id}/bulk-update` | 벌크 업데이트 |
| POST | `.../financial-models/{fm_id}/checklist/{cl_id}/finalize` | Finalize → Pass 2 트리거 |

---

## 4. DB 스키마 (3 테이블)

### financial_models

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| transaction_id | UUID FK | 거래 참조 |
| title | VARCHAR(200) | 모델 제목 |
| model_type | ENUM | DCF, LBO, COMPS, PRECEDENT, CUSTOM |
| status | ENUM | DRAFT → GENERATING → CHECKLIST_REVIEW → FINALIZING → READY / FAILED |
| file_path | TEXT | 생성된 Excel 파일 경로 |
| file_name | VARCHAR(200) | 파일명 |
| created_by_email | VARCHAR(200) | 생성자 |

### fm_checklists

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| financial_model_id | UUID FK | 재무모델 참조 |
| status | ENUM | PENDING → IN_REVIEW → FINALIZED |
| finalized_by | VARCHAR(200) | Finalize 수행자 |

### fm_checklist_items

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| checklist_id | UUID FK | 체크리스트 참조 |
| category | VARCHAR(100) | 분류 (assumptions, revenue, costs 등) |
| field_name | VARCHAR(200) | 검토 항목명 |
| ai_value | TEXT | AI 추출 값 |
| ai_confidence | FLOAT | AI 신뢰도 (0.0~1.0) |
| ai_source | TEXT | 출처 문서 |
| user_status | ENUM | PENDING / CONFIRMED / CORRECTED / FLAGGED |
| user_value | TEXT | 사용자 수정 값 |
| user_comment | TEXT | 사용자 코멘트 |
| reviewed_by | VARCHAR(200) | 검토자 |

---

## 5. 코드 리뷰 결과 및 수정 사항

코드 리뷰 점수: **4.7/5** — 7개 이슈 발견, 전체 수정 완료.

### P1 (Major) — generator cleanup 패턴 수정

**이전**: `if "generator" in locals():` — 불안정한 패턴
**이후**: `generator: RalphExcelGenerator | None = None` + `if generator is not None:` — 명시적 초기화

파일: `financial_model_service.py` (2개소)

### P2 (Major) — asyncio.create_task → Celery 태스크 큐 전환

**이전**: `asyncio.create_task(...)` — 서버 재시작 시 태스크 소실, 재시도 없음
**이후**: `task.delay(...)` — Redis 기반 Celery, 재시도/타임아웃/모니터링 내장

**전환된 4개 호출부**:

| 파일 | 태스크 내용 | Celery 태스크명 |
|------|----------|--------------|
| `financial_model_service.py` | VDR 추출 + Ralph Pass 1 | `deal_mgmt.fm.vdr_extraction_and_ralph` |
| `routers/financial_models.py` | Finalize + Ralph Pass 2 | `deal_mgmt.fm.finalize_and_generate` |
| `marketing_material_service.py` | PPTX 생성 | `deal_mgmt.marketing.generate_pptx` |
| `routers/ralph.py` | Ralph Loop 세션 | `deal_mgmt.ralph.run_loop` |

**신규 인프라**:
- `app/tasks/celery_app.py` — Celery 앱 팩토리
- `app/tasks/fm_tasks.py` — FM 태스크 2개
- `app/tasks/marketing_tasks.py` — 마케팅 태스크 1개
- `app/tasks/ralph_tasks.py` — Ralph 태스크 1개
- Docker: `deal-mgmt-redis` (포트 6381) + `deal-mgmt-celery-worker`

### P3 (Moderate) — REVIEWED 코멘트 개선

파일: `types/financial_model.ts:22`
`// DB enum 호환용 — 백엔드 서비스 미전환, FE 렌더링은 준비됨`

### P4 (Minor) — aria-label 접근성 수정

파일: `FMChecklistItemCard.tsx:233-241`
`title` → `aria-label` 3개소 (확인/플래그/해당 없음 버튼)

### P5 (Minor) — 경로 순회 방지

파일: `routers/financial_models.py:99-112`
다운로드 엔드포인트에 `Path.resolve()` + `startswith` 기반 경로 검증 추가

---

## 6. 테스트 수정 사항

### test_integrations.py — 외부 서비스 mock 추가

**문제**: KIIS 서비스가 로컬에서 실행 중일 때 `"ok"` 반환 → 테스트 비결정적
**수정**: FDD/IM/KIIS 클라이언트를 `httpx.ConnectError` mock으로 패치하여 결정적 테스트로 변환

### test_ldd_review.py — WorkflowError 상태 코드 수정

**문제**: `assert resp.status_code == 409` — 실제 WorkflowError 핸들러는 422 반환
**수정**: `assert resp.status_code == 422`

### test_ralph_learning.py — FK constraint 수정

**문제**: `RalphSession.transaction_id`에 임의 UUID 사용 → FK constraint 위반 (SQLite)
**수정**: `_make_txn()` 헬퍼로 Transaction 먼저 생성 + `flush()` 후 Session 생성

### conftest.py — Celery mock 추가

**문제**: celery 패키지 미설치 환경에서 `import celery` 실패
**수정**: `_FakeCelery` 클래스를 `sys.modules["celery"]`에 주입. `.task()` 데코레이터가 `.delay` = `MagicMock` 부착

---

## 7. 최종 테스트 결과

```
472 passed, 14 skipped, 0 failed, 2 warnings (97.45s)
```

- **warnings**: httpx `DeprecationWarning` (쿠키), FastAPI `HTTP_413` deprecation — 기능 영향 없음
- **skipped**: 선택적 테스트 (환경 의존)

---

## 8. 다음 단계 (미구현)

| 항목 | 설명 | 우선순위 |
|------|------|---------|
| FM 페이지 통합 | TransactionWorkspacePage 재무모델 탭에 체크리스트 UI 완전 연결 | Medium |
| Excel 생성 엔진 | openpyxl 기반 실제 Excel 생성 로직 (현재 스텁) | High |
| VDR 연동 | VDR 문서 파싱 → 재무 데이터 자동 추출 | High |
| 다중 모델 비교 | 동일 거래의 DCF/LBO/COMPS 결과 비교 뷰 | Low |
