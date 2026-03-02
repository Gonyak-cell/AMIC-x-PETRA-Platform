# Code Review — SHA(주주간계약서) LLM 역분석 확장

> **Review Date**: 2026-03-02 13:31 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: SHA 확장 전체 — BE 4파일 + FE 4파일 (8파일)
> **Method**: Quality Gates + Verified Multi-Agent Review (5 agents) + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(WARN — 기존 2건, SHA 무관) ruff(PASS) pytest(85/85 PASS) build(PASS)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2               | P0: 2               |
| Major    | 6     | HIGH: 6               | P1: 6               |
| Moderate | 11    | HIGH: 8 / MEDIUM: 2 / LOW: 1 | P1: 1 / P2: 8 / P3: 2 |
| Minor    | 7     | HIGH: 3 / MEDIUM: 4   | P2: 1 / P3: 6       |
| **Total**| **26**| HIGH: **19** / MEDIUM: **6** / LOW: **1** | P0: **2** / P1: **7** / P2: **9** / P3: **8** |

**Agents**: python-code-reviewer, general-purpose (FE), backend-security-reviewer, performance-profiler, migration-validator

**SHA-specific vs Pre-existing**: SHA 확장이 도입한 이슈 8건 / 기존 코드에서 발견된 이슈 18건

---

## Priority Matrix

### P0 — 즉시 수정 (점수 90+)

**[SEC-C1] .env 파일에 실제 API 키 4종 평문 저장 — [Critical/HIGH] (점수: 100)**
- 파일: `deal-mgmt/.env`
- Anthropic, OpenAI, Google, Clova 실제 API 키가 평문 저장
- `.gitignore`에 등록되어 커밋되지 않으나, 키 폐기(revoke) + 비밀관리 서비스 전환 필요
- **분류: 기존 코드** (SHA 확장과 무관)

**[BE-C1] `asyncio.TimeoutError`가 아닌 내장 `TimeoutError` catch — [Critical/HIGH] (점수: 100)**
- 파일: `spa_analysis_service.py:132`
- Python 3.10에서 `asyncio.wait_for` 타임아웃 → `asyncio.TimeoutError` (내장 `TimeoutError`와 다른 타입)
- `except TimeoutError:` → 타임아웃 미포착 → 호출자에게 raw asyncio.TimeoutError 전파
- **분류: 기존 코드** (SHA 확장 전부터 존재)
- 권장: `except asyncio.TimeoutError:`로 변경

---

### P1 — 스프린트 우선 (점수 60-89)

**[FE-R2] docType SHA↔SPA 전환 시 dealStructure 리셋 누락 — [Major/HIGH] (점수: 70) ★SHA 신규**
- 파일: `SpaAnalysisWizard.tsx:334-337`
- Step 1 완료 후 docType 드롭다운 변경 시 `setDocType`만 호출, `setDealStructure` 미호출
- SHA→SPA 전환: dealStructure가 "POST_BUYOUT" 등 SHA 값 유지 → `DEAL_STRUCTURE_LABELS[...] = undefined`
- SPA→SHA 전환: dealStructure가 "PURE_SHARE_TRANSFER" → `SHA_TYPE_LABELS[...] = undefined`
- **교차 검증: CONFIRMED** (FE agent + 직접 코드 확인)
- 권장: docType 변경 핸들러에서 SHA_TYPES/DEAL_STRUCTURES 포함 여부 검사 후 기본값 리셋

**[FE-R1] dealStructure 타입이 `string`으로 느슨 — [Major/HIGH] (점수: 70) ★SHA 신규**
- 파일: `spa_analysis.ts:118,144`, `SpaAnalysisWizard.tsx:354`
- `dealStructure as ShaType` 캐스팅이 타입 가드 없이 사용됨
- FE-R2와 연동 — docType 전환 시 잘못된 값이 캐스팅되면 undefined 렌더링
- **교차 검증: CONFIRMED**
- 권장: `AllStructureType` 타입 사용 또는 런타임 가드 추가

**[SEC-H1] spa_text를 통한 프롬프트 인젝션 방어 미흡 — [Major/HIGH] (점수: 80, 교차 검증 +10)**
- 파일: `spa_analysis_service.py:562-568`
- 구분자(`--- 계약서 원문 끝 ---`)를 spa_text에 삽입하여 프롬프트 구조 교란 가능
- **교차 검증: 2 agents (BE reviewer + Security reviewer) 독립 발견**
- **분류: 기존 코드** (SHA는 동일 패턴 사용)
- 권장: UUID 기반 동적 구분자 + 인젝션 패턴 탐지 로깅

**[SEC-H2] session_id 소유권 미검증 — 타 사용자 세션 접근 — [Major/HIGH] (점수: 70)**
- 파일: `spa_analysis_service.py:70-77`
- AnalysisSession에 `owner_email` 필드 없음 → session_id 추측/탈취 시 타인 계약서 원문 접근
- **분류: 기존 코드** (SHA 확장에서 악화되지 않음)
- 권장: AnalysisSession에 owner_email 추가 + _get_session에서 소유권 검증

**[BE-M2] 인메모리 _sessions / _analysis_rate 멀티프로세스 비안전 — [Major/HIGH] (점수: 80, 교차 검증 +10)**
- 파일: `spa_analysis_service.py:67`, `routers/spa_analysis.py:34`
- 멀티워커 환경에서 세션 미공유 → Step 1→Step 2 워커 불일치 시 세션 미존재
- Rate Limit이 워커별 독립 → 실제 제한의 N배 허용
- **교차 검증: 4 agents (BE, Security, Performance, Migration) 모두 발견**
- **분류: 기존 코드** (SHA 확장에서 악화되지 않음)
- 권장: Redis 기반 세션/Rate Limiter 전환

**[PERF-P01] 세션에 계약서 원문(최대 500KB) 저장 + Step 2 재전송 — [Major/HIGH] (점수: 70)**
- 파일: `spa_analysis_service.py:555, 884-888`
- 100 세션 × 500KB = 최악 50MB + Step 2에서 원문 재전송 → 토큰 비용 2배
- **분류: 기존 코드**
- 권장: 세션에서 원문 제거 또는 Redis 세션 전환

**[SEC-H3] condition_expression 필터에 subprocess/os 미차단 — [Major/MEDIUM ⚠️] (점수: 42)**
- 파일: `spa_analysis_service.py:52, 166-181`
- ⚠️ MEDIUM 신뢰도로 P2로 하향되어야 하나, Jinja2 SandboxedEnvironment 미사용 시 Major
- `_FORBIDDEN_RE`에 subprocess, os, sys, getattr 등 누락
- **분류: 기존 코드**
- 실제 위험: `_parse_expression`은 ast.parse만 수행 (eval 없음), Jinja2 렌더링 경로 확인 필요

---

### P2 — 개선 권장 (점수 30-59)

**[FE-R8] handleCreateTemplate에 try/catch 누락 — [Moderate/HIGH] (점수: 40) ★SHA 신규**
- 파일: `SpaAnalysisWizard.tsx:202-230`
- step3Mut.mutateAsync 실패 시 unhandled promise rejection (onError 토스트는 표시됨)
- 권장: Step 1/Step 2 핸들러와 동일하게 try/catch 래핑

**[FE-R3] result.sha_type 응답 필드 미사용 — [Moderate/HIGH] (점수: 40) ★SHA 신규**
- 파일: `SpaAnalysisWizard.tsx:129-158`
- `result.sha_type`이 무시됨, `result.deal_structure`로 SHA 유형을 간접 참조
- 현재 동일 값이므로 동작은 정상이나, 향후 분리 시 동기화 깨짐
- 권장: 명시적으로 sha_type을 별도 상태에 저장 또는 주석 문서화

**[FE-R5] VariableReviewPanel 분류 드롭다운이 SPA 전용 DEAL_STRUCTURES만 표시 — [Moderate/HIGH] (점수: 40) ★SHA 신규**
- 파일: `AnalysisReviewPanel.tsx:137-141`
- SHA에서 `hideClassification` prop으로 숨김 처리 중 — 현재 동작 문제 없음
- 방어적으로 ALL_STRUCTURE_TYPES 폴백 또는 JSDoc 제약 명시 권장

**[BE-Mod1] TimeoutError 발생 시 세션 미정리 — [Moderate/HIGH] (점수: 40)**
- 파일: `spa_analysis_service.py:546-572`
- LLM 호출 전 세션 저장 → 실패 시 세션 잔류 (TTL 30분 후 자동 정리)
- 권장: try/finally로 예외 시 세션 정리

**[BE-Mod2] ExtractedVariable.variable_key 포맷 패턴 미검증 — [Moderate/MEDIUM ⚠️] (점수: 24)**
- 파일: `schemas/spa_analysis.py:82-83`
- LLM이 공백/특수문자 포함 키 반환 시 Jinja2 렌더링 오류 가능
- **교차 검증: 2 agents (BE + Security)**
- 권장: `pattern=r"^[a-z][a-z0-9_]*$"` 추가

**[BE-Mod3] TimeoutError 재시도 미지원 — [Moderate/HIGH] (점수: 40)**
- 파일: `spa_analysis_service.py:121-138`
- JSON 파싱 실패만 재시도, 타임아웃은 즉시 raise
- 분류: 기존 코드

**[SEC-M3] Step 1 비용 한도 체크 누락 — [Moderate/HIGH] (점수: 40)**
- 파일: `spa_analysis_service.py:548-552`
- Step 2에만 `_MAX_COST_PER_SESSION` 체크, Step 1에서는 세션 수 상한만 체크
- 분류: 기존 코드

**[PERF-P03] _cleanup_expired_sessions O(n) 매 요청 호출 — [Moderate/HIGH] (점수: 40)**
- 파일: `spa_analysis_service.py:70-85`
- 현재 MAX_SESSIONS=100으로 무시 가능하나, 비동기 주기 태스크 분리 권장
- 분류: 기존 코드

**[PERF-P07] Step 3 DB에 불필요한 db.refresh() 호출 — [Moderate/HIGH] (점수: 40)**
- 파일: `spa_analysis_service.py:1023`
- flush 후 template.id는 이미 사용 가능, refresh는 추가 SELECT 유발
- 분류: 기존 코드

---

### P3 — 저우선 (점수 <30)

**[FE-R7] SHA 모드 Step 3 요약 그리드 6셀 vs 5열 불일치 — [Minor/MEDIUM ⚠️] (점수: 12) ★SHA 신규**
- 파일: `SpaAnalysisWizard.tsx:523`
- SHA: 6개 셀(+산업) → `sm:grid-cols-5`에서 마지막 셀이 다음 행으로 밀림
- 권장: SHA일 때 `sm:grid-cols-6` 분기

**[FE-R4] import 문이 함수 정의 이후에 위치 — [Minor/HIGH] (점수: 20)**
- 파일: `AnalysisReviewPanel.tsx:31-47`
- `sanitizeHtml` 함수(14-30행) 이후에 import → ESLint `import/first` 위반 가능
- 분류: 기존 코드 구조

**[FE-R6] docType select에 id 속성 누락 — [Minor/HIGH] (점수: 20) ★SHA 신규**
- 파일: `SpaAnalysisWizard.tsx:332-345`
- implicit labeling (감싸기)으로 기본 접근성 충족, 명시적 id/htmlFor 권장

**[BE-Mod4] Step 3 응답 메시지 "SPA 분석 템플릿" 하드코딩 — [Moderate/LOW ⚠️] (점수: 12)**
- 파일: `routers/spa_analysis.py:219`
- SHA 저장 시에도 "SPA 분석 템플릿" 표시
- 권장: `f"{body.doc_type} 분석 템플릿"` 동적 변경

**[BE-Min2] analyze_step1_variables 반환 튜플 10개 과도 — [Minor/MEDIUM] (점수: 12)**
- 파일: `spa_analysis_service.py:524-539`
- 순서 오류 위험, dataclass/NamedTuple로 구조화 권장
- 분류: 기존 코드 (SHA가 2개 필드 추가)

**[BE-Min1] test_max_sessions 테스트가 실제 서비스 미호출 — [Minor/HIGH] (점수: 20)**
- 파일: `tests/test_spa_analysis.py:1132-1165`
- 조건문 재현 방식 → 서비스 로직 변경 시 미감지
- 분류: 기존 코드

**[PERF-P08] _extract_json 중첩 JSON 블록 처리 미흡 — [Minor/MEDIUM] (점수: 12)**
- 파일: `spa_analysis_service.py:141-160`
- regex 기반 추출로 개선 권장
- 분류: 기존 코드

**[MIG-I4] 멀티워커 환경에서 SHA 폴백 시 detected_doc_type 미복원 — [Minor/HIGH] (점수: 20) ★SHA 신규**
- 파일: `spa_analysis_service.py:858-863`
- 폴백 세션의 `detected_doc_type` 기본값 "SPA" → SHA Step 2에서 SPA 프롬프트 사용
- 권장: `SpaStep2Request`에 `doc_type_hint` 필드 추가하여 폴백 복원

---

## SHA 확장 전용 이슈 요약 (8건)

| # | ID | 심각도 | 우선순위 | 설명 |
|---|-----|--------|---------|------|
| 1 | FE-R2 | Major | P1 | docType 전환 시 dealStructure 리셋 누락 |
| 2 | FE-R1 | Major | P1 | dealStructure `string` 타입 느슨 |
| 3 | FE-R8 | Moderate | P2 | handleCreateTemplate try/catch 누락 |
| 4 | FE-R3 | Moderate | P2 | result.sha_type 미사용 |
| 5 | FE-R5 | Moderate | P2 | VariableReviewPanel SPA 전용 드롭다운 |
| 6 | FE-R7 | Minor | P3 | SHA 그리드 6셀 vs 5열 |
| 7 | FE-R6 | Minor | P3 | docType select id 누락 |
| 8 | MIG-I4 | Minor | P3 | 멀티워커 SHA 폴백 doc_type 미복원 |

---

## 기존 코드 발견 이슈 요약 (18건)

SHA 확장 리뷰 중 기존 코드에서 발견된 이슈. SHA와 무관하나 개선 필요:

| 우선순위 | 건수 | 대표 이슈 |
|---------|------|----------|
| P0 | 2 | .env API 키 노출, asyncio.TimeoutError catch 오류 |
| P1 | 4 | 프롬프트 인젝션, 세션 소유권, 멀티프로세스 비안전, 원문 중복 저장 |
| P2 | 6 | 세션 미정리, variable_key 패턴, 타임아웃 재시도, 비용 한도, DB refresh |
| P3 | 6 | Step 3 메시지, 반환 튜플, 테스트 품질, JSON 파싱 |

---

## Migration Validation

| 항목 | 상태 | 설명 |
|------|------|------|
| SHA 확장 마이그레이션 필요성 | PASS | AnalysisSession 완전 인메모리, DB 변경 불필요 |
| 기존 047 마이그레이션 정합성 | PASS | downgrade() 정상, legaldoctype enum 재사용 정상 |
| SHA 값 DB 호환 | PASS | `LegalDocType.SHA`는 007에서 이미 포함 |
| condition_expression 길이 | WARNING | String(500) — 복합 SHA 조건식 초과 가능성 (Minor) |

---

## 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1 | BE 스키마: SHA_TYPES, EXIT_STRATEGIES, ALL_STRUCTURE_TYPES | ✅ | `schemas/spa_analysis.py:22-29` |
| 2 | BE 스키마: doc_type_hint, sha_type, exit_strategy 필드 | ✅ | `schemas/spa_analysis.py:107,128-131` |
| 3 | BE 스키마: sha_type/exit_strategy validator | ✅ | `schemas/spa_analysis.py:133-148` |
| 4 | BE 서비스: AnalysisSession.detected_doc_type | ✅ | `spa_analysis_service.py:60` |
| 5 | BE 서비스: _SHA_STEP1_SYSTEM_PROMPT | ✅ | `spa_analysis_service.py:368-521` |
| 6 | BE 서비스: _SHA_STEP2_SYSTEM_PROMPT | ✅ | `spa_analysis_service.py:744-836` |
| 7 | BE 서비스: 프롬프트 분기 (Step 1/2) | ✅ | `spa_analysis_service.py:558,889` |
| 8 | BE 라우터: doc_type_hint 전달 + 응답 매핑 | ✅ | `routers/spa_analysis.py:103,133-137` |
| 9 | BE 테스트: SHA 13개 추가 | ✅ | `tests/test_spa_analysis.py` — 85/85 통과 |
| 10 | FE 타입: SHA_TYPES, EXIT_STRATEGIES, 인터페이스 확장 | ✅ | `types/spa_analysis.ts` |
| 11 | FE SpaTextInput: doc_type_hint 드롭다운 | ✅ | `SpaTextInput.tsx:87-101` |
| 12 | FE AnalysisReviewPanel: ShaClassificationPanel | ✅ | `AnalysisReviewPanel.tsx:659-747` |
| 13 | FE SpaAnalysisWizard: SHA 조건부 렌더링 | ✅ | `SpaAnalysisWizard.tsx:351-381` |
| 14 | 기존 SPA 코드 파괴적 변경 0건 | ✅ | 85/85 테스트 통과, tsc 0 에러 |

---

## 품질 게이트 상태

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| tsc --noEmit | ✅ PASS | FE 타입 정합성 자동 검증됨 |
| eslint | ⚠️ WARN (2건) | 기존 경고, SHA 변경 무관 |
| ruff check + format | ✅ PASS | BE 린트/포맷 자동 검증됨 |
| pytest (85/85) | ✅ PASS | SHA 13개 포함 전체 통과 |
| vite build | ✅ PASS (10.91s) | 프로덕션 빌드 성공 |

---

## Methodology

- **Agents**: python-code-reviewer, general-purpose (FE), backend-security-reviewer, performance-profiler, migration-validator
- **Files scanned**: 8개 (BE 4 + FE 4) + 관련 참조 파일 다수
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 8건 수행
- **Backend availability**: deal-mgmt(✅) kiis(N/A) im(N/A) fdd(N/A)

## 검증 투명성

### 검증 통계
- 검증한 가설: ~50건
- 보고된 이슈: 26건
- SHA 확장 전용: 8건
- 기존 코드 발견: 18건

### FP 방지
- 교차 검증으로 3건의 중복 이슈 병합 (프롬프트 인젝션, 멀티프로세스, variable_key)
- Migration validator: 마이그레이션 불필요 확인 (FP 방지)
- SEC-H3 (condition_expression): ast.parse만 사용, eval 없음 확인 → 신뢰도 MEDIUM으로 하향
