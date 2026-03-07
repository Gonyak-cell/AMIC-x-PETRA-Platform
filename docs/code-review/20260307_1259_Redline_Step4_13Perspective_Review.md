# Redline Step 4 — 13-Perspective Integrated Review

> **Review Date**: 2026-03-07 12:59
> **Reviewer**: Claude Code (13-Perspective Integrated Review)
> **Scope**: deal-mgmt Redline Engine Step 4 구현 전체 (미수정 이슈 + 신규 발견)
> **Method**: R2 Security + R3 Data Integrity + R4 Production Resilience + R5 Operations + R6 Business/UX
> **Base Review**: 20260307 Full Code Review (18건) — 3건 수정 완료 (C-02, M-01, M-03)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 1 / MEDIUM: 1   | P0: 1 / P1: 1       |
| Major    | 7     | HIGH: 5 / MEDIUM: 2   | P1: 5 / P2: 2       |
| Moderate | 8     | HIGH: 5 / MEDIUM: 3   | P1: 1 / P2: 6 / P3: 1 |
| Minor    | 5     | HIGH: 2 / MEDIUM: 2 / LOW: 1 | P2: 2 / P3: 3 |
| Warning  | 3     | HIGH: 2 / MEDIUM: 1   | P2: 2 / P3: 1       |
| Suggestion | 4   | MEDIUM: 3 / LOW: 1    | P3: 4               |
| **Total**| **29**| HIGH: **15** / MEDIUM: **12** / LOW: **2** | P0: **1** / P1: **7** / P2: **12** / P3: **9** |

**FP Prevention**: 3개 에이전트 교차 검증, 중복 이슈 5건 병합

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)

| ID | Severity/Confidence | 제목 | 파일 | 점수 |
|----|---------------------|------|------|------|
| SEC-001 | Critical/HIGH | XXE 공격 벡터 — `etree.fromstring()` safe parser 미사용 | redline_engine.py:70,131,163,720,746 | 100 |

### P1 — 스프린트 우선 (점수: 60-89)

| ID | Severity/Confidence | 제목 | 파일 | 점수 |
|----|---------------------|------|------|------|
| SEC-NEW-01 | Critical/MEDIUM | ZIP Bomb DoS — 파일 크기 사전 검증 미비 | redline_engine.py:125,153 | 60 |
| C-01 | Major/HIGH | ZipFile context manager 미사용 — 리소스 누수 | redline_engine.py:125,153 | 70 |
| N-R4-01 | Major/HIGH | `XMLSyntaxError` 미포착 — 손상된 XML 500 에러 | redline_engine.py:131,163 | 70 |
| M-02 | Major/HIGH | `_apply_segments` KEEP/DEL 상태 변이 버그 | redline_engine.py:623-668 | 70 |
| R6-S-02 | Major/HIGH | `_collect_and_split_target_runs` 하이퍼링크 내부 Run 누락 | redline_engine.py:417-432 | 70 |
| M-04 | Major/MEDIUM | Content-Disposition 한글 파일명 깨짐 | spa_analysis.py(router):334-340 | 42 |
| MOD-02 | Major/MEDIUM | `_apply_segments` 연속 DEL+INS 순서 미보장 | redline_engine.py:623-668 | 42 |

### P2 — 개선 권장 (점수: 30-59)

| ID | Severity/Confidence | 제목 | 파일 | 점수 |
|----|---------------------|------|------|------|
| SEC-NEW-02 | Moderate/HIGH | ValueError 메시지 클라이언트 노출 | spa_analysis.py(router):319-324 | 40 |
| SEC-NEW-04 | Moderate/HIGH | ZIP Slip 경로 순회 방어 미비 | redline_engine.py:_repack_docx | 40 |
| N-R4-02 | Moderate/HIGH | 라우터 예외 처리 범위 부족 (`BadZipFile` 등) | spa_analysis.py(router):315-330 | 40 |
| P-01 | Moderate/HIGH | `extract_paragraphs_text` CPU 바운드 미분리 | spa_analysis_service.py:2110 | 40 |
| R6-W-03 | Moderate/HIGH | 심각도 기준 충돌 — 에스크로 High vs DOMESTIC_KR 예외 | redline_prompts.py:22-24 vs 112 | 40 |
| R3-NEW-01 | Moderate/MEDIUM | `comments.xml` 파싱 에러 시 전체 실패 | redline_engine.py:CommentManager | 24 |
| SEC-NEW-05 | Moderate/MEDIUM | MIME 타입 이중 검증 미비 (확장자만 체크) | spa_analysis.py(router):280-290 | 24 |
| N-R4-03 | Moderate/MEDIUM | request_id 로깅 미연동 | spa_analysis.py(router) | 24 |
| P-02 | Minor/HIGH | `_build_char_map` 반환 리스트 대규모 문서 메모리 | redline_engine.py:_build_char_map | 20 |
| R6-W-01 | Warning/HIGH | FRANCHISE 프롬프트 가맹사업법 조항 누락 | redline_prompts.py:100-104 | 20 |
| R6-S-01 | Warning/HIGH | WEAK 레버리지 대응 전략 모호 | redline_prompts.py | 20 |

### P3 — 저우선 (점수: <30)

| ID | Severity/Confidence | 제목 | 파일 | 점수 |
|----|---------------------|------|------|------|
| SEC-NEW-03 | Minor/MEDIUM | Rate limiter 멀티 워커 비공유 | spa_analysis.py(router) | 12 |
| P-03 | Minor/MEDIUM | 대규모 문서 청킹 미구현 (Phase 1 제외) | spa_analysis_service.py | 12 |
| R3-NEW-02 | Minor/LOW | LLM 에러 메시지 .docx 파일에 노출 가능성 | redline_engine.py | 6 |
| N-R5-01 | Suggestion/MEDIUM | God Module — redline_engine.py 730줄 | redline_engine.py | — |
| N-R5-02 | Suggestion/MEDIUM | `_apply_segments` 상태 변이 리팩토링 권장 | redline_engine.py:623-668 | — |
| N-R5-03 | Suggestion/MEDIUM | lxml Alpine/musl 빌드 호환성 사전 확인 | pyproject.toml | — |
| N-R5-04 | Suggestion/LOW | `_resolve_run_properties` first-run bias | redline_engine.py | — |
| R6-W-02 | Warning/MEDIUM | 에스크로 대안 판단 기준 구체화 필요 | redline_prompts.py | 12 |
| MOD-01 | Minor/HIGH | Comment anchor 범위 단일 Run 한정 | redline_engine.py | 20 |

---

## Findings Detail

### SEC-001: XXE 공격 벡터 — `etree.fromstring()` safe parser 미사용

- **Severity**: Critical | **Confidence**: HIGH | **Priority**: P0 (100)
- **Perspectives**: R2 Security, R6 Business
- **Location**: [redline_engine.py:70,131,163,720,746](deal-mgmt/app/services/redline_engine.py)

`lxml.etree.fromstring()` 호출 5건 모두 외부 업로드 .docx 파일의 XML을 파싱하면서 safe parser를 사용하지 않음.
악의적 DOCX 내 `<!DOCTYPE>` 선언으로 서버 파일 읽기(SSRF) 또는 Billion Laughs DoS 가능.

**수정 방안**: `XMLParser(resolve_entities=False, no_network=True)` 생성 후 `etree.fromstring(xml_bytes, parser=safe_parser)` 사용.

---

### SEC-NEW-01: ZIP Bomb DoS — 파일 크기 사전 검증 미비

- **Severity**: Critical | **Confidence**: MEDIUM | **Priority**: P1 (60)
- **Perspectives**: R2 Security
- **Location**: [redline_engine.py:125,153](deal-mgmt/app/services/redline_engine.py)

20MB 파일 크기 제한은 라우터에서 체크하나, ZIP 내부 `word/document.xml`의 압축 해제 크기는 미검증.
ZIP Bomb으로 수백 MB XML 추출 시 메모리/CPU 고갈 가능.

**수정 방안**: `ZipInfo.file_size` 사전 체크 (예: 50MB 상한) + `zf.read()` 전 검증.

---

### C-01: ZipFile context manager 미사용 — 리소스 누수

- **Severity**: Major | **Confidence**: HIGH | **Priority**: P1 (70)
- **Perspectives**: R4 Resilience, R5 Operations
- **Location**: [redline_engine.py:125,153](deal-mgmt/app/services/redline_engine.py)

`zipfile.ZipFile(BytesIO(docx_bytes))` 호출 시 `with` 문 미사용. XML 파싱 중 예외 발생 시 ZipFile 핸들 미해제.

**수정 방안**: `with zipfile.ZipFile(...) as zf:` 패턴 적용.

---

### N-R4-01: `XMLSyntaxError` 미포착 — 손상된 XML 500 에러

- **Severity**: Major | **Confidence**: HIGH | **Priority**: P1 (70)
- **Perspectives**: R4 Resilience
- **Location**: [redline_engine.py:131,163](deal-mgmt/app/services/redline_engine.py)

`etree.fromstring()` 호출 시 손상된 XML이 `XMLSyntaxError`를 발생시키면 미포착 → FastAPI 500.
라우터에서 `ValueError`만 catch하므로 `XMLSyntaxError`는 통과.

**수정 방안**: `try/except lxml.etree.XMLSyntaxError` → `ValueError("손상된 DOCX 파일입니다")` 변환.

---

### M-02: `_apply_segments` KEEP/DEL 상태 변이 버그

- **Severity**: Major | **Confidence**: HIGH | **Priority**: P1 (70)
- **Perspectives**: R3 Data Integrity, R5 Operations
- **Location**: [redline_engine.py:623-668](deal-mgmt/app/services/redline_engine.py)

`_apply_segments`에서 KEEP 세그먼트 처리 시 `run_idx` 전진 로직이 DEL 세그먼트의 Run 제거와 상호작용하여, 특정 KEEP+DEL+INS 조합에서 잘못된 Run을 대상으로 조작할 수 있음.

**재현 시나리오**: "ABC DEF GHI" 텍스트에서 "DEF"만 DEL 시, KEEP("ABC ") 후 `run_idx` 위치가 DEL 대상 Run과 불일치할 수 있음 (Run 파편화 상태에 따라).

**수정 방안**: char_map 기반 절대 인덱싱으로 변경하거나, 상태 변이 대신 새 리스트 구성 방식 적용.

---

### R6-S-02: `_collect_and_split_target_runs` 하이퍼링크 내부 Run 누락

- **Severity**: Major | **Confidence**: HIGH | **Priority**: P1 (70)
- **Perspectives**: R6 Business/UX
- **Location**: [redline_engine.py:417-432](deal-mgmt/app/services/redline_engine.py)

`_build_char_map()`은 `paragraph.iter(f'{W}r')`로 하이퍼링크 내부 `<w:r>`도 포함하여 매핑하지만, `_collect_and_split_target_runs()`는 직접 자식만 순회하여 하이퍼링크 내부 Run을 수집하지 못함.

**영향**: 하이퍼링크 텍스트에 대한 Tracked Changes 적용 실패 → 해당 이슈 자동 skip.

**수정 방안**: `_collect_and_split_target_runs`에서도 `paragraph.iter()` 또는 하이퍼링크 컨테이너 순회 적용.

---

### MOD-02: `_apply_segments` 연속 DEL+INS 순서 미보장

- **Severity**: Major | **Confidence**: MEDIUM | **Priority**: P2 (42)
- **Perspectives**: R3 Data Integrity
- **Location**: [redline_engine.py:623-668](deal-mgmt/app/services/redline_engine.py)

M-02와 관련. 연속된 `[DEL]...[/DEL][INS]...[/INS]` 패턴에서 DEL 후 INS 삽입 위치가 의도와 다를 수 있음 (DEL이 Run을 제거하면 INS의 `reference_run`이 변경됨).

---

### M-04: Content-Disposition 한글 파일명 깨짐

- **Severity**: Major | **Confidence**: MEDIUM | **Priority**: P2 (42)
- **Perspectives**: R6 Business/UX
- **Location**: [spa_analysis.py(router):334-340](deal-mgmt/app/routers/spa_analysis.py)

Content-Disposition 헤더에 한글 파일명을 RFC 5987 인코딩 없이 직접 삽입. 일부 브라우저에서 파일명이 깨지거나 다운로드 실패.

**수정 방안**: `filename*=UTF-8''` + `urllib.parse.quote()` 적용 + ASCII fallback `filename=` 병기.

---

### SEC-NEW-02: ValueError 메시지 클라이언트 노출

- **Severity**: Moderate | **Confidence**: HIGH | **Priority**: P2 (40)
- **Perspectives**: R2 Security
- **Location**: [spa_analysis.py(router):319-324](deal-mgmt/app/routers/spa_analysis.py)

`except ValueError as e: raise HTTPException(422, detail=str(e))` — 내부 ValueError 메시지(파일 경로, XML 파싱 상세 등)가 클라이언트에 그대로 노출될 수 있음.

**수정 방안**: 사용자 친화적 고정 메시지 사용 + 원본 에러는 로그만.

---

### SEC-NEW-04: ZIP Slip 경로 순회 방어 미비

- **Severity**: Moderate | **Confidence**: HIGH | **Priority**: P2 (40)
- **Perspectives**: R2 Security
- **Location**: [redline_engine.py:_repack_docx](deal-mgmt/app/services/redline_engine.py)

`_repack_docx`에서 원본 ZIP 엔트리를 복사할 때 `entry.filename`에 `../` 등 경로 순회가 포함된 경우 미검증. 메모리 내 BytesIO로 재패키징하므로 파일시스템 직접 영향은 제한적이나, defense-in-depth 관점에서 검증 필요.

---

### N-R4-02: 라우터 예외 처리 범위 부족

- **Severity**: Moderate | **Confidence**: HIGH | **Priority**: P2 (40)
- **Perspectives**: R4 Resilience
- **Location**: [spa_analysis.py(router):315-330](deal-mgmt/app/routers/spa_analysis.py)

`RuntimeError`와 `ValueError`만 catch. `zipfile.BadZipFile`, `lxml.etree.XMLSyntaxError`, `KeyError`("word/document.xml" 부재) 등 미포착 → 500 에러.

**수정 방안**: 서비스 레이어에서 이들을 `ValueError`로 통일 변환하거나, 라우터에서 추가 except 절.

---

### P-01: `extract_paragraphs_text` CPU 바운드 미분리

- **Severity**: Moderate | **Confidence**: HIGH | **Priority**: P2 (40)
- **Perspectives**: R4 Resilience
- **Location**: [spa_analysis_service.py:2110](deal-mgmt/app/services/spa_analysis_service.py)

`apply_redlines`는 `run_in_threadpool`로 감싸져 있으나, `extract_paragraphs_text`는 이벤트 루프에서 직접 실행. 대용량 DOCX(수백 페이지) 시 이벤트 루프 차단.

**수정 방안**: `await run_in_threadpool(extract_paragraphs_text, file_bytes)`.

---

### R6-W-03: 심각도 기준 충돌 — 에스크로 판정

- **Severity**: Moderate | **Confidence**: HIGH | **Priority**: P2 (40)
- **Perspectives**: R6 Business/UX
- **Location**: [redline_prompts.py:22-24 vs 112](deal-mgmt/app/services/redline_prompts.py)

글로벌 심각도 기준에서 에스크로 부재를 High로 정의하나, DOMESTIC_KR 섹션에서는 "에스크로 없어도 곧바로 HIGH 판정 금지"라고 상충. LLM이 혼란하여 일관성 없는 판정 가능.

**수정 방안**: 글로벌 기준에 `(DOMESTIC_KR 예외 참조)` 단서 추가 또는 조건부 기준 통합.

---

### R3-NEW-01: `comments.xml` 파싱 에러 시 전체 실패

- **Severity**: Moderate | **Confidence**: MEDIUM | **Priority**: P2 (24)
- **Perspectives**: R3 Data Integrity
- **Location**: [redline_engine.py:CommentManager](deal-mgmt/app/services/redline_engine.py)

기존 DOCX에 손상된 `word/comments.xml`이 있을 경우 `CommentManager.from_docx_zip()`에서 XML 파싱 에러 → 전체 redline 실패.

**수정 방안**: 파싱 실패 시 빈 `<w:comments>` 폴백 + 경고 로그.

---

### SEC-NEW-05: MIME 타입 이중 검증 미비

- **Severity**: Moderate | **Confidence**: MEDIUM | **Priority**: P2 (24)
- **Perspectives**: R2 Security
- **Location**: [spa_analysis.py(router):280-290](deal-mgmt/app/routers/spa_analysis.py)

파일 확장자(`.docx`)만 검증, `content_type` 또는 magic bytes 미검증. 악의적 파일이 `.docx` 확장자로 업로드 가능.

**수정 방안**: `file.content_type` 검증 또는 ZIP magic bytes (`PK\x03\x04`) 확인 추가.

---

### N-R4-03: request_id 로깅 미연동

- **Severity**: Moderate | **Confidence**: MEDIUM | **Priority**: P2 (24)
- **Perspectives**: R5 Operations
- **Location**: [spa_analysis.py(router)](deal-mgmt/app/routers/spa_analysis.py)

Step 4 엔드포인트의 로그에 request_id가 미포함. 프로덕션 에러 추적 시 요청-응답 매핑 어려움.

---

### P-02: `_build_char_map` 대규모 문서 메모리

- **Severity**: Minor | **Confidence**: HIGH | **Priority**: P2 (20)
- **Perspectives**: R4 Resilience
- **Location**: [redline_engine.py:_build_char_map](deal-mgmt/app/services/redline_engine.py)

글자마다 `CharMapping` 객체를 생성하므로, 수백 페이지 문서에서 수십만 개 객체 → 수백 MB 메모리. Phase 1 범위에서는 허용되나 장기적 최적화 필요.

---

### MOD-01: Comment anchor 범위 단일 Run 한정

- **Severity**: Minor | **Confidence**: HIGH | **Priority**: P3 (20)
- **Perspectives**: R6 Business/UX
- **Location**: [redline_engine.py](deal-mgmt/app/services/redline_engine.py)

`_anchor_comment_to_run`이 단일 Run에만 앵커를 설정. 여러 Run에 걸친 변경의 경우 Comment 범위가 실제 변경 범위와 불일치.

---

### R6-W-01: FRANCHISE 프롬프트 가맹사업법 조항 누락

- **Severity**: Warning | **Confidence**: HIGH | **Priority**: P2 (20)
- **Perspectives**: R6 Business/UX
- **Location**: [redline_prompts.py:100-104](deal-mgmt/app/services/redline_prompts.py)

FRANCHISE 산업 프롬프트에 한국 가맹사업거래의 공정화에 관한 법률 주요 조항(정보공개서, 가맹금 예치, 영업지역 보호) 미반영.

---

### R6-S-01: WEAK 레버리지 대응 전략 모호

- **Severity**: Warning | **Confidence**: HIGH | **Priority**: P2 (20)
- **Perspectives**: R6 Business/UX
- **Location**: [redline_prompts.py](deal-mgmt/app/services/redline_prompts.py)

WEAK 레버리지 시 구체적 대응 전략("대안 조항 제시" vs "위험 고지만") 미명시. LLM이 STRONG과 유사한 공격적 수정안을 생성할 위험.

---

### SEC-NEW-03: Rate limiter 멀티 워커 비공유

- **Severity**: Minor | **Confidence**: MEDIUM | **Priority**: P3 (12)
- **Perspectives**: R2 Security
- **Location**: [spa_analysis.py(router)](deal-mgmt/app/routers/spa_analysis.py)

인메모리 rate limiter가 Gunicorn 멀티 워커 환경에서 프로세스 간 비공유. 현재 단일 워커 운영이므로 즉시 위험은 낮음.

---

### R6-W-02: 에스크로 대안 판단 기준 구체화 필요

- **Severity**: Warning | **Confidence**: MEDIUM | **Priority**: P3 (12)
- **Perspectives**: R6 Business/UX
- **Location**: [redline_prompts.py](deal-mgmt/app/services/redline_prompts.py)

DOMESTIC_KR에서 "대체 담보(연대보증/질권) 확인" 지시는 있으나, 대체 담보의 "충분성" 판단 기준(금액 비율, 보증인 신용 등) 미제시.

---

### P-03: 대규모 문서 청킹 미구현

- **Severity**: Minor | **Confidence**: MEDIUM | **Priority**: P3 (12)
- **Perspectives**: R4 Resilience
- **Location**: [spa_analysis_service.py](deal-mgmt/app/services/spa_analysis_service.py)

계획서에 "Phase 1에서 제외"로 명시. 수백 페이지 SPA + 긴 실사 보고서 시 LLM 컨텍스트 초과 가능. Phase 2에서 Map-Reduce 청킹 구현 예정.

---

### R3-NEW-02: LLM 에러 메시지 .docx 파일에 노출 가능성

- **Severity**: Minor | **Confidence**: LOW | **Priority**: P3 (6)
- **Perspectives**: R3 Data Integrity
- **Location**: [redline_engine.py](deal-mgmt/app/services/redline_engine.py)

LLM 호출 실패 시 에러 메시지가 매칭 실패 Comment에 포함될 가능성. 현재 코드 경로상 발생 확률 낮음 (서비스 레이어에서 사전 처리).

---

### N-R5-01: God Module — redline_engine.py 730줄

- **Severity**: Suggestion | **Confidence**: MEDIUM | **Priority**: P3
- **Perspectives**: R5 Operations

핵심 알고리즘, 코멘트 관리, ZIP 재패키징이 단일 파일에 집중. 현재 Phase 1 규모에서는 허용되나, 기능 확장 시 모듈 분리 권장.

---

### N-R5-02: `_apply_segments` 상태 변이 리팩토링 권장

- **Severity**: Suggestion | **Confidence**: MEDIUM | **Priority**: P3
- **Perspectives**: R5 Operations

M-02/MOD-02와 관련. in-place DOM 변이 대신 immutable 구성 방식으로 리팩토링하면 버그 표면 감소.

---

### N-R5-03: lxml Alpine/musl 빌드 호환성

- **Severity**: Suggestion | **Confidence**: MEDIUM | **Priority**: P3
- **Perspectives**: R5 Operations

Alpine Linux Docker 이미지 사용 시 `lxml` C 확장 빌드에 `libxml2-dev`, `libxslt-dev` 필요. 현재 Ubuntu 기반이므로 즉시 문제 없음.

---

### N-R5-04: `_resolve_run_properties` first-run bias

- **Severity**: Suggestion | **Confidence**: LOW | **Priority**: P3
- **Perspectives**: R5 Operations

인접 Run 탐색 시 "이전" Run만 탐색하거나 "다음" Run만 탐색하는 편향 가능. 대부분의 Word 문서에서 실질적 영향 미미.

---

## 이슈 간 관계 맵

```
SEC-001 (XXE) ──┬── N-R4-01 (XMLSyntaxError) : 같은 etree.fromstring() 위치
                └── C-01 (ZipFile) : 같은 파일 I/O 블록

M-02 (KEEP/DEL 상태 변이) ──┬── MOD-02 (DEL+INS 순서) : 같은 _apply_segments 함수
                             └── N-R5-02 (리팩토링 권장) : 근본 해결

R6-S-02 (하이퍼링크 Run 누락) ── _build_char_map과 _collect_and_split_target_runs 비대칭

R6-W-03 (심각도 충돌) ── R6-W-02 (에스크로 대안 기준) : 같은 에스크로 판정 맥락
```

---

## 수정 권장 순서

### Phase A: 보안 + 안정성 (P0~P1) — 즉시

1. **SEC-001**: safe parser 적용 (5개 위치)
2. **C-01 + SEC-NEW-01**: ZipFile context manager + ZIP bomb 크기 검증
3. **N-R4-01 + N-R4-02**: XMLSyntaxError/BadZipFile 예외 처리 통합
4. **M-02 + MOD-02**: `_apply_segments` 상태 관리 수정
5. **R6-S-02**: `_collect_and_split_target_runs` 하이퍼링크 순회 수정

### Phase B: 품질 개선 (P2) — 스프린트 내

6. **SEC-NEW-02**: ValueError 메시지 마스킹
7. **M-04**: Content-Disposition RFC 5987 인코딩
8. **P-01**: `extract_paragraphs_text` 스레드풀 래핑
9. **R6-W-03**: 심각도 기준 충돌 해소
10. **SEC-NEW-04 + SEC-NEW-05**: ZIP Slip + MIME 검증

### Phase C: 프롬프트 보완 (P2~P3) — 다음 이터레이션

11. **R6-W-01**: FRANCHISE 가맹사업법 조항 보강
12. **R6-S-01**: WEAK 레버리지 전략 구체화
13. **R6-W-02**: 에스크로 대안 충분성 기준

### Phase D: 장기 개선 (P3/Suggestion)

14. **N-R5-01**: 모듈 분리 (확장 시)
15. **P-02 + P-03**: 메모리 최적화 + 청킹 (Phase 2)

---

## 교차 검증 결과

| 원본 이슈 | 13-관점 재검증 결과 | 비고 |
|-----------|-------------------|------|
| C-01 (Major/HIGH) | CONFIRMED | R4+R5 에이전트 독립 확인 |
| C-02 (Critical/HIGH) | RESOLVED | 이전 세션에서 수정 완료 |
| M-01 (Major/HIGH) | RESOLVED | 이전 세션에서 수정 완료 |
| M-02 (Major/HIGH) | CONFIRMED + 확장 | MOD-02와 연관성 발견 |
| M-03 (Moderate/HIGH) | RESOLVED | 이전 세션에서 수정 완료 |
| M-04 (Major/MEDIUM) | CONFIRMED | R6 에이전트 확인 |
| MOD-01 (Minor/HIGH) | CONFIRMED | 기능적 영향 낮음 |
| MOD-02 (Major/MEDIUM) | CONFIRMED | M-02와 동시 수정 권장 |
| MIN-01 | RESOLVED | 코드 확인 결과 이미 처리됨 |
| P-01 (Moderate/HIGH) | CONFIRMED | R4 에이전트 확인 |
| P-02 (Minor/HIGH) | CONFIRMED | Phase 1 허용 범위 |
| P-03 (Minor/MEDIUM) | CONFIRMED | Phase 2 계획 확인 |
| SEC-001 (Critical/HIGH) | CONFIRMED | 3개 에이전트 모두 최우선 지적 |

---

## Methodology

- **Agents**: R2+R3 (Security + Data Integrity), R4+R5 (Resilience + Operations), R6 (Business/UX)
- **Files scanned**: 8 (redline_engine.py, spa_analysis_service.py, spa_analysis.py(router), spa_analysis.py(schema), redline_prompts.py, llm_client.py, pyproject.toml, test_redline_engine.py)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 3개 에이전트 독립 실행 → 중복 5건 병합
- **Issue deduplication**: SEC-001 (3개 에이전트), M-02/MOD-02 (2개 에이전트), C-01 (2개 에이전트)

---

## 검증 투명성

### 검증 통계
- 원본 미수정 이슈: 15건
- 신규 발견 이슈: 18건 (R2-R6)
- 중복 병합: 5건
- 최종 보고: 29건
- RESOLVED (이전 수정): 4건 (C-02, M-01, M-03, MIN-01)

### 에이전트별 기여

| 에이전트 | 기존 확인 | 신규 발견 | 중복 제거 후 |
|---------|----------|---------|------------|
| R2+R3 (Security + Data Integrity) | 2건 | 7건 | 9건 |
| R4+R5 (Resilience + Operations) | 7건 | 6건 | 13건 |
| R6 (Business/UX) | 6건 | 5건 | 11건 |
