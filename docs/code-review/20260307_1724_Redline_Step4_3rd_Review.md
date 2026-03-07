# Redline Step 4 — 3차 통합 리뷰 (Phase A~D 수정 후 최종 검증)

> **Review Date**: 2026-03-07 17:24
> **Reviewer**: Claude Code (4-Agent Parallel Review)
> **Scope**: deal-mgmt Step 4 교차 검증 + Tracked Changes .docx 생성 API
> **Method**: 4개 전문 에이전트 병렬 디스패치 (보안 R1-R3, 코드품질 R4-R6, 성능 R7-R9, 테스트/통합 R10-R13)
> **Context**: 이전 2차 리뷰(27건) Phase A~D 수정 완료 후, 수정 코드 기반 최종 검증 리뷰

---

## 이전 수정 재검증

Phase A~D에서 수정된 27건 모두 4개 에이전트가 재보고하지 않음 = 수정 완료 확인.

---

## Summary

| Severity | Count | Priority Distribution |
|----------|-------|-----------------------|
| Critical | 2 | P0: 1 / P1: 1 |
| Major | 5 | P1: 5 |
| Moderate | 13 | P2: 13 |
| Minor/Suggestion | 10 | P3: 10 |
| **Total** | **30** | P0: **1** / P1: **6** / P2: **13** / P3: **10** |

**Cross-Agent Deduplication**: 원본 34건 -> 4건 중복 병합 -> 30건 최종
- SEC3-002 = PERF3-002 (repack 크기 무제한)
- SEC3-003 = CQ3-004 = PERF3-007 (멀티워커 rate limiter, 이전 FU-16 재보고)
- PERF3-008 ~ 이전 FU-17 (멀티워커 sessions, 재보고)

---

## P0 -- 즉시 수정 (1건)

### [R3-001] `_apply_segments` 다중 DEL 세그먼트 시 두 번째 DEL이 silent skip
- **관점**: R6 (비즈니스 로직)
- **출처**: CQ3-001
- **파일**: `redline_engine.py:681-690`
- **심각도**: Critical / HIGH

`proposed_redline`이 `[DEL]A[/DEL]KEEP[DEL]B[/DEL]` 형태일 때:
1. 첫 DEL 처리 후 `remaining_runs = []`
2. KEEP 세그먼트에서 `remaining_runs`가 빈 상태로 진입
3. 두 번째 DEL 시 `if seg.action == "DEL" and remaining_runs:` 조건이 False
4. 두 번째 DEL이 **완전히 무시**됨 -> Word에 원본 텍스트가 그대로 남음

런타임 오류 없이 silent하게 잘못된 결과물을 생성한다.

**수정**: `_apply_segments`에서 `remaining_runs` 소진 후 추가 DEL 세그먼트가 있으면 로그 경고 + comment로 매칭 실패 표시. 또는 `_collect_and_split_target_runs`가 세그먼트별 run 범위를 분리 반환하도록 리팩토링.

---

## P1 -- 스프린트 우선 (6건)

### [R3-002] `_repack_docx` 나머지 ZIP 항목 크기 검증 없음
- **관점**: R1 (보안) + R7 (메모리)
- **출처**: SEC3-002 + PERF3-002
- **파일**: `redline_engine.py:765`
- **심각도**: Major / HIGH (교차 검증됨)

```python
else:
    zf_out.writestr(item, zf_in.read(item.filename))  # 크기 무제한
```

`word/document.xml` 등 3개 파일만 `_read_zip_entry()`로 보호. 나머지 (이미지, 미디어 등)은 크기 제한 없이 읽음. 악의적 .docx에 15MB 임베디드 이미지 포함 시 메모리 폭증.

**수정**: `else` 분기에서도 `item.file_size` 사전 체크 + 스트리밍 복사 적용.

---

### [R3-003] `safe_name` 특수문자 미제거 -- Content-Disposition 헤더 인젝션
- **관점**: R2 (입력 검증)
- **출처**: SEC3-005
- **파일**: `spa_analysis.py:360-363`
- **심각도**: Moderate / HIGH -> **Major 상향** (외부 입력 -> HTTP 헤더 직접 영향)

```python
safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
safe_name = safe_name[:200]  # 길이만 제한, 특수문자 미제거
output_filename = f"{safe_name}_redline.docx"
```

파일명에 `"` (큰따옴표) 포함 시 `filename="say"hello_redline.docx"` -> Content-Disposition 헤더 파싱 깨짐.

**수정**: `safe_name = re.sub(r'[^\w\s\-\.]', '_', safe_name)` 등 특수문자 필터링 추가.

---

### [R3-004] `.rels` 파일 미존재 시 comments 관계 미등록 -> 댓글 유실
- **관점**: R6 (비즈니스 로직)
- **출처**: CQ3-002
- **파일**: `redline_engine.py:755-759`
- **심각도**: Critical / HIGH -> **P1** (발생 빈도 낮음: 정상 DOCX는 .rels 보유)

```python
if item.filename == "word/_rels/document.xml.rels" and comments_xml is not None:
    rels_data = _read_zip_entry(zf_in, item.filename)
    rels_data = _ensure_comments_relationship(rels_data)
```

`word/_rels/document.xml.rels` 파일이 없는 DOCX에서 comments.xml은 ZIP에 쓰이지만 관계 등록이 누락 -> Word에서 댓글 미표시.

**수정**: 루프 종료 후 `.rels` 파일이 없었으면 새 `.rels` 파일 생성하여 comment 관계 포함.

---

### [R3-005] `<w:ins>` 내부 run을 DEL 대상으로 지정 시 충돌 tracked changes
- **관점**: R6 (비즈니스 로직)
- **출처**: CQ3-003
- **파일**: `redline_engine.py:286-301, 488`
- **심각도**: Major / HIGH

기존 tracked changes가 있는 DOCX에서 LLM이 `<w:ins>` 내부 텍스트를 `original_target_text`로 선택 -> `_inject_deletion`이 이미 `<w:ins>` 내부에 있는 run을 `<w:del>`로 감쌈 -> OOXML 스펙상 유효하지만 Word에서 충돌하는 tracked changes로 표시.

**수정**: `_build_char_map`에서 `<w:ins>` 내부 run에 별도 플래그를 설정하고, `_inject_deletion` 시 해당 플래그가 있으면 `<w:ins>` 요소 전체를 먼저 "수락(accept)" 처리 후 삭제 적용.

---

### [R3-006] `_collect_and_split_target_runs` 직접 단위 테스트 없음
- **관점**: R10 (테스트 커버리지)
- **출처**: TEST3-001
- **파일**: `test_redline_engine.py` (누락)
- **심각도**: Critical / HIGH (테스트 부재이므로 P1)

핵심 알고리즘(문자 매핑 -> 경계 분할 -> Run 수집)이 직접 테스트되지 않음. 특히 start_run == end_run 케이스(동일 Run 내에서 시작/끝 모두 분할)에서 첫 번째 `_split_run_at` 후 `end_mapping.run_element`가 DOM에서 제거된 노드를 가리킬 위험.

**수정**: 3개 테스트 추가:
1. 단일 Run 중간 범위 수집 (start + end 분할 동시 발생)
2. start_run == end_run 케이스
3. 연속 여러 Run 범위 수집

---

### [R3-007] 세션 소유권 검증 fail-open 로직
- **관점**: R1 (인증/권한)
- **출처**: SEC3-006
- **파일**: `spa_analysis_service.py:121`
- **심각도**: Moderate / HIGH -> **Major 상향** (인증 우회 가능)

```python
if owner_user_id and session.owner_user_id and session.owner_user_id != owner_user_id:
    raise ValueError(...)
```

`session.owner_user_id`가 빈 문자열이면 검증 건너뜀 (fail-open). 세션 생성 시 빈 문자열이 설정되는 버그 경로가 있으면 모든 사용자가 해당 세션에 접근 가능.

**수정**: `if session.owner_user_id and owner_user_id != session.owner_user_id:` -- 세션에 소유자가 있으면 항상 검증.

---

## P2 -- 개선 권장 (13건)

### [R3-008] JSON 파싱 실패 시 재시도 없이 즉시 실패 (Step 1/2와 불일치)
- **출처**: CQ3-005 | **파일**: `spa_analysis_service.py:2151` | Major / MEDIUM
- Step 1/2는 `_call_llm_with_json` (재시도 포함), Step 4는 직접 `llm.call` 호출. LLM 응답이 JSON 아닌 경우 즉시 실패.
- **수정**: Step 4에서도 `_call_llm_with_json` 패턴 또는 재시도 로직 적용.

### [R3-009] `<w:r>` 내 복수 `<w:t>` 시 `_split_run_at` 텍스트 중복
- **출처**: CQ3-007 | **파일**: `redline_engine.py:403-419` | Moderate / HIGH
- 복수 `<w:t>`를 가진 run에서 `text_elem`이 두 번째 `<w:t>`이면 `run_after`에서 첫 번째 `<w:t>`가 원본 텍스트 전체를 유지 -> 텍스트 중복.
- **수정**: `_split_run_at`에서 분할 대상 `<w:t>` 외 나머지 `<w:t>`도 적절히 처리.

### [R3-010] Comment anchor에 `<w:del>`/`<w:ins>` 전달 시 순서 이상
- **출처**: CQ3-009 | **파일**: `redline_engine.py:261-267, 597-620` | Moderate / HIGH
- `_anchor_comment_to_run`이 `<w:del>`/`<w:ins>` 요소를 받으면 commentRangeEnd 위치가 revision mark와 겹침.
- **수정**: `_apply_segments` 반환 시 `last_processed_run`을 revision 요소가 아닌 실제 `<w:r>` 노드로 설정.

### [R3-011] `re.compile` 패턴 매번 컴파일
- **출처**: PERF3-003 | **파일**: `redline_engine.py:568` | Moderate / HIGH
- `_parse_redline_markup` 호출마다 `re.compile` 실행. 50 issue 기준 ~5ms.
- **수정**: 모듈 상단에 `_REDLINE_PATTERN = re.compile(...)` 정의.

### [R3-012] `_find_target_in_paragraphs` 문단별 정규화 캐싱 없음
- **출처**: PERF3-005 | **파일**: `redline_engine.py:366-385` | Moderate / HIGH
- 50 issue x 200 문단 = 10,000회 `_build_char_map` + `_normalize_with_index_map` 재실행.
- **수정**: `apply_redlines` 시작 시 문단별 캐시 사전 계산.

### [R3-013] `BytesIO` 삼중 래핑 -- 메모리 피크 +40~60MB
- **출처**: PERF3-001 | **파일**: `redline_engine.py:188, 739-740` | Major / HIGH -> P2 (기능 정상)
- `apply_redlines` + `_repack_docx`에서 `docx_bytes` BytesIO 3회 생성.
- **수정**: `_repack_docx`에 이미 열린 ZipFile 핸들 전달 또는 xml_bytes 조기 해제.

### [R3-014] LLM raw 응답 문자열 미해제
- **출처**: PERF3-006 | **파일**: `spa_analysis_service.py:2148-2151` | Moderate / HIGH
- `del user_prompt, spa_text`는 있으나 `raw`, `parsed`, `issues_list` 미해제.
- **수정**: `valid_issues` 구성 직후 `del raw, parsed, issues_list` 추가.

### [R3-015] 감사 추적(Audit Trail) 부재
- **출처**: SEC3-007 | **파일**: `spa_analysis.py:260-371` | Moderate / HIGH
- Step 4 처리 결과물이 DB에 전혀 기록되지 않음. 누가 어떤 계약서를 분석했는지 추적 불가.
- **수정**: `spa_redline_audit` 테이블 추가 (txn_id, user_id, params, issues_count, cost, created_at).

### [R3-016] txn_id 미사용 -- 권한 검증 후 실제 파일 연결 없음
- **출처**: SEC3-001 | **파일**: `spa_analysis.py:277, 317-326` | Major / HIGH -> P2 (현재 기능 정상)
- `_get_and_authorize_txn` 통과 후 `txn` 반환값을 사용하지 않음. `file_bytes`는 txn과 무관하게 처리됨.
- **수정**: `analyze_step4_redline`에 `txn_id` 전달 -> 감사 추적 연계.

### [R3-017] CommentManager.from_docx_zip next_id 검증 테스트 없음
- **출처**: TEST3-003 | **파일**: `test_redline_engine.py` (누락) | Major / HIGH -> P2 (테스트)
- 기존 comment ID가 있는 DOCX에서 `next_id`가 `max_id + 1`로 설정되는지 미검증.
- **수정**: 기존 ID 5,10,3 포함 DOCX에서 `next_id == 11` 검증 테스트 추가.

### [R3-018] Comment anchor ID 속성값 검증 없음
- **출처**: TEST3-002 | **파일**: `test_redline_engine.py:430-449` | Major / HIGH -> P2 (테스트)
- `commentRangeStart`/`commentRangeEnd` 존재만 확인, `w:id` 값 일치는 미검증.
- **수정**: `get(f"{W}id") == "42"` 검증 + 순서 검증 추가.

### [R3-019] `<w:body>` 없는 DOCX 에러 경로 테스트 없음
- **출처**: TEST3-005 | **파일**: `test_redline_engine.py` (누락) | Major / HIGH -> P2 (테스트)
- `apply_redlines`에서 `body is None -> ValueError` 경로가 미검증.
- **수정**: `<w:document>` 있으나 `<w:body>` 없는 XML로 구성된 DOCX 테스트 추가.

### [R3-020] `_resolve_run_properties` 문단 전체 iter 재탐색
- **출처**: PERF3-004 | **파일**: `redline_engine.py:636-640` | Moderate / HIGH
- `reference_run`에 rPr 없으면 문단 전체를 처음부터 재탐색.
- **수정**: `run.getprevious()`/`run.getnext()` 우선 확인 후 폴백.

---

## P3 -- 저우선 / 제안 (10건)

### [R3-021] KEEP 소비 후 remaining_runs 공백 run 문제
- **출처**: CQ3-006 | **파일**: `redline_engine.py:708-722` | Moderate / MEDIUM
- 정규화 공백 축소로 KEEP 텍스트와 실제 run 텍스트 길이 불일치 시 잔여 run 오배정.

### [R3-022] `leverage` 비STRONG 값 무조건 WEAK 폴백
- **출처**: CQ3-008 | **파일**: `redline_prompts.py:151` | Moderate / HIGH
- 라우터 패턴 검증으로 STRONG/WEAK 외 값은 도달 불가. 다만 직접 호출 시 방어 부족.

### [R3-023] `author` 필드 데이터 보호 정책 미정의
- **출처**: SEC3-004 | **파일**: `redline_engine.py:185` | Moderate / MEDIUM
- 향후 `claims.email`을 author에 연결 시 이메일이 .docx에 영구 저장되는 데이터 보호 이슈.

### [R3-024] 멀티워커 Rate Limiter 무효화
- **출처**: SEC3-003 + CQ3-004 + PERF3-007 | **파일**: `spa_analysis.py:37-58` | Major / HIGH
- 이전 FU-16에서도 보고됨. 단일 워커 환경에서는 무해. Redis 기반 교체 권장.
- **교차 검증**: 3개 에이전트 독립 발견 (교차 확인됨)

### [R3-025] `_sessions` 멀티워커 세션 유실 + TOCTOU
- **출처**: PERF3-008 | **파일**: `spa_analysis_service.py:110, 1157-1169` | Major / HIGH
- 이전 FU-17에서도 보고됨. 단일 워커에서는 안전.

### [R3-026] `file_bytes` 보유 기간 미최적화
- **출처**: PERF3-009 | **파일**: `spa_analysis_service.py:2115,2173` | Minor / MEDIUM
- `run_in_threadpool(apply_redlines, file_bytes, ...)` 완료 후까지 `file_bytes` 보유.

### [R3-027] `pytest.raises` match 패턴 느슨
- **출처**: TEST3-006 | **파일**: `test_redline_engine.py:505` | Moderate / HIGH
- `match=r"DEL.*INS|태그"` -- 실제 메시지에 밀착된 패턴 권장.

### [R3-028] `_parse_redline_markup` 빈 DEL/INS, 멀티라인 케이스 미검증
- **출처**: TEST3-008 | **파일**: `test_redline_engine.py` (누락) | Moderate / HIGH
- `[DEL][/DEL]` (빈 내용), `[DEL]줄\n바꿈[/DEL]` (DOTALL) 케이스 미검증.

### [R3-029] `industry_type` 라우터<->프롬프트 정합성 테스트 없음
- **출처**: TEST3-009 | **파일**: `test_redline_engine.py` (누락) | Moderate / MEDIUM
- 라우터 Form 패턴과 `build_step4_prompt` 내 `industry_map` 키가 독립 정의.

### [R3-030] `test_streaming_size_exceeds_limit` mock 패턴 개선
- **출처**: TEST3-007 | **파일**: `test_redline_engine.py:1092` | Moderate / HIGH
- `side_effect=fake_open` -> `return_value=io.BytesIO(...)` 가 더 명시적.

---

## 조치 권장 Phase 분류

### Phase A: 즉시 수정 (P0-P1, 7건) -- 코드 수정 필요

| ID | 작업 | 예상 수정 범위 |
|----|------|--------------|
| R3-001 | `_apply_segments` 다중 DEL 처리 로직 보완 | `redline_engine.py` 10줄 |
| R3-002 | `_repack_docx` 나머지 항목 크기 제한 추가 | `redline_engine.py` 5줄 |
| R3-003 | `safe_name` 특수문자 필터링 추가 | `spa_analysis.py` 1줄 |
| R3-004 | `.rels` 미존재 시 새 `.rels` 생성 폴백 | `redline_engine.py` 15줄 |
| R3-005 | `<w:ins>` 내부 run DEL 시 사전 처리 | `redline_engine.py` 10줄 |
| R3-006 | `_collect_and_split_target_runs` 테스트 3종 추가 | `test_redline_engine.py` 50줄 |
| R3-007 | 세션 소유권 fail-open 조건 수정 | `spa_analysis_service.py` 1줄 |

### Phase B: 개선 권장 (P2, 13건)

| ID | 작업 | 비고 |
|----|------|------|
| R3-008 | Step 4 JSON 재시도 로직 | 서비스 레이어 |
| R3-009 | 복수 `<w:t>` 분할 처리 | 엔진 |
| R3-010 | Comment anchor 실제 `<w:r>` 반환 | 엔진 |
| R3-011 | `re.compile` 모듈 상단 캐싱 | 엔진 1줄 |
| R3-012 | 문단별 정규화 캐시 | 엔진 |
| R3-013 | `BytesIO` 중복 생성 제거 | 엔진 |
| R3-014 | `raw`/`parsed` 조기 해제 | 서비스 1줄 |
| R3-015 | 감사 추적 테이블 | DB + 서비스 |
| R3-016 | `txn_id` 감사 연계 | 라우터 + 서비스 |
| R3-017~019 | 테스트 추가 3건 | 테스트 |
| R3-020 | `_resolve_run_properties` 인접 우선 | 엔진 |

### Phase C: 장기 개선 (P3, 10건)
R3-021 ~ R3-030 -- 기능적 위험 낮음, 점진적 개선

---

## Methodology

- **Agents**: backend-security-reviewer (R1-R3), python-code-reviewer (R4-R6), performance-profiler (R7-R9), python-code-reviewer (R10-R13)
- **Files scanned**: 7 (`redline_engine.py`, `spa_analysis.py` router, `spa_analysis_service.py`, `redline_prompts.py`, `spa_analysis.py` schema, `llm_client.py`, `test_redline_engine.py`)
- **Cross-Agent Deduplication**: 4건 중복 병합 (SEC3-002=PERF3-002, SEC3-003=CQ3-004=PERF3-007, PERF3-008~FU-17)
- **Previous Fix Verification**: Phase A~D 27건 전부 재보고 없음 = 수정 확인
- **Tests**: 62/62 passed, ruff 0 errors

---

## 검증 투명성

### 에이전트별 발견 건수
| 에이전트 | 원본 건수 | 중복 제거 후 |
|---------|----------|------------|
| backend-security-reviewer | 7 | 6 |
| python-code-reviewer (R4-R6) | 9 | 8 |
| performance-profiler | 9 | 7 |
| python-code-reviewer (R10-R13) | 9 | 9 |
| **합계** | **34** | **30** |

### 교차 검증 확인
| 이슈 | 발견 에이전트 수 | 비고 |
|------|----------------|------|
| _repack_docx 크기 무제한 | 2 (SEC + PERF) | 신뢰도 보강 |
| 멀티워커 rate limiter | 3 (SEC + CQ + PERF) | 이전 리뷰에서도 보고 |
| 멀티워커 sessions | 2 (PERF + 이전) | 이전 리뷰에서도 보고 |
