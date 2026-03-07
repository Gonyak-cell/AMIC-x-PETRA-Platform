# Redline Step 4 — 추가 통합 리뷰 (13개 관점 미수행 부분)

> **Review Date**: 2026-03-07 16:48
> **Reviewer**: Claude Code (4-Agent Parallel Review)
> **Scope**: deal-mgmt Step 4 교차 검증 + Tracked Changes .docx 생성 API
> **Method**: 4개 전문 에이전트 병렬 디스패치 (보안 R1-R3, 코드품질 R4-R6, 성능 R7-R9, 테스트/통합 R10-R13)
> **Context**: 이전 리뷰(20260307_1259)에서 16건 수정 완료 후, 미수행 관점에 대한 후속 리뷰

---

## 이전 수정 항목 재검증 (6건 전부 확인)

| # | 수정 항목 | 상태 | 검증 위치 |
|---|----------|------|----------|
| 1 | XXE 방어 (`_SAFE_PARSER`) | ✅ 확인 | `redline_engine.py:26, 73, 148, 184, 764, 790` |
| 2 | ZIP Bomb 방어 (`_read_zip_entry`) | ✅ 확인 | `redline_engine.py:123-133` |
| 3 | ZIP Slip 방어 | ✅ 확인 | `redline_engine.py:733-735` |
| 4 | MIME 타입 이중 검증 | ✅ 확인 | `spa_analysis.py:288-297` |
| 5 | ValueError 메시지 마스킹 | ✅ 확인 | `spa_analysis.py:118-121, 131-134, 190-193, 332-337` |
| 6 | XML 파싱 에러 처리 | ✅ 확인 | `redline_engine.py:149-150, 185-186` |

---

## Summary

| Severity | Count | Priority Distribution |
|----------|-------|-----------------------|
| Critical | 1 | P0: 1 |
| Major | 5 | P1: 5 |
| Moderate | 7 | P2: 7 |
| Minor/Suggestion | 14 | P3: 14 |
| **Total** | **27** | P0: 1 / P1: 5 / P2: 7 / P3: 14 |

**Cross-Agent Deduplication**: 원본 33건 → 6건 중복 병합 → 27건 최종

---

## P0 — 즉시 수정 (1건)

### [FU-01] `except (zipfile.BadZipFile, Exception)` 예외 처리 구조 오류
- **관점**: R1 (보안) + R10 (테스트)
- **파일**: `spa_analysis.py:338`
- **심각도**: Critical / HIGH
- **교차 검증**: 보안 에이전트 SEC-001 + 테스트 에이전트 C-02 동일 발견

```python
except (zipfile.BadZipFile, Exception) as exc:
    if isinstance(exc, zipfile.BadZipFile):
        ...
        raise HTTPException(...) from exc
    raise  # ← 모든 Exception이 그대로 전파
```

`except (BadZipFile, Exception)`은 사실상 `except Exception`과 동일. `BadZipFile`이 아닌 경우 `raise`로 예외를 그대로 재발생시켜 내부 스택 트레이스가 노출될 수 있다.

**수정**: `except zipfile.BadZipFile`과 `except Exception`을 별도 절로 분리.

---

## P1 — 스프린트 우선 (5건)

### [FU-02] 서비스 레이어 파일 크기 상한 없음 — DoS 위험
- **관점**: R4 (에러 핸들링)
- **파일**: `spa_analysis_service.py:2111`
- **심각도**: Major / HIGH

`file_bytes` 전체 크기를 체크하지 않아 극단적으로 큰 파일이 메모리에 로드될 수 있다. `_read_zip_entry`의 50MB 상한은 ZIP 내부 엔트리 단위이며, `io.BytesIO(docx_bytes)` 호출 자체는 제한 없음.

**수정**: 함수 진입부에 `if len(file_bytes) > 20 * 1024 * 1024: raise ValueError(...)` 추가.

### [FU-03] 세션 소유권 검증 우회 가능성
- **관점**: R1 (보안)
- **파일**: `spa_analysis_service.py:121, 1886`
- **심각도**: Major / HIGH (SEC-004)

`owner_user_id`가 빈 문자열이면 소유권 검증이 건너뛰어짐. 멀티워커 폴백 경로(라인 1886)에서 `owner_user_id=""`로 세션이 생성되어 누구든 세션 ID만 알면 접근 가능.

**수정**: 폴백 경로에서도 `owner_user_id=owner_user_id`를 반드시 설정.

### [FU-04] `_split_run_at` 텍스트 동일성 비교로 인한 잘못된 run 분할
- **관점**: R6 (비즈니스 로직)
- **파일**: `redline_engine.py:393-399`
- **심각도**: Major / MEDIUM

`deepcopy(run)` 후 복사본 내 `<w:t>` 텍스트가 `original_text`와 다르거나 동일 텍스트 `<w:t>`가 여러 개인 경우, 잘못된 노드가 분할될 수 있음.

**수정**: 인덱스 기반 접근 — `text_elem`이 원본 run에서 몇 번째 `<w:t>`인지 계산 후 복사본의 동일 인덱스에 접근.

### [FU-05] `except Exception` 범위 과도 — 프로그래밍 오류 은폐
- **관점**: R4 (에러 핸들링)
- **파일**: `spa_analysis_service.py:2160`
- **심각도**: Major / HIGH

Pydantic 검증 실패는 `ValidationError`인데, `except Exception`으로 모든 예외를 삼킴.

**수정**: `except (ValidationError, ValueError) as exc:`로 한정.

### [FU-06] `_repack_docx`에서 `rels`/`content_types` 읽기 시 크기 제한 없음
- **관점**: R1 (보안)
- **파일**: `redline_engine.py:741-747`
- **심각도**: Major / MEDIUM (SEC-006)

`word/document.xml`은 `_read_zip_entry()`로 50MB 제한 적용하지만, `word/_rels/document.xml.rels`와 `[Content_Types].xml`은 `zf_in.read()` 직접 호출.

**수정**: 두 경로에도 `_read_zip_entry()` 적용.

---

## P2 — 개선 권장 (7건)

### [FU-07] `list(parent).index(run)` O(n) 선형 탐색 4곳
- **관점**: R8 (CPU 최적화) + R5 (코드 구조)
- **파일**: `redline_engine.py:402, 488, 540, 587`
- **심각도**: Moderate / HIGH (P-02 + MOD-01)

lxml `addnext()`/`addprevious()` API로 O(1) 대체 가능. 10개 issue × 100개 run 문단 = 4,000회 비교 연산 제거.

**수정**: `parent.insert(idx, el)` → `run.addnext(el)` 등으로 교체.

### [FU-08] `BytesIO(docx_bytes)` 중복 생성 — 메모리 2배 낭비
- **관점**: R7 (메모리)
- **파일**: `redline_engine.py:173, 724`
- **심각도**: Moderate / HIGH (P-01)

`apply_redlines`에서 1회, `_repack_docx`에서 1회 = 20MB 파일 기준 40MB 추가 메모리.

**수정**: `io.BytesIO` 객체를 한 번만 생성하고 `_repack_docx`에 전달하여 재사용.

### [FU-09] ZIP Bomb 방어 불완전 — `file_size` 필드 신뢰 문제
- **관점**: R1 (보안) + R4 (에러 핸들링)
- **파일**: `redline_engine.py:128-129`
- **심각도**: Moderate / MEDIUM (SEC-003 + MOD-02)

Data Descriptor 방식 ZIP에서 `file_size=0`으로 기록된 경우 체크가 우회됨.

**수정**: 스트리밍 방식으로 읽으면서 누적 크기 측정하는 방어적 읽기 추가.

### [FU-10] `issue_id` 패턴 — 프롬프트 지시와 스키마 불일치
- **관점**: R6 (비즈니스 로직) + R13 (일관성)
- **파일**: `spa_analysis.py:464`
- **심각도**: Moderate / HIGH (MOD-03 + S-05)

프롬프트는 `ISS-001` 형식만 지시하지만 스키마는 `ISSUE-001`도 허용. 3자리 제한으로 100개 이상 이슈 시 검증 실패.

**수정**: `pattern=r"^ISS-\d{3,}$"` — 형식 통일 + 자릿수 확장.

### [FU-11] `_scan_max_revision_id` 5회 전체 트리 순회
- **관점**: R8 (CPU 최적화)
- **파일**: `redline_engine.py:637-648`
- **심각도**: Moderate / HIGH (P-04)

5개 태그를 각각 `root.iter(tag)`로 순회 → 5회 전체 트리 순회.

**수정**: `set` 기반 단일 패스 `root.iter()` + `tag in revision_tags_set`.

### [FU-12] `CharMapping` dataclass에 `__slots__` 미적용
- **관점**: R7 (메모리)
- **파일**: `redline_engine.py:45-50`
- **심각도**: Moderate / HIGH (P-06)

100페이지 문서에서 ~250,000개 객체 생성. `__slots__` 추가 시 메모리 약 50% 절감 (25-37MB).

### [FU-13] `_build_char_map` + `_normalize_with_index_map` 이중 재생성
- **관점**: R8 (CPU 최적화)
- **파일**: `redline_engine.py:346-371`
- **심각도**: Moderate / HIGH (P-03)

N개 issue × 모든 문단에 대해 `_build_char_map` 반복 호출. 정규화 매칭용 결과를 묶어서 반환하면 중복 제거 가능.

---

## P3 — 저우선 / 제안 (14건)

### [FU-14] `Content-Disposition` 파일명 길이 제한 없음
- **관점**: R1 (보안) — SEC-005
- **파일**: `spa_analysis.py:357-365`
- **심각도**: Minor / HIGH
- **수정**: `safe_name = safe_name[:100]` 추가

### [FU-15] `spa_text` 세션 메모리 평문 보관
- **관점**: R3 (정보 노출) — SEC-009
- **파일**: `spa_analysis_service.py:101-103`
- **심각도**: Minor / HIGH
- **제안**: Step 2 완료 후 `spa_text = None`으로 즉시 해제

### [FU-16] Rate Limiter 멀티워커 환경 우회
- **관점**: R2 (DoS 방어) + R9 (동시성) — SEC-002 + P-07
- **파일**: `spa_analysis.py:36-57`
- **심각도**: Minor / HIGH (단일 워커 환경에서는 무해)
- **제안**: 장기적으로 Redis 기반 또는 Nginx `limit_req_zone` 적용

### [FU-17] `_sessions`/`_llm_client` 전역 싱글턴 경쟁 조건
- **관점**: R9 (동시성) — P-08
- **파일**: `spa_analysis_service.py:110, 139-147`
- **심각도**: Minor / HIGH (단일 asyncio 루프에서는 안전)
- **제안**: `asyncio.Lock` 보호 또는 모듈 초기화 시 즉시 생성

### [FU-18] `pytest.raises(Exception)` → `pytest.raises(ValidationError)`
- **관점**: R10 (테스트 품질) — W-01
- **파일**: `test_redline_engine.py:488, 504`
- **심각도**: Minor / HIGH
- **제안**: `pydantic.ValidationError`를 직접 사용하여 정확한 예외 검증

### [FU-19] ZIP bomb 테스트에 실제 초과 케이스 없음
- **관점**: R10 (테스트 커버리지) — C-01
- **파일**: `test_redline_engine.py:802-813`
- **심각도**: Minor / MEDIUM
- **제안**: `unittest.mock`으로 `ZipInfo.file_size`를 패치하여 `ValueError` 발생 검증

### [FU-20] `_apply_segments` KEEP-only / INS-only 시나리오 미테스트
- **관점**: R10 (테스트 커버리지) — W-03
- **파일**: `test_redline_engine.py`
- **심각도**: Minor / MEDIUM

### [FU-21] `_split_run_at` 경계 조건 (offset=0, offset=len) 미테스트
- **관점**: R10 (테스트 커버리지) — W-04
- **파일**: `test_redline_engine.py`
- **심각도**: Minor / MEDIUM

### [FU-22] `apply_redlines` 다중 이슈 + 겹치는 이슈 E2E 테스트 없음
- **관점**: R10 (테스트 커버리지) — W-06
- **파일**: `test_redline_engine.py`
- **심각도**: Minor / MEDIUM
- **제안**: 동일 문단에 두 이슈가 겹칠 때 DOM 변경 후 두 번째 매칭 정확성 검증

### [FU-23] `gemini-2.5-flash` COST_PER_1K 미등록
- **관점**: R12 (의존성 호환성) — W-05
- **파일**: `llm_client.py:191`
- **심각도**: Minor / HIGH
- **제안**: `COST_PER_1K`에 `gemini-2.5-flash` 비용 등록

### [FU-24] `OTHER_INDUSTRY` 테스트 누락
- **관점**: R10 (테스트 커버리지) — MOD-04
- **파일**: `test_redline_engine.py:720-723`
- **심각도**: Minor / HIGH

### [FU-25] 지역 import 패턴 불일치
- **관점**: R5 (구조) + R8 (성능) — MIN-02 + P-09 + S-01
- **파일**: `spa_analysis_service.py:2103-2107`, `spa_analysis.py:355`
- **심각도**: Minor / HIGH
- **제안**: 순환 import 문제가 없다면 모듈 최상단으로 이동

### [FU-26] `del_runs` set 사전 생성 패턴 개선
- **관점**: R8 (CPU) — P-05
- **파일**: `redline_engine.py:277-286`
- **심각도**: Suggestion
- **제안**: `iterancestors()`로 직접 `<w:del>` 조상 확인 (트레이드오프 있음)

### [FU-27] 테스트 파일 조직 — `_extract_json` 등 비 redline 테스트 분리
- **관점**: R13 (유지보수성) — W-07
- **파일**: `test_redline_engine.py:643-675`
- **심각도**: Suggestion
- **제안**: `test_spa_analysis_service.py`로 분리 권장

---

## 조치 권장 Phase 분류

### Phase A: 즉시 수정 (P0-P1, 6건)
| ID | 작업 | 예상 수정 범위 |
|----|------|--------------|
| FU-01 | `except (BadZipFile, Exception)` 분리 | `spa_analysis.py` 3줄 |
| FU-02 | 서비스 레이어 파일 크기 상한 추가 | `spa_analysis_service.py` 3줄 |
| FU-03 | 세션 소유권 폴백 경로 수정 | `spa_analysis_service.py` 1줄 |
| FU-04 | `_split_run_at` 인덱스 기반 접근 | `redline_engine.py` 5줄 |
| FU-05 | `except Exception` → `except (ValidationError, ValueError)` | `spa_analysis_service.py` 2줄 |
| FU-06 | `rels`/`content_types` 읽기에 `_read_zip_entry` 적용 | `redline_engine.py` 2줄 |

### Phase B: 성능 개선 (P2, 7건)
| ID | 작업 | 성능 영향 |
|----|------|----------|
| FU-07 | `list(parent).index` → `addnext`/`addprevious` | O(n) → O(1), issue당 4,000회 비교 제거 |
| FU-08 | `BytesIO` 중복 생성 제거 | 20MB 파일 기준 40MB 메모리 절감 |
| FU-09 | ZIP 스트리밍 읽기 방어 | file_size 스푸핑 방어 |
| FU-10 | `issue_id` 패턴 통일 + 확장 | 100+ 이슈 대응 |
| FU-11 | `_scan_max_revision_id` 단일 패스 | 5회 → 1회 트리 순회 |
| FU-12 | `CharMapping.__slots__` | 25-37MB 메모리 절감 |
| FU-13 | `_normalize_with_index_map` 중복 제거 | 검색 시간 30-50% 단축 |

### Phase C: 테스트 보강 (P3, 5건)
| ID | 작업 |
|----|------|
| FU-19 | ZIP bomb 초과 케이스 테스트 |
| FU-20 | `_apply_segments` KEEP-only/INS-only 테스트 |
| FU-21 | `_split_run_at` 경계 조건 테스트 |
| FU-22 | 다중 이슈 겹침 E2E 테스트 |
| FU-24 | `OTHER_INDUSTRY` 테스트 |

### Phase D: 장기 개선 (P3, 9건)
FU-14 ~ FU-18, FU-23, FU-25 ~ FU-27 — 기능적 위험 없음, 점진적 개선

---

## Methodology

- **Agents**: backend-security-reviewer (R1-R3), python-code-reviewer (R4-R6), performance-profiler (R7-R9), python-code-reviewer (R10-R13)
- **Files scanned**: 7 (`redline_engine.py`, `spa_analysis.py` 라우터, `spa_analysis_service.py`, `redline_prompts.py`, `spa_analysis.py` 스키마, `llm_client.py`, `test_redline_engine.py`)
- **Cross-Agent Deduplication**: 6건 중복 병합 (SEC-001=C-02, SEC-002=P-07, SEC-003=MOD-02, MOD-01≈P-02, MIN-02=P-09=S-01, MOD-03≈S-05)
- **Previous Fix Verification**: 6건 전부 ✅ 확인
