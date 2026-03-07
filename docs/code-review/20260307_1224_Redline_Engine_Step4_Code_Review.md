# Code Review — Redline Engine (Step 4)

> **Review Date**: 2026-03-07 12:24
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: deal-mgmt Step 4 — SPA 교차 검증 + Tracked Changes 생성 파이프라인 (6개 파일)
> **Method**: Review Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: ruff(PASS) pytest(PASS, 30/30)
> **Review Gates**: Backend(available) Agent-Filtering(3개 에이전트 호출, 0개 제외)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1               | P0: 1               |
| Major    | 5     | HIGH: 3 / MEDIUM: 2   | P1: 3 / P2: 2       |
| Moderate | 7     | HIGH: 2 / MEDIUM: 3 / LOW: 2 | P2: 5 / P3: 2 |
| Minor    | 5     | MEDIUM: 3 / LOW: 2    | P3: 5               |
| **Total**| **18**| HIGH: **6** / MEDIUM: **8** / LOW: **4** | P0: **1** / P1: **3** / P2: **7** / P3: **7** |

**FP Prevention**: 가설 34건 검증, 16건 사전 거부 (거부율: 47%) | 교차 검증 11건 수행
- Phase 2 결과: CONFIRMED 6건, PARTIAL 3건 (심각도 하향), DESIGN_RISK 2건 (심각도 하향)

---

## Findings

### P0 — 즉시 수정 (점수: 100, 기능 전체 불동작)

---

#### [C-02] `_extract_json`이 `list` 반환 불가 — Step 4 LLM 응답 항상 실패 — Critical/HIGH — P0

**위치**: `spa_analysis_service.py:190~208` (함수 정의), `:2145~2152` (Step 4 호출)

**증거**:
```python
# spa_analysis_service.py:190 — dict만 반환 허용
def _extract_json(text: str) -> dict[str, Any]:
    result = json.loads(stripped)
    if not isinstance(result, dict):       # ← list일 때 ValueError 발생
        msg = f"JSON 최상위가 object가 아닙니다: {type(result).__name__}"
        raise ValueError(msg)
    return result

# spa_analysis_service.py:2145 — list를 기대하지만 절대 도달 불가
parsed = _extract_json(raw)
if isinstance(parsed, list):              # ← 항상 False (dead code)
    issues_list = parsed
```

**영향**: 시스템 프롬프트(`redline_prompts.py:36`)가 "반드시 JSON 배열로 출력하라"고 지시하므로, 정상적인 LLM 응답이 오면 `_extract_json`에서 `ValueError`가 발생하여 Step 4 전체가 항상 실패한다.

**수정 제안**: `_extract_json` 반환 타입을 `dict[str, Any] | list[Any]`로 변경하고 `isinstance(result, dict)` 가드 제거. 또는 Step 4 전용 `_extract_json_array` 함수를 별도 작성.

**교차 검증**: CONFIRMED — 코드 직접 확인. dead code 경로 확인 완료.

---

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [M-01] 정규화 매칭 인덱스가 원본 `char_map`과 불일치 — Major/HIGH — P1 (점수: 70)

**위치**: `redline_engine.py:309~315`

**증거**:
```python
# redline_engine.py:309-315
norm_merged = _normalize_text_for_matching(merged)
idx = norm_merged.find(norm_target)
if idx >= 0:
    # 정규화된 인덱스를 원본 인덱스로 매핑 (근사치)   ← 코드 주석이 "근사치"로 인정
    return para, idx, idx + len(norm_target), merged, char_map
```

**영향**: `_normalize_text_for_matching`이 연속 공백을 축소하거나 스마트 따옴표를 일반 따옴표로 변환하면 문자열 길이가 바뀐다. 정규화된 문자열의 `idx`를 원본 `char_map`(원본 `merged` 기준)에 그대로 적용하면 잘못된 Run에 DEL/INS가 주입된다.

**수정 제안**: 정규화 매칭 성공 후 원본 문자열에서 fuzzy 재탐색하는 offset 보정 로직 추가. 또는 정규화 시 원본→정규화 인덱스 매핑 테이블을 함께 생성.

**교차 검증**: CONFIRMED

---

#### [M-03] `industry_type` Form 파라미터 pattern 검증 누락 — Major/HIGH — P1 (점수: 70)

**위치**: `spa_analysis.py:265`

**증거**:
```python
# 다른 파라미터는 pattern 검증이 있음:
leverage: str = Form("STRONG", pattern=r"^(STRONG|WEAK)$"),
rwi_status: str = Form("NO_RWI", pattern=r"^(HAS_RWI|NO_RWI)$"),
# industry_type만 누락:
industry_type: str = Form("GENERAL"),   # ← 임의 문자열 허용
```

**영향**: 미검증 문자열이 `build_step4_prompt()`에서 시스템 프롬프트에 직접 삽입된다. 프롬프트 인젝션 위험은 낮지만(LLM이 최종 소비자), 예상치 못한 입력으로 프롬프트 품질 저하 가능.

**수정 제안**: `pattern=r"^(GENERAL|SOFTWARE|MANUFACTURING|FRANCHISE|BIO|OTHER)$"` 추가.

**교차 검증**: CONFIRMED

---

#### [M-04] `Content-Disposition` 헤더에 한글 파일명 — RFC 5987 미준수 — Major/MEDIUM — P1 (점수: 60 ⚠️ MEDIUM 신뢰도)

**위치**: `spa_analysis.py:334~340`

**증거**:
```python
safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
output_filename = f"{safe_name}_redline.docx"
headers={"Content-Disposition": f'attachment; filename="{output_filename}"'}
```

**영향**: 원본 업로드 파일명이 한글이면 (예: `주식매매계약서.docx`) 비ASCII 문자가 `filename=` 값에 직접 들어가 RFC 2616 위반. 브라우저에 따라 다운로드 파일명이 깨질 수 있다.

**수정 제안**:
```python
from urllib.parse import quote
headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(output_filename, safe='')}"}
```

**교차 검증**: CONFIRMED

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [C-01] ZipFile context manager 누락 — ~~Critical~~ → Major/HIGH — P2 (점수: 55, 심각도 하향)

**위치**: `redline_engine.py:125`, `:153`

**증거**:
```python
# redline_engine.py:125
zf = zipfile.ZipFile(io.BytesIO(docx_bytes))  # ← with 문 없음
try:
    xml_bytes = zf.read("word/document.xml")
except KeyError as exc:
    raise ValueError(...)  # ← zf.close() 미호출
```

**교차 검증**: CONFIRMED — 단, read-only ZipFile이며 GC가 처리하므로 Critical에서 Major로 하향. `_repack_docx`(L651)는 `with` 문을 올바르게 사용하므로 일관성 문제도 존재.

**수정 제안**: `with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:` 패턴으로 통일.

---

#### [M-02] `_apply_segments` — KEEP 세그먼트가 target_runs에서 분리되지 않음 — Major/MEDIUM — P2 (점수: 42 ⚠️ MEDIUM 신뢰도)

**위치**: `redline_engine.py:603~613`

**증거**:
```python
for seg in segments:
    if seg.action == "DEL" and target_runs:
        del_el = _inject_deletion(target_runs, ...)
        target_runs = []  # ← 전체 소진, KEEP 부분도 포함
```

**영향**: `proposed_redline`이 `"KEEP(A)[DEL]B[/DEL][INS]C[/INS]KEEP(D)"` 구조일 때, KEEP에 해당하는 A와 D도 DEL에 포함되어 삭제된다. 실제로는 시스템 프롬프트가 `original_target_text`와 `proposed_redline`의 KEEP 부분이 일치하도록 유도하므로 대부분의 경우 `[DEL]전체[/DEL][INS]수정안[/INS]` 패턴이 사용된다. 하지만 LLM이 KEEP+DEL 혼합 마크업을 생성하면 문제 발생.

**교차 검증**: CONFIRMED

---

#### [SEC-001] lxml `etree.fromstring()` — XXE 방어 심층 보호 미적용 — ~~Major~~ → Moderate/HIGH — P2 (점수: 40, 심각도 하향)

**위치**: `redline_engine.py:131`, `:163`, `:688`, `:710`, `:731`

**증거**: `etree.fromstring(xml_bytes)` 5곳에서 safe parser(`XMLParser(resolve_entities=False)`) 없이 호출.

**교차 검증**: PARTIAL — lxml >=5.0.0은 기본적으로 외부 엔티티를 해석하지 않는다. 실질적 XXE 취약점은 아니지만, 방어 심층 보호(defense-in-depth) 관점에서 명시적 파서 사용 권장. 심각도 Major → Moderate로 하향.

**수정 제안**:
```python
_SAFE_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)
root = etree.fromstring(xml_bytes, parser=_SAFE_PARSER)
```

---

#### [P-01] `extract_paragraphs_text` — 이벤트 루프 차단 — ~~Major~~ → Moderate/HIGH — P2 (점수: 40, 심각도 하향)

**위치**: `spa_analysis_service.py:2110`

**증거**:
```python
# async 함수 내에서 동기 호출 (run_in_threadpool 없음)
spa_text = redline_engine.extract_paragraphs_text(file_bytes)
```

**교차 검증**: PARTIAL — `apply_redlines`는 `run_in_threadpool`로 올바르게 격리되어 있으나, `extract_paragraphs_text`는 직접 호출. 일반적인 문서(< 5MB)에서는 < 100ms이므로 실무 영향은 낮다. 심각도 하향.

---

#### [P-02] `list(parent).index(run)` — O(n) 선형 검색 — ~~Major~~ → Moderate/MEDIUM — P2 (점수: 36, 심각도 하향)

**위치**: `redline_engine.py:326` (`_split_run_at`), 기타 3곳

**교차 검증**: DESIGN_RISK — 문단의 자식 노드 수는 보통 < 100개이므로 실제 성능 영향은 미미하다. 심각도 하향.

---

#### [MOD-02] `_apply_segments` — 다중 DEL 세그먼트 시 두 번째 DEL skip — Moderate/MEDIUM — P2 (점수: 36)

**위치**: `redline_engine.py:603~613`

**영향**: `proposed_redline`에 DEL이 두 개 이상이면 첫 번째 DEL에서 `target_runs`가 소진되어 이후 DEL은 무시. M-02와 연관된 구조적 한계.

---

#### [MOD-06] `_extract_json` 반환 타입 시그니처 불일치 — Moderate/HIGH — P2 (점수: 40)

**위치**: `spa_analysis_service.py:190`

**영향**: C-02의 타입 시그니처 측면. `dict[str, Any]` 선언 때문에 정적 분석 도구에서 `isinstance(parsed, list)` 분기가 "always False" 경고를 유발. C-02 수정 시 함께 해결됨.

---

### P3 — 저우선 (점수: <30)

---

#### [MOD-01] Run 분할 후 `char_map` stale 상태 미문서화 — Moderate/HIGH — P3 (점수: 24)

**위치**: `redline_engine.py:353~400`

**영향**: 실제 버그는 아님 (각 이슈마다 `_find_target_in_paragraphs` 재호출). 향후 리팩토링 시 주의 필요.

---

#### [MOD-03] `build_step4_prompt` — 잘못된 leverage 값 silent fallback — Moderate/MEDIUM — P3 (점수: 24)

**위치**: `redline_prompts.py:134~169`

**영향**: `leverage`가 `"STRONG"/"WEAK"` 외 값이면 `else` 분기로 `LEVERAGE_WEAK` 자동 선택. 라우터에서 `pattern=` 검증이 있으므로 실제 발생 가능성 극히 낮음.

---

#### [MOD-04] `CommentManager` dataclass `eq=False` 미명시 — Moderate/LOW — P3 (점수: 12)

**위치**: `redline_engine.py:58~81`

**영향**: `etree._Element` 필드의 `__eq__` 충돌 가능성. 현재 코드에서 `CommentManager` 인스턴스 비교를 하지 않으므로 실질 영향 없음.

---

#### [MOD-05] `_scan_max_revision_id` — 표 관련 revision 태그 누락 — Moderate/LOW — P3 (점수: 12)

**위치**: `redline_engine.py:580`

**영향**: `tblPrChange`, `trPrChange` 등 표 revision 태그 미포함. 실무에서 표 tracked change가 매우 높은 ID를 갖는 경우에만 ID 충돌 발생. 드문 엣지 케이스.

---

#### [P-03] Triple memory holding — ~~Major~~ → Minor/MEDIUM — P3 (점수: 18, 심각도 하향)

**위치**: `redline_engine.py:125`, `:153`

**교차 검증**: DESIGN_RISK — `docx_bytes` 원본 + `BytesIO` 복사 + `xml_bytes`로 최대 3배 메모리. 하지만 최대 파일 크기 20MB 제한이므로 worst case 60MB. 실무 영향 낮음.

---

#### [MIN-01] `RedlineIssueSchema.issue_id` pattern — 프롬프트와 불일치 — Minor/LOW — P3 (점수: 6)

**위치**: `spa_analysis.py:464`

**영향**: `r"^ISS(UE)?-\d{3}$"`는 `ISSUE-001`과 `ISS-001` 모두 허용하지만 프롬프트는 `ISS-001`만 지시. 기능에 영향 없음.

---

#### [MIN-02] 인메모리 rate limiter — 멀티 워커 무효화 — Minor/MEDIUM — P3 (점수: 12)

**위치**: `spa_analysis.py:35~56`

**영향**: 단일 프로세스에서만 공유되는 모듈 레벨 딕셔너리. 멀티 워커 시 실제 rate limit = `_RATE_LIMIT_MAX × worker_count`. 기존 Step 1~3도 동일 구조이므로 Step 4 고유 이슈 아님.

---

#### [MIN-03] `apply_redlines` — `issues: list[dict]` 타입 힌트 과소 명세 — Minor/LOW — P3 (점수: 6)

**위치**: `redline_engine.py:148`

**영향**: `list[dict[str, Any]]` 또는 `TypedDict` 사용 권장. 코드 동작에는 영향 없음.

---

#### [MIN-04] 테스트 커버리지 갭 — Minor/MEDIUM — P3 (점수: 12)

**위치**: `test_redline_engine.py` 전체

**영향**: `_collect_and_split_target_runs`, `_apply_segments`, `_repack_docx`, `_ensure_comments_*` 직접 단위 테스트 부재. E2E 테스트로 간접 커버되지만 경계 케이스 미검증.

---

## Priority Matrix

### P0 — 즉시 수정 (1건)
1. **[C-02]** [Critical/HIGH]: `_extract_json` dict-only → Step 4 항상 실패 (점수: 100)

### P1 — 스프린트 우선 (3건)
1. **[M-01]** [Major/HIGH]: 정규화 매칭 인덱스 불일치 → 잘못된 위치에 redline 삽입 (점수: 70)
2. **[M-03]** [Major/HIGH]: `industry_type` pattern 검증 누락 (점수: 70)
3. **[M-04]** [Major/MEDIUM ⚠️]: 한글 파일명 Content-Disposition 깨짐 (점수: 60)

### P2 — 개선 권장 (7건)
1. **[C-01→M]** [Major/HIGH]: ZipFile context manager 누락 (점수: 55)
2. **[M-02]** [Major/MEDIUM ⚠️]: KEEP 세그먼트 target_runs 미분리 (점수: 42)
3. **[SEC-001→MOD]** [Moderate/HIGH]: lxml XXE 방어 심층 보호 (점수: 40)
4. **[P-01→MOD]** [Moderate/HIGH]: extract_paragraphs_text 이벤트 루프 차단 (점수: 40)
5. **[MOD-06]** [Moderate/HIGH]: _extract_json 타입 시그니처 불일치 (점수: 40)
6. **[P-02→MOD]** [Moderate/MEDIUM ⚠️]: O(n) list.index() (점수: 36)
7. **[MOD-02]** [Moderate/MEDIUM]: 다중 DEL 세그먼트 skip (점수: 36)

### P3 — 저우선 (7건)
1. **[MOD-01]** char_map stale 미문서화 (점수: 24)
2. **[MOD-03]** leverage silent fallback (점수: 24)
3. **[P-03→MIN]** Triple memory holding (점수: 18)
4. **[MIN-02]** 인메모리 rate limiter 멀티워커 (점수: 12)
5. **[MIN-04]** 테스트 커버리지 갭 (점수: 12)
6. **[MOD-04]** CommentManager eq (점수: 12)
7. **[MOD-05]** scan_max_revision_id 표 태그 누락 (점수: 12)
8. **[MIN-01]** issue_id pattern 불일치 (점수: 6)
9. **[MIN-03]** list[dict] 타입 과소 명세 (점수: 6)

---

## Methodology

- **Agents**: python-code-reviewer, backend-security-reviewer, performance-profiler
- **Excluded Agents**: 0개 (범위-에이전트 필터링 후 3개 전부 호출)
- **Files scanned**: 6개 (redline_engine.py, redline_prompts.py, spa_analysis.py schemas, spa_analysis_service.py, spa_analysis.py router, test_redline_engine.py)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 11건 수행
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 34건 (Security 10 + Performance 8 + Python 16)
- 거부된 가설 (사전 제거): 16건
- 보고된 이슈: 18건
- 거부율: 47%

### Phase 2 교차 검증 결과

| Issue | Phase 1 판정 | Phase 2 판정 | 변경 |
|-------|-------------|-------------|------|
| C-02 | Critical/HIGH | CONFIRMED | 유지 |
| C-01 | Critical/HIGH | CONFIRMED | Major로 하향 (read-only ZipFile, GC 처리) |
| M-01 | Major/HIGH | CONFIRMED | 유지 |
| M-02 | Major/MEDIUM | CONFIRMED | 유지 |
| M-03 | Major/HIGH | CONFIRMED | 유지 |
| M-04 | Major/MEDIUM | CONFIRMED | 유지 |
| SEC-001 | Major/HIGH | PARTIAL | Moderate로 하향 (lxml >=5.0 기본 안전) |
| SEC-002 | Major/HIGH | DUPLICATE | M-04와 중복, 제거 |
| P-01 | Major/HIGH | PARTIAL | Moderate로 하향 (일반 문서 < 100ms) |
| P-02 | Major/HIGH | DESIGN_RISK | Moderate로 하향 (n < 100 실무) |
| P-03 | Major/HIGH | DESIGN_RISK | Minor로 하향 (20MB 제한) |

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 중복 | 3 | SEC-002 = M-04, MOD-06 = C-02 타입 측면 |
| 범위 외 | 4 | 기존 Step 1~3에도 동일한 패턴 (rate limiter 등) |
| 반증됨 | 5 | lxml >=5.0 기본 XXE 방어, GC 파일 핸들 해제 |
| 과대 심각도 | 4 | 실무 데이터 규모에서 영향 미미 |

---

## Passed Checks (주요 합격 항목)

- [x] `run_in_threadpool`으로 CPU 바운드 OOXML 처리 이벤트 루프 격리
- [x] 파일 업로드 확장자(`.docx`) 및 크기(20MB) 검증
- [x] 인증/인가: `require_write_access()` + `_get_and_authorize_txn()` 적용
- [x] Rate limiting: 기존 Step 1~3 패턴과 일관
- [x] Pydantic v2 검증: `field_validator` + `model_validator` 올바른 사용
- [x] ruff check/format 0건 통과
- [x] pytest 30/30 전체 통과
- [x] 하드코딩 시크릿/토큰 없음
- [x] SQL injection 위험 없음 (Step 4는 DB 미사용)
- [x] snake_case / PascalCase 일관 적용
