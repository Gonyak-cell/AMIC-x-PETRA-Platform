# Code Review — NDA Markup (Track Change + Version Management)

> **Review Date**: 2026-03-07 23:44 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: NDA Markup 신규 구현 (BE 8파일 + FE 4파일 = 12파일)
> **Method**: Quality Gates + Review Gates + Verified Multi-Agent Review (5 agents) + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(5개 에이전트 호출, 0개 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1                | P0: 1                |
| Major    | 6     | HIGH: 6                | P1: 6                |
| Moderate | 8     | HIGH: 7 / MEDIUM: 1   | P2: 8                |
| Minor    | 7     | HIGH: 4 / MEDIUM: 2 / LOW: 1 | P3: 7         |
| **Total**| **22**| HIGH: **18** / MEDIUM: **3** / LOW: **1** | P0: **1** / P1: **6** / P2: **8** / P3: **7** |

**FP Prevention**: 가설 31건 검증, 3건 사전 거부 (거부율: 10%) | 교차 검증 8건 수행 (FP 1건 제거)
**Cross-Verified**: Critical 1건 + Major 7건 중 1건 FALSE_POSITIVE 판정 (T1 다운로드 URL — 기존 패턴과 동일)

---

## Findings

### P0 — 즉시 수정 (점수: 90+)

#### [C1] 동기 파일 I/O가 async 이벤트 루프를 차단 — Critical/HIGH (점수: 110)

**교차 검증**: CONFIRMED (3개 에이전트 독립 확인 — 보안, Python 품질, 성능)

`generate_nda_redline` 엔드포인트에서 4곳의 동기 I/O가 이벤트 루프를 차단한다. 50MB 파일 처리 시 수백ms~수초 동안 다른 모든 요청이 블로킹된다.

| 위치 | 코드 | 문제 |
|------|------|------|
| `nda_markups.py:253` | `current_file_path.read_bytes()` | 동기 파일 읽기 |
| `nda_markups.py:266` | `Path(base_markup.file_path).read_bytes()` | `run_in_threadpool` 인자 평가 시점에 메인 스레드에서 실행 |
| `nda_markups.py:284` | `Path(prev_markup.file_path).read_bytes()` | 동일 |
| `nda_markups.py:303` | `redline_path.write_bytes(result_docx.getvalue())` | 동기 파일 쓰기 |

같은 파일의 `create_nda_markup`(L127)에서는 `aiofiles`를 올바르게 사용하고 있어 불일치가 있다.

**수정 방향**:
```python
# L253: threadpool에서 파일 읽기
current_bytes = await run_in_threadpool(current_file_path.read_bytes)

# L266, L284: 읽기와 파싱을 함께 threadpool로 위임
def _read_and_extract(path: Path) -> str:
    return redline_engine.extract_paragraphs_text(path.read_bytes())
reference_text = await run_in_threadpool(_read_and_extract, Path(base_markup.file_path))

# L303: aiofiles 사용
async with aiofiles.open(redline_path, "wb") as f:
    await f.write(result_docx.getvalue())
```

---

### P1 — 스프린트 우선 (점수: 60-89)

#### [M1] 단건 조회/삭제/다운로드에서 txn_id↔nda_id 연결 미검증 (IDOR) — Major/HIGH (점수: 85)

**교차 검증**: CONFIRMED

`get_nda_markup`(L62-72), `download_nda_markup`(L157-188), `delete_nda_markup`(L190-218)에서 `check_client_deal_access(db, txn_id, claims)` 후 `_get_markup_or_404(db, nda_id, markup_id)`만 호출한다. `nda_id`가 `txn_id`에 속하는지 검증하지 않아, 접근 권한이 있는 `txn_id`를 사용하면서 다른 거래의 `nda_id`를 지정하면 해당 NDA의 마크업에 접근 가능하다.

`list_nda_markups`(L44-46)와 `generate_nda_redline`(L240-242)에서는 `_get_nda_or_404(db, txn_id, nda_id)`를 올바르게 호출한다.

**참고**: `contract_markups.py:56-66`도 동일한 패턴이나 NDA 민감도를 고려하여 우선 수정 필요.

**수정**: `get_nda_markup`, `download_nda_markup`, `delete_nda_markup`에 `await _get_nda_or_404(db, txn_id, nda_id)` 추가.

---

#### [M2] 삭제 시 Redline 파일 미삭제 (파일 고아 발생) — Major/HIGH (점수: 85)

**교차 검증**: CONFIRMED

`delete_nda_markup`(L204-208)에서 `markup.file_path`(업로드 원본)만 삭제하고 `markup.redline_file_path`(생성된 Redline .docx)는 삭제하지 않는다. Redline이 생성된 마크업을 삭제하면 서버에 파일이 무기한 잔존한다.

**수정**:
```python
for path_attr in (markup.file_path, markup.redline_file_path):
    if path_attr:
        p = Path(path_attr)
        if p.exists():
            p.unlink()
```

---

#### [M3] LLM 서비스 예외 미처리 → 500 + 내부 메시지 노출 — Major/HIGH (점수: 80)

**교차 검증**: CONFIRMED (2개 에이전트 확인)

`generate_nda_redline`(L291-297)에서 `nda_analysis_service.generate_nda_redline()` 호출 시 `ValueError`(유효 이슈 0건)와 `RuntimeError`(LLM 불가용)를 처리하지 않는다. FastAPI가 500으로 반환하며, 에러 메시지에 "LLM이 반환한 N건의 이슈 중 유효한 항목이 없습니다" 등 내부 정보가 포함된다(`nda_analysis_service.py:95`).

**수정**: try/except 블록 추가. `ValueError` → 422, `RuntimeError` → 503, 에러 메시지는 사용자 친화적으로 변환.

---

#### [M4] 비공개 함수 `_call_llm_json` 직접 import — Major/HIGH (점수: 70)

`nda_analysis_service.py:20`에서 `spa_analysis_service._call_llm_json`을 직접 import한다. 언더스코어 접두사 함수는 모듈 내부 구현이므로, SPA 서비스 리팩토링 시 NDA 서비스가 즉시 파괴된다.

**수정**: `_call_llm_json`과 `_get_llm_client`를 `app/services/llm_utils.py`로 분리하여 공개 API로 제공.

---

#### [M5] 마이그레이션↔모델 JSON 컬럼 타입 불일치 — Major/HIGH (점수: 70)

마이그레이션 `073_nda_markups.py:37`의 `key_changes`는 `sa.JSON()`이지만, 모델 `nda_markup.py:39-41`은 `JSON().with_variant(JSONB, "postgresql")`이다. PostgreSQL에서 실제 동작은 동일하나, Alembic `autogenerate`가 schema drift를 감지하여 불필요한 마이그레이션을 생성할 수 있다.

**수정**: 마이그레이션의 `key_changes` 타입을 `sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")`로 통일.

---

#### [M6] 내부 파일 경로 API 응답 노출 — Major/HIGH (점수: 70)

`NdaMarkupOut` 스키마(`nda_markup.py:21, 27`)가 `file_path`와 `redline_file_path`를 그대로 직렬화한다. 서버 파일시스템 경로 정보가 클라이언트에 노출된다.

**참고**: `contract_markups.py`의 `ContractMarkupOut`도 동일. 기존 패턴 이슈(DESIGN_RISK).

**수정**: `file_path` 대신 `has_file: bool`과 `has_redline: bool` 필드로 교체, 또는 `exclude` 처리.

---

### P2 — 개선 권장 (점수: 30-59)

#### [m1] MIME 타입 검증 없음 — Moderate/HIGH (점수: 40)

`nda_markups.py:102-110`에서 파일 확장자만 검증하고 magic bytes는 검사하지 않는다. 악성 파일을 `.docx`로 위장하여 업로드할 수 있다. 기존 `contract_markups.py`도 동일.

---

#### [m2] `version_date` 형식 미검증 — Moderate/HIGH (점수: 40)

`nda_markups.py:84`에서 `version_date: str = Form(...)`로 받지만 "YYYY-MM-DD" 포맷 검증이 없다. 임의 문자열이 DB에 저장될 수 있다. `Date` 타입 사용 또는 `datetime.date.fromisoformat(v)` 검증 추가 권고.

---

#### [m3] `UPLOAD_DIR` 상대경로 — CWD 의존 — Moderate/HIGH (점수: 40)

`nda_markups.py:22`의 `UPLOAD_DIR = Path("uploads/nda_markups")`가 상대경로. CWD 변경 시 경로 검증이 우회될 수 있다. 기존 `contract_markups.py`도 동일.

---

#### [m4] 업로드 성공 여부 무관하게 폼 초기화 — Moderate/HIGH (점수: 40)

`NdaVersionPanel.tsx:132-148`에서 `onUpload(fd)` 호출 직후 mutation 결과를 기다리지 않고 폼을 초기화한다. 업로드 실패 시 사용자 입력이 소실된다. `onSuccess` 콜백 패턴으로 수정 필요.

---

#### [m5] useQuery 로딩/에러 상태 미처리 — Moderate/HIGH (점수: 40)

`NdaVersionPanel.tsx:59`에서 `isLoading`, `isError`를 구조 분해하지 않아 로딩 스피너와 에러 표시가 없다. 빈 상태와 로딩 상태를 구분할 수 없다.

---

#### [m6] `window.confirm` 사용 — Moderate/HIGH (점수: 40)

`NdaVersionPanel.tsx:97`, `NdasTab.tsx:227`에서 네이티브 confirm 다이얼로그 사용. 스타일링 불가, a11y 지원 불완전. 기존 `Modal` 컴포넌트로 교체 권고.

---

#### [m7] 아이콘 전용 버튼에 `aria-label` 누락 — Moderate/HIGH (점수: 40)

`NdaVersionPanel.tsx:265-292`의 다운로드/Redline/삭제 버튼에 텍스트 레이블 없이 아이콘만 렌더링. `title`은 있으나 `aria-label` 누락.

---

#### [m8] `base_version_id` FK 인덱스 누락 — Moderate/MEDIUM (점수: 24)

마이그레이션/모델 모두에 `base_version_id` 인덱스가 없다. 버전 계보 추적 쿼리 시 Full Scan 발생 가능. `nda_id`, `version_date`에는 인덱스 존재.

---

### P3 — 저우선 (점수: <30)

#### [L1] `(nda_id, version_number)` 복합 유니크 제약 없음 — Minor/MEDIUM (점수: 12)

`FOR UPDATE` 잠금으로 레이스 컨디션을 방지하지만, DB 수준 유니크 제약이 없어 직접 INSERT 시 중복 가능. 기존 `ContractMarkup`도 동일.

---

#### [L2] `key_changes` 스키마 타입 불일치 — Minor/MEDIUM (점수: 12)

스키마(`nda_markup.py:25`)는 `list[str]`이나 모델 주석은 "구조화된 변경 목록"(`list[dict]` 예상). 현재 미사용이므로 런타임 영향 없으나 향후 불일치 발생 가능.

---

#### [L3] `markup_type` 자유 문자열 허용 — Minor/HIGH (점수: 20)

모델 주석에 "draft"/"1st"/"2nd"/"final"이 있으나 Enum 검증 없이 임의 문자열 저장 가능.

---

#### [L4] `run_in_threadpool` 중복 지연 import — Minor/HIGH (점수: 20)

`nda_markups.py:263, 281`에서 `from starlette.concurrency import run_in_threadpool`이 if/else 양쪽에서 중복. 파일 상단으로 이동.

---

#### [L5] 삭제 시 파일 삭제 오류가 DB 삭제를 차단 — Minor/HIGH (점수: 20)

`nda_markups.py:207-208`에서 `unlink()` 예외 시 DB 레코드도 삭제되지 않는다. try/except로 감싸고 경고 로그 후 DB 삭제 진행 권고.

---

#### [L6] `<label>`과 `<input>`의 `htmlFor` 미연결 — Minor/HIGH (점수: 20)

`NdaVersionPanel.tsx:189-195`에서 파일 입력 라벨이 연결되지 않아 라벨 클릭 시 파일 선택이 열리지 않는다.

---

#### [L7] UTC 기준 날짜 초기값 (KST 오차) — Minor/LOW (점수: 6)

`NdaVersionPanel.tsx:125-127`에서 `new Date().toISOString().slice(0, 10)`은 UTC 기준. KST 21:00~24:00에 전날 날짜가 기본값으로 표시된다.

---

## Priority Matrix

### P0 — 즉시 수정 (1건)
1. [C1] Critical/HIGH: 동기 파일 I/O가 이벤트 루프 차단 — `nda_markups.py:253,266,284,303` (점수: 110)

### P1 — 스프린트 우선 (6건)
1. [M1] Major/HIGH: 단건 조회/삭제 IDOR (txn↔nda 미검증) — `nda_markups.py:62,157,194` (점수: 85)
2. [M2] Major/HIGH: Redline 파일 삭제 누락 — `nda_markups.py:204-208` (점수: 85)
3. [M3] Major/HIGH: LLM 예외 미처리 → 500 + 내부 메시지 노출 — `nda_markups.py:291` (점수: 80)
4. [M4] Major/HIGH: 비공개 함수 직접 import — `nda_analysis_service.py:20` (점수: 70)
5. [M5] Major/HIGH: 마이그레이션↔모델 JSON 타입 불일치 — `073_nda_markups.py:37` (점수: 70)
6. [M6] Major/HIGH: 내부 파일 경로 API 노출 — `nda_markup.py:21,27` (점수: 70, DESIGN_RISK)

### P2 — 개선 권장 (8건)
1. [m1] Moderate/HIGH: MIME 타입 미검증 — `nda_markups.py:102` (점수: 40)
2. [m2] Moderate/HIGH: version_date 형식 미검증 — `nda_markups.py:84` (점수: 40)
3. [m3] Moderate/HIGH: UPLOAD_DIR 상대경로 — `nda_markups.py:22` (점수: 40)
4. [m4] Moderate/HIGH: 업로드 실패 시 폼 초기화 — `NdaVersionPanel.tsx:132` (점수: 40)
5. [m5] Moderate/HIGH: useQuery 로딩/에러 미처리 — `NdaVersionPanel.tsx:59` (점수: 40)
6. [m6] Moderate/HIGH: window.confirm 사용 — `NdaVersionPanel.tsx:97` (점수: 40)
7. [m7] Moderate/HIGH: aria-label 누락 — `NdaVersionPanel.tsx:265` (점수: 40)
8. [m8] Moderate/MEDIUM: base_version_id 인덱스 누락 — `073_nda_markups.py` (점수: 24)

### P3 — 저우선 (7건)
1. [L1] Minor/MEDIUM: 복합 유니크 제약 누락 (점수: 12)
2. [L2] Minor/MEDIUM: key_changes 타입 불일치 (점수: 12)
3. [L3] Minor/HIGH: markup_type Enum 미적용 (점수: 20)
4. [L4] Minor/HIGH: run_in_threadpool 중복 import (점수: 20)
5. [L5] Minor/HIGH: 파일 삭제 실패 시 DB 삭제 차단 (점수: 20)
6. [L6] Minor/HIGH: label htmlFor 미연결 (점수: 20)
7. [L7] Minor/LOW: UTC 기준 날짜 초기값 (점수: 6)

---

## 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | nda_markup.py 모델 생성 | ✅ | `models/nda_markup.py` — 전체 필드 구현 |
| 2 | `__init__.py` 등록 | ✅ | `models/__init__.py:118, 231` — import + `__all__` |
| 3 | Alembic 마이그레이션 | ⚠️ | `073_nda_markups.py` — key_changes 타입 불일치 [M5] |
| 4 | Pydantic 스키마 | ⚠️ | `schemas/nda_markup.py` — key_changes 타입 [L2], file_path 노출 [M6] |
| 5 | CRUD 라우터 | ⚠️ | `routers/nda_markups.py` — IDOR [M1], 동기 I/O [C1] |
| 6 | main.py 라우터 등록 | ✅ | `main.py:205` — prefix="/api/v1" |
| 7 | NDA Redline 프롬프트 | ✅ | `services/nda_redline_prompts.py` — NDA 10대 조항 커버 |
| 8 | NDA 분석 서비스 | ⚠️ | `services/nda_analysis_service.py` — _call_llm_json 직접 import [M4] |
| 9 | generate-redline 엔드포인트 | ⚠️ | `routers/nda_markups.py:224` — 예외 미처리 [M3], 동기 I/O [C1] |
| 10 | FE 타입 정의 | ✅ | `types/nda_markup.ts` — BE 스키마와 1:1 매칭 확인 |
| 11 | React Query 훅 | ✅ | `hooks/useNdaMarkups.ts` — 4개 훅 구현 |
| 12 | NdaVersionPanel 컴포넌트 | ⚠️ | `components/NdaVersionPanel.tsx` — UX 이슈 [m4-m7] |
| 13 | NdasTab 확장 | ✅ | `tabs/NdasTab.tsx` — 버전 컬럼 + 패널 연결 |

---

## Methodology

- **Agents**: backend-security-reviewer, python-code-reviewer, migration-validator, performance-profiler, general-purpose (FE)
- **Files scanned**: 12 (BE 8 + FE 4)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 1건 + Major 7건 → 7건 CONFIRMED, 1건 FALSE_POSITIVE
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 31건
- 거부된 가설 (사전 제거): 3건
- 보고된 이슈: 22건
- 거부율: 10%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 기존 패턴과 동일 (FALSE_POSITIVE) | 1 | T1: 다운로드 URL `/api/v1` — `main.py:205` prefix 확인, 기존 contract_markups와 동일 |
| 범위 외 | 1 | NDA 원문 LLM 전송 — 설계 결정 사항 (DESIGN_RISK로 기록) |
| 이미 정상 동작 확인 | 1 | JSONB import — `with_variant` 래핑으로 CI 통과, 기존 ContractMarkup 동일 패턴 |

### 정상 동작 확인 항목

- SQL Injection: 모든 쿼리 ORM 사용 (f-string SQL 없음)
- CORS: `settings.ALLOWED_ORIGINS` 환경변수 기반 (와일드카드 없음)
- JWT: `verify_exp=True`, HS256, 프로덕션 JWT_SECRET 필수
- Path Traversal: `resolve().relative_to()` 검증 존재
- 버전 번호 레이스 컨디션: `FOR UPDATE` DB 레벨 락 적용
- 파일명 인젝션: `Path(safe_filename).name`으로 디렉토리 구성요소 제거
- 인증: 모든 엔드포인트에 `get_jwt_claims` 또는 `require_write_access()` 적용
- 감사 추적: CREATE/DELETE/UPDATE 모두 `audit_service.record()` 호출
- FE↔BE 타입: `NdaMarkup` 인터페이스와 `NdaMarkupOut` 스키마 전 필드 1:1 매칭 확인
