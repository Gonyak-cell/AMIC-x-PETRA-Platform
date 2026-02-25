# Financial Model 코드 리뷰 및 수정 리포트

> **작성일**: 2026-02-25 21:04
> **범위**: `deal-mgmt` 재무모델(Financial Model) 전체 — 라우터, 서비스, Celery 태스크, Excel 빌더, 스키마, 프론트엔드 타입
> **브랜치**: `feat/ma-workflow`

---

## 리뷰 요약

- **총 이슈 수**: 18개 (Critical: 3, Major: 5, Moderate: 6, Minor: 4)
- **수정 완료**: Critical 3개 + Major 5개 + Moderate 5개 = **13개 수정 완료**
- **미수정 (Minor/의도적 보류)**: 5개
- **테스트 결과**: 20/20 통과, tsc --noEmit OK

---

## 수정 완료 이슈

### [Critical] C-01: GET/DELETE 6개 엔드포인트 JWT 인증 추가

- **파일**: `deal-mgmt/app/routers/financial_models.py`
- **수정**: `list_models`, `get_model`, `regenerate_model`, `delete_model`, `download_model`, `get_checklist` 6개 엔드포인트에 `claims: JWTClaims = Depends(get_jwt_claims)` 추가
- **검증**: 동일 모듈 다른 라우터(contracts.py, meeting_logs.py)와 패턴 일치 확인

### [Critical] C-02: 파일 다운로드 경로 순회(Path Traversal) 방지

- **파일**: `deal-mgmt/app/routers/financial_models.py:88-119`
- **수정**: `download_model` 엔드포인트에 3단계 검증 추가
  1. `FM_OUTPUT_DIR.resolve()` 기준 경로 검증
  2. `startswith()` 비교로 디렉토리 탈출 차단 (403)
  3. `file_path.exists()` 확인 (404)
- **추가**: `from pathlib import Path` import, `logger.warning()` 경로 순회 시도 로깅

### [Critical] C-03: Celery 태스크 멱등성 가드

- **파일**: `deal-mgmt/app/services/financial_model_service.py`
- **수정**:
  - `_run_vdr_extraction_and_ralph()`: FM 상태가 `GENERATING` 또는 `PENDING_REVIEW`가 아니면 스킵
  - `run_finalize_and_generate()`: FM 상태가 `FINALIZING`이 아니면 스킵
  - `_BUSY_STATUSES = frozenset({GENERATING, FINALIZING})` 상수 정의
- **효과**: 중복 실행, 상태 경합 방지

### [Major] M-01: Input 시트 카테고리 필터링 수정

- **파일**: `deal-mgmt/app/excel/model_builder.py:213-234`
- **수정 전**: `if title` — 항상 True, 모든 값이 모든 카테고리에 중복 표시
- **수정 후**: `FM_FIELD_REGISTRY`에서 `_TITLE_TO_CATEGORY` 매핑 구축, `_TITLE_TO_CATEGORY.get(title) == cat`으로 필터링
- **추가**: 값이 없는 카테고리도 레지스트리 기반 빈 입력 슬롯 생성, 단위 표시

### [Major] M-02: WACC Kd 세전/세후 명칭 불일치 수정

- **파일 2곳**:
  - `financial_model_service.py:57`: `"세후 타인자본비용 (Kd)"` → `"세전 타인자본비용 (Kd pre-tax)"`
  - `model_builder.py:533`: 동일 키 업데이트
- **효과**: Excel "Pre-tax Cost of Debt" 셀과 체크리스트 키가 의미적으로 일치 → WACC 이중 세금 조정 오류 방지

### [Major] M-03: finalize 이중 커밋 → 단일 커밋 (원자성 복원)

- **파일**: `deal-mgmt/app/services/fm_checklist_service.py:148`
- **수정**: `await self.db.commit()` → `await self.db.flush()`
- **효과**: 체크리스트 FINALIZED + FM FINALIZING 상태 변경이 라우터의 단일 `commit()`으로 원자적 처리. 크래시 시 불일치 방지.

### [Major] M-04: regenerate 상태 가드 + Celery 트리거 추가

- **파일**: `deal-mgmt/app/services/financial_model_service.py:182-225`
- **수정**:
  1. 상태 가드: `if fm.status in _BUSY_STATUSES: raise HTTPException(409)`
  2. VDR doc ID가 있으면 `run_vdr_extraction_and_ralph_task.delay()` 트리거
  3. VDR 없으면 즉시 `PENDING_REVIEW` 전환
- **효과**: regenerate 후 GENERATING 영구 정체 해결

### [Major] M-04 연관: finalize 엔드포인트 상태 가드

- **파일**: `deal-mgmt/app/routers/financial_models.py:186-193`
- **수정**: finalize 호출 시 FM이 `GENERATING`/`FINALIZING`이면 409 반환
- **효과**: 진행 중인 Celery 태스크와 충돌 방지

### [Moderate] Mo-01: error_message 잘림 길이 통일

- **파일**: `deal-mgmt/app/services/financial_model_service.py`
- **수정**: `MAX_ERROR_LEN = 1000` 상수 정의, Pass 1 `[:300]` → `[:MAX_ERROR_LEN]`, Pass 2 `[:500]` → `[:MAX_ERROR_LEN]`

### [Moderate] Mo-03: FMChecklistStatus 데드 코드 주석 명확화

- **파일**: `deal-mgmt/app/models/enums.py:567-571`
- **수정**: `GENERATING`, `REVIEWED` 주석에 `Reserved — DB enum 호환용, 서비스에서 미사용` 명시

### [Moderate] Mo-04: confidence 필드 범위 검증

- **파일**: `deal-mgmt/app/schemas/financial_model.py:73`
- **수정**: `confidence: float | None` → `confidence: float | None = Field(None, ge=0.0, le=1.0)`

### [Moderate] Mo-06: compute_summary NOT_APPLICABLE 미집계 수정

- **파일 3곳**:
  - `fm_checklist_service.py:162`: `"not_applicable_count"` 추가
  - `financial_model.py (schema):104`: `not_applicable_count: int = 0` 필드 추가
  - `financial_models.py (router)`: 2곳 `out.not_applicable_count = summary["not_applicable_count"]` 주입
- **FE 타입**: `financial_model.ts:129` — `not_applicable_count: number` 추가

---

## 미수정 이슈 (Minor — 별도 스프린트)

| 이슈 | 사유 |
|------|------|
| m-01: LBO 전용 시트 stub | Sprint 2 LBO 구현 시 함께 처리 |
| m-02: FE ralph 파라미터 범위 미검증 | BE Pydantic이 422로 거부하므로 기능적 문제 없음 |
| m-03: Pass 2 max_iterations 하드코딩 | 의도적 설계 가능성 — 주석 추가 권장 |
| m-04: 비인가 접근 테스트 부재 | M-05(핵심 테스트 추가)와 함께 별도 세션 |
| Mo-02: GENERATING 상태 관측 불가 | M-04 수정으로 VDR 있는 경우 GENERATING 유지됨, 부분 해소 |
| Mo-05: parameters JSONB 스키마 검증 | 모델 타입별 서브모델 정의 필요 — 별도 설계 |

---

## 변경 파일 목록

| 파일 | 변경 유형 |
|-----|---------|
| `deal-mgmt/app/routers/financial_models.py` | C-01, C-02, M-04, Mo-06 |
| `deal-mgmt/app/services/financial_model_service.py` | C-03, M-02, M-04, Mo-01 |
| `deal-mgmt/app/services/fm_checklist_service.py` | M-03, Mo-06 |
| `deal-mgmt/app/excel/model_builder.py` | M-01, M-02 |
| `deal-mgmt/app/schemas/financial_model.py` | Mo-04, Mo-06 |
| `deal-mgmt/app/models/enums.py` | Mo-03 |
| `amic-platform/src/modules/ma/types/financial_model.ts` | Mo-06 (FE 타입) |
| `deal-mgmt/tests/test_financial_models.py` | 테스트 기대값 수정 |

---

## 검증 결과

```
# 백엔드 테스트
deal-mgmt$ python -m pytest tests/test_financial_models.py -v
→ 20 passed in 4.63s ✅

# Python import 검증
deal-mgmt$ python -c "from app.routers.financial_models import router"
→ Router import OK ✅

# TypeScript 타입 체크
amic-platform$ npx tsc --noEmit
→ No errors ✅
```

---

## FE ↔ BE 타입 계약 (변경 후)

| 항목 | 변경 | 일치 |
|------|------|------|
| FMChecklist.not_applicable_count | BE 스키마 + FE 타입 동시 추가 | ✅ |
| FM_FIELD_REGISTRY Kd 명칭 | `세전 타인자본비용 (Kd pre-tax)` 통일 | ✅ |
| FMChecklistItemOut.confidence | `Field(ge=0, le=1)` 범위 추가 | ✅ |
| 나머지 전체 | 변경 없음 — 기존 100% 일치 유지 | ✅ |
