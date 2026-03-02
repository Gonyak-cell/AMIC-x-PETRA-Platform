# Code Review — BTA 확장 + SHA 갭 수정 + DOCX 서식 표준화

> **Review Date**: 2026-03-02 21:39
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 이번 세션 변경 9개 파일 (BE 스키마/서비스/라우터/테스트 + FE 타입/컴포넌트 2개 + DOCX 서식 2개)
> **Method**: Quality Gates + 3-Agent Verified Review (python-code-reviewer + general-purpose + backend-security-reviewer)
> **Quality Gates**: ruff(PASS) pytest 104/104(PASS) tsc(PASS)

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|-----------|----------|
| Critical | 1 | HIGH: 1 | P0: 1 |
| Major | 4 | HIGH: 4 | P1: 4 |
| Moderate | 6 | HIGH: 5 / MEDIUM: 1 | P1: 2 / P2: 4 |
| Minor | 6 | HIGH: 4 / MEDIUM: 1 / LOW: 1 | P3: 6 |
| **Total** | **17** | HIGH: **14** / MEDIUM: **2** / LOW: **1** | P0: **1** / P1: **6** / P2: **4** / P3: **6** |

---

## P0 — 즉시 수정 (1건)

### [CRIT-1] `analyze_step1_variables` 반환 타입 어노테이션 10-tuple → 실제 반환 12-tuple 불일치 — [Critical/HIGH]
**파일**: `spa_analysis_service.py:729~740`
**설명**: 함수 시그니처의 `-> tuple[...]`이 10개 요소만 선언하지만 실제로는 `bta_scope`, `severance_pay_handling` 포함 12개를 반환. mypy/pyright에서 오탐 발생, docstring의 Returns 설명도 누락.

---

## P1 — 스프린트 우선 (6건)

### [R01] PAGE fldChar에 `separate` 노드 누락 — [Major/HIGH]
**파일**: `contract_styles.py:390-392`
**설명**: OOXML 규격상 `begin → instrText → separate → end` 순서 필수. `separate`가 없으면 LibreOffice/Google Docs/한글에서 페이지 번호 미렌더링 가능.

### [R10] `add_signature_table` — `w:tcW` 중복 추가 가능성 — [Major/HIGH]
**파일**: `contract_styles.py:348-353`
**설명**: 기존 `w:tcW` 요소 존재 확인 없이 `tcp.append(val_el)` 호출 → 중복 XML 요소 생성 가능.

### [MAJOR-2] 멀티워커 폴백 세션 생성 시 `_MAX_SESSIONS` 한도 미체크 — [Major/HIGH]
**파일**: `spa_analysis_service.py:1229-1239`
**설명**: Step 2 폴백 경로에서 세션 생성 시 한도 검사 없이 `_sessions` 딕셔너리에 삽입.

### [INJ-002] `ExtractedVariable.variable_key` 패턴 검증 미적용 — [High Security/HIGH]
**파일**: `schemas/spa_analysis.py:96`
**설명**: `DiscoveredBoolean.variable_key`는 `pattern=r"^has_[a-z_]+$"` 제한이 있으나 `ExtractedVariable.variable_key`는 `min_length=1, max_length=100`만. Jinja2 구문 삽입 가능.

### [INJ-003] `visible_condition` 필드 보안 검증 누락 — [High Security/HIGH]
**파일**: `schemas/spa_analysis.py:105`
**설명**: `condition_expression`은 `validate_condition_expression()` 검증을 거치지만, 동일 문법의 `visible_condition`은 검증 없이 DB 저장.

### [R09] CONFIG 값을 참조하지 않는 하드코딩 (설정-코드 불일치) — [Moderate/HIGH]
**파일**: `contract_styles.py:125,128`
**설명**: `WD_LINE_SPACING.AT_LEAST`, `WD_ALIGN_PARAGRAPH.JUSTIFY`가 CONFIG 딕셔너리 대신 하드코딩. CONFIG 변경해도 동작 불변.

---

## P2 — 개선 권장 (4건)

### [MOD-1] `except Exception` 광범위 캐치 — [Moderate/HIGH]
**파일**: `spa_analysis_service.py:776-780`
**설명**: `_call_llm_json`이 발생시키는 `RuntimeError`/`ValueError`만 명시적으로 캐치 권장.

### [MOD-3] 인메모리 Rate Limiter 다중 워커 무력화 — [Moderate/HIGH]
**파일**: `routers/spa_analysis.py:34-55`
**설명**: 프로세스 전역 변수 기반. 2워커 = 분당 6회 허용. 주석에 제한 명시 필요.

### [R03] `_add_preamble_body` 래퍼의 `indent_cm` 파라미터 무시 — [Moderate/MEDIUM]
**파일**: `create_legal_templates.py:86-87`
**설명**: 호출자가 `indent_cm=1.30` 넘겨도 내부에서 항상 1.4cm 적용. 기만적 API.

### [VAL-001] `DiscoveredBoolean.question_label` / `detected_in_clause` max_length 미지정 — [Moderate Security/HIGH]
**파일**: `schemas/spa_analysis.py:122-126`
**설명**: `ExtractedVariable.question_label`은 300자 제한이지만 `DiscoveredBoolean`은 무제한.

---

## P3 — 저우선 (6건)

| ID | 심각도 | 파일 | 설명 |
|----|--------|------|------|
| R02 | Minor/HIGH | `spa_analysis.ts:150` | `deal_structure` 주석에 `BtaScope` 누락 |
| R04 | Minor/HIGH | `SpaAnalysisWizard.tsx:414,435` | `as ShaType`/`as BtaScope` 캐스팅 (분기 조건으로 안전) |
| R05 | Minor/HIGH | `AnalysisReviewPanel.tsx:31-53` | import가 `sanitizeHtml` 함수 다음에 위치 |
| R07 | Minor/MEDIUM | `contract_styles.py:139` | `run: object` 타입 + type: ignore |
| R08 | Minor/HIGH | `contract_styles.py:17` | `dict` 브로드 타입 (TypedDict 추천) |
| R11 | Minor/LOW | `create_legal_templates.py:64-126` | 13개 단순 래퍼 함수 |

---

## 보안 리뷰 추가 사항 (Info 등급)

| ID | 심각도 | 설명 |
|----|--------|------|
| PI-001 | Info | LLM 프롬프트 인젝션 (spa_text 직접 삽입) — 구조적 한계, XML 래핑 권장 |
| INFO-001 | Info | 에러 메시지에 내부 비용 정보 노출 가능 |
| XSS-001 | Info | sanitize_html blocklist 방식 — `nh3` allowlist 전환 권장 (기존 코드) |

---

## 양호 사항

- [x] 인증/인가: 3개 엔드포인트 모두 `require_write_access()` 적용
- [x] BE-FE 스키마: BTA 필드(bta_scope, severance_pay_handling) 양측 완전 일치
- [x] BtaClassificationPanel A11Y: `id` + `htmlFor` 올바르게 연결
- [x] LLM 잘못된 값 폴백: 4개 validator 모두 안전한 기본값 반환
- [x] condition_expression 인젝션 방어: `_FORBIDDEN_RE` + AST 파싱 이중 검증
- [x] DOCX 서식: 여백/폰트/줄간격 모두 샘플 분석 결과와 일치
- [x] 테스트: 104개 전부 통과, BTA 전용 13개 커버
- [x] SandboxedEnvironment: Jinja2 템플릿 실행 시 코드 인젝션 방지
- [x] DOCX 파일 경로: SSRF/XXE 위험 없음 (외부 참조 없음)

---

## Methodology

- Agents: python-code-reviewer, general-purpose (FE+DOCX), backend-security-reviewer
- Files scanned: 9
- Protocol: 3-agent parallel review + quality gates
- Quality Gates: ruff PASS, pytest 104/104 PASS, tsc PASS
