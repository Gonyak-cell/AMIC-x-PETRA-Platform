# deal-mgmt 재무모델 코드 리뷰 프롬프트

## Context

deal-mgmt 모듈의 Financial Model 기능 전체에 대한 세부 코드 리뷰 프롬프트.
DCF/LBO/COMPS 등 재무모델 생성 → 체크리스트 리뷰 → Ralph Loop AI 검증 → Excel 생성의 전체 워크플로우를 커버.
백엔드 10개 엔드포인트, 3개 DB 테이블, 2개 Celery 태스크 + 프론트엔드 2개 훅 파일, 4개 컴포넌트 대상.

---

## 프롬프트 (바로 사용 가능)

````
deal-mgmt의 재무모델(Financial Model) 기능 전체에 대해 실제 코드베이스를 기준으로 세부항목별 코드 리뷰를 수행해줘.

리뷰 시 반드시 실제 파일을 `Read`로 읽고, 주장에 대해 `Grep`으로 검증한 후 이슈를 보고할 것.
추측이나 기억에 의존한 이슈 보고 절대 금지.

---

## 0단계: 리뷰 대상 파일 전체 읽기

아래 파일을 **모두** `Read`로 전체 읽기:

**백엔드 핵심 (deal-mgmt/):**
- `app/routers/financial_models.py` — 10개 엔드포인트 (189줄)
- `app/models/financial_model.py` — 3개 ORM 모델: FinancialModel, FMChecklist, FMChecklistItem (184줄)
- `app/services/financial_model_service.py` — CRUD + Ralph Loop Pass 1/2 (405줄)
- `app/services/fm_checklist_service.py` — 체크리스트 서비스 (163줄)
- `app/schemas/financial_model.py` — Pydantic 스키마 (127줄)
- `app/models/enums.py` (549~615줄 구간) — 6개 FM 전용 Enum
- `app/tasks/fm_tasks.py` — Celery 태스크 래퍼 (91줄)
- `migrations/versions/020_financial_models.py` — Alembic 마이그레이션 (190줄)
- `tests/test_financial_models.py` — 테스트 (481줄, 23개 케이스)

**백엔드 의존 (deal-mgmt/):**
- `app/main.py` — 라우터 등록 확인
- `app/models/__init__.py` — 모델 import/export 확인
- `app/core/security.py` — JWTClaims, get_jwt_claims
- `app/core/exceptions.py` — DocumentNotFoundError
- `app/ralph/` — Ralph Loop 코어 (오케스트레이터, 게이트, 생성기)
- `app/excel/model_builder.py` — Excel 폴백 생성기

**프론트엔드 (amic-platform/src/modules/ma/):**
- `types/financial_model.ts` — 타입 + 상수 + 라벨 맵 (257줄)
- `hooks/useFinancialModels.ts` — 모델 CRUD 훅 (94줄)
- `hooks/useFMChecklist.ts` — 체크리스트 훅 (106줄)
- `components/fm/FMChecklistReview.tsx` — 메인 리뷰 컴포넌트
- `components/fm/FMChecklistSummaryBar.tsx` — 진행률 바
- `components/fm/FMChecklistCategorySection.tsx` — 카테고리별 그룹
- `components/fm/FMChecklistItemCard.tsx` — 개별 항목 카드
- `pages/TransactionWorkspacePage.tsx` — 통합 페이지 (FM 탭 부분)

---

## 1단계: 상태 머신 정확성 (State Machine Correctness)

재무모델의 핵심은 상태 전이 흐름의 정확성.

### 1-1. FinancialModelStatus 전이 검증

기대되는 상태 흐름:
```
DRAFT → GENERATING → PENDING_REVIEW → FINALIZING → READY
                                    ↓               ↓
                                  FAILED          FAILED
```

- [ ] **모든 상태 전이가 유효한지**: 서비스 코드에서 `fm.status = ...` 할당을 전수 검색 (`Grep`). 기대되지 않는 전이(예: READY→DRAFT, FAILED→GENERATING 직접)가 없는지
- [ ] **GENERATING 상태 진입**: `create_financial_model()`에서 GENERATING으로 설정 후 PENDING_REVIEW로 변경되는 흐름이 올바른지
- [ ] **FINALIZING 상태 진입**: `finalize_checklist()` 라우터에서만 FINALIZING으로 변경되는지
- [ ] **READY 상태 진입**: `run_finalize_and_generate()`에서만 READY로 변경되는지
- [ ] **FAILED 상태 진입**: 예외 catch 블록에서만 FAILED로 변경되는지
- [ ] **라우터의 상태 가드**: download 엔드포인트가 `status == READY` 검증하는지, 다른 엔드포인트에도 적절한 상태 가드가 있는지

### 1-2. FMChecklistStatus 전이 검증

```
GENERATING → PENDING_REVIEW → FINALIZED
```

- [ ] **REVIEWED 상태**: enums.py에 REVIEWED가 정의되어 있지만 서비스에서 사용되지 않음 — 데드 코드인지, 향후 사용 예정인지 확인
- [ ] **Finalize 조건**: 미리뷰 항목(AUTO_GENERATED)이 남아있어도 finalize가 가능함 (warning 로그만 출력) — 이것이 의도된 동작인지 검증

### 1-3. FMChecklistItemStatus 전이 검증

```
AUTO_GENERATED → CONFIRMED / CORRECTED / FLAGGED / NOT_APPLICABLE
```

- [ ] **역방향 전이 허용 여부**: CONFIRMED → AUTO_GENERATED로 되돌리는 것이 가능한지 (서비스 코드에서 상태 가드 존재 여부)
- [ ] **FLAGGED 후 처리**: FLAGGED된 항목이 finalize 시 어떻게 처리되는지

---

## 2단계: 백엔드 아키텍처 정합성 (Backend Consistency)

### 2-1. 라우터 계층 분리

10개 엔드포인트 각각에 대해:
- [ ] 비즈니스 로직이 라우터에 직접 작성되어 있지 않은지 — 특히 `finalize_checklist` 엔드포인트에서 `fm.status = FINALIZING` 설정 + Celery 태스크 트리거가 라우터 레벨에 있는데, 이것이 서비스 레이어로 분리되어야 하는지
- [ ] `get_checklist` 엔드포인트에서 `compute_summary()` 호출 후 직접 필드를 설정하는 로직이 라우터에 있는지 (스키마 직렬화로 처리해야 하는지)

### 2-2. 인증/인가 갭 분석

각 엔드포인트의 `Depends` 검증:

| 엔드포인트 | JWT 필요 | 현재 상태 | 리스크 |
|-----------|---------|---------|-------|
| GET list_models | ? | 확인 필요 | 타인의 거래 FM 열람 가능? |
| POST create_model | ✓ | claims.email 사용 | OK |
| GET get_model | ? | 확인 필요 | |
| POST regenerate_model | ? | 확인 필요 | 비인가 재생성 위험 |
| DELETE delete_model | ? | 확인 필요 | 비인가 삭제 위험 |
| GET download_model | ? | 확인 필요 | 재무 데이터 유출 위험 |
| GET get_checklist | ? | 확인 필요 | |
| PUT update_checklist_item | ✓ | claims.email 사용 | OK |
| PUT bulk_update | ✓ | claims.email 사용 | OK |
| POST finalize_checklist | ✓ | claims.email 사용 | OK |

- [ ] **GET/DELETE 엔드포인트에 JWT 미적용**: `get_jwt_claims` Depends가 없는 엔드포인트를 `Grep`으로 식별. 비인가 접근이 가능한지 확인
- [ ] **transaction_id 검증만으로 충분한지**: 사용자가 본인 거래가 아닌 다른 거래의 FM에 접근할 수 있는지

### 2-3. 에러 처리 일관성

- [ ] `DocumentNotFoundError` 사용 일관성: 모든 "not found" 상황에서 동일한 예외 사용 여부
- [ ] download 엔드포인트의 `HTTPException(404)` 직접 사용이 `DocumentNotFoundError` 패턴과 불일치하는지
- [ ] Celery 태스크 내 예외 처리: `error_message` 잘림(300~500자) 시 디버깅에 충분한 정보가 보존되는지

### 2-4. 데이터 모델 무결성

3개 테이블 각각에 대해:

**financial_models:**
- [ ] `ralph_score`가 `Float` 타입임 — 재무 데이터이므로 `Decimal`이어야 하는지 검토 (0.0~1.0 범위의 품질 점수이므로 Float 허용 가능할 수 있음)
- [ ] `parameters` JSONB 컬럼의 스키마 검증 부재 — 어떤 데이터든 저장 가능한 리스크
- [ ] `file_path` 보안: 경로 순회(path traversal) 공격 가능성 — download 엔드포인트에서 검증 여부
- [ ] Composite Index `ix_fm_txn_type_status`의 쿼리 커버리지 적절성

**fm_checklists:**
- [ ] `financial_model_id` UNIQUE 제약의 올바른 적용 (1:1 관계 보장)
- [ ] cascade delete 설정: FM 삭제 시 체크리스트 + 항목 모두 삭제되는지

**fm_checklist_items:**
- [ ] `confidence`가 `Float` 타입 — 0.0~1.0 범위 DB 레벨 CHECK 제약 부재
- [ ] `auto_value`, `user_value`가 `String(200)` — 금액 값이 문자열로 저장되는 패턴의 적절성
- [ ] `metadata` 컬럼명이 ORM에서 `extra_metadata`로 매핑되는지 확인 (Python reserved word 회피)

### 2-5. Pydantic 스키마 검증

- [ ] `FinancialModelCreate.ralph_max_cost_usd`가 `float` 타입 — 비용 제어 값이므로 `Decimal` 필요 여부
- [ ] `FinancialModelOut`의 모든 필드가 ORM 모델과 1:1 매칭되는지
- [ ] `FMChecklistOut.items`가 빈 리스트 기본값 — `joinedload`가 실패했을 때 빈 리스트가 반환되는지 vs None
- [ ] `FMChecklistOut`의 summary 필드(total_items, confirmed_count 등)가 라우터에서 수동 주입되는 패턴의 적절성 — `@computed_field` 또는 `@model_validator` 사용이 더 나은지

---

## 3단계: Celery 태스크 안정성 (Background Task Safety)

### 3-1. 태스크 구성 검증

2개 Celery 태스크 각각에 대해:

- [ ] **`_run_async()` 헬퍼 안전성**: 이미 실행 중인 이벤트 루프가 있을 때 `ThreadPoolExecutor`로 새 루프를 생성하는 패턴의 스레드 안전성
- [ ] **`soft_time_limit=1800`(30분)**: Ralph Loop + Excel 생성에 30분이 충분한지, 타임아웃 시 상태가 FAILED로 변경되는지
- [ ] **`max_retries=1`**: 재시도 시 동일 FM에 대해 중복 Excel 생성 방지 — 멱등성(idempotency) 보장 여부
- [ ] **`acks_late=True`**: 워커 크래시 시 태스크 재실행 — 부분 완료 상태의 FM 처리 방법

### 3-2. Ralph Loop 통합

**Pass 1 (VDR 추출 + 초안):**
- [ ] `_run_vdr_extraction_and_ralph()` 내에서 DB 세션 생성 패턴: `async_session_factory()` 사용 시 커넥션 풀 고갈 리스크
- [ ] VDR 문서 ID가 유효한지 검증하는 로직 존재 여부 — 존재하지 않는 VDR ID 전달 시 동작
- [ ] Ralph Loop 실패 시 FM 상태가 PENDING_REVIEW로 설정됨 (FAILED가 아님) — 의도된 동작인지

**Pass 2 (확정값 → 최종 Excel):**
- [ ] 확정값 추출 로직: `user_value > auto_value` 우선순위가 올바른지
- [ ] Excel 폴백 생성기(`FinancialModelBuilder`) 품질: Ralph 실패 시에도 사용 가능한 Excel이 생성되는지
- [ ] `output_dir` 경로(`generated/financial_models/{txn_id}/`)가 컨테이너 볼륨에 마운트되어 있는지
- [ ] 생성된 파일에 대한 정리(cleanup) 정책 존재 여부 — 오래된 버전 파일 삭제

### 3-3. 동시성 문제

- [ ] 동일 FM에 대해 Pass 1과 Pass 2가 동시 실행될 수 있는지 — 상태 가드 존재 여부
- [ ] 사용자가 체크리스트 수정 중에 finalize가 트리거되면? — 락(lock) 메커니즘 존재 여부
- [ ] regenerate와 finalize가 동시에 호출되면? — 레이스 컨디션 방지

---

## 4단계: 프론트엔드 품질 (Frontend Quality)

### 4-1. 타입 계약 일치 (FE ↔ BE)

`types/financial_model.ts` vs `schemas/financial_model.py` 1:1 비교:

**Enum 대조:**
| FE Union Type | BE StrEnum | 값 일치 |
|--------------|-----------|--------|
| FinancialModelType | FinancialModelType | 6값 모두 확인 |
| FinancialModelStatus | FinancialModelStatus | 6값 모두 확인 |
| FMChecklistStatus | FMChecklistStatus | 4값 모두 확인 |
| FMChecklistItemStatus | FMChecklistItemStatus | 5값 모두 확인 |
| FMChecklistCategory | FMChecklistCategory | 19값 모두 확인 (BE 18 vs FE 18 — 수 일치) |
| FMChecklistSeverity | FMChecklistSeverity | 4값 모두 확인 |

- [ ] **모든 enum 값이 정확히 일치하는지** 양쪽 파일을 `Read`로 읽어서 값 하나하나 대조
- [ ] **FE에만 있는 값 / BE에만 있는 값이 없는지**

**Interface 대조:**
| FE Interface | BE Schema | 비교 항목 |
|-------------|-----------|---------|
| FinancialModel | FinancialModelOut | 필드명, 타입, nullable 일치 |
| FinancialModelCreate | FinancialModelCreate | 필드명, 기본값 일치 |
| FMChecklist | FMChecklistOut | 필드명, summary 필드 포함 |
| FMChecklistItem | FMChecklistItemOut | 24개 필드 전수 대조 |
| FMChecklistItemUpdate | FMChecklistItemUpdate | |
| FMChecklistBulkItem | FMChecklistBulkItem | |

- [ ] **`extra_metadata` (BE) vs `extra_metadata` (FE)**: ORM 컬럼명은 `metadata`인데 alias가 적용되는지
- [ ] **날짜 필드**: BE `datetime` → FE `string` (ISO 8601) 변환이 올바른지
- [ ] **UUID 필드**: BE `UUID` → FE `string` 변환 일관성

### 4-2. 훅 패턴 검증

**useFinancialModels.ts:**
- [ ] **폴링 로직**: `refetchInterval`이 GENERATING/FINALIZING 상태일 때만 5초 활성화 — 정상 동작 확인
- [ ] **enabled 조건**: `!!txnId`로 빈 ID 방지
- [ ] **데이터 정규화**: BE가 `list[FinancialModelOut]`을 직접 반환하는데, 훅에서 배열 처리가 올바른지
- [ ] **download URL**: `getFMDownloadUrl()`이 nginx 프록시 경로 `/api/ma/...`와 BE 실제 경로 `/api/v1/...` 매핑이 올바른지

**useFMChecklist.ts:**
- [ ] **retry: false** 설정이 적절한지 — 네트워크 일시 에러 시에도 재시도 없음
- [ ] **bulk update 후 invalidation**: 체크리스트 + 모델 리스트 모두 무효화하는지 (모델 상태 변경 가능)
- [ ] **finalize 후 이중 invalidation**: 체크리스트 키 + 모델 리스트 키 모두 무효화 확인

### 4-3. 컴포넌트 품질

**FMChecklistReview.tsx:**
- [ ] `canFinalize` 조건이 `pending_count === 0`인데, FLAGGED 항목도 finalize 가능한 것이 의도된 동작인지
- [ ] 로딩/에러/빈 상태 모두 처리되는지
- [ ] Finalize 버튼에 확인 다이얼로그(confirm dialog) 존재 여부 — 실수 방지

**FMChecklistItemCard.tsx:**
- [ ] 인라인 편집 모드: Enter 저장 / Escape 취소 키보드 핸들러 존재 확인
- [ ] `isUpdating` prop으로 mutation 진행 중 이중 클릭 방지
- [ ] confidence 바의 접근성: `role="progressbar"`, `aria-valuenow` 설정

**FMChecklistCategorySection.tsx:**
- [ ] "전체 확인" 버튼이 AUTO_GENERATED 항목만 대상으로 하는지 (이미 CORRECTED된 항목을 CONFIRMED로 덮어쓰지 않는지)
- [ ] 카테고리 그룹 내 항목 정렬이 `order_index` 기준인지

**FMChecklistSummaryBar.tsx:**
- [ ] 진행률 계산: `(total - pending) / total * 100`이 올바른지
- [ ] 0으로 나누기 방지 (total_items === 0일 때)

---

## 5단계: 도메인 특화 검증 (Financial Model Domain)

### 5-1. FM_FIELD_REGISTRY 완성도

`financial_model_service.py`의 33개 사전 정의 항목 검증:

- [ ] **DCF 필수 입력**: 할인율(WACC), 영구성장률(Terminal Growth), 예측기간이 포함되어 있는지
- [ ] **LBO 필수 입력**: 차입 구조, 상환 일정, Exit Multiple이 포함되어 있는지
- [ ] **COMPS 필수 입력**: EV/EBITDA, P/E 등 주요 배수가 포함되어 있는지
- [ ] **카테고리별 coverage**: 8개 카테고리(Revenue, Cost, WC, CF, Capital, WACC, Valuation, Sensitivity)가 재무모델 주요 섹션을 모두 커버하는지
- [ ] **severity 분류 적절성**: HIGH/MEDIUM/LOW 배분이 재무적 중요도와 일치하는지
- [ ] **한국 특화 항목**: 원화(KRW) 단위, 한국 세율 기본값, K-IFRS 기준 등이 반영되어 있는지

### 5-2. 값 처리 안전성

- [ ] `auto_value`와 `user_value`가 String(200)로 저장 — 숫자 값의 형식 검증(파싱 가능한 숫자인지) 존재 여부
- [ ] 금액 단위 변환: KRW, USD, x(배수), %(퍼센트), 일(days) 등 다양한 단위가 혼재할 때 처리 방법
- [ ] 소수점/천단위 구분: "150,000,000" vs "150000000" vs "1.5억" 등 다양한 표현 처리

### 5-3. Excel 생성 품질

- [ ] `FinancialModelBuilder`(폴백)가 실제로 의미 있는 Excel을 생성하는지 — 빈 템플릿인지, 데이터가 채워진 모델인지
- [ ] 생성된 Excel의 수식(formula) 포함 여부 — 정적 값만 들어가면 재무모델로서 가치 저하
- [ ] `file_size_bytes` 계산이 `Path.stat().st_size` 기반 — 파일이 아직 쓰기 중일 때 불완전한 사이즈 반환 가능성

---

## 6단계: 보안 (Security)

- [ ] **파일 다운로드 경로 순회**: `fm.file_path`에 `../` 등 경로 순회 문자가 포함될 수 있는지 — FileResponse에 전달되기 전 검증 여부
- [ ] **VDR 문서 ID 검증**: 사용자가 타인 거래의 VDR 문서 ID를 전달하면 해당 문서에 접근 가능한지
- [ ] **JWT claims.email 위조**: JWT 토큰의 email 클레임이 실제 사용자와 일치하는지 검증 여부
- [ ] **Celery 태스크 직접 호출**: `run_finalize_and_generate_task.delay(fm_id=..., transaction_id=...)` — fm_id/txn_id 조합의 유효성을 태스크 내에서 재검증하는지
- [ ] **생성된 파일 접근 제어**: `generated/financial_models/` 디렉토리에 대한 OS 레벨 접근 제어

---

## 7단계: 테스트 완성도 (Test Coverage)

`tests/test_financial_models.py`의 23개 테스트를 읽고:

### 커버리지 갭 분석

| 시나리오 | 테스트 존재 | 우선순위 |
|---------|-----------|---------|
| FM CRUD (list/create/get/delete) | ✅ | — |
| FM regenerate | ✅ | — |
| 체크리스트 자동 생성 (33항목) | ✅ | — |
| 체크리스트 항목 단일 수정 | ✅ | — |
| 체크리스트 일괄 수정 | ✅ | — |
| 체크리스트 finalize | ✅ | — |
| cascade 삭제 | ✅ | — |
| 교차 거래 격리 | ✅ | — |
| download (READY 상태) | ✅ | — |
| download (비READY 상태) | ✅ | — |
| **Celery 태스크 실행** | ? | HIGH |
| **Ralph Loop 통합** | ? | HIGH |
| **Excel 생성 + 파일 검증** | ? | HIGH |
| **동시 finalize 호출** | ? | MEDIUM |
| **만료된 txn_id로 FM 생성** | ? | MEDIUM |
| **잘못된 VDR doc ID** | ? | MEDIUM |
| **비인가 사용자 접근** | ? | HIGH |
| **Enum 값 외 입력** | ? | LOW |

- [ ] 위 표에서 `?`인 항목의 테스트 존재 여부를 `Grep`으로 확인
- [ ] 누락된 테스트 중 HIGH 우선순위 항목을 이슈로 보고

---

## 8단계: 마이그레이션 안전성 (Migration Safety)

`020_financial_models.py` 검증:

- [ ] **upgrade()**: 3개 테이블 + 6개 Enum + 인덱스 생성 순서가 FK 의존성을 만족하는지
- [ ] **downgrade()**: 역순 삭제 + Enum 타입 DROP이 올바른지
- [ ] **FK CASCADE 설정**: `ON DELETE CASCADE`가 모든 FK에 적용되어 있는지
- [ ] **기존 데이터 영향**: 순수 CREATE 마이그레이션이므로 기존 데이터 손실 리스크 없음 — 확인
- [ ] **이전 마이그레이션(019)과의 의존**: `ralph_sessions` 테이블 FK가 존재하므로 019 마이그레이션이 먼저 실행되어야 함 — 의존 체인 확인

---

## 9단계: 허위 리뷰 방지 검증 (Anti-False-Positive)

**모든 이슈를 보고하기 전에 반드시 아래 5개 항목을 검증.**

- [ ] **SC-1 도달 가능성**: 이 코드가 실제로 실행되는 경로에 있는가?
- [ ] **SC-2 부재 주장 검증**: "X가 없다"는 주장을 `Grep`으로 전체 코드베이스에서 확인했는가?
- [ ] **SC-3 프레임워크 처리**: FastAPI, SQLAlchemy, React Query가 이미 처리하는 부분을 지적하고 있지 않은가?
- [ ] **SC-4 의도된 패턴**: deal-mgmt의 다른 라우터/서비스에서 동일 패턴이 사용되고 있지 않은가?
- [ ] **SC-5 수정 안전성**: 제안한 수정이 타입 에러, 런타임 에러, cascade 삭제 문제를 야기하지 않는가?

---

## 출력 형식

### 리뷰 요약
```
- 총 이슈 수: N개 (Critical: X, Major: Y, Moderate: Z, Minor: W)
- 카테고리별: 상태머신 N, 아키텍처 N, Celery N, 프론트엔드 N, 도메인 N, 보안 N, 테스트 N
- 전체 평가: {한 줄 요약}
```

### 이슈 목록 (심각도 내림차순)

각 이슈:
```
### [{심각도}] {이슈 제목}
- **위치**: `파일경로:라인번호`
- **카테고리**: 상태머신 / 아키텍처 / Celery / 프론트엔드 / 도메인 / 보안 / 테스트
- **신뢰도**: HIGH / MEDIUM / LOW
- **셀프 체크**: SC-1(✓) SC-2(✓) SC-3(✓) SC-4(✓) SC-5(✓)
- **근거**: (실제 Read로 읽은 코드 스니펫)
- **설명**: 무엇이 문제인지
- **영향**: 문제가 발생하면 어떤 일이 일어나는지
- **수정 제안**: 구체적인 코드 변경 방향
```

### FE ↔ BE 타입 계약 대조표

| FE 타입/Enum | BE 스키마/Enum | 일치 여부 | 불일치 상세 |
|-------------|-------------|---------|-----------|
| FinancialModelType (6값) | FinancialModelType (6값) | ✅/❌ | {상세} |
| FinancialModelStatus (6값) | FinancialModelStatus (6값) | ✅/❌ | {상세} |
| ... | ... | ... | ... |
| FinancialModel (18필드) | FinancialModelOut (18필드) | ✅/❌ | {상세} |
| ... | ... | ... | ... |

### 테스트 커버리지 갭

| 누락 시나리오 | 우선순위 | 권장 테스트 |
|-------------|---------|-----------|
| ... | HIGH/MEDIUM/LOW | {테스트 설명} |

## 핵심 원칙
- **추측 금지**: 모든 주장은 `Read`/`Grep` 확인 기반
- **증거 첨부 필수**: 실제 코드 스니펫으로 근거 제시
- **허위 양성 방지**: SC-1~5 셀프 체크 통과한 이슈만 보고
- **상태 머신 우선**: 재무모델의 가장 큰 리스크는 잘못된 상태 전이 — 1단계를 가장 깊이 검증
- **deal-mgmt 패턴 비교**: 동일 모듈의 다른 라우터(vdr.py, meeting_logs.py 등)와 패턴 비교하여 정합성 확인
````
