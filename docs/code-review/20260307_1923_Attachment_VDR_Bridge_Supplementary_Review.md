# Code Review — Attachment-VDR Bridge 추가 통합 리뷰

> **Review Date**: 2026-03-07 19:23
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 마케팅 자료 첨부 파일 → VDR 자동 연동 구현 전체 (BE + FE)
> **Method**: Quality Gates + Verified Multi-Agent Review (5 agents) + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS) pytest(PASS)
> **Agents**: Python Code Reviewer, Security Reviewer, Performance Profiler, Migration Validator, FE Type/Hook Reviewer

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1 | HIGH: 1 | P0: 1 |
| Major | 4 | HIGH: 2 / MEDIUM: 2 | P1: 2 / P2: 2 |
| Moderate | 8 | HIGH: 5 / MEDIUM: 3 | P2: 5 / P3: 3 |
| Minor | 6 | HIGH: 3 / MEDIUM: 3 | P3: 6 |
| **Total** | **19** | HIGH: **11** / MEDIUM: **8** | P0: **1** / P1: **2** / P2: **7** / P3: **9** |

**FP Prevention**: 가설 28건 검증, 9건 사전 거부 (거부율: 32%)
**Cross-Verification**: Critical + Major 6건 수행 → FP 2건 제거, PARTIAL 2건 조정

---

## Phase 2: Cross-Verification Results

| ID | 원본 심각도 | 판정 | 사유 |
|----|-----------|------|------|
| A-01 | Critical/HIGH | **CONFIRMED** | JWTClaims에 `sub` 필드 없음, 7곳에서 `claims.sub` 직접 접근 |
| S-01 | Critical/HIGH | **PARTIAL → Major** | `.gitignore`에 `.env` 포함 → git 미추적. "커밋됨" 주장은 FP |
| C-01 | Critical/HIGH | **CONFIRMED → Major** | cost_usd 노출 확인. 보안 위험보다는 정보 노출 수준 → 심각도 하향 |
| A-02 | High/HIGH | **FALSE_POSITIVE** | `check_client_deal_access` 이미 4곳 호출 (L110, 152, 289, 315) |
| R1 | Major/HIGH | **FALSE_POSITIVE** | 401은 정상 응답, signal 미abort → 재시도 시 signal 유효 |
| M-01 | Major/HIGH | **PARTIAL → Moderate** | anyio 트랜지티브 dep로 설치됨, 테스트 실제 통과. 혼용 정리 권장 수준 |

---

## Findings (우선순위 점수 내림차순)

### [A-01] `claims.sub` AttributeError — Runtime 500 에러 [Critical/HIGH] — P0 (점수: 100)

**파일**: `deal-mgmt/app/routers/vdr.py`
**위치**: L348, L530, L591, L781, L805, L844, L868

**문제**: `JWTClaims` 데이터클래스에는 `user_id`, `email`, `role` 3개 필드만 존재 (`security.py:26-31`). 그러나 `vdr.py`에서 `claims.sub`를 7곳에서 참조.

- L781: `qa_rate_limiter.check(claims.sub)` — **직접 접근, 즉시 AttributeError**
- L844: `qa_rate_limiter.check(claims.sub)` — 동일
- L805: `user_sub=claims.sub` — 동일
- L868: `user_sub=claims.sub` — 동일
- L348/530/591: `claims.email or claims.sub` — email이 None이면 동일 에러

**영향**: VDR Q&A 엔드포인트(비스트리밍/스트리밍) 호출 시 100% 500 에러. Rate limiter도 우회됨.

**수정 방안**: `claims.sub` → `claims.user_id` 전체 치환

```python
# Before
qa_rate_limiter.check(claims.sub)
user_sub=claims.sub

# After
qa_rate_limiter.check(claims.user_id)
user_sub=claims.user_id
```

**검증**: Read로 security.py:26-31 확인, Grep으로 7곳 위치 확인.

---

### [C-01] cost_usd 비인가 노출 [Major/HIGH] — P1 (점수: 70)

**파일**: `deal-mgmt/app/routers/vdr.py:822`
**교차 검증**: Python Code Reviewer + Security Reviewer 동시 발견

**문제**: 비스트리밍 Q&A 응답에서 `cost_usd`가 모든 인증 사용자에게 노출.
```python
return VdrQAResponse(
    answer=result.answer,
    sources=[...],
    conversation_id=result.conversation_id,
    cost_usd=result.cost_usd,  # 모든 사용자에게 노출
)
```

**수정 방안**: ADMIN 역할만 cost_usd 포함, 그 외는 None 반환
```python
cost_usd=result.cost_usd if claims.role == "ADMIN" else None,
```

---

### [S-01] .env 파일 보안 관리 [Major/MEDIUM] — P1 (점수: 42)

**파일**: `deal-mgmt/.env`

**원본 주장**: ".env에 실제 API 키가 커밋됨" → **교차 검증: .gitignore에 .env 포함 (line 2), git 미추적 확인**

**잔여 위험**: 서버에 실제 API 키(Anthropic, OpenAI, Google, Azure Storage)가 포함된 .env 파일 존재. 서버 접근 시 키 유출 가능.

**권장**: 환경변수 관리를 Azure Key Vault 또는 GitHub Secrets로 이전 검토

---

### [P5] VDR 복합 인덱스 누락 [Major/HIGH] — P1 (점수: 70)

**파일**: `deal-mgmt/app/models/vdr_document.py`

**문제**: `vdr_documents` 테이블에 빈번한 쿼리 패턴에 대한 복합 인덱스 미정의:
- `(transaction_id, classification_status)` — 분류 상태별 조회
- `(folder_id, transaction_id, classification_status)` — 폴더별 문서 목록

**영향**: 문서 수 증가 시 풀 테이블 스캔 → 응답 지연

**수정 방안**: Alembic 마이그레이션으로 복합 인덱스 추가

---

### [P6] 50MB 파일 전체 메모리 로드 [Major/MEDIUM] — P2 (점수: 42)

**파일**: `deal-mgmt/app/services/attachment_vdr_bridge.py:116`

**문제**: `file_content = await asyncio.to_thread(file_path.read_bytes)` — 최대 50MB 파일을 메모리에 전체 로드

**영향**: 동시 업로드 시 메모리 압박. 현재 단일 워커(2 vCPU/16GB RAM) 환경에서는 수용 가능하나, 확장 시 리스크.

**상태**: 설계 단계에서 인지된 트레이드오프. 스트리밍 업로드로 전환은 VDR 서비스 리팩토링 필요.

---

### [P3] Gemini 문서 직렬 업로드 [Moderate/HIGH] — P2 (점수: 40)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:373-405`

**문제**: VDR Q&A에서 Gemini File API에 문서를 하나씩 순차 업로드. N개 문서 시 N × RTT 지연.

**수정 방안**: `asyncio.gather()` 또는 `asyncio.Semaphore(3)`으로 병렬화

---

### [M-02] `run_in_threadpool` 서비스 레이어 사용 [Moderate/MEDIUM] — P2 (점수: 24)

**문제**: Starlette 내부 함수 `run_in_threadpool`을 서비스 레이어에서 직접 사용. 프레임워크 결합도 증가.

**수정 방안**: `asyncio.to_thread()` (stdlib)로 대체

---

### [M-03] os/sys 지연 import [Moderate/MEDIUM] — P2 (점수: 24)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:59-84`

**문제**: `os`, `sys` 등 stdlib 모듈을 함수 내부에서 지연 import. 성능 이점 없고 가독성 저하.

---

### [MOD-01] Pydantic validator 타입 힌트 불일치 [Moderate/HIGH] — P2 (점수: 40)

**문제**: `@field_validator`에서 `cls` 대신 `self` 사용 또는 반환 타입 누락. Pydantic v2 경고 유발 가능.

---

### [R2] VdrQAResponse cost_usd 타입 불일치 [Moderate/HIGH] — P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/types/vdr.ts`

**문제**: BE에서 `cost_usd: float | None`이지만 FE 타입에서 `number` (nullable 미반영).

---

### [P1] init_vdr_folders 후 N회 refresh [Moderate/HIGH] — P2 (점수: 40)

**문제**: VDR 초기화 시 12개 기본 폴더 생성 후 각각 `db.refresh()` → 12 DB 라운드트립.

**수정 방안**: `flush()` + 단일 `commit()` 패턴으로 라운드트립 최소화

---

### [R3] refreshAuth promise chain .catch() 누락 [Moderate/MEDIUM] — P3 (점수: 24)

**파일**: `amic-platform/src/api/client.ts:23-41`

**문제**: refreshAuth 호출 시 reject 핸들러 미연결 → unhandled promise rejection 가능.

---

### [P9] GenerativeModel 매 호출 생성 [Moderate/MEDIUM] — P3 (점수: 24)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py`

**문제**: Q&A 호출마다 `GenerativeModel` 인스턴스 신규 생성. 모듈 레벨 캐싱으로 개선 가능.

---

### [V-04] 인덱스명 자동생성 불일치 가능 [Moderate/HIGH] — P3 (점수: 40)

**파일**: `deal-mgmt/migrations/versions/071_attachment_vdr_document_id.py`

**상태**: Migration Validator APPROVED. 인덱스명 `ix_attachments_vdr_document_id` 명시적 지정 확인. WARNING 수준.

---

### [R4] SSE 파서 멀티라인 data 미지원 [Minor/MEDIUM] — P3 (점수: 12)

**파일**: `amic-platform/src/modules/ma/hooks/useVdrQA.ts`

**문제**: SSE 스트림에서 `data:` 접두사 파싱이 단일 라인만 지원. 현재 서버가 멀티라인 전송하지 않으므로 실제 영향 없음.

---

### [R5] VDR 캐시 무효화 매직 스트링 [Minor/HIGH] — P3 (점수: 20)

**문제**: `queryKey: ["ma", "transactions", txnId, "vdr"]` 하드코딩. queryKey 팩토리 패턴 권장.

---

### [R6] 오디오 MIME 타입 라벨 누락 [Minor/HIGH] — P3 (점수: 20)

**파일**: `amic-platform/src/modules/ma/types/attachment.ts`

**문제**: `ATTACHMENT_MIME_LABELS`에 오디오 MIME 타입(audio/mpeg, audio/wav 등) 매핑 누락.

---

### [MOD-05] Gemini 파일 정리 누락 [Minor/HIGH] — P3 (점수: 20)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py`

**문제**: Gemini File API에 업로드된 임시 파일의 명시적 삭제 미구현. Gemini 자동 만료(48h)에 의존.

---

### [P10] 인메모리 대화 저장소 [Minor/MEDIUM] — P3 (점수: 12)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py`

**문제**: 대화 히스토리가 dict로 메모리에 저장. 워커 재시작 시 소멸. 현재 단일 워커이므로 즉시 문제 아님.

---

### [MIN-03] InMemory Rate Limiter 멀티워커 우회 [Minor/MEDIUM] — P3 (점수: 12)

**문제**: 인메모리 rate limiter는 단일 프로세스에서만 유효. 멀티 워커 시 우회됨. 코드 주석에 이미 인지됨.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 런타임 에러)
1. **[A-01]** [Critical/HIGH]: `claims.sub` AttributeError → VDR Q&A 100% 500 에러 — vdr.py (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89)
1. **[C-01]** [Major/HIGH]: cost_usd 비인가 노출 — vdr.py:822 (점수: 70)
2. **[P5]** [Major/HIGH]: VDR 복합 인덱스 누락 — vdr_document.py (점수: 70)

### P2 — 개선 권장 (점수: 30-59)
1. **[S-01]** [Major/MEDIUM]: .env 보안 관리 (점수: 42)
2. **[P6]** [Major/MEDIUM]: 50MB 전체 메모리 로드 (점수: 42)
3. **[P3]** [Moderate/HIGH]: Gemini 직렬 업로드 (점수: 40)
4. **[MOD-01]** [Moderate/HIGH]: Pydantic validator 타입 힌트 (점수: 40)
5. **[R2]** [Moderate/HIGH]: cost_usd FE 타입 불일치 (점수: 40)
6. **[P1]** [Moderate/HIGH]: N회 refresh 라운드트립 (점수: 40)
7. **[M-02]** [Moderate/MEDIUM]: run_in_threadpool 결합 (점수: 24)

### P3 — 저우선 (점수: <30)
1. **[M-03]** [Moderate/MEDIUM]: os/sys 지연 import (점수: 24)
2. **[R3]** [Moderate/MEDIUM]: refreshAuth .catch() 누락 (점수: 24)
3. **[P9]** [Moderate/MEDIUM]: GenerativeModel 캐싱 (점수: 24)
4. **[V-04]** [Moderate/HIGH]: 인덱스명 자동생성 (점수: 40, WARNING)
5. **[R5]** [Minor/HIGH]: queryKey 매직 스트링 (점수: 20)
6. **[R6]** [Minor/HIGH]: 오디오 MIME 라벨 (점수: 20)
7. **[MOD-05]** [Minor/HIGH]: Gemini 파일 정리 (점수: 20)
8. **[R4]** [Minor/MEDIUM]: SSE 멀티라인 (점수: 12)
9. **[P10]** [Minor/MEDIUM]: 인메모리 대화 저장소 (점수: 12)

---

## Methodology

- **Agents**: Python Code Reviewer, Security Reviewer, Performance Profiler, Migration Validator, FE Type/Hook Reviewer
- **Files scanned**: ~25 files (BE router/service/model/schema + FE hooks/types)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 6건 수행 → FP 2건 제거 (A-02, R1), PARTIAL 2건 (S-01, M-01)

## 검증 투명성

### 검증 통계
- 검증한 가설: 28건
- 거부된 가설 (사전 제거): 9건
- 보고된 이슈: 19건
- 거부율: 32%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | A-02: `check_client_deal_access` 이미 4곳 호출 확인 |
| 범위 외 | 2 | 백엔드 일반 패턴 이슈 (이번 변경 범위 밖) |
| 오판 | 2 | R1: 401은 abort가 아닌 정상 응답, signal 유효 |
| 심각도 재조정 | 2 | S-01: Critical→Major (.gitignore 확인), M-01: Major→Moderate (테스트 통과) |

---

## 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | Attachment 모델 `vdr_document_id` 추가 | OK | attachment.py FK 컬럼 확인 |
| 2 | Alembic 마이그레이션 | OK | 071_attachment_vdr_document_id.py 검증 APPROVED |
| 3 | 스키마 확장 (VdrSyncInfo) | OK | schemas/attachment.py 확인 |
| 4 | Bridge 서비스 생성 | OK | attachment_vdr_bridge.py + 5개 단위 테스트 |
| 5 | 라우터 수정 (best-effort 연동) | OK | attachments.py에 VDR 연동 호출 추가 확인 |
| 6 | FE 타입 추가 | OK | attachment.ts VdrSyncInfo 타입 추가 확인 |
| 7 | FE 캐시 무효화 | OK | useAttachments.ts onSuccess VDR 캐시 무효화 확인 |
