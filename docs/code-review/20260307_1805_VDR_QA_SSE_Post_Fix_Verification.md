# VDR Q&A SSE -- 수정 후 재검증 리뷰

> **Review Date**: 2026-03-07 18:05
> **Reviewer**: Claude Code (3-agent parallel verification)
> **Scope**: 커밋 79c900c (추가 리뷰 25건 수정) 검증
> **Method**: BE/FE/Infra 3개 병렬 에이전트 + 이전 세션 4개 에이전트 교차 분석

---

## Part 1: 수정 검증 (22건)

### 결과: 22/22 전체 통과

| 영역 | 항목 수 | 결과 | 신규 이슈 |
|------|--------|------|----------|
| BE (vdr_qa_service.py) | 9건 | 전체 통과 | 없음 |
| BE (rate_limiter.py) | 1건 | 전체 통과 | 없음 |
| FE (vdr.ts + useVdrQA.ts) | 3건 | 전체 통과 | 없음 |
| FE (VdrQAPanel + VdrDocumentSelector) | 7건 | 전체 통과 | 없음 |
| Infra (nginx + docker-compose) | 2건 | 전체 통과 | 없음 |

### BE 수정 상세 검증

| ID | 수정 내용 | 증거 |
|----|----------|------|
| J-02 | `_resolve_file_refs()`에서 `genai.configure()` 제거 | :227-241 (configure 없음), :262 (get_model에만 존재) |
| J-03 | `_model_cache` OrderedDict LRU (max=8) | :251-252, :260 move_to_end, :268-269 popitem |
| J-04 | `asyncio.gather()` 병렬 해석 | :240-241 tasks + gather |
| J-07 | 에러/타임아웃 시 부분 대화 저장 | :592-597, :641-645 if chunks 가드 |
| M-01/M-02 | chunks 리스트 + 슬라이딩 윈도우 | :569, :614, :675 |
| M-03 | 히스토리 최대 50턴 제한 | :65-66 _MAX_HISTORY_MESSAGES |
| M-08 | dict[str, Any] 타입 | :203, :208 |
| M-09 | _build_gemini_contents 헬퍼 | :215-224, :467, :567 양쪽 호출 |
| M-10 | api_key field(repr=False) | :101 |
| M-04 | rate_limiter 60초 주기 정리 | :12, :36, :62-68 |

### FE 수정 상세 검증

| ID | 수정 내용 | 증거 |
|----|----------|------|
| J-01 | relevance에 "referenced" 추가 | vdr.ts:122 |
| P-09 | conversationIdRef useRef | useVdrQA.ts:55, deps=[txnId] :236 |
| m-01 | pendingTokens 배열 push+join | useVdrQA.ts:82, :87, :152 |
| M-12 | aria-live="polite" | VdrQAPanel.tsx:168 |
| M-14 | aria-label="질문 입력" | VdrQAPanel.tsx:234 |
| m-06 | aria-hidden="true" (커서) | VdrQAPanel.tsx:39 |
| m-07 | role="alert" (에러) | VdrQAPanel.tsx:34 |
| P-08 | rAF 스크롤 | VdrQAPanel.tsx:113-117 |
| P-06 | selectedSet useMemo | VdrDocumentSelector.tsx:71 |
| M-13 | 폴더 체크박스 aria-label | VdrDocumentSelector.tsx:180 |

### 인프라 수정 상세 검증

| ID | 수정 내용 | 증거 |
|----|----------|------|
| J-05 | nginx proxy_http_version 1.1 + Connection "" | prod.conf:145-146 |
| J-06 | deal-mgmt-api --workers 1 | docker-compose.prod.yml:246 |

다른 서비스(fdd-api :43, kiis-api :88, im-api :157) workers 설정 영향 없음 확인.

---

## Part 2: 신규 발견 이슈 (10건)

이전 세션 에이전트(R1+R3, R8+R12, R9+R10, R11+R13)가 기존 보고서에 포함되지 않았던 추가 이슈를 발견.

### Critical (1건)

#### [N-01] _model_cache 키에 API 키 평문 저장 -- R1 보안

**파일**: `vdr_qa_service.py:260`
**설명**: `cache_key = f"{api_key}:{model_name}"`로 API 키 전체가 딕셔너리 키에 저장됨. 프로세스 메모리 덤프, 디버거 연결 시 노출 위험.
**수정 제안**: `hashlib.sha256(api_key.encode()).hexdigest()[:16]`로 키 해시 후 사용.
**우선순위**: P1 (단일 키 환경에서 실질 위험 낮으나 보안 원칙상 중요)

### Major (1건)

#### [N-02] GZipMiddleware가 SSE 응답 버퍼링 가능 -- R13 인프라

**파일**: `deal-mgmt/app/main.py:126`
**설명**: `GZipMiddleware(minimum_size=1000)`가 전역 적용. SSE 응답이 1000바이트 초과 시 GZip 미들웨어가 버퍼링하여 토큰 단위 스트리밍 지연 가능. `X-Accel-Buffering: no`는 nginx 전용이며 FastAPI 미들웨어에 무관.
**수정 제안**: SSE StreamingResponse에 `Content-Encoding: identity` 헤더 추가, 또는 `text/event-stream` 제외 커스텀 미들웨어.
**우선순위**: P1

### Moderate (3건)

#### [N-03] _conversation_store 히스토리 리스트 참조 공유 -- R12 무결성

**파일**: `vdr_qa_service.py:395`
**설명**: `prepare_qa_context()`에서 `history = _conversation_store.get(store_key, [])`로 원본 리스트 참조를 그대로 전달. 동일 store_key로 동시 요청 시 같은 리스트를 양쪽에서 append하여 히스토리 뒤섞힘 가능.
**수정 제안**: `history = list(_conversation_store.get(store_key, []))` 복사본 전달.
**우선순위**: P2

#### [N-04] document_ids=[] 시 전체 문서 조회 fallback -- R12 무결성

**파일**: `vdr_qa_service.py:267`
**설명**: `if document_ids:` 조건이 빈 리스트도 falsy로 처리 → 전체 문서 조회. 사용자가 문서를 전부 해제했을 때(빈 배열) 의도와 다르게 전체 문서 대상 Q&A 수행.
**수정 제안**: `if document_ids is not None:`로 변경하여 None(전체)과 [](없음)을 구분.
**우선순위**: P2

#### [N-05] `as VdrQASource[]` 타입 단언에 런타임 검증 없음 -- R3 타입

**파일**: `useVdrQA.ts:173`
**설명**: SSE sources 이벤트에서 `parsed.sources as VdrQASource[]` 강제 캐스팅. BE 응답 구조가 예상과 다르면 UI 렌더링 에러.
**수정 제안**: `Array.isArray(parsed.sources)` 체크 + 필드 존재 확인, 또는 zod 스키마 검증.
**우선순위**: P2

### Minor (5건)

| ID | 제목 | 파일 | 수정 제안 |
|----|------|------|----------|
| N-06 | `_PRODUCER_SHUTDOWN_TIMEOUT` 미사용 상수 | vdr_qa_service.py:46 | 제거 |
| N-07 | 폴더 펼침 버튼 `aria-expanded` 누락 | VdrDocumentSelector.tsx:158 | `aria-expanded={...}` 추가 |
| N-08 | SSE location에 `gzip off;` 미명시 | nginx/prod.conf:138 | `gzip off;` 추가 |
| N-09 | `VdrQASSEEventType` 정의됐으나 미활용 | vdr.ts:157, useVdrQA.ts | 이벤트 분기에 타입 활용 |
| N-10 | conftest.py `qa_rate_limiter.clear()` 누락 | tests/conftest.py:138 | clear() 추가 |

---

## Priority Matrix

### P1 -- 스프린트 우선 (2건)
1. [N-01] API 키 캐시 키 해시 처리
2. [N-02] GZipMiddleware SSE 제외

### P2 -- 개선 권장 (3건)
1. [N-03] 히스토리 리스트 복사본 전달
2. [N-04] document_ids None vs [] 구분
3. [N-05] SSE sources 런타임 검증

### P3 -- 저우선 (5건)
1. [N-06~N-10] 미사용 상수, aria-expanded, gzip off, 타입 활용, 테스트 격리

---

## 기존 보류 항목 (3건, 변경 없음)

| ID | 제목 | 사유 |
|----|------|------|
| M-05 | (transaction_id, status) 복합 DB 인덱스 | Alembic 마이그레이션 필요 |
| M-07 | HTTP 200 + SSE error 이중 에러 경로 | 설계 문서 필요 |
| M-11 | vdr_qa_service SRP 분리 | 대규모 리팩토링 |

---

## 전체 리뷰 이력

| 라운드 | 날짜 | 관점 | 발견 | 수정 | 커밋 |
|--------|------|------|------|------|------|
| 1차 | 03-06 | R2, R4, R5, R6 | 15건 C+M | 15건 | 8e13317 |
| 추가 | 03-07 | R1, R3, R7~R13 | 28건 | 25건 (3건 보류) | 79c900c |
| 재검증 | 03-07 | 전체 | 22건 검증 + 10건 신규 | - | - |
| **합계** | | **R1~R13 전체** | **53건 발견** | **40건 수정** | **13건 잔여** |

잔여 13건 = 보류 3건 + 재검증 신규 10건
