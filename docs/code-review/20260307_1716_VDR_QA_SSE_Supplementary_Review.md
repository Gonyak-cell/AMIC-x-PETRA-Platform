# VDR Q&A SSE 스트리밍 — 추가 통합 리뷰 (9개 관점)

> **Review Date**: 2026-03-07 17:16
> **Reviewer**: Claude Code (multi-agent)
> **Scope**: VDR Q&A 챗봇 SSE 스트리밍 + 문서 선택 기능
> **Method**: 5개 병렬 에이전트 → 교차 검증 → 중복 제거
> **이전 리뷰**: R2 Security, R4 Resilience, R5 Operations, R6 UX (완료, 커밋 8e13317)
> **본 리뷰**: R1, R3, R7, R8, R9, R10, R11, R12, R13

---

## Summary

| Severity | Count | Cross-verified |
|----------|-------|----------------|
| Critical | 3     | 0 (테스트 커버리지 — 단독 발견) |
| Major    | 10    | 5건 (2+ 에이전트 교차 확인) |
| Moderate | 14    | 2건 |
| Minor    | 8     | 1건 |
| **Total**| **35 (중복 제거 후 28)** | **8건** |

**중복 제거**: 7건의 동일 이슈가 복수 에이전트에서 보고 → 교차 검증됨으로 표시 후 병합

---

## Critical (3건)

### [C-01] ask_question_stream / prepare_qa_context 테스트 완전 부재 — R9

**파일**: `deal-mgmt/tests/test_vdr_qa.py`
**에이전트**: R9 Testing (단독)

690줄 서비스 파일의 핵심 비즈니스 로직(`ask_question_stream` 534~689행, `prepare_qa_context` 344~408행)에 대한 테스트가 **0건**. 현재 18건 테스트는 모두 순수 유틸 함수(`_validate_question`, `_sanitize_answer` 등)만 커버.

미검증 경로:
- 정상 스트리밍 → token + sources + done 이벤트 순서
- Gemini TimeoutError → error 이벤트
- 슬라이딩 윈도우 fingerprint 탐지 → 조기 종료
- 세션 타임아웃 초과 → error 이벤트
- 프롬프트 인젝션 → QAResult 반환 (rejection)
- 문서 없음 → "참조 가능한 문서 없음" QAResult

**우선순위**: P0 (핵심 경로 리그레션 위험)

---

### [C-02] /qa/stream 엔드포인트 통합 테스트 부재 — R9

**파일**: `deal-mgmt/tests/test_vdr_qa.py`
**에이전트**: R9 Testing (단독)

라우터의 `stream_vdr_question()` (826~897행)은 수동 DB 세션, QAResult early exit, StreamingResponse 생성 등 고유 로직을 포함하지만, 엔드포인트 레벨 테스트 **0건**.

미검증 시나리오: VDR_QA_ENABLED=False → 403, GOOGLE_API_KEY 미설정 → 503, 권한 없음 → 403, prepare 단계 거부 → SSE error 스트림

**우선순위**: P0

---

### [C-03] FE 훅/컴포넌트 테스트 완전 부재 — R9

**파일**: `useVdrQA.ts`, `VdrQAPanel.tsx`, `VdrDocumentSelector.tsx`
**에이전트**: R9 Testing (단독)

`useVdrQA` 훅(SSE 파싱, rAF 배칭, AbortController), `VdrDocumentSelector`(폴더별 선택 토글) 등 복잡한 FE 로직에 대한 단위 테스트 전무.

**우선순위**: P1 (BE 대비 상대적으로 낮으나 여전히 중요)

---

## Major (10건, 중복 제거 후 7건)

### [J-01] BE/FE relevance 타입 불일치 — R8, R10 (교차 검증)

**파일**: BE `vdr_qa_service.py:75` / FE `vdr.ts:122`
**에이전트**: R8 API Design + R10 Architecture (2건 → 1건 병합)

BE: `relevance: str = "referenced"` → FE: `relevance?: "high" | "medium" | "low"`. FE 타입에 `"referenced"` 없음. 런타임에서 relevance 기반 조건문이 항상 false가 되어 UI 동작 불일치 가능.

**수정 제안**: FE 타입을 `relevance?: string`으로 변경하거나 `"referenced"` 추가

**우선순위**: P1

---

### [J-02] genai.configure() 전역 상태 경쟁 — 중복 호출 — R1, R7, R10 (3개 에이전트 교차 검증)

**파일**: `vdr_qa_service.py:216, 244`
**에이전트**: R1 Code Quality + R7 Performance + R10 Architecture

`genai.configure(api_key=)`가 `_resolve_file_refs()`와 `_get_model()` 양쪽에서 호출. 프로세스 전역 상태 변경이므로 동시 요청 시 API 키 덮어쓰기 위험. 현재 단일 키 환경에서는 무해하나, 멀티 테넌트 확장 시 보안 취약점.

**수정 제안**: `_resolve_file_refs()`에서 `genai.configure()` 제거, `_get_model()`에 일원화

**우선순위**: P1

---

### [J-03] _model_cache 무제한 증가 (eviction 없음) — R7, R10 (교차 검증)

**파일**: `vdr_qa_service.py:235-250`
**에이전트**: R7 Performance + R10 Architecture

`_model_cache: dict[str, genai.GenerativeModel] = {}` — eviction 정책 없음. `_conversation_store`는 LRU eviction이 있으나 `_model_cache`는 일반 dict. 현재 엔트리 소수이므로 실질 위험 낮으나 아키텍처 일관성 부족.

**수정 제안**: `functools.lru_cache(maxsize=8)` 또는 동일 OrderedDict 패턴

**우선순위**: P2

---

### [J-04] _resolve_file_refs / _ensure_file_uris 순차 처리 — R7 (단독)

**파일**: `vdr_qa_service.py:218-225, 301-336`
**에이전트**: R7 Performance

문서 N개에 대해 `genai.get_file`(라인 218-225)과 blob 다운로드+업로드(라인 301-336)가 순차 실행. 50개 문서 기준 5~15초 지연 → SSE 첫 토큰 도달 시간에 직접 반영.

**수정 제안**: `asyncio.gather()` 병렬화, 루프 내 `db.flush()` 제거 → 루프 완료 후 1회 통합

**우선순위**: P1

---

### [J-05] nginx SSE location에 proxy_http_version 1.1 누락 — R13 (단독)

**파일**: `nginx/prod.conf:138-149`
**에이전트**: R13 Deployment/Infrastructure

SSE location에 `proxy_http_version 1.1`과 `Connection ""` 헤더 미설정. nginx 기본값은 HTTP/1.0 → chunked transfer encoding 미지원 → SSE 불안정/조기 종료 가능.

**수정 제안**: `proxy_http_version 1.1;`, `proxy_set_header Connection "";` 추가

**우선순위**: P1

---

### [J-06] docker-compose.prod.yml workers=2 vs entrypoint workers=1 충돌 — R13 (단독)

**파일**: `docker-compose.prod.yml:246`, `docker-entrypoint.sh:7`
**에이전트**: R13 Deployment + R10 Architecture (교차 검증)

`docker-compose.prod.yml`에서 `--workers 2` 하드코딩 → entrypoint의 `${WORKERS:-1}` 무시. workers=2에서 인메모리 `_conversation_store`가 워커별 분리 → 멀티턴 대화 깨짐.

**수정 제안**: command 제거 → entrypoint 사용, 또는 WORKERS=1 환경변수 명시 설정

**우선순위**: P0

---

### [J-07] SSE 스트림 중단 시 부분 답변 히스토리 미저장 — R8 (단독)

**파일**: `vdr_qa_service.py:646-652`
**에이전트**: R8 API Design

에러/타임아웃 시 히스토리 업데이트가 스킵됨. FE에서는 부분 답변이 화면에 남아있으나 BE에서는 해당 턴 미기록 → 다음 질문 시 문맥 불일치.

**수정 제안**: 에러 시에도 accumulated 텍스트가 있으면 히스토리에 저장하거나, FE에서 에러 시 부분 답변 제거

**우선순위**: P2

---

## Moderate (14건, 중복 제거 후 12건)

| ID | 제목 | 관점 | 파일 | 교차 |
|----|------|------|------|------|
| M-01 | O(n^2) 문자열 연결 (`accumulated += text`) | R7 | vdr_qa_service.py:589 | - |
| M-02 | 매 청크 슬라이싱 fingerprint 검사 | R7 | vdr_qa_service.py:591-602 | - |
| M-03 | _conversation_store 히스토리 무제한 증가 | R7 | vdr_qa_service.py:61-66 | - |
| M-04 | InMemoryRateLimiter O(users) stale 정리 | R7 | rate_limiter.py:58-61 | - |
| M-05 | (transaction_id, status) 복합 인덱스 누락 | R7 | vdr_document.py | - |
| M-06 | 비용 계산 1/1000 오차 가능성 | R8 | vdr_qa_service.py:473 | - |
| M-07 | HTTP 200 + SSE error 이중 에러 경로 | R8 | vdr.py:783-792 | - |
| M-08 | `list[object]` 과도한 타입 사용 | R1 | vdr_qa_service.py 다수 | - |
| M-09 | contents 조립 로직 DRY 위반 | R1 | vdr_qa_service.py:447,549 | - |
| M-10 | QAPreparedContext에 api_key 평문 저장 (repr 노출) | R1 | vdr_qa_service.py:97 | - |
| M-11 | vdr_qa_service 10가지 책임 (SRP 위반) | R10 | vdr_qa_service.py 전체 | - |
| M-12 | 채팅 메시지 영역 aria-live 리전 누락 | R11 | VdrQAPanel.tsx:163 | - |
| M-13 | 폴더 체크박스 aria-label 누락 | R11 | VdrDocumentSelector.tsx:172 | - |
| M-14 | textarea aria-label 누락 | R11 | VdrQAPanel.tsx:224 | - |

---

## Minor (8건, 중복 제거 후 7건)

| ID | 제목 | 관점 | 파일 |
|----|------|------|------|
| m-01 | FE pendingTokens 문자열 연결 | R7 | useVdrQA.ts:81 |
| m-02 | tempfile.mkdtemp 문서마다 별도 생성 | R7 | vdr_qa_service.py:320 |
| m-03 | done 이벤트에 conversation_id 미포함 | R8 | vdr_qa_service.py:689 |
| m-04 | UUID 패턴 소문자만 허용 | R1+R8 | vdr.py:188 (교차 검증) |
| m-05 | 함수 내부 import 과다 | R1 | vdr.py:837-842 |
| m-06 | 스트리밍 커서 접근성 대안 없음 | R11 | VdrQAPanel.tsx:37 |
| m-07 | 에러 메시지 role="alert" 없음 | R11 | VdrQAPanel.tsx:24 |

---

## Priority Matrix

### P0 — 즉시 수정 (프로덕션 영향)
1. **[J-06]** [Major/HIGH] docker-compose.prod.yml workers=2 → 멀티턴 대화 깨짐
2. **[C-01]** [Critical/HIGH] ask_question_stream 테스트 0건 → 리그레션 위험
3. **[C-02]** [Critical/HIGH] /qa/stream 엔드포인트 테스트 0건

### P1 — 스프린트 우선
1. **[J-01]** [Major/HIGH] relevance 타입 불일치 → UI 동작 불일치 (교차 검증)
2. **[J-02]** [Major/HIGH] genai.configure 전역 경쟁 (3개 에이전트 교차 검증)
3. **[J-04]** [Major/HIGH] 순차 처리 → SSE 첫 토큰 5~15초 지연
4. **[J-05]** [Major/HIGH] nginx proxy_http_version 1.1 누락 → SSE 불안정
5. **[C-03]** [Critical/HIGH] FE 테스트 전무
6. **[M-12]** [Moderate/HIGH] aria-live 리전 누락 → 스크린리더 차단

### P2 — 개선 권장
1. **[J-03]** [Major/HIGH] _model_cache eviction 없음 (교차 검증)
2. **[J-07]** [Major/HIGH] 스트림 중단 시 히스토리 미저장
3. **[M-01~M-05]** 성능 최적화 (문자열 연결, 인덱스 등)
4. **[M-06]** 비용 계산 정확도
5. **[M-08~M-11]** 코드 품질 (타입, DRY, SRP)

### P3 — 저우선
1. **[M-13,M-14]** 접근성 aria-label 추가
2. **[m-01~m-07]** Minor 전체

---

## 교차 검증 요약

| 이슈 | 보고 에이전트 수 | 병합 ID |
|------|----------------|---------|
| genai.configure 전역 경쟁 | 3 (R1, R7, R10) | J-02 |
| relevance 타입 불일치 | 2 (R8, R10) | J-01 |
| _model_cache eviction 없음 | 2 (R7, R10) | J-03 |
| workers 충돌 / 인메모리 store | 2 (R10, R13) | J-06 |
| UUID 소문자만 허용 | 2 (R1, R8) | m-04 |

---

## 이전 리뷰 (R2, R4, R5, R6) 대비 신규 발견

| 카테고리 | 이전 리뷰 | 본 리뷰 | 비고 |
|----------|----------|---------|------|
| 보안 | 15건 수정 완료 | genai.configure 경쟁 1건 추가 | 멀티테넌트 확장 시 |
| 성능 | - | 10건 신규 | 순차 처리, 메모리, 인덱스 |
| 테스트 | - | 3건 Critical | 핵심 경로 0% 커버리지 |
| 접근성 | - | 7건 | aria-live, aria-label |
| 인프라 | workers=1 적용 | workers=2 하드코딩 발견 | docker-compose.prod.yml |
| 타입 안전성 | - | 3건 | relevance, object, document_id |

---

## Methodology

- **Agents**: python-code-reviewer, performance-profiler, general-purpose x3
- **Perspectives**: R1(코드품질), R3(타입안전성), R7(성능), R8(API설계), R9(테스트), R10(아키텍처), R11(접근성), R12(데이터무결성), R13(배포인프라)
- **Files scanned**: 10 (BE 6, FE 4) + nginx/prod.conf + docker-compose.prod.yml
- **Cross-verification**: 7건 중복 → 5건 교차 검증됨
- **Previously reviewed (R2, R4, R5, R6)**: 15건 Critical+Major 수정 완료 (커밋 8e13317)
