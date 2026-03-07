# Code Review — Redline Step 4 (4th Supplementary Review)

> **Review Date**: 2026-03-07 18:24 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: deal-mgmt Step 4 Redline API — 1~3차 리뷰 미커버 관점 보완
> **Method**: 4-Agent Parallel Review + Cross-Verification + Deduplication
> **Review Perspectives**: R4(API 계약), R5(에러 처리), R6(async/성능), R8(설정/환경), R9(의존성/결합도), R10(도메인 로직), R11(테스트 품질), R12(인지 복잡도)
> **Prior Reviews**: 1차(30건), 2차(30건), 3차(30건) — 총 90건 기존 발견

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 7     | HIGH: 6 / MEDIUM: 1   | P0: 3 / P1: 4       |
| Warning  | 19    | HIGH: 11 / MEDIUM: 8  | P1: 11 / P2: 8      |
| Suggestion | 12 | HIGH: 2 / MEDIUM: 6 / LOW: 4 | P2: 2 / P3: 10 |
| **Total**| **38** | HIGH: **19** / MEDIUM: **15** / LOW: **4** | P0: **3** / P1: **15** / P2: **10** / P3: **10** |

**Raw → Final**: 45건 수집 → 교차 검증 3건 병합 → 4건 중복 제거 → **38건 최종**

**FP Prevention**: Agent별 Passed Checks 확인, 증거 기반 검증

---

## Findings

### Critical Issues (7건)

---

#### [R4-C1] KEEP 텍스트 소비가 문자 단위가 아닌 Run 단위 — P0

- **관점**: R10 도메인 로직 + R12 추상화 혼합 (Agent 3+4 교차 확인)
- **파일**: `redline_engine.py:729-742`
- **심각도/신뢰도**: Critical / HIGH
- **우선순위 점수**: 110 (100 x 1.0 + 교차검증 10)

**증거**:
```python
elif seg.action == "KEEP" and remaining_runs:
    keep_len = len(seg.text)
    consumed = 0
    keep_idx = 0
    for i, run in enumerate(remaining_runs):
        run_text = "".join(t.text or "" for t in run.findall(f"{W}t"))
        consumed += len(run_text)
        keep_idx = i + 1
        if consumed >= keep_len:
            break
```

**문제**: `consumed >= keep_len` 조건에서 run이 KEEP 경계를 넘어서 소비된다. run 텍스트가 `"ABCDE"`(5자)이고 `keep_len`이 3이면, run 전체(5자)가 KEEP으로 처리되어 이후 DEL 대상 2자(`DE`)가 누락된다.

**영향**: M&A 계약서에서 삭제 마커가 잘못된 위치에 삽입되어 법률 검토 결과가 오도된다.

**수정 제안**: KEEP 소비 시에도 `_split_run_at()`으로 경계를 분할하는 로직 추가.

---

#### [R4-C2] Step 4 LLM JSON 파싱 실패 시 재시도 없음 — P0

- **관점**: R5 에러 처리 (Agent 2)
- **파일**: `spa_analysis_service.py:2140-2160`
- **심각도/신뢰도**: Critical / HIGH
- **우선순위 점수**: 100 (100 x 1.0)

**증거**: Step 1~3는 `_call_llm_json()`으로 최대 3회 재시도하지만, Step 4의 `analyze_step4_redline()`은 `llm_client.call()`을 1회만 호출하고 `json.loads()` 실패 시 바로 예외를 전파한다.

**영향**: LLM이 JSON이 아닌 출력(마크다운 래핑, 불완전 출력 등)을 반환하면 Step 4 전체가 실패한다. Step 1~3 대비 안정성 저하.

**수정 제안**: `_call_llm_json()` 패턴을 Step 4에도 적용하거나, `_extract_json()` + 재시도 로직을 감싸는 래퍼를 사용.

---

#### [R4-C3] issue_id 패턴 불일치 시 유효 이슈가 침묵 속에 사라짐 — P0

- **관점**: R10 도메인 로직 (Agent 4)
- **파일**: `spa_analysis.py:464`, `spa_analysis_service.py:2166`
- **심각도/신뢰도**: Critical / HIGH
- **우선순위 점수**: 100 (100 x 1.0)

**증거**:
```python
# 스키마
issue_id: str = Field(..., pattern=r"^ISS-\d{3,}$")

# 서비스 — 검증 실패 시 조용히 skip
for raw_issue in raw_issues:
    try:
        validated = RedlineIssueSchema(**raw_issue)
        valid_issues.append(validated.model_dump())
    except ValidationError:
        logger.warning(...)  # 로그만 남김
```

**문제**: LLM이 `ISSUE-001`이나 `ISS-1`을 출력하면 유효한 High severity 이슈가 전부 drop된다. `issues_count`는 성공 건수만 반환하므로 클라이언트는 drop 여부를 알 수 없다.

**영향**: M&A 리뷰에서 법적 리스크가 검토되지 않은 계약서가 반환될 수 있다.

**수정 제안**: `issue_id` 전처리 정규화(`ISSUE-` → `ISS-`) + 반환 타입에 `skipped_count` 추가 + 응답 헤더에 `X-Skipped-Issues` 노출.

---

#### [R4-C4] apply_redlines 이슈 루프에 개별 예외 처리 없음 — P1

- **관점**: R5 에러 처리 (Agent 2+4 교차 확인)
- **파일**: `redline_engine.py:220-280` (apply_redlines 이슈 루프)
- **심각도/신뢰도**: Critical / HIGH
- **우선순위 점수**: 110 (100 x 1.0 + 교차검증 10)

**증거**: 이슈 처리 루프에 개별 try-except가 없어, 하나의 이슈에서 `_inject_deletion`의 `ValueError`("삭제 대상 Run이 없습니다")가 발생하면 나머지 모든 이슈가 처리되지 않는다.

**영향**: 10개 이슈 중 1개의 엣지 케이스로 전체 레드라인이 실패한다.

**수정 제안**: 이슈 루프에 `try-except`를 추가하여 개별 이슈 실패 시 경고 로그 + skip + 매칭 실패 메모로 처리.

---

#### [R4-C5] 20MB 파일 크기 상한이 라우터/서비스 두 곳에 독립 정의 — P1

- **관점**: R9 의존성 (Agent 3)
- **파일**: `spa_analysis_service.py:2110`, `spa_analysis.py:258`
- **심각도/신뢰도**: Critical / HIGH
- **우선순위 점수**: 100 (100 x 1.0)

**증거**:
```python
# 서비스 — 지역변수
_max_file_size = 20 * 1024 * 1024

# 라우터 — 모듈 상수
_STEP4_MAX_FILE_SIZE = 20 * 1024 * 1024
```

**문제**: Shotgun Surgery 패턴. 하나만 수정하면 라우터/서비스 허용 크기가 불일치한다.

**수정 제안**: 한 곳(서비스 모듈 레벨)에만 정의하고 라우터에서 import.

---

#### [R4-C6] 지연 import가 의존성을 숨김 — God Module 징후 — P1

- **관점**: R9 의존성 + R12 복잡도 (Agent 3)
- **파일**: `spa_analysis_service.py:2103-2107`
- **심각도/신뢰도**: Critical / HIGH
- **우선순위 점수**: 100 (100 x 1.0)

**증거**:
```python
async def analyze_step4_redline(...):
    from starlette.concurrency import run_in_threadpool
    from app.schemas.spa_analysis import RedlineIssueSchema
    from app.services import redline_engine
    from app.services.redline_prompts import build_step4_prompt
```

**문제**: 2176줄 God Module(`spa_analysis_service.py`)에서 4개 지연 import로 실제 의존성이 숨겨진다. IDE 정적 분석/의존성 추적 도구가 감지 불가.

**수정 제안**: 모듈 상단으로 이동하거나, Step 4 로직을 `redline_service.py`로 분리.

---

#### [R4-C7] _GoogleAdapter.generate 동기 스레드가 취소 불가 — P1

- **관점**: R6 async/성능 (Agent 2)
- **파일**: `llm_client.py:238`
- **심각도/신뢰도**: Critical / MEDIUM
- **우선순위 점수**: 60 (100 x 0.6)

**증거**: `asyncio.to_thread(_sync_call)` + `asyncio.wait_for(timeout=90)` 조합에서 타임아웃 발생 시 `_sync_call` 스레드는 계속 실행된다.

**수정 제안**: `generate_content_async()` 또는 `google-genai` 패키지의 async 클라이언트 사용.

---

### Warning Issues (19건)

---

#### [R4-W1] valid_issues=[] 시 빈 DOCX 반환 (HTTP 200) — P1

- **관점**: R5 에러 처리 (Agent 2)
- **파일**: `spa_analysis_service.py:2168-2175`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

LLM 이슈 전부가 Pydantic 검증 실패 시 변경 없는 원본 DOCX가 200으로 반환된다. 클라이언트는 "변경 없음"과 "분석 실패"를 구분할 수 없다.

**수정 제안**: `valid_issues`가 빈 리스트이면 422 반환 또는 응답 헤더에 경고.

---

#### [R4-W2] 다중 DEL 세그먼트 미처리 — P1

- **관점**: R10 도메인 로직 (Agent 4)
- **파일**: `redline_engine.py:704-711`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

`[DEL]A[/DEL][KEEP]B[/KEEP][DEL]C[/DEL]` 패턴에서 두 번째 DEL은 경고만 남기고 건너뛴다. 복잡한 조항 수정에서 삭제 표시 누락.

---

#### [R4-W3] `_apply_segments`의 추상화 수준 혼합 — P1

- **관점**: R12 인지 복잡도 (Agent 3)
- **파일**: `redline_engine.py:679-744`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

고수준 로직(세그먼트 처리)과 저수준 XML 조작이 한 함수에 혼합. KEEP 처리 내 run 소비 로직을 헬퍼로 추출 권장.

---

#### [R4-W4] `_collect_and_split_target_runs`의 3단계 중첩 + 플래그 패턴 — P1

- **관점**: R12 인지 복잡도 (Agent 3)
- **파일**: `redline_engine.py:427-481`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

`for child` → `for r in child_runs` → 3개 if + `found_end` 플래그로 외부 루프 탈출. 평탄화 제너레이터 + 슬라이스 추출로 단순화 가능.

---

#### [R4-W5] spa_analysis_service.py God Module (2176줄) — P1

- **관점**: R9 결합도 (Agent 3)
- **파일**: `spa_analysis_service.py` 전체
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

5개 문서 유형 x Step 1~4 로직 + 세션 관리 + LLM 싱글턴 + JSON 파싱 + 검증 로직이 단일 파일에 집중. Step 1~3 프롬프트도 인라인(Step 4만 별도 파일).

---

#### [R4-W6] `_call_llm_json`과 Step 4 `max_tokens` 패턴 불일치 — P1

- **관점**: R4 API 계약 (Agent 1)
- **파일**: `spa_analysis_service.py`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

Step 1~3는 `_call_llm_json()`이 max_tokens를 내부 관리하지만, Step 4는 직접 `llm_client.call(max_tokens=16384)`를 호출. 일관성 부재.

---

#### [R4-W7] RWI 상태별 프롬프트 분기 없음 — P1

- **관점**: R10 도메인 로직 (Agent 4)
- **파일**: `redline_prompts.py:15-18`, `:122-131`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

`rwi_status`를 텍스트로만 주입하고 `LEVERAGE_STRONG/WEAK`처럼 분기 프롬프트가 없다. 크로스보더 거래에서 RWI 분기 지침 자체가 없음.

---

#### [R4-W8] `rev_id_counter: list[int]` 뮤터블 리스트 래핑 패턴 — P1

- **관점**: R12 코드 스멜 (Agent 3)
- **파일**: `redline_engine.py:210`, `:685`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

단일 정수를 `list[int]`로 감싸서 side-effect로 증가시키는 비관용적 패턴. 타입만 보면 의도 파악 불가.

---

#### [R4-W9] `_inject_deletion`의 `<w:ins>` 필터링이 직계 부모만 검사 — P1

- **관점**: R10 도메인 로직 (Agent 4)
- **파일**: `redline_engine.py:500-508`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

하이퍼링크 등 중첩 구조에서 `<w:ins>`가 간접 조상인 경우 필터링을 우회한다. 조상 전체 탐색 헬퍼 `_is_inside_ins()` 필요.

---

#### [R4-W10] Content-Disposition filename 따옴표 처리 — P2

- **관점**: R4 API 계약 (Agent 1)
- **파일**: `spa_analysis.py:362-365`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

`safe_name`에서 특수문자 필터링은 되지만, RFC 5987 인코딩(`filename*=UTF-8''...`)을 사용하지 않아 한글 파일명이 일부 브라우저에서 깨질 수 있다.

---

#### [R4-W11] Step 4 에러 로그에 file_bytes 크기 정보 없음 — P2

- **관점**: R5 에러 처리 (Agent 2)
- **파일**: `spa_analysis_service.py`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

---

#### [R4-W12] `call_for_provider` 폴백 시 예외 정보 소실 — P2

- **관점**: R5 에러 처리 (Agent 2)
- **파일**: `llm_client.py`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

---

#### [R4-W13] 라우터 catch-all 예외에 타입 분류 없음 — P2

- **관점**: R5 에러 처리 (Agent 2)
- **파일**: `spa_analysis.py`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

---

#### [R4-W14] `_normalize_text_for_matching`이 탭 문자 처리 시 인덱스 오류 가능 — P2

- **관점**: R10 도메인 로직 (Agent 4)
- **파일**: `redline_engine.py:346-357`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

OOXML 탭은 `<w:tab/>` 요소이나 `merged` 문자열에는 없어서 `norm_target`과 불일치 가능.

---

#### [R4-W15] CommentManager.serialize() XML 특수문자 가독성 문제 — P2

- **관점**: R10 도메인 로직 (Agent 4)
- **파일**: `redline_engine.py:113-120`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

`clause_ref`에 `<진술보증>`이 있으면 lxml 자동 이스케이프로 `&lt;진술보증&gt;`으로 표시.

---

#### [R4-W16] `_extract_json`의 미종결 마크다운 블록 로그 부재 — P2

- **관점**: R12 가독성 (Agent 3)
- **파일**: `spa_analysis_service.py:195-208`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

`` ```json `` 시작은 있으나 종료 `` ``` ``가 없는 LLM 출력 시 `ValueError`가 발생하지만 원인이 "JSON 파싱 실패"로 숨겨짐.

---

#### [R4-W17] `transaction_service`가 HTTPException 직접 raise — P2

- **관점**: R8 설정/환경 (Agent 1)
- **파일**: 관련 서비스 레이어
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

서비스 레이어에서 HTTP 계층 예외를 직접 raise하는 레이어 위반.

---

#### [R4-W18] lxml 테스트 직접 의존 — 격리 없음 — P2

- **관점**: R9 의존성 (Agent 3)
- **파일**: `test_redline_engine.py:10`
- **심각도/신뢰도**: Warning / MEDIUM
- **우선순위 점수**: 42 (70 x 0.6)

테스트가 내부 XML 표현(`etree._Element`)에 직접 결합. 테스트 픽스처 모듈 분리 권장.

---

#### [R4-W19] test_keep_then_del_then_ins 단언이 너무 약함 — P2

- **관점**: R11 테스트 품질 (Agent 4)
- **파일**: `test_redline_engine.py:952-961`
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 70 (70 x 1.0)

`assert len(del_els) >= 1`로만 검증하고 DEL/INS된 실제 텍스트를 확인하지 않아, 핵심 로직 오류가 회귀 테스트를 통과할 수 있다.

---

### Suggestion Issues (12건)

---

#### [R4-S1] .env 파일에 실제 API 키 존재 (Step 4 비특정) — P3

- **관점**: R8 (Agent 1)
- **파일**: `.env`
- **심각도/신뢰도**: Suggestion / HIGH — Step 4 비특정이므로 Suggestion으로 분류
- **우선순위 점수**: 20

---

#### [R4-S2] .env.example 파일 미존재 — P3

- **관점**: R8 (Agent 1)
- **심각도/신뢰도**: Suggestion / MEDIUM
- **우선순위 점수**: 12

---

#### [R4-S3] `_call_llm_json` cost 측정 docstring 갭 — P3

- **관점**: R5 (Agent 2)
- **심각도/신뢰도**: Suggestion / MEDIUM
- **우선순위 점수**: 12

---

#### [R4-S4] `_extract_json` 디버그 로깅 부재 — P3

- **관점**: R5 (Agent 2)
- **심각도/신뢰도**: Suggestion / MEDIUM
- **우선순위 점수**: 12

---

#### [R4-S5] LLM 에러 메시지에 민감 정보 포함 가능 — P3

- **관점**: R5 (Agent 2)
- **심각도/신뢰도**: Suggestion / LOW
- **우선순위 점수**: 6

---

#### [R4-S6] Step 4 성공 로그에 경과 시간 없음 — P3

- **관점**: R6 (Agent 2)
- **심각도/신뢰도**: Suggestion / LOW
- **우선순위 점수**: 6

---

#### [R4-S7] `W`, `W_NS` 약어 네이밍 — P3

- **관점**: R12 (Agent 3) — OOXML 관용적 네이밍
- **심각도/신뢰도**: Suggestion / LOW
- **우선순위 점수**: 6

---

#### [R4-S8] `_resolve_run_properties` 2차 폴백이 "인접" 아닌 "최초" Run 반환 — P3

- **관점**: R12 (Agent 3)
- **파일**: `redline_engine.py:638-662`
- **심각도/신뢰도**: Suggestion / MEDIUM
- **우선순위 점수**: 12

주석에는 "인접 run"이라 적혀있으나 실제로는 문단 내 최초 rPr이 있는 run을 반환. 삽입 위치와 먼 run의 서식이 적용될 수 있다.

---

#### [R4-S9] `_check_analysis_rate` 만료 키 정리 O(n) — P3

- **관점**: R9 (Agent 3)
- **파일**: `spa_analysis.py:56-59`
- **심각도/신뢰도**: Suggestion / MEDIUM
- **우선순위 점수**: 12

---

#### [R4-S10] `_MAX_SESSIONS=100` 상수가 실제 사용되지 않음 — P3

- **관점**: R12 (Agent 3)
- **파일**: `spa_analysis_service.py:86`
- **심각도/신뢰도**: Suggestion / MEDIUM
- **우선순위 점수**: 12

세션 추가 시 상한 검사 코드가 없어 B-3 요구사항이 미구현 상태.

---

#### [R4-S11] NFKC 정규화가 한국 법률 특수 기호(㈜, ①) 변환 — P3

- **관점**: R10 (Agent 4)
- **파일**: `redline_engine.py:327`
- **심각도/신뢰도**: Suggestion / MEDIUM
- **우선순위 점수**: 12

---

#### [R4-S12] `<w:ins>` 필터링 skip에 대한 회귀 테스트 없음 — P3

- **관점**: R11 (Agent 4)
- **파일**: `test_redline_engine.py`
- **심각도/신뢰도**: Suggestion / HIGH
- **우선순위 점수**: 20

3차 리뷰에서 추가된 방어 코드(R3-005)에 대한 직접 테스트가 없어 리팩토링 시 제거되어도 테스트가 통과한다.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 도메인 정확성/데이터 무결성)

1. **[R4-C1]** [Critical/HIGH]: KEEP 텍스트 소비가 Run 단위 — DEL 경계 오류 (110)
2. **[R4-C2]** [Critical/HIGH]: Step 4 LLM JSON 파싱 재시도 없음 (100)
3. **[R4-C3]** [Critical/HIGH]: issue_id 패턴 불일치 시 유효 이슈 silent drop (100)

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)

1. **[R4-C4]** [Critical/HIGH]: apply_redlines 이슈 루프 개별 예외 처리 없음 (110)
2. **[R4-C5]** [Critical/HIGH]: 20MB 상한 중복 정의 (100)
3. **[R4-C6]** [Critical/HIGH]: 지연 import — God Module (100)
4. **[R4-W19]** [Warning/HIGH]: 테스트 단언 너무 약함 (70)
5. **[R4-W1]** [Warning/HIGH]: valid_issues=[] 빈 DOCX 반환 (70)
6. **[R4-W2]** [Warning/HIGH]: 다중 DEL 세그먼트 미처리 (70)
7. **[R4-W3]** [Warning/HIGH]: _apply_segments 추상화 혼합 (70)
8. **[R4-W4]** [Warning/HIGH]: 3단계 중첩 + 플래그 패턴 (70)
9. **[R4-W5]** [Warning/HIGH]: God Module 2176줄 (70)
10. **[R4-W6]** [Warning/HIGH]: max_tokens 패턴 불일치 (70)
11. **[R4-W7]** [Warning/HIGH]: RWI 프롬프트 분기 없음 (70)
12. **[R4-W8]** [Warning/HIGH]: rev_id_counter 뮤터블 리스트 패턴 (70)
13. **[R4-C7]** [Critical/MEDIUM]: Google 동기 스레드 취소 불가 (60)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)

1. **[R4-W9]** [Warning/MEDIUM]: `<w:ins>` 필터링 직계 부모만 (42)
2. **[R4-W10]** [Warning/MEDIUM]: Content-Disposition RFC 5987 미적용 (42)
3. **[R4-W11]** [Warning/MEDIUM]: 에러 로그 file_bytes 크기 없음 (42)
4. **[R4-W12]** [Warning/MEDIUM]: call_for_provider 예외 정보 소실 (42)
5. **[R4-W13]** [Warning/MEDIUM]: 라우터 catch-all 타입 분류 없음 (42)
6. **[R4-W14]** [Warning/MEDIUM]: 탭 문자 매칭 인덱스 오류 (42)
7. **[R4-W15]** [Warning/MEDIUM]: XML 특수문자 가독성 (42)
8. **[R4-W16]** [Warning/MEDIUM]: 미종결 마크다운 블록 로그 (42)
9. **[R4-W17]** [Warning/MEDIUM]: HTTPException 레이어 위반 (42)
10. **[R4-W18]** [Warning/MEDIUM]: lxml 테스트 격리 (42)

### P3 — 저우선 (점수: <30, 개선 가능)

1. **[R4-S12]** [Suggestion/HIGH]: `<w:ins>` 필터링 회귀 테스트 없음 (20)
2. **[R4-S1]** [Suggestion/HIGH]: .env 실제 API 키 (20)
3. **[R4-S2]** [Suggestion/MEDIUM]: .env.example 미존재 (12)
4. **[R4-S8]** [Suggestion/MEDIUM]: _resolve_run_properties 폴백 (12)
5. **[R4-S9]** [Suggestion/MEDIUM]: rate 정리 O(n) (12)
6. **[R4-S10]** [Suggestion/MEDIUM]: _MAX_SESSIONS 미사용 (12)
7. **[R4-S11]** [Suggestion/MEDIUM]: NFKC 한국 특수 기호 (12)
8. **[R4-S3]** [Suggestion/MEDIUM]: cost docstring (12)
9. **[R4-S4]** [Suggestion/MEDIUM]: debug logging (12)
10. **[R4-S5]** [Suggestion/LOW]: 에러 메시지 민감 정보 (6)

---

## Methodology

- **Agents**: python-code-reviewer x 4 (병렬)
  - Agent 1: R4 API 계약 + R8 설정/환경
  - Agent 2: R5 에러 처리 + R6 async/성능
  - Agent 3: R9 의존성/결합도 + R12 인지 복잡도
  - Agent 4: R10 도메인 로직 + R11 테스트 품질
- **Files scanned**: 7개 (redline_engine.py, spa_analysis_service.py, spa_analysis.py, spa_analysis.py[schema], llm_client.py, redline_prompts.py, test_redline_engine.py)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Agent 3+4 교차 확인 2건 (R4-C1, R4-C4)
- **Dedup**: 3건 병합 + 4건 중복 제거

## 4차 리뷰 누적 현황 (1~4차 총합)

| 차수 | 이슈 수 | P0 | P1 | P2 | P3 | 비고 |
|------|---------|----|----|----|----|------|
| 1차  | 30      | 2  | 5  | 13 | 10 | 초기 구현 리뷰 |
| 2차  | 30      | 1  | 7  | 13 | 9  | 심층 리뷰 |
| 3차  | 30      | 1  | 6  | 13 | 10 | 보안/엣지 케이스 |
| **4차** | **38** | **3** | **15** | **10** | **10** | **미커버 관점 보완** |
| **총합** | **128** | **7** | **33** | **49** | **39** | — |

### 3차까지 P0+P1 수정 완료 현황

- 1차 P0+P1 (7건): 수정 완료
- 2차 P0+P1 (8건): 수정 완료
- 3차 P0+P1 (7건): 수정 완료
- **4차 P0+P1 (18건): 미수정 — 다음 수정 대상**
