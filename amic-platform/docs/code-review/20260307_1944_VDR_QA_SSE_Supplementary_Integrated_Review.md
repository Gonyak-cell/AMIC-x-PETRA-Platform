# Code Review — VDR Q&A SSE 스트리밍 보충 통합 리뷰

> **Review Date**: 2026-03-07 19:44
> **Reviewer**: Claude Code (병렬 에이전트 3개 + 교차 검증)
> **Scope**: VDR Q&A SSE 미수행 관점 (R3, R7, R8, R9, R10, R12) + 잔여 이슈 재검증
> **Method**: 병렬 에이전트 리뷰 + 교차 검증 + 잔여 이슈 재검증
> **Base Commit**: `fbd1e9e` (VDR Q&A 13관점 통합 리뷰 수정 적용 후)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 4     | HIGH: 4                | P1: 4                |
| Moderate | 10    | HIGH: 7 / MEDIUM: 3    | P2: 7 / P3: 3        |
| Minor    | 2     | MEDIUM: 2              | P3: 2                |
| **Total**| **16**| HIGH: **11** / MEDIUM: **5** | P1: **4** / P2: **7** / P3: **5** |

**교차 검증**: 3개 에이전트 병렬 실행, 중복 2건 병합, FP 2건 제거 (N-02, N-08)
**잔여 이슈 재검증**: 8건 중 CONFIRMED 6건, FALSE_POSITIVE 2건

---

## 잔여 이슈 재검증 결과

| ID | 판정 | 근거 |
|----|------|------|
| **N-02** | **FALSE_POSITIVE** | `deal-mgmt/app/main.py:126`에 `GZipMiddleware(minimum_size=1000)` 활성화 확인 |
| **N-03** | CONFIRMED (Low) | `vdr_qa_service.py:466` — 원본 참조 반환. S-03/S-04에서 통합 다룸 |
| **N-04** | CONFIRMED (Low) | `vdr_qa_service.py:340` — FE에서 `undefined` 전달하여 현재 미트리거. BE 방어 부재 |
| **N-05** | CONFIRMED (Low) | `useVdrQA.ts:198` — 런타임 미검증 타입 단언 |
| **N-06** | CONFIRMED (Trivial) | `vdr_qa_service.py:50` — `_PRODUCER_SHUTDOWN_TIMEOUT` 미사용 |
| **N-07** | CONFIRMED (Low) | `VdrDocumentSelector.tsx:165` — `aria-expanded` 누락 |
| **N-08** | **FALSE_POSITIVE** | N-02와 동일 — GZipMiddleware 활성화 확인 |
| **N-09** | CONFIRMED (Trivial) | `vdr.ts:156` — `VdrQASSEEventType` 미사용 export |

---

## Findings

### P1 — 즉시 수정 (점수: 60+)

---

#### [S-01] `cost_usd: float` 스키마에 `None` 전달 → Pydantic ValidationError — [Major/HIGH] — P1 (70)

**파일**: `deal-mgmt/app/schemas/vdr.py:207`, `deal-mgmt/app/routers/vdr.py:822`
**관점**: R3 Type Safety
**교차 검증**: Agent 1 발견

**스키마**:
```python
class VdrQAResponse(BaseModel):
    cost_usd: float  # ← float 필수
```

**라우터**:
```python
cost_usd=result.cost_usd if claims.role == "ADMIN" else None,  # ← 비-ADMIN에게 None 전달
```

**문제**: Pydantic v2에서 `float` 필드에 `None`을 할당하면 `ValidationError` 발생. 비-ADMIN 사용자의 모든 Q&A 비스트리밍 응답이 500 에러로 실패한다. FE 타입(`vdr.ts:129`)은 `cost_usd: number | null`로 올바르게 정의되어 있어 BE 스키마만 수정하면 된다.

**권장**: `cost_usd: float | None = None`으로 변경.

---

#### [S-02] 401 재시도 시 만료된 Authorization 헤더 재사용 — [Major/HIGH] — P1 (80, 교차 검증 +10)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:115-123,134-140`
**관점**: R8 API Design
**교차 검증**: Agent 1 (R8-01) + Agent 3 (NV-01) 독립 발견

**코드**:
```typescript
// :115-123 — 요청 전 헤더 캡처
const fetchHeaders: Record<string, string> = { "Content-Type": "application/json" };
const authHeader = maApi.defaults.headers.common?.["Authorization"] ?? ...;
if (typeof authHeader === "string") fetchHeaders["Authorization"] = authHeader;

// :134-140 — 401 재시도
let response = await fetch(sseUrl, fetchOpts);
if (response.status === 401) {
  const refreshed = await refreshAuth();
  if (refreshed) {
    response = await fetch(sseUrl, fetchOpts);  // ← 동일한 fetchOpts 재사용
  }
}
```

**문제**: `refreshAuth()` 후 쿠키는 자동 갱신되지만, `fetchHeaders`에 캡처된 만료 `Authorization` 헤더는 갱신되지 않는다. BE가 쿠키보다 Authorization 헤더를 우선 검증하면 재시도도 401로 실패한다. 현재 httpOnly 쿠키 전용 인증이면 무영향이나, Authorization 헤더가 설정된 환경에서는 재시도 실패.

**권장**: 재시도 시 `maApi.defaults.headers`에서 최신 Authorization을 다시 읽어 `fetchOpts.headers`를 재구성.

---

#### [S-03] `_conversation_store` 동시 접근 경합 — Lock 부재 — [Major/HIGH] — P1 (70)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:57,93-101,466`
**관점**: R12 Data Integrity
**교차 검증**: Agent 2 발견

**코드**:
```python
_conversation_store: OrderedDict[str, list[dict[str, str]]] = OrderedDict()  # :57

def _save_conversation(key, history):    # :93
    _conversation_store[key] = history
    _conversation_store.move_to_end(key)
    while len(_conversation_store) > _MAX_CONVERSATIONS:
        _conversation_store.popitem(last=False)

history = _conversation_store.get(store_key, [])  # :466 — 원본 참조 반환
```

**문제**: `_model_cache`에는 `asyncio.Lock`이 적용되어 있지만, `_conversation_store`에는 동기화 메커니즘이 없다. 같은 사용자가 동일 conversation에 빠르게 두 번 질문하면, 두 요청 모두 같은 `history`를 읽고 각각 append/저장하여 첫 번째 Q&A 쌍이 소실될 수 있다. 또한 N-03(원본 참조 반환)과 결합되어 `_save_conversation()` 내 `history[-N:]` 슬라이싱이 참조를 분리시키는 추가 위험이 있다.

**권장**: `_conversation_store` 접근에 `asyncio.Lock` 도입. `get()` 시 `.copy()` 반환.

---

#### [S-04] 핵심 비즈니스 로직 테스트 부재 (34개 테스트 케이스 제안) — [Major/HIGH] — P1 (70)

**파일**: `deal-mgmt/tests/test_vdr_qa.py`
**관점**: R9 Testing
**교차 검증**: Agent 2 발견

**문제**: 기존 테스트(211줄)는 순수 함수(`_validate_question`, `_sanitize_answer`, `_format_sse` 등)만 검증. 핵심 로직인 `ask_question_stream()`, `prepare_qa_context()`, `_ensure_file_uris()`, `_fetch_documents()`에 대한 테스트가 전혀 없다.

**구체적 테스트 케이스 (34개)**:

| 대상 함수 | 케이스 수 | 주요 시나리오 |
|----------|----------|-------------|
| `prepare_qa_context()` | 6 | 인젝션 거부, 빈 VDR, 업로드 실패, 정상, conv_id 생성/재사용 |
| `ask_question_stream()` | 8 | 토큰 스트리밍, sources/done, 타임아웃, 보안 누출 차단, 빈 응답, 히스토리 저장 |
| `_fetch_documents()` | 4 | ACTIVE 필터, document_ids 필터, max_count, 정렬 |
| `_ensure_file_uris()` | 5 | 캐시 URI, 만료 재업로드, 업로드 실패 스킵, 토큰 예산, tmp 정리 |
| `useVdrQA` (FE) | 7 | 메시지 추가, 토큰 누적, sources 업데이트, 에러, 취소, 401 재시도, 초기화 |
| `_get_model()` (기존 수정) | 4 | async 호출 + 캐싱 + 다른 키 분리 + 캐시 정리 |

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [S-05] `genai.configure()` 전역 상태 경쟁 — 다중 모듈 간 — [Moderate/HIGH] — P2 (40)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:309`
**관점**: R12 Data Integrity

`genai.configure(api_key=...)` 호출이 `vdr_qa_service.py`, `gemini_classification_service.py`, `gemini_file_service.py`, `ralph/llm_client.py`에 분산. 현재 단일 API 키 사용으로 문제없으나, 모듈별 다른 키 사용 시 경쟁 조건 발생.

**권장**: 앱 시작 시 1회 configure 또는 `google-genai` Client 인스턴스 패턴으로 전환.

---

#### [S-06] `WEB_CONCURRENCY` int 변환 미보호 — [Moderate/HIGH] — P2 (50, 교차 검증 +10)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:80-81`
**관점**: R3 Type Safety + R12 Data Integrity
**교차 검증**: Agent 1 (R3-03) + Agent 2 (R12-05) 독립 발견

```python
concurrency = os.environ.get("WEB_CONCURRENCY")
if concurrency and int(concurrency) > 1:  # ← ValueError 미보호
```

같은 함수의 `--workers` 파싱(69-71행)은 `try/except ValueError`로 보호. 일관성 부재.

**권장**: `try/except ValueError`로 감싸기.

---

#### [S-07] 매 rAF마다 전체 messages 배열 + 문자열 복사 — GC 압력 — [Moderate/HIGH] — P2 (40)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:92-102`
**관점**: R7 Performance

```typescript
setMessages((prev) => {
  const updated = [...prev];  // 전체 배열 스프레드
  const last = updated[updated.length - 1];
  if (last?.role === "assistant") {
    updated[updated.length - 1] = { ...last, content: last.content + text };  // 문자열 연결
  }
  return updated;
});
```

긴 응답(수천 토큰)에서 `content` 문자열이 커질수록 매 프레임마다 점점 큰 문자열을 복사+연결. rAF 배칭으로 프레임당 1회 제한은 좋으나, 불변 업데이트 비용이 누적.

**권장**: `useRef`로 누적 텍스트 관리 후 최종 상태만 반영, 또는 마지막 메시지만 교체하는 최적화.

---

#### [S-08] BE `relevance: str` vs FE 리터럴 유니온 타입 불일치 — [Moderate/HIGH] — P2 (40)

**파일**: `deal-mgmt/app/schemas/vdr.py:198`, `amic-platform/src/modules/ma/types/vdr.ts:122`
**관점**: R3 Type Safety

BE: `relevance: str` (무제한), FE: `relevance?: "high" | "medium" | "low" | "referenced"` (4개 리터럴 + optional). BE에서 필수, FE에서 optional인 차이도 있다.

**권장**: BE를 `Literal["high", "medium", "low", "referenced"]`로 제한.

---

#### [S-09] 스트림 중단 시 불완전 응답이 정상처럼 표시 — [Moderate/HIGH] — P2 (40)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:228-233`
**관점**: R12 Data Integrity

`done` 이벤트 없이 스트림 종료 시 toast 알림은 표시되지만, `messages`의 마지막 assistant 메시지에 **불완전한 부분 응답이 그대로 남아있음**. AbortError(사용자 취소) 경로에서는 빈 메시지 제거 로직 있으나, 네트워크 끊김 경로에는 없음.

**권장**: `receivedDone === false`일 때 마지막 assistant 메시지에 `isIncomplete: true` 플래그 추가.

---

#### [S-10] `ask_question_stream()`이 `QAPreparedContext` 내부 상태 직접 변이 — [Major/MEDIUM] — P2 (42)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:737-740`
**관점**: R10 Architecture

`ctx.history.append()`로 인자의 mutable 리스트를 직접 변이. 함수의 부수효과가 호출자에게 투명하지 않음. `QAPreparedContext`가 `frozen=False` dataclass이며 `history`가 mutable list.

**권장**: `prepare_qa_context()`에서 `list(history)` 복사본 제공. 히스토리 저장을 단일 지점에서만 수행.

---

#### [S-11] 라우터 내 인라인 import + 이질적 DB 세션 관리 패턴 — [Moderate/HIGH] — P2 (40)

**파일**: `deal-mgmt/app/routers/vdr.py:837-842,859`
**관점**: R10 Architecture

`stream_vdr_question()` 내 5개 인라인 import. 같은 라우터의 `ask_vdr_question()`은 `Depends(get_db)` 사용, `stream_vdr_question()`은 `async_session_factory()` 수동 사용. SSE 스트리밍의 기술적 필요에 의한 것이나 두 패턴 공존이 유지보수 혼란 초래.

**권장**: 인라인 import의 필요성 검증 후 가능하면 모듈 상단 이동. DB 패턴 차이를 주석으로 명시적 문서화.

---

#### [S-12] `_get_model` 테스트가 async 함수를 동기 호출 — 캐싱 미검증 — [Moderate/HIGH] — P2 (40)

**파일**: `deal-mgmt/tests/test_vdr_qa.py:180-193`
**관점**: R9 Testing

```python
# _get_model은 async def (line 320)
m1 = _get_model("test-key", "gemini-2.0-flash")  # ← await 없음
m2 = _get_model("test-key", "gemini-2.0-flash")
assert m1 is m2  # ← 코루틴 객체 비교 → 캐싱 로직 미검증
```

**권장**: `@pytest.mark.asyncio` + `async def` + `await` 사용, 또는 내부 동기 함수 `_get_model_sync()` 직접 테스트.

---

### P3 — 저우선 (점수: <30)

---

#### [S-13] `asyncio.gather` 무제한 동시성 — Gemini File API rate limit 위험 — [Moderate/MEDIUM] — P3 (24)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:266-279`
**관점**: R7 Performance

`_resolve_file_refs()`에서 모든 파일을 `asyncio.gather`로 동시 호출. `asyncio.Semaphore(5~10)`으로 제한 권장.

---

#### [S-14] error 이벤트 후 done 이벤트 미전송 — FE 중복 에러 토스트 — [Moderate/MEDIUM] — P3 (24)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:648-655,696-703`
**관점**: R12 Data Integrity

세션 타임아웃·Gemini 타임아웃 시 `error` 이벤트만 전송, `done` 미전송. FE에서 "응답이 완료되지 않았습니다" 토스트가 추가 표시되어 중복 알림.

**권장**: error 이벤트 후 done 이벤트 전송, 또는 FE에서 error 수신 시 `receivedDone = true` 처리.

---

#### [S-15] 보안 레이어와 비즈니스 로직 혼재 — SRP 확장 — [Moderate/MEDIUM] — P3 (24)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:164-180,215-231,663-674`
**관점**: R10 Architecture

프롬프트 인젝션 탐지, 답변 보안 후처리, 스트리밍 중 fingerprint 검사가 모두 Q&A 서비스 파일 안에 인라인. 향후 다른 AI 기능에서 재사용 불가.

**권장**: `app/core/llm_security.py`로 보안 함수/상수 분리.

---

#### [S-16] SSE 에러 이벤트 구조 불일치 (`conversation_id` 유무) — [Minor/MEDIUM] — P3 (12)

**파일**: `deal-mgmt/app/routers/vdr.py:874-885`, `deal-mgmt/app/services/vdr_qa_service.py:649-654`
**관점**: R8 API Design

라우터의 `_error_stream`에는 `conversation_id` 미포함, 서비스의 에러 이벤트에는 포함. 에러 응답 구조가 일관되지 않음.

---

#### [S-17] SSE 파서 멀티라인 `data` 미지원 — [Minor/MEDIUM] — P3 (12)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:37-41`
**관점**: R12 Data Integrity

현재 파서는 마지막 `data:` 라인만 취함. SSE 스펙과 불일치하나, BE가 단일 라인 JSON만 전송하므로 실질 영향 없음.

---

## 잔여 확인 이슈 (이전 리뷰에서 CONFIRMED, 신규 수정 불필요)

| ID | 심각도 | 설명 | 비고 |
|----|--------|------|------|
| N-04 | Low | `if document_ids:` 빈 배열 falsy | FE에서 undefined 전달하여 현재 미트리거 |
| N-05 | Low | `parsed.sources as VdrQASource[]` 런타임 미검증 | BE 스키마 안정적 |
| N-06 | Trivial | `_PRODUCER_SHUTDOWN_TIMEOUT` 미사용 상수 | 데드코드 정리 시 제거 |
| N-07 | Low | 폴더 토글 `aria-expanded` 누락 | 접근성 개선 시 추가 |
| N-09 | Trivial | `VdrQASSEEventType` 미사용 export | 데드코드 정리 시 제거 |

---

## Priority Matrix

### P1 — 즉시 수정 (4건)

| # | ID | 이슈 | 파일 | 점수 |
|---|-----|------|------|------|
| 1 | S-02 | 401 재시도 시 만료된 Authorization 헤더 재사용 | useVdrQA.ts | 80 |
| 2 | S-01 | `cost_usd: float` → None 전달 ValidationError | vdr.py, vdr_qa.py | 70 |
| 3 | S-03 | conversation_store 동시 접근 Lock 부재 | vdr_qa_service.py | 70 |
| 4 | S-04 | 핵심 비즈니스 로직 테스트 부재 (34개 케이스) | test_vdr_qa.py | 70 |

### P2 — 개선 권장 (7건)

| # | ID | 이슈 | 파일 | 점수 |
|---|-----|------|------|------|
| 1 | S-06 | WEB_CONCURRENCY int 변환 미보호 | vdr_qa_service.py | 50 |
| 2 | S-10 | ctx.history 직접 변이 | vdr_qa_service.py | 42 |
| 3 | S-05 | genai.configure() 전역 상태 경쟁 | vdr_qa_service.py | 40 |
| 4 | S-07 | 매 rAF 배열+문자열 복사 GC 압력 | useVdrQA.ts | 40 |
| 5 | S-08 | relevance BE str vs FE 리터럴 불일치 | vdr.py, vdr.ts | 40 |
| 6 | S-09 | 스트림 중단 시 불완전 응답 표시 | useVdrQA.ts | 40 |
| 7 | S-11 | 인라인 import + 이질적 DB 세션 패턴 | vdr.py | 40 |
| 8 | S-12 | _get_model 테스트 async 동기 호출 | test_vdr_qa.py | 40 |

### P3 — 저우선 (5건)

| # | ID | 이슈 | 파일 | 점수 |
|---|-----|------|------|------|
| 1 | S-13 | asyncio.gather 무제한 동시성 | vdr_qa_service.py | 24 |
| 2 | S-14 | error 후 done 미전송 중복 토스트 | vdr_qa_service.py | 24 |
| 3 | S-15 | 보안/비즈니스 로직 혼재 SRP | vdr_qa_service.py | 24 |
| 4 | S-16 | SSE 에러 이벤트 구조 불일치 | vdr.py | 12 |
| 5 | S-17 | SSE 파서 멀티라인 data 미지원 | useVdrQA.ts | 12 |

---

## Methodology

- **Agents**: 3개 병렬 (R3+R7+R8, R9+R10+R12, N-이슈 재검증)
- **Files scanned**: 7개 (vdr_qa_service.py, vdr.py, useVdrQA.ts, vdr.ts, VdrQAPanel.tsx, VdrDocumentSelector.tsx, client.ts)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 중복 발견 2건 병합 (S-02, S-06), FP 2건 제거 (N-02, N-08)
- **Previous reviews**: F-01~F-16 수정 완료 (fbd1e9e), 본 리뷰는 미수행 관점 보충

## 검증 투명성

### 검증 통계
- 검증한 가설: 20건
- 거부된 가설 (사전 제거): 2건 (N-02, N-08 — GZipMiddleware 활성화 확인)
- 보고된 이슈: 16건 + 잔여 5건
- 거부율: 10%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 2 | N-02/N-08: GZipMiddleware가 main.py:126에서 활성화 확인 |

### 중복 병합

| 병합 ID | 원본 | 설명 |
|---------|------|------|
| S-02 | R8-01 + NV-01 | 401 재시도 Authorization 헤더 — Agent 1, 3 독립 발견 |
| S-06 | R3-03 + R12-05 | WEB_CONCURRENCY 파싱 — Agent 1, 2 독립 발견 |
