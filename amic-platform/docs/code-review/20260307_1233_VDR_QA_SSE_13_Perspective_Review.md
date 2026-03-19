# VDR Q&A SSE 스트리밍 — 13개 관점 심층 리뷰

> **Review Date**: 2026-03-07 12:33 KST
> **Reviewer**: Claude Code (직접 리뷰)
> **Scope**: VDR Q&A SSE 스트리밍 + 문서 선택적 참조 구현 (BE 2파일 + FE 4파일)
> **Method**: §9 R2-R6 13개 관점 심층 리뷰

## 대상 파일

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `deal-mgmt/app/services/vdr_qa_service.py` | 578 | Q&A 서비스 (스트리밍 + 비스트리밍) |
| `deal-mgmt/app/routers/vdr.py` | 790~893 | `/qa`, `/qa/stream` 엔드포인트 |
| `amic-platform/src/modules/ma/hooks/useVdrQA.ts` | 215 | SSE 파싱 훅 |
| `amic-platform/src/modules/ma/types/vdr.ts` | 239 | 타입 정의 |
| `amic-platform/src/modules/ma/components/VdrDocumentSelector.tsx` | 217 | 문서 선택 UI |
| `amic-platform/src/modules/ma/components/VdrQAPanel.tsx` | 248 | 채팅 UI |

---

## Summary

| 심각도 | 건수 | 우선순위 분포 |
|--------|------|-------------|
| Critical | 1 | P0: 1 |
| Major | 5 | P1: 5 |
| Moderate | 8 | P2: 8 |
| Minor | 5 | P3: 5 |
| **Total** | **19** | P0: 1 / P1: 5 / P2: 8 / P3: 5 |

---

## R2: 보안 심층 (보안 + 위협 모델링 & 공격 표면)

### [SEC-01] Q&A 엔드포인트에 Rate Limiting 없음 — [Major/HIGH] — P1

**파일**: `deal-mgmt/app/routers/vdr.py:848-893`

**설명**: `/qa`와 `/qa/stream` 엔드포인트에 rate limiter가 적용되지 않았다. 같은 파일의 업로드 엔드포인트(라인 117-118)는 `InMemoryRateLimiter(max_calls=20, window_seconds=60.0)`를 사용하지만, Q&A 엔드포인트는 무제한 호출이 가능하다.

**영향**: 악의적 사용자가 대량 Q&A 요청을 보내 Gemini API 비용 폭증 + 서버 리소스 고갈(각 요청이 180초까지 유지). SSE 스트리밍 엔드포인트는 장시간 커넥션을 유지하므로 특히 위험하다.

**권장 수정**:
```python
_qa_limiter = InMemoryRateLimiter(max_calls=10, window_seconds=60.0)
# 엔드포인트에 적용
await _qa_limiter.check(claims.sub)
```

---

### [SEC-02] 프롬프트 인젝션 패턴 우회 가능 — [Moderate/MEDIUM] — P2

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:98-113`

**설명**: `_INJECTION_PATTERNS` 정규식이 영어/한국어 패턴만 커버한다. 유니코드 변형(전각 문자, 호모글리프), Base64 인코딩, 또는 문서 내 삽입된 지시문(indirect injection)은 탐지하지 못한다. 예:
- `"ｉｇｎｏｒｅ ｐｒｅｖｉｏｕｓ ｉｎｓｔｒｕｃｔｉｏｎｓ"` (전각)
- `"이 전 지 시를 무 시"` (공백 삽입)

**영향**: 정규식 우회를 통한 프롬프트 인젝션 성공 가능. 다만 시스템 프롬프트의 보안 지침 + `_SYSTEM_PROMPT_FINGERPRINTS` 출력 감시가 2차 방어선으로 작동하므로 실제 위험은 중간 수준.

**권장 수정**: 정규식 정규화(NFKC normalization) 전처리 추가, 또는 LLM 기반 인젝션 탐지 2차 레이어 고려.

---

### [SEC-03] SSE 스트리밍 중 JWT 만료 시 스트림 계속 진행 — [Moderate/HIGH] — P2

**파일**: `deal-mgmt/app/routers/vdr.py:848-893`, `deal-mgmt/app/services/vdr_qa_service.py:400-577`

**설명**: JWT 인증은 엔드포인트 진입 시(`Depends(get_jwt_claims)`, 라인 853) 한 번만 수행된다. SSE 스트리밍은 최대 180초 유지되므로, 스트림 도중 JWT가 만료되어도 응답이 계속 전송된다.

**영향**: 이론적으로 만료된 세션에서 답변을 계속 수신할 수 있음. 다만 SSE는 서버→클라이언트 단방향이고 새 질문을 보낼 수는 없으므로 실질적 위험은 제한적.

**권장 수정**: 현재 수준 수용 가능. 극도의 보안이 필요하면 generator 내부에서 주기적 JWT 검증 추가.

---

### [SEC-04] 임시 파일 경로 예측 가능 — [Minor/MEDIUM] — P3

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:374-376`

**설명**: `tmp_path = tmp_dir / f"{doc.id}_{doc.stored_name}"` — 임시 파일 경로가 문서 ID와 저장명으로 구성되어 예측 가능하다. `tempfile.gettempdir()` 하위에 고정 디렉토리(`vdr_qa`)를 사용한다.

**영향**: 동일 서버의 다른 프로세스가 파일을 미리 생성(symlink attack)하여 내용을 대체할 수 있는 이론적 가능성. Docker 컨테이너 환경에서는 실질적 위험 매우 낮음.

**권장 수정**: `tempfile.NamedTemporaryFile` 또는 `tempfile.mkdtemp()` 사용으로 경로 예측 불가능하게 변경.

---

## R3: 데이터 정합성 (데이터 흐름 & 무결성 + API 계약 & 호환성)

### [DATA-01] 스트리밍 에러 시 대화 히스토리 오염 — [Major/HIGH] — P1

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:504-551`

**설명**: `ask_question_stream()`에서 스트리밍 도중 에러(보안 누출 감지, 타임아웃)가 발생하면 `return`으로 generator가 종료된다(라인 509, 519, 532). 이때 `finally` 블록(라인 537-543)에서 stop_event만 처리하고, 라인 546-551의 히스토리 저장 코드에 도달하지 않는다.

그러나 **에러가 아닌 정상 종료 시**, 라인 546에서 `accumulated` 전체를 `_sanitize_answer()`로 후처리하여 히스토리에 저장한다. 문제는 FE에서 이미 token 이벤트로 수신한 원본 텍스트와 `_sanitize_answer()` 후처리 결과가 다를 수 있다는 점이다(`[NO_RELEVANT_CONTENT]` 마커 제거 등).

**영향**: 다음 턴에서 히스토리 기반 대화가 FE에 표시된 내용과 불일치할 수 있음.

**권장 수정**: 히스토리에는 sanitize 전 원본(`accumulated`)을 저장하거나, FE에도 sanitize된 최종 텍스트를 전달하는 이벤트 추가.

---

### [DATA-02] 비스트리밍 /qa와 스트리밍 /qa/stream의 sources 형식 불일치 — [Moderate/MEDIUM] — P2

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:292-303` vs `554-564`

**설명**:
- `/qa` (비스트리밍): sources를 `QASource` dataclass 리스트로 반환 → router에서 `VdrQASourceOut` Pydantic 모델로 변환 (라인 836-841)
- `/qa/stream` (스트리밍): sources를 plain dict 리스트로 SSE에 직접 포함 (라인 554-564)

두 경우 모두 같은 필드(`document_id`, `document_name`, `relevance`)를 갖지만, 스트리밍 버전은 Pydantic 검증을 거치지 않아 타입 안전성이 낮다.

**영향**: 현재는 동일 데이터이므로 기능적 문제 없음. 향후 스키마 변경 시 한쪽만 업데이트하는 실수 가능성.

**권장 수정**: 스트리밍에서도 `QASource` dataclass를 생성한 후 `asdict()`로 직렬화.

---

### [DATA-03] FE useVdrQA에서 maApi 미사용 — 직접 fetch 호출 — [Moderate/MEDIUM] — P2

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:86-95`

**설명**: 프로젝트의 다른 API 호출은 `maApi` axios 인스턴스를 사용하지만(인터셉터, 베이스 URL, 에러 핸들링 공통 처리), `useVdrQA`는 `fetch()`를 직접 호출한다. SSE 스트리밍을 위해 fetch가 필요한 것은 맞지만, 베이스 URL이 하드코딩(`/api/ma/transactions/...`)되어 있다.

**영향**: API 베이스 URL 변경 시 이 훅만 누락될 수 있음. 인터셉터(토큰 갱신, 에러 로깅 등)가 적용되지 않음.

**권장 수정**: 베이스 URL을 `maApi.defaults.baseURL`에서 가져오거나, 최소한 상수로 추출.

---

### [DATA-04] conversation_id 초기값 불일치 — [Minor/LOW] — P3

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:53` vs `deal-mgmt/app/services/vdr_qa_service.py:419`

**설명**: FE의 `conversationId` 초기값은 `null`이고, 첫 요청 시 `conversation_id: conversationId ?? undefined`(라인 83)로 전달된다. BE에서는 `conversation_id or str(uuid.uuid4())`(라인 419)로 새 ID를 생성한다. FE는 `sources` 이벤트에서 `conversation_id`를 수신하여 상태를 업데이트한다(라인 139).

이 흐름 자체는 정상이지만, **스트리밍 에러 시 sources 이벤트가 도달하지 않으면** FE의 `conversationId`가 `null`로 남아 다음 질문에서 새 대화가 시작된다.

**영향**: 에러 후 대화 연속성이 끊김. 사용자가 다시 질문하면 이전 맥락 없이 새 대화 시작.

**권장 수정**: error 이벤트에도 `conversation_id`를 포함하여 FE가 대화 ID를 유지하도록 변경.

---

## R4: 프로덕션 복원력 (에러 처리 + 관찰 가능성 & 디버깅 용이성)

### [RESIL-01] DB 세션이 스트리밍 전체 기간 동안 열려 있음 — [Critical/HIGH] — P0

**파일**: `deal-mgmt/app/routers/vdr.py:848-893`, `deal-mgmt/app/services/vdr_qa_service.py:400-577`

**설명**: `stream_vdr_question()` 라우터 핸들러에서 `db: AsyncSession = Depends(get_db)`로 주입받은 DB 세션이 `ask_question_stream()` async generator의 수명 동안 유지된다. `StreamingResponse`는 응답이 완전히 전송될 때까지 라우터의 의존성을 해제하지 않으므로, DB 커넥션이 **최대 180초** 동안 점유된다.

동시 사용자 10명이 Q&A를 사용하면 10개 DB 커넥션이 180초씩 점유되어 커넥션 풀이 고갈될 수 있다.

**영향**: DB 커넥션 풀 고갈 → 다른 API 엔드포인트(거래 목록, 문서 업로드 등)도 DB 접근 불가 → 전체 서비스 장애.

**권장 수정**: generator 내부에서 DB 작업을 모두 완료한 후(파일 URI 확보까지), DB 세션을 명시적으로 커밋/닫고, 스트리밍 단계에서는 DB 세션을 사용하지 않도록 분리.
```python
# 라우터에서 DB 작업 완료 후 generator에는 결과만 전달
docs, file_refs, history = await prepare_qa(db, ...)
# db 세션은 여기서 해제됨
stream = stream_from_prepared(docs, file_refs, history, question, ...)
return StreamingResponse(stream, ...)
```

---

### [RESIL-02] 스트리밍 producer 스레드의 graceful shutdown 불완전 — [Moderate/HIGH] — P2

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:537-543`

**설명**: `finally` 블록에서 `stop_event.set()` 후 `asyncio.wait_for(asyncio.shield(fut), timeout=5.0)`으로 스레드 완료를 기다린다. 그러나:
1. `stop_event.set()` 후 producer가 Gemini API 응답을 기다리는 중이면 `for chunk in response:` 반복에서 블로킹되어 5초 안에 종료되지 않을 수 있다.
2. 타임아웃 시 `fut.cancel()`을 호출하지만, `run_in_executor`로 실행된 스레드 함수는 **cancel이 불가능**하다 (Python asyncio 제한).

**영향**: 클라이언트가 연결을 끊어도 백그라운드 스레드가 Gemini 응답 수신을 끝까지 진행하여 불필요한 비용 발생 + 스레드 누적.

**권장 수정**: Gemini SDK의 스트리밍에서 timeout을 설정하거나, producer 내부에서 chunk 수신 사이에 `stop_event.is_set()` 체크(이미 구현됨, 라인 477-478). Gemini SDK 레벨에서 cancel 지원 확인 필요.

---

### [RESIL-03] 로깅에 요청 컨텍스트(txn_id, user_sub) 부재 — [Moderate/MEDIUM] — P2

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:127, 277, 385, 496`

**설명**: 로그 메시지에 `txn_id`는 일부 포함되지만(라인 277, 496), `user_sub`가 포함된 로그는 없다. 프롬프트 인젝션 탐지 로그(라인 127)에도 `user_sub`와 `txn_id`가 없어 어떤 사용자가 어떤 거래에서 인젝션을 시도했는지 추적이 불가능하다.

**영향**: 프로덕션에서 보안 이벤트 발생 시 사용자/거래 특정 불가. 디버깅 시 로그 상관관계 파악 어려움.

**권장 수정**:
```python
logger.warning(
    "프롬프트 인젝션 탐지: user=%s txn=%s (질문 길이: %d)",
    user_sub, transaction_id, len(question),
)
```

---

### [RESIL-04] 스트리밍 응답 시간/토큰 메트릭 로깅 없음 — [Minor/MEDIUM] — P3

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:400-577`

**설명**: `ask_question()` (비스트리밍)과 `ask_question_stream()` 모두 응답 시간, 사용 토큰 수, 비용을 로그에 기록하지 않는다. `cost_usd`는 계산되어 FE에 전달되지만 서버 로그에는 남지 않는다.

**영향**: Gemini API 비용 모니터링, 응답 시간 추이 분석, 이상 탐지가 불가능. 운영 비용 관리에 어려움.

**권장 수정**: generator 완료 시 `logger.info("Q&A 완료: txn=%s cost=%.4f tokens=%d duration=%.1fs", ...)`

---

## R5: 운영 & 코드 건강성 (성능 + 배포 안전성 + 의존성 & 결합도)

### [OPS-01] 멀티 워커 환경에서 _conversation_store 비공유 — [Major/HIGH] — P1

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:36-37`, `deal-mgmt/scripts/docker-entrypoint.sh:7`

**설명**: `_conversation_store`는 프로세스 메모리 내 `OrderedDict`이다. `docker-entrypoint.sh`에서 `uvicorn --workers ${WORKERS:-2}`로 **2개 워커**를 실행하므로, 대화 히스토리가 워커 간 공유되지 않는다. 사용자의 연속 질문이 다른 워커로 라우팅되면 이전 대화 맥락을 잃는다.

**영향**: 대화 히스토리 기반 연속 질문이 불안정. 워커 1에서 첫 질문 → 워커 2로 두 번째 질문 시 이전 맥락 없이 답변.

**권장 수정**:
- 단기: `WORKERS=1`로 설정 (Azure VM 2 vCPU에서 충분)
- 중기: Redis 기반 대화 히스토리 저장소로 전환

---

### [OPS-02] 매 token 이벤트마다 React 상태 업데이트 — 렌더링 비용 — [Moderate/MEDIUM] — P2

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:125-135`

**설명**: 매 SSE token 이벤트마다 `setMessages(prev => [...prev, {...last, content: last.content + parsed.text}])`가 호출된다. Gemini의 스트리밍은 초당 수십~수백 개 chunk를 전송할 수 있으며, 각 chunk마다 전체 messages 배열이 복사되고 React 리렌더링이 발생한다.

**영향**: 긴 답변(8192 토큰) 스트리밍 시 수백 번의 리렌더링 → 저사양 기기에서 UI 버벅임 가능.

**권장 수정**: `requestAnimationFrame` 또는 `throttle`로 UI 업데이트를 프레임 단위로 제한. 또는 `useRef`로 누적하고 주기적으로 `setState`.

---

### [OPS-03] 서버 재시작/배포 시 진행 중인 SSE 스트림 무응답 — [Moderate/MEDIUM] — P2

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:400-577`

**설명**: 배포 시 서버가 재시작되면 진행 중인 SSE 스트림이 갑자기 끊긴다. FE에서 `reader.read()`가 `done: true`를 반환하지만, `sources`/`done` 이벤트를 수신하지 못한다. FE의 `finally` 블록(라인 188-191)에서 `isStreaming = false`로 리셋하지만, 불완전한 답변이 화면에 남는다.

**영향**: 배포 시 Q&A 사용 중인 사용자의 답변이 중간에 끊김. 에러 메시지 없이 불완전한 상태로 표시.

**권장 수정**: FE에서 스트림이 `done` 이벤트 없이 종료되면 "연결이 끊겼습니다. 다시 시도해 주세요." 안내 표시.

---

### [OPS-04] google.generativeai 함수 내 import — 콜드 스타트 비일관성 — [Minor/LOW] — P3

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:158, 230, 444`

**설명**: `import google.generativeai as genai`가 3곳에서 함수 내부에 위치한다. 첫 호출 시 모듈 로딩 지연이 발생하고, 이후 호출에서는 캐시된다. 또한 `genai.configure(api_key=api_key)`가 매 호출마다 실행되어 전역 상태를 반복 설정한다.

**영향**: 기능적 문제 없음. 코드 정리 차원의 개선 사항.

**권장 수정**: 모듈 상단에서 한 번 import, `configure`는 필요 시에만 호출 (이미 같은 키인지 확인).

---

## R6: 비즈니스 & UX (도메인 로직 + 테스트 품질 + 인지 복잡도 & 가독성 + 접근성 & UX)

### [UX-01] sources.relevance가 항상 "high" — 의미 없는 필드 — [Major/MEDIUM] — P1

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:299, 561`

**설명**: `QASource(relevance="high")`와 스트리밍 `"relevance": "high"`가 모든 문서에 하드코딩되어 있다. FE 타입(`vdr.ts:122`)에서 `"high" | "medium" | "low"`로 정의되어 있지만, 실제로는 모든 참조 문서가 "high"로 표시된다.

**영향**: FE에서 relevance 기반 정렬/필터링을 구현해도 의미 없음. 사용자에게 잘못된 신뢰감을 줄 수 있음.

**권장 수정**:
- 단기: relevance 필드를 제거하거나 optional로 변경
- 중기: Gemini 응답에서 실제 참조된 문서를 파싱하여 relevance 계산

---

### [UX-02] 문서 정렬이 file_size DESC — 큰 파일 우선 — [Major/MEDIUM] — P1

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:327`

**설명**: `stmt.order_by(VdrDocument.file_size_bytes.desc()).limit(max_count)` — 토큰 예산 초과 시 큰 파일이 우선 포함된다. M&A 실사에서 큰 파일(예: 스캔된 이미지 PDF)이 반드시 중요한 것은 아니다. 오히려 핵심 재무제표(작은 엑셀)가 누락될 수 있다.

**영향**: 토큰 예산(800K)이 부족할 때 중요한 소형 문서가 누락되고 대용량 스캔 문서가 포함될 수 있음.

**권장 수정**: 파일 크기 대신 최근 업로드 순(`created_at DESC`) 또는 폴더 카테고리 우선순위 기반 정렬. 또는 사용자가 선택한 문서(`document_ids`)가 있으면 해당 문서만 사용하므로 선택적 참조 UI를 적극 활용하도록 안내.

---

### [UX-03] VDR Q&A 테스트 부재 — [Major/HIGH] — P1

**파일**: `deal-mgmt/tests/` (Grep 결과: 관련 테스트 파일 0건)

**설명**: `deal-mgmt/tests/` 디렉토리에 `vdr_qa`를 포함한 테스트 파일이 전혀 없다. `ask_question()`, `ask_question_stream()`, `_validate_question()`, `_sanitize_answer()` 등 핵심 함수에 단위 테스트가 없다.

**영향**: 프롬프트 인젝션 탐지, 시스템 프롬프트 누출 방지, SSE 이벤트 형식 등 보안/기능 핵심 로직이 검증되지 않음.

**필요 테스트 목록**:
1. `_validate_question()` — 인젝션 패턴 탐지/통과
2. `_sanitize_answer()` — 핑거프린트 감지, NO_RELEVANT_CONTENT 처리
3. `_format_sse()` — SSE 형식 정확성
4. `ask_question()` — 정상 응답, 빈 문서, 타임아웃 (Gemini mock)
5. `ask_question_stream()` — 스트리밍 이벤트 순서, 에러 시 정리

---

### [UX-04] ask_question()과 ask_question_stream()의 코드 중복 — [Moderate/MEDIUM] — P2

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:172-310` vs `400-577`

**설명**: 두 함수가 공통 로직을 대부분 복제한다:
- 프롬프트 인젝션 검증 (라인 203-206 ↔ 422-425)
- 문서 조회 (라인 209-214 ↔ 428-431)
- File URI 확보 (라인 217-222 ↔ 434-437)
- 대화 히스토리 (라인 225-227 ↔ 440-441)
- 모델 설정 + contents 조립 (라인 230-246 ↔ 444-456)
- 응답 후처리 + 히스토리 저장 (라인 284-309 ↔ 546-577)

**영향**: 한쪽만 수정하고 다른 쪽을 빠뜨리는 실수 가능성 높음. 현재도 sources 형식이 미묘하게 다름(DATA-02).

**권장 수정**: 공통 로직을 `_prepare_qa_context()` 같은 private 함수로 추출.

---

### [UX-05] 매직 넘버 다수 — [Minor/LOW] — P3

**파일**: `deal-mgmt/app/services/vdr_qa_service.py` 전반

**설명**:
- `180.0` (타임아웃, 라인 258, 507)
- `6` (히스토리 메시지 수, 라인 243, 454) → 실제로 3턴
- `10` (최대 sources 수, 라인 301, 563)
- `0.5` (tokens_per_byte, 라인 354)
- `8192` (max_output_tokens, 라인 255, 472)
- `5.0` (producer 종료 대기, 라인 541)

**영향**: 값 조정 시 여러 곳을 동시에 수정해야 하며, 의미 파악에 시간 소요.

**권장 수정**: 모듈 상단에 상수로 추출.
```python
_TIMEOUT_SECONDS = 180.0
_MAX_HISTORY_MESSAGES = 6
_MAX_SOURCES = 10
```

---

### [UX-06] VdrDocumentSelector 폴더 토글 버튼에 aria-label 없음 — [Minor/MEDIUM] — P3

**파일**: `amic-platform/src/modules/ma/components/VdrDocumentSelector.tsx:159-168`

**설명**: 폴더 펼치기/접기 버튼(`<button>`)에 `aria-label`이 없다. 스크린 리더 사용자가 버튼의 목적을 알 수 없다.

**영향**: 접근성 위반 (WCAG 4.1.2 Name, Role, Value).

**권장 수정**: `aria-label={expandedFolders.has(group.folder.id) ? "폴더 접기" : "폴더 펼치기"}` 추가.

---

### [UX-07] 스트림 비정상 종료 시 사용자 피드백 없음 — [Moderate/MEDIUM] — P2

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts:107-169`

**설명**: SSE 스트림이 `done` 이벤트 없이 종료되면(`reader.read()`가 `done: true` 반환), FE는 `finally` 블록에서 `isStreaming = false`만 설정하고 아무 피드백도 주지 않는다. 불완전한 답변이 화면에 그대로 남는다.

**영향**: 서버 재시작, 네트워크 단절, nginx 타임아웃 시 사용자가 불완전한 답변을 완전한 답변으로 오인.

**권장 수정**: `while` 루프 종료 후, `sources` 이벤트 수신 여부를 체크하여 미수신 시 경고 표시.

---

## Priority Matrix

### P0 — 즉시 수정 (보안/데이터 무결성)
1. [RESIL-01] DB 세션 스트리밍 전체 점유 — Critical/HIGH (점수: 100)

### P1 — 스프린트 우선 (안정성/정확성)
1. [SEC-01] Q&A Rate Limiting 없음 — Major/HIGH (점수: 70)
2. [DATA-01] 스트리밍 에러 시 히스토리 오염 — Major/HIGH (점수: 70)
3. [OPS-01] 멀티 워커 대화 히스토리 비공유 — Major/HIGH (점수: 70)
4. [UX-02] 문서 정렬 file_size DESC — Major/MEDIUM (점수: 42)
5. [UX-03] VDR Q&A 테스트 부재 — Major/HIGH (점수: 70)

### P2 — 개선 권장 (코드 품질)
1. [SEC-02] 프롬프트 인젝션 우회 가능 — Moderate/MEDIUM (점수: 24)
2. [SEC-03] SSE 중 JWT 만료 — Moderate/HIGH (점수: 40)
3. [DATA-02] sources 형식 불일치 — Moderate/MEDIUM (점수: 24)
4. [DATA-03] maApi 미사용 — Moderate/MEDIUM (점수: 24)
5. [RESIL-02] producer 스레드 shutdown 불완전 — Moderate/HIGH (점수: 40)
6. [RESIL-03] 로깅 컨텍스트 부재 — Moderate/MEDIUM (점수: 24)
7. [OPS-02] token마다 React 리렌더링 — Moderate/MEDIUM (점수: 24)
8. [OPS-03] 배포 시 SSE 스트림 끊김 — Moderate/MEDIUM (점수: 24)
9. [UX-01] relevance 항상 "high" — Major/MEDIUM (점수: 42)
10. [UX-04] ask_question 코드 중복 — Moderate/MEDIUM (점수: 24)
11. [UX-07] 스트림 비정상 종료 피드백 없음 — Moderate/MEDIUM (점수: 24)

### P3 — 저우선 (개선 가능)
1. [SEC-04] 임시 파일 경로 예측 — Minor/MEDIUM (점수: 12)
2. [DATA-04] conversation_id 에러 시 유실 — Minor/LOW (점수: 6)
3. [RESIL-04] 메트릭 로깅 없음 — Minor/MEDIUM (점수: 12)
4. [OPS-04] 함수 내 import — Minor/LOW (점수: 6)
5. [UX-05] 매직 넘버 — Minor/LOW (점수: 6)
6. [UX-06] 폴더 버튼 aria-label — Minor/MEDIUM (점수: 12)

---

## Methodology

- **13개 관점**: R2(보안 2) + R3(데이터 2) + R4(복원력 2) + R5(운영 3) + R6(비즈니스 4) = 13
- **Files scanned**: 6
- **Protocol**: 직접 Read + Grep 검증 기반
- **보조 검증**: Rate limiter 존재 확인, 테스트 파일 존재 확인, 설정값 확인, 워커 수 확인, API 호출 패턴 확인
