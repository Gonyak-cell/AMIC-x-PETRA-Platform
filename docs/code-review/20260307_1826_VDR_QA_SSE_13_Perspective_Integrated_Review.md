# VDR Q&A SSE — 13개 관점 통합 리뷰

> **Review Date**: 2026-03-07 18:26
> **Reviewer**: Claude Code (3-agent parallel review)
> **Scope**: 수정 완료 후 코드 대상, 13개 관점 통합 리뷰 (기존 보고 이슈 제외)
> **Method**: R1~R13 전체 관점 병렬 에이전트 리뷰
> **Base**: 커밋 79c900c (25건 수정 완료) + fbbf2c2 (재검증 리포트)

---

## Summary

| Severity | Count | Priority Distribution |
|----------|-------|-----------------------|
| Critical | 2     | P0: 2               |
| High     | 2     | P1: 2               |
| Moderate | 7     | P1: 1 / P2: 6       |
| Minor    | 5     | P3: 5               |
| **Total**| **16**| P0: **2** / P1: **3** / P2: **6** / P3: **5** |

**에이전트 배분**:
- Agent 1 (R1+R3+R7): 코드 품질, 타입 안전성, 성능 — 4 Warnings + 3 Suggestions
- Agent 2 (R2+R5+R8+R12): 보안, 운영, API 설계, 데이터 무결성 — 1 HIGH + 4 MEDIUM + 4 LOW
- Agent 3 (R4+R6+R9+R10+R11+R13): 복원력, UX, 테스트, 아키텍처, 접근성, 인프라 — 2 P0 + 2 P1 + 4 P2 + 4 P3

**중복 병합**: R4-02(genai 경쟁 조건)과 M-04(genai 전역 상태)를 F-04로 병합

---

## Findings

### P0 — 즉시 수정 (2건)

#### [F-01] docker-compose.prod.yml에 GOOGLE_API_KEY 미전달 — [Critical/HIGH]

- **관점**: R13 (Deployment/Infrastructure)
- **파일**: docker-compose.prod.yml:249-262
- **설명**: deal-mgmt-api 서비스의 environment 블록에 `GOOGLE_API_KEY`가 없음. config.py에서 기본값이 빈 문자열이므로, 프로덕션에서 VDR Q&A 요청 시 항상 503 반환. celery-worker에만 GOOGLE_API_KEY가 전달됨.
- **증거**:
  ```yaml
  deal-mgmt-api:
    environment:
      DATABASE_URL: ...
      # GOOGLE_API_KEY 없음!

  deal-mgmt-celery-worker:
    environment:
      GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}  # 여기에만 있음
  ```
- **수정 제안**: deal-mgmt-api environment에 `GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}` 추가

#### [F-02] docker-compose.prod.yml에 VDR_QA_ENABLED 미전달 — [Critical/HIGH]

- **관점**: R13 (Deployment/Infrastructure)
- **파일**: docker-compose.prod.yml:249-262, deal-mgmt/app/core/config.py:78
- **설명**: config.py에서 `VDR_QA_ENABLED: bool = False`가 기본값. docker-compose.prod.yml에 이 환경변수가 전달되지 않으므로 항상 403 반환.
- **증거**:
  ```python
  # config.py:78
  VDR_QA_ENABLED: bool = False
  ```
  docker-compose.prod.yml deal-mgmt-api environment에 VDR_QA_ENABLED 없음
- **수정 제안**: `VDR_QA_ENABLED: ${VDR_QA_ENABLED:-true}` 추가

---

### P1 — 스프린트 우선 (3건)

#### [F-03] stream_vdr_question manual DB session — auth 구조 취약 — [High/HIGH]

- **관점**: R2 (Security)
- **파일**: deal-mgmt/app/routers/vdr.py (stream_vdr_question 함수)
- **설명**: SSE 스트리밍 엔드포인트가 `Depends(get_jwt_claims)` 대신 수동으로 `async_session_factory()`를 생성하여 인증을 처리. FastAPI의 의존성 주입 보안 체인을 우회하므로, 인증 미들웨어 변경 시 이 엔드포인트만 누락될 위험.
- **수정 제안**: `get_jwt_claims`를 Depends로 주입하고, DB 세션만 수동 관리하는 구조로 분리

#### [F-04] genai.configure() 전역 상태 경쟁 조건 — [Moderate→High/MEDIUM]

- **관점**: R4 (Resilience), R10 (Architecture)
- **파일**: deal-mgmt/app/services/vdr_qa_service.py:255-270
- **설명**: `_get_model()`에서 `genai.configure(api_key=api_key)`가 프로세스 전역 상태를 변경. 동시 요청 시 교차 호출로 잘못된 API 키 사용 가능. 현재 --workers 1이므로 asyncio 컨텍스트 스위칭에서만 발생 가능하나, 워커 증설 시 위험 증가.
- **수정 제안**: asyncio.Lock으로 원자적 실행 보장, 또는 모델별 직접 api_key 전달 방식 전환

#### [F-05] useVdrQA fetch에 JWT 토큰 미전달 — [High/HIGH]

- **관점**: R6 (UX), R4 (Resilience)
- **파일**: amic-platform/src/modules/ma/hooks/useVdrQA.ts:112-122
- **설명**: axios(maApi) 기반 일반 API는 Authorization 헤더가 자동 포함되나, SSE fetch는 `credentials: "include"`만 설정. httpOnly 쿠키 기반이면 문제없으나, 헤더 기반 인증 폴백 시 SSE만 401 실패.
- **증거**:
  ```typescript
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },  // Authorization 없음
    credentials: "include",
    body, signal,
  });
  ```
- **수정 제안**: maApi 인터셉터에서 현재 토큰을 가져와 `Authorization: Bearer ${token}` 헤더 추가

---

### P2 — 개선 권장 (6건)

#### [F-06] asyncio.gather에 return_exceptions=True 누락 — [Moderate/HIGH]

- **관점**: R1 (Code Quality), R4 (Resilience)
- **파일**: deal-mgmt/app/services/vdr_qa_service.py (_resolve_file_refs)
- **설명**: `asyncio.gather(*tasks)`에서 하나의 파일 해석 실패 시 전체 gather가 예외로 중단됨. 나머지 성공 파일의 결과도 함께 소실.
- **수정 제안**: `asyncio.gather(*tasks, return_exceptions=True)` + 개별 예외 로깅

#### [F-07] _ensure_file_uris 임시 파일 정리 실패 시 고아 디렉토리 누적 — [Moderate/HIGH]

- **관점**: R4 (Resilience)
- **파일**: deal-mgmt/app/services/vdr_qa_service.py:353-356
- **설명**: `tmp_path.unlink()` 실패 시 `tmp_dir.rmdir()`도 실패하고 예외가 무시됨. 장기 실행 시 /tmp에 고아 디렉토리 누적.
- **수정 제안**: `shutil.rmtree(tmp_dir, ignore_errors=True)` 또는 `tempfile.TemporaryDirectory` 컨텍스트 매니저

#### [F-08] ask_question_stream/prepare_qa_context 테스트 전무 — [Moderate/HIGH]

- **관점**: R9 (Testing)
- **파일**: deal-mgmt/tests/test_vdr_qa.py
- **설명**: 순수 함수만 테스트 존재. 핵심 비즈니스 로직(prepare_qa_context, ask_question_stream)에 대한 테스트 부재. SSE 이벤트 순서, 타임아웃, 보안 차단 미검증.
- **수정 제안**: Gemini mock으로 SSE 이벤트 시퀀스 검증, 프롬프트 인젝션 차단 통합 테스트

#### [F-09] /qa/stream 엔드포인트 통합 테스트 부재 — [Moderate/HIGH]

- **관점**: R9 (Testing)
- **파일**: deal-mgmt/tests/
- **설명**: SSE 엔드포인트의 HTTP 레벨 통합 테스트 없음. 수동 DB 세션, StreamingResponse, 에러 이벤트 등 특수 패턴이 미검증.
- **수정 제안**: httpx.AsyncClient로 403(disabled), 503(no key), 정상 SSE 스트림 검증

#### [F-10] _conversation_store/model_cache 멀티 워커 비안전 — [Moderate/MEDIUM]

- **관점**: R10 (Architecture)
- **파일**: deal-mgmt/app/services/vdr_qa_service.py:54, 252
- **설명**: 모듈 전역 변수로 관리되어 워커 증가 시 대화 연속성 깨짐. 코드 주석에 제약 명시되어 있으나 자동 경고 메커니즘 없음.
- **수정 제안**: startup 시 워커 수 체크 → 경고 로그, 또는 Redis 기반 저장소 전환 계획 문서화

#### [F-11] cost_usd 클라이언트 노출 — [Moderate/MEDIUM]

- **관점**: R2 (Security), R8 (API Design)
- **파일**: deal-mgmt/app/schemas/vdr.py, useVdrQA.ts
- **설명**: SSE sources 이벤트에 cost_usd가 포함되어 클라이언트에 전달됨. 내부 비용 정보가 외부에 노출되며, 공격자가 비용 최적화된 리소스 소모 공격에 활용 가능.
- **수정 제안**: sources 이벤트에서 cost_usd 제거, 서버 로그에만 기록

---

### P3 — 저우선 (5건)

#### [F-12] VdrDocumentSelector 개별 문서 체크박스 aria-label 누락 — [Minor/HIGH]

- **관점**: R11 (Accessibility)
- **파일**: amic-platform/src/modules/ma/components/VdrDocumentSelector.tsx:199-202
- **설명**: 개별 문서 체크박스에 aria-label이 없어 스크린 리더가 "체크박스"만 읽음.
- **수정 제안**: `aria-label={doc.original_name}` 추가

#### [F-13] 빈 Gemini 응답 시 빈 assistant 메시지 저장 — [Minor/HIGH]

- **관점**: R4, R6
- **파일**: deal-mgmt/app/services/vdr_qa_service.py:672-718
- **설명**: 모든 chunk.text가 빈 문자열이면 빈 답변이 히스토리에 저장되고 FE에 빈 말풍선 표시.
- **수정 제안**: chunks 비어있으면 폴백 메시지 또는 error 이벤트 발행

#### [F-14] 스트리밍 취소 시 빈 assistant 메시지 잔류 — [Minor/HIGH]

- **관점**: R6 (UX)
- **파일**: amic-platform/src/modules/ma/hooks/useVdrQA.ts:71-74, 211-213
- **설명**: 스트리밍 전에 빈 assistant 메시지가 추가되나, AbortError 시 정리되지 않아 빈 말풍선 잔류.
- **수정 제안**: AbortError 처리 시 마지막 assistant 메시지가 비어있으면 제거

#### [F-15] VdrQAPanel 채팅 영역에 role="log" 미적용 — [Minor/MEDIUM]

- **관점**: R11 (Accessibility)
- **파일**: amic-platform/src/modules/ma/components/VdrQAPanel.tsx:168
- **설명**: aria-live="polite"만 적용. WAI-ARIA 채팅 패턴 권장 role="log" 미사용.
- **수정 제안**: `role="log"` + `aria-atomic="false"` 추가

#### [F-16] list_all_documents 페이지네이션 미지원 — [Minor/MEDIUM]

- **관점**: R7 (Performance)
- **파일**: deal-mgmt/app/services/vdr_qa_service.py
- **설명**: 문서 전체 조회 시 페이지네이션 없이 모든 문서를 한 번에 로드. VDR_QA_MAX_DOCUMENTS=50 제한이 있으나, DB 쿼리 자체에 LIMIT 없음.
- **수정 제안**: DB 쿼리에 LIMIT 절 추가

---

## 기존 이슈와의 관계

### 이미 보고된 이슈 (이 리뷰에서 제외)

| 출처 | 이슈 | 상태 |
|------|------|------|
| 재검증 리뷰 | N-01~N-10 (10건) | 미수정 |
| 이전 리뷰 | M-05 (복합 DB 인덱스) | 보류 |
| 이전 리뷰 | M-07 (이중 에러 경로) | 보류 |
| 이전 리뷰 | M-11 (SRP 분리) | 보류 |

### 병합된 이슈

| 원본 | 병합 대상 | 결과 |
|------|----------|------|
| Agent 2 M-04 (genai 전역 상태) | Agent 3 R4-02 (경쟁 조건) | → F-04 (두 관점 통합) |

---

## Priority Matrix

### P0 — 즉시 수정 (2건, 프로덕션 배포 차단)
1. **[F-01]** GOOGLE_API_KEY 미전달 → docker-compose.prod.yml
2. **[F-02]** VDR_QA_ENABLED 미전달 → docker-compose.prod.yml

### P1 — 스프린트 우선 (3건)
1. **[F-03]** 수동 DB session 인증 우회 → vdr.py
2. **[F-04]** genai.configure 전역 상태 경쟁 조건 → vdr_qa_service.py
3. **[F-05]** fetch JWT 토큰 미전달 → useVdrQA.ts

### P2 — 개선 권장 (6건)
1. **[F-06]** asyncio.gather return_exceptions 누락 → vdr_qa_service.py
2. **[F-07]** 임시 파일 정리 실패 → vdr_qa_service.py
3. **[F-08]** ask_question_stream 테스트 부재 → tests/
4. **[F-09]** /qa/stream 통합 테스트 부재 → tests/
5. **[F-10]** 멀티 워커 비안전 아키텍처 → vdr_qa_service.py
6. **[F-11]** cost_usd 클라이언트 노출 → vdr.ts/vdr.py

### P3 — 저우선 (5건)
1. **[F-12]** 문서 체크박스 aria-label 누락 → VdrDocumentSelector.tsx
2. **[F-13]** 빈 응답 시 빈 메시지 저장 → vdr_qa_service.py
3. **[F-14]** 취소 시 빈 메시지 잔류 → useVdrQA.ts
4. **[F-15]** role="log" 미적용 → VdrQAPanel.tsx
5. **[F-16]** 문서 조회 페이지네이션 미지원 → vdr_qa_service.py

---

## 전체 리뷰 이력

| 라운드 | 날짜 | 관점 | 발견 | 수정 | 커밋 |
|--------|------|------|------|------|------|
| 1차 | 03-06 | R2, R4, R5, R6 | 15건 C+M | 15건 | 8e13317 |
| 추가 | 03-07 | R1, R3, R7~R13 | 28건 | 25건 (3건 보류) | 79c900c |
| 재검증 | 03-07 | 전체 | 22건 검증 + 10건 신규 | - | fbbf2c2 |
| **13관점 통합** | **03-07** | **R1~R13 전체** | **16건 신규** | - | - |
| **누적** | | **R1~R13** | **69건** | **40건** | **29건 잔여** |

잔여 29건 = 보류 3건 + 재검증 신규 10건 + 13관점 통합 16건

---

## Methodology

- **Agents**: 3개 병렬 에이전트 (R1+R3+R7 / R2+R5+R8+R12 / R4+R6+R9+R10+R11+R13)
- **Files scanned**: 10개 (BE 4, FE 4, Infra 2)
- **Protocol**: Verified Claim Protocol — 실제 코드 Read 후 증거 기반 보고
- **Deduplication**: 기존 보고 이슈(N-01~N-10, M-05/M-07/M-11) + 에이전트 간 중복 병합
