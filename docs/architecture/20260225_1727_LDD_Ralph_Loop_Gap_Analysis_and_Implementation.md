# LDD Ralph Loop 품질 갭 분석 및 보완 구현

> 2026-02-25 17:27 | FDD 실제 코드베이스 대비 LDD Ralph Loop 갭 분석 + 보완 + 리뷰 + 버그 수정

## 1. 개요

FDD 백엔드(`fdd/backend/app/ralph/`)에 2-Pass Ralph Loop가 완전 구현되었다.
LDD(`deal-mgmt/app/ralph/`)도 Ralph Loop를 사용하지만, FDD 대비 4건의 갭이 존재했다.
이 작업에서 갭을 식별 → 구현 → 전면 코드 리뷰 → 리뷰에서 발견된 P0 버그 수정까지 완료했다.

---

## 2. FDD vs LDD 갭 분석 결과

### 갭 발견 (4건)

| # | Feature | FDD 구현 | LDD 상태 | 심각도 |
|---|---------|---------|---------|--------|
| 1 | **세션 영속화** | `FddRalphSession` 생성→업데이트→커밋 | 저장 안 함 (UUID만 기록) | **P0** |
| 2 | **학습 패턴 축적** | pass_type별 패턴 분리, DB 축적 | 세션 미저장 → 데이터 없음 | **P0** |
| 3 | **Pass 2 리뷰 반영 검증** | `checklist_alignment` (10%) | 해당 차원 없음 | **P1** |
| 4 | **Pass 2 예산 기본값** | `$5 하드코딩` (max_iter=2) | 프론트엔드 의존 (기본값 없음) | **P2** |

### 갭 없음 확인 (5건)

| # | Feature | 결론 |
|---|---------|------|
| 5 | 전용 게이트 클래스 | 공용 게이트의 `doc_type` 분기로 기능 동등 |
| 6 | Generator 블록 구분 | 도메인 차이 (FDD: Report IR 블록, LDD: 체크리스트 항목) |
| 7 | PRD | `ldd_full.json` 10개 섹션 + `global_criteria` 완비 |
| 8 | Convergence | 동일 `ConvergenceChecker` 코어 사용 |
| 9 | LLM Judge 차원 | LDD용 6차원 + 법률실사 특화 프롬프트 |

---

## 3. 구현 내역

### Task 1: RalphSession 영속화 (P0)

**수정 파일**: `deal-mgmt/app/services/ldd_report_service.py`

- Pass 1 (`create_ldd_report_from_vdr()`): orchestrator.run() 전 `RalphSession` 생성 → flush → 실행 후 결과 업데이트
- Pass 2 (`finalize_ldd_report()`): 동일 패턴 적용

### Task 2: 학습 패턴 축적 (P0 — Task 1 종속)

추가 코드 불필요. Task 1 완료 시 `PatternAggregator.get_learned_patterns("LDD")`가 자동으로 데이터 반환.

### Task 3: review_alignment 차원 추가 (P1)

**수정 파일**: `deal-mgmt/app/ralph/gates/docx_gate.py`

- `__init__(user_reviews=None)` 파라미터 추가 (하위호환)
- `_check_review_alignment()` 메서드: 반려 항목 재분석 여부 검증
- Pass 2에서 6차원 (0.15+0.25+0.15+0.15+0.20+0.10 = 1.00)
- Pass 1에서 5차원 (0.20+0.30+0.15+0.15+0.20 = 1.00)

### Task 4: Pass 2 예산 안전장치 (P2)

- `max_iterations_per_section = min(body.max_iterations, 3)`
- `max_cost_usd = min(body.max_cost_usd, 10.0)`

---

## 4. 전면 코드 리뷰 결과

3개 병렬 에이전트로 리뷰:

### 발견된 이슈

| # | 심각도 | 위치 | 이슈 |
|---|--------|------|------|
| 1 | **P0 BUG** | `ldd_report_service.py:664,879` | doc_type 불일치 — 저장 `"ldd_full"` vs 쿼리 `"LDD"` → 학습 패턴 영구 미적재 |
| 2 | P2 | `ldd_report_service.py:741,961` | orchestrator.run() 실패 시 RalphSession PLANNING 상태 방치 |
| 3 | P2 | `ldd_report_service.py:425-432` | `create_ldd_report_from_file()` 경로에 RalphSession 미구현 (범위 외) |

### 정상 확인 (15건, 허위 양성 0건)

Import 정합성, 모델 컬럼 매핑, LoopResult 속성 접근, 하위호환성, 가중치 합계, review_alignment 로직, 타입 변환, 스키마 필드 존재, flush/commit 순서 등 15개 검증 항목 모두 통과.

---

## 5. 리뷰 후 수정 내역

### P0 수정: doc_type 불일치

```python
# AS-IS (Pass 1): doc_type=prd_key → "ldd_full"
# AS-IS (Pass 2): doc_type="ldd_full"
# TO-BE (Both):   doc_type="LDD"
```

### P2 수정: 실패 시 RalphSession FAILED 상태

Pass 1/2 except 블록에 추가:
```python
try:
    ralph_session.status = RalphSessionStatus.FAILED
    ralph_session.error_message = str(exc)[:500]
except NameError:
    pass
```

---

## 6. 수정 파일 전체 목록

| 파일 | 수정 내용 |
|------|---------|
| `deal-mgmt/app/services/ldd_report_service.py` | Pass 1/2 RalphSession 영속화, doc_type="LDD" 수정, 예산 캡, user_reviews 전달, except FAILED 처리 |
| `deal-mgmt/app/ralph/gates/docx_gate.py` | `user_reviews` 파라미터, `review_alignment` 차원, 가중치 재조정 |

## 7. 테스트 결과

- Ralph + LDD 관련 테스트: **109 passed**, 14 skipped, 0 errors
- DOCXProgrammaticGate 단독 검증: Pass 1→5차원, Pass 2→6차원, 가중치 합 1.0 확인
