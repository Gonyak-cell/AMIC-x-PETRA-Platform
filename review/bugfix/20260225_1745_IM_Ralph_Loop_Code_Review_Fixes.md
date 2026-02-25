# IM Ralph Loop 코드 리뷰 — 8건 버그 수정

> 작성: 2026-02-25 17:45 | 브랜치: `feat/ma-workflow`

## 개요

IM Ralph Loop 2-Pass 구현(Session 34~37) 완료 후, 실제 코드베이스를 기반으로 전체 리뷰를 수행했다.
3개 탐색 에이전트 + 수동 검증을 통해 허위 리뷰 3건을 걸러내고, 실제 런타임 오류를 발생시키는 **8건의 버그를 확정·수정**했다.

## 허위 리뷰 검증 (수정 불필요 3건)

| # | 에이전트 지적 | 검증 결과 | 근거 |
|---|-------------|----------|------|
| 1 | `from src.ralph...` Import 경로 오류 | **FALSE** | IM Docker의 PYTHONPATH에 `im/` 포함, 기존 패턴과 동일 |
| 2 | `orchestrator.py` log_error_with_input 누락 | **FALSE** | 의도적 제거, IM 이식본에서 미사용 |
| 3 | status가 문자열 (Enum 아님) | **FALSE** | IM 전체 코드베이스와 일관 (Document 모델 동일 패턴) |

## 수정 요약 (8건)

### CRITICAL (6건)

**Bug 1: IMDocumentGenerator 생성자 시그니처 불일치**
- 위치: `ralph_loop.py:251-254` → `im_generator.py:32-41`
- 문제: `IMDocumentGenerator(api_config=..., llm_client=...)` 호출 — 존재하지 않는 파라미터
- 수정: `im_data_dict` 파라미터를 Celery 체인 전체에 전달
  - `ralph_loop.py`: 태스크 시그니처에 `im_data_dict` 추가 + fallback 로직
  - `generate_im.py:477`: `.delay(im_data_dict=im_data_dict)` 추가
  - `generate_im_from_checklist.py:231`: `im_data_to_dict(im_data)` 직렬화 후 전달

**Bug 2: LoopConfig 필드 불일치**
- 위치: `ralph_loop.py:239-243`
- 문제: `LoopConfig(max_iterations=..., pass_threshold=..., budget_usd=...)` — 존재하지 않는 필드
- 수정: `ConvergenceConfig` 분리 생성 후 `LoopConfig(convergence=convergence)`

**Bug 3: RalphLoopOrchestrator 필수 `prd` 누락**
- 위치: `ralph_loop.py:257-261`
- 문제: `RalphLoopOrchestrator(generator, gates, config)` — 필수 `prd` 파라미터 미전달
- 수정: `prd=prd` 추가

**Bug 4: orchestrator.run() 파라미터 오류**
- 위치: `ralph_loop.py:270-273`
- 문제: `await orchestrator.run(prd_sections=prd, source_data=source_data)` — 존재하지 않는 kwarg
- 수정: `await orchestrator.run(source_data)`

**Bug 5: IMDocumentData.from_dict() 미존재**
- 위치: `im_generator.py:43-47`
- 문제: `IMDocumentData.from_dict(self._im_data_dict)` — 메서드 없음 (grep 확인)
- 수정: `serializers.dict_to_im_data()` 재사용

**Bug 6: IMDocumentData.to_dict() 미존재**
- 위치: `im_generator.py:167`
- 문제: `im_data.to_dict()` — 메서드 없음 (grep 확인)
- 수정: `serializers.im_data_to_dict()` 재사용

### HIGH (1건)

**Bug 7: result.progress.to_dict() 중복 호출**
- 위치: `ralph_loop.py:281`
- 문제: `result.progress`는 이미 dict (orchestrator.py:186에서 `self._tracker.to_dict()`)
- 수정: `.to_dict()` 호출 제거

### MEDIUM (1건)

**Bug 8: LLMClient.from_config() 모델명 미전달**
- 위치: `llm_client.py:262-268`
- 문제: `primary_model`, `judge_model`이 기본값만 사용 — config 설정 무시
- 수정: `getattr(config, "ralph_primary_model", ...)` + `getattr(config, "ralph_judge_model", ...)` 추가

## 수정 파일 (5개)

| 파일 | 변경 내용 |
|------|----------|
| `im/src/ralph/im_generator.py` | Bug 5,6: from_dict/to_dict → serializers 재사용 |
| `im/src/api/tasks/ralph_loop.py` | Bug 1,2,3,4,7: 전면 수정 |
| `im/src/api/tasks/generate_im.py` | Bug 1-B: im_data_dict 전달 |
| `im/src/api/tasks/generate_im_from_checklist.py` | Bug 1-C: im_data_dict 직렬화 전달 |
| `im/src/ralph/llm_client.py` | Bug 8: from_config 모델명 전달 |

## 검증

- [x] Python 구문 검사: 5개 파일 `py_compile` 통과
- [x] TypeScript 타입 검사: `tsc --noEmit` 통과
- [x] Vite 빌드: `vite build` 15.87s 통과
