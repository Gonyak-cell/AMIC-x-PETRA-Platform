# LDD RalphSession doc_type 불일치 수정 + 실패 처리 개선

> 2026-02-25 17:27 | P0 버그 수정 + P2 모범사례 개선

## 배경

FDD 대비 LDD Ralph Loop 갭 분석 후 4건(P0 2건, P1 1건, P2 1건)을 구현했다.
구현 후 3개 병렬 에이전트(서비스 리뷰, 게이트 리뷰, 시스템 교차검증)로 전면 코드 리뷰를 수행하여
**P0 실제 버그 1건** + **P2 권고 2건**을 발견하고 수정했다.

---

## P0 BUG: doc_type 불일치 (학습 패턴 영구 미적재)

### 근본 원인

| 위치 | 값 | 역할 |
|------|-----|------|
| `ldd_report_service.py:664` (Pass 1 저장) | `doc_type=prd_key` → `"ldd_full"` | DB 저장 |
| `ldd_report_service.py:879` (Pass 2 저장) | `doc_type="ldd_full"` | DB 저장 |
| `ldd_report_service.py:404,632,832` (쿼리) | `get_learned_patterns("LDD")` | DB 조회 |
| `pattern_aggregator.py:42` | `WHERE doc_type = 'LDD'` | 필터 |

**결과**: `"ldd_full" != "LDD"` → 학습 패턴 쿼리 결과 항상 0건 (영구 불일치)

### 확정 근거

1. `pattern_aggregator.py:42` — `RalphSession.doc_type == doc_type` 정확 매치 필터
2. `ldd_report_service.py:404,632,832` — 3곳 모두 `"LDD"` 쿼리
3. `ldd_report_service.py:664` — `doc_type=prd_key` = `"ldd_full"` 저장
4. `ldd_report_service.py:879` — `doc_type="ldd_full"` 하드코딩 저장
5. `ralph.py:284` — 범용 라우터는 `doc_type=body.doc_type` 저장 + `get_learned_patterns(body.doc_type)` 쿼리 → 일관됨 (대조 근거)
6. `test_ralph_learning.py:146` — fixture는 `doc_type="LDD"` 사용 (쿼리와 일치)

### 수정

- Pass 1: `doc_type=prd_key` → `doc_type="LDD"`
- Pass 2: `doc_type="ldd_full"` → `doc_type="LDD"`

---

## P2 권고: 실패 시 RalphSession FAILED 상태 업데이트

### 문제

`orchestrator.run()` 실패 시 `except` 블록에서 `ralph_session`을 업데이트하지 않아 DB에 `PLANNING` 상태로 영구 방치.
학습 패턴 쿼리는 `COMPLETED`만 필터하므로 기능상 버그는 아니지만, 모니터링/정리 관점에서 불완전.

### 수정

Pass 1/2 except 블록에 추가:
```python
try:
    ralph_session.status = RalphSessionStatus.FAILED
    ralph_session.error_message = str(exc)[:500]
except NameError:
    pass  # ralph_session 생성 이전에 실패한 경우
```

---

## 전면 리뷰 정상 확인 항목 (15건, 허위 양성 0건)

| 항목 | 결과 |
|------|------|
| Import 정합성 (RalphSession, RalphSessionStatus) | OK |
| 모델 컬럼 매핑 (13개 필드) | OK |
| LoopResult 속성 접근 (8개 필드 + `.value`) | OK |
| DOCXProgrammaticGate `__init__` 하위호환 (10개 호출처) | OK |
| QualityGate base class — super 불필요 | OK |
| 가중치 합계 (Pass 1: 1.00, Pass 2: 1.00) | OK |
| `_check_review_alignment` 로직 | OK |
| DOCX 모드에서 user_reviews 미사용 | OK |
| `orchestrator.session_id` str→UUID 변환 | OK |
| `loop_result.status` StrEnum → `.value` | OK |
| `LDDFinalizeRequest` 스키마 필드 존재 | OK |
| PatternAggregator 호출 시그니처 일관성 | OK |
| user_reviews 구성 (approved/rejected) | OK |
| Pass 2 예산 캡 `min(3)`, `min($10)` | OK |
| flush/commit 순서 (트랜잭션 일관성) | OK |

---

## 수정 파일

| 파일 | 수정 | 심각도 |
|------|------|--------|
| `deal-mgmt/app/services/ldd_report_service.py:664` | Pass 1 `doc_type="LDD"` | P0 |
| `deal-mgmt/app/services/ldd_report_service.py:879` | Pass 2 `doc_type="LDD"` | P0 |
| `deal-mgmt/app/services/ldd_report_service.py:741` | Pass 1 except 블록 FAILED 처리 | P2 |
| `deal-mgmt/app/services/ldd_report_service.py:961` | Pass 2 except 블록 FAILED 처리 | P2 |

## 테스트 결과

- `pytest deal-mgmt/tests/ (Ralph + LDD)` — **109 passed**, 14 skipped, 0 errors
