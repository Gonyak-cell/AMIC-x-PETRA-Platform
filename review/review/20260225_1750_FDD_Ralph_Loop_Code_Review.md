# FDD Ralph Loop 2-Pass 품질 개선 시스템 — 코드 리뷰

> 작성: 2026-02-25 17:50
> 대상: FDD Ralph Loop 전체 구현 (7 Steps)
> 상태: **✅ 리뷰 완료 — 버그 3건 수정 완료**

## 리뷰 범위

| 영역 | 파일 수 | 검증 방법 |
|------|--------|----------|
| 코어 모듈 (ralph/) | 10 | 코드 Read + 원본 deal-mgmt 비교 |
| API/스키마/서비스 | 4 | URL·필드 정합성 교차 검증 |
| DB 모델/마이그레이션 | 2 | 컬럼 1:1 매핑 확인 |
| 프론트엔드 훅/타입 | 2 | URL·타입 매칭 검증 |
| 테스트 | 3 (39 tests) | 실행 + 구조 검증 |
| 기존 테스트 | 1369+70 | 회귀 분석 |

## 검증된 항목 (정상 — 수정 불필요)

| 영역 | 상태 | 검증 내용 |
|------|------|----------|
| 코어 포팅 정합성 | ✅ | orchestrator, convergence, progress_tracker, gates/base — deal-mgmt 원본과 동기화 |
| DocumentGenerator Protocol | ✅ | FDDReportGenerator가 3개 메서드 올바르게 구현 |
| Convergence 5개 종료 조건 | ✅ | PASSED, DETERIORATED, DIMINISHING_RETURNS, MAX_ITERATIONS, BUDGET_EXCEEDED |
| Gate 1 (Programmatic) 5개 차원 | ✅ | numerical_consistency(0.30) + evidence_coverage(0.25) + placeholder_absence(0.20) + structure_completeness(0.15) + checklist_alignment(0.10) = 1.0 |
| Gate 2 (LLM Judge) 6개 차원 | ✅ | numerical_accuracy(0.25) + completeness(0.20) + analytical_depth(0.20) + professionalism(0.15) + evidence_linking(0.15) + confidentiality(0.05) = 1.0 |
| Learning 모듈 | ✅ | PatternAggregator(`get_learned_patterns(pass_type=)`) + LearningPromptInjector |
| PRD JSON | ✅ | 6개 섹션 + global_criteria + convergence draft/final 설정 |
| DB 모델 ↔ 마이그레이션 | ✅ | 20개 컬럼 1:1 매핑, FK `deal.id` 수정 완료 |
| API URL ↔ 프론트엔드 훅 | ✅ | 4개 엔드포인트 URL 정확히 일치 |
| 스키마 필드 ↔ FE 타입 | ✅ | RalphSessionRead 15개 필드 모두 일치 |
| 서비스 → Orchestrator 통합 | ✅ | run_draft_pass/run_final_pass → LoopConfig → LoopResult → session 업데이트 |
| import 경로 | ✅ | 모든 `app.ralph.*` 경로 유효 |
| LoopResult.status.value | ✅ | LoopStatus(StrEnum) → `.value`로 문자열 변환 후 세션에 저장 |

## 발견된 버그 및 수정 내역

### BUG-1: Refined IR이 docx/xlsx/pptx에 적용되지 않음 [Critical] — ✅ 수정 완료

**위치**: `fdd/backend/app/api/reports.py`

**문제**: `generate_report()`에서 `ralph_enabled=True`일 때 JSON 출력만 Refined IR을 사용하고, docx/xlsx/pptx 렌더러에는 원본 `report_ir` 객체를 그대로 전달.

**수정**: `_patch_report_ir(report_ir, ir_dict)` 함수 추가 (156-187행). Ralph refined IR dict의 텍스트 필드를 원본 ReportIR 객체에 in-place 패치:
- `TextBlock`: `content`, `bullet_points`
- `ClaimBlock`: `claim_text`
- `IssueBlock`: 각 issue의 `description`, `recommendation`

Line 79-81에서 렌더러 호출 전에 패치 적용:
```python
if ir_dict:
    _patch_report_ir(report_ir, ir_dict)
```

### BUG-2: 테스트 픽스처가 실제 IR 구조와 불일치 [Medium] — ✅ 수정 완료

**위치**: `fdd/backend/tests/test_fdd_ralph.py`

**문제**: `sample_ir_dict` 픽스처에서 TextBlock이 `"body"` 필드를 사용. 실제 `TextBlock` dataclass는 `content` 필드 사용 (`report_builder.py:181`).

**수정**: 4곳 `"body"` → `"content"` 변경:
- Line 64: Executive Summary
- Line 69: QoE Commentary

### MINOR-1: mock_llm_call 반환값 구조도 content로 변경 [Low] — ✅ 수정 완료

**위치**: `fdd/backend/tests/test_fdd_ralph.py`

**수정**: Line 114, 178: `"body"` → `"content"`

## 기존 테스트 실패 분석 — Ralph과 무관

### test_uploads.py (65개 실패) — 수정 불필요

**근본 원인**: `AUTH_ENABLED=True` (기본값)에서 인증 헤더 없이 요청 → 401 Unauthorized. `_create_deal(client)`가 헤더 미포함. `TESTING=true AUTH_ENABLED=false pytest` 실행 시 정상 통과. Ralph Loop 변경과 완전히 무관.

### security tests (5개 에러) — 수정 불필요

**근본 원인**: `security/conftest.py`의 `deal_by_admin` 픽스처에서 딜 생성 실패 (422). Ralph Loop 변경과 완전히 무관.

## 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `fdd/backend/app/api/reports.py` | 함수 추가 | `_patch_report_ir()` 함수 + 호출 (79-81, 156-187행) |
| `fdd/backend/tests/test_fdd_ralph.py` | 필드명 수정 | `"body"` → `"content"` 4곳 (64, 69, 114, 178행) |

## 검증 결과

```
# Ralph Loop 테스트: 39/39 PASSED
# Report API 회귀: PASSED
# 전체 FDD 백엔드: 1369 passed, 65 failed (기존 auth 이슈), 5 errors (기존 security 이슈)
# 프론트엔드 tsc --noEmit: PASSED
```
