# SHA 확장 보충 통합 리뷰 (13개 관점 중 나머지 6개)

> **작성일**: 2026-03-02 14:26 KST
> **대상 파일**: SHA 확장 변경 8개 파일 + 테스트
> **이전 리뷰**: `20260302_1331_SHA_Extension_Integrated_Review.md` (5개 에이전트, 26건)

---

## 리뷰 관점 커버리지

| # | 관점 | 1차 리뷰 | 보충 리뷰 |
|---|------|---------|----------|
| §1 | 정합성 | ✅ | — |
| §2 | 기능 완전성 | ✅ | — |
| §2 | **통합 완전성** | — | ✅ 이번 |
| §2 | **테스트 완전성** | — | ✅ 이번 |
| §3 | 설계 품질 | ✅ | — |
| §3 | 구현 품질 | ✅ | — |
| §3 | 가독성 | ✅ | — |
| §4 | 보안 | ✅ | — |
| §4 | 에러 복원 | ✅ | — |
| §4 | 데이터 무결성 | ✅ | — |
| §4 | **모듈 간 계약** | — | ✅ 이번 |
| §5 | **접근성 & UX** | — | ✅ 이번 |
| §6 | **도메인 로직** | — | ✅ 이번 |
| §7 | **관찰 가능성** | — | ✅ 이번 |

---

## 1절. API 계약 + 통합 완전성

### 스키마 대조 결과 (BE Pydantic ↔ FE TypeScript)

| 스키마 | 필드 수 | 결과 | 비고 |
|--------|--------|------|------|
| SpaStep1Request | 3 | ✅ PASS | 필드명/타입/optional 완전 일치 |
| SpaStep1Response | 10 | ✅ PASS | sha_type, exit_strategy 포함 |
| SpaStep2Request | 6 | ✅ PASS | doc_type_hint 포함 |
| SpaStep2Response | 4 | ✅ PASS | |
| SpaStep3Request | 6 | ✅ PASS | doc_type 포함 |
| SpaStep3Response | 5 | ✅ PASS | template_id UUID→string 호환 |
| ExtractedVariable | 12 | ✅ PASS | |
| DiscoveredBoolean | 3 | ✅ PASS | |
| AnalyzedClause | 7 | ✅ PASS | |

### Enum/상수 대조

| 상수 | BE 값 | FE 값 | 결과 |
|------|-------|-------|------|
| DEAL_STRUCTURES | 4개 | 4개 | ✅ 일치 |
| SHA_TYPES | 4개 | 4개 | ✅ 일치 |
| EXIT_STRATEGIES | 3개 | 3개 | ✅ 일치 |
| INDUSTRY_TYPES | 5개 | 5개 | ✅ 일치 |
| VALID_DOC_TYPES | 5개 | 5개 | ✅ 일치 |
| VALID_INPUT_TYPES | 8개 | 8개 | ✅ 일치 |

### API 엔드포인트 경로

| 엔드포인트 | BE 라우터 | FE 훅 | 결과 |
|-----------|----------|-------|------|
| Step 1 | `POST /transactions/{txn_id}/spa-analysis/step1-variables` | `maApi.post(${BASE}/step1-variables)` | ✅ 일치 |
| Step 2 | `POST .../step2-clauses` | `maApi.post(${BASE}/step2-clauses)` | ✅ 일치 |
| Step 3 | `POST .../step3-seed` | `maApi.post(${BASE}/step3-seed)` | ✅ 일치 |

### 데이터 흐름 추적 (Step 1→2→3)

| 흐름 | 검증 결과 |
|------|----------|
| Step 1 sha_type → FE dealStructure 상태 | ✅ `sha_type ?? deal_structure` 폴백 |
| Step 1 exit_strategy → FE exitStrategy 상태 | ✅ `exit_strategy ?? "OTHER_STRATEGY"` 폴백 |
| FE doc_type_hint → Step 2 전달 | ✅ SHA일 때만 "SHA" 전달, 그 외 undefined |
| 멀티워커 폴백 doc_type_hint → detected_doc_type 복원 | ✅ 세션 유실 시 doc_type_hint로 복원 |
| FE docType → Step 3 doc_type 전달 | ✅ _DOC_TYPE_MAP으로 LegalDocType 매핑 |
| SHA↔SPA 전환 시 dealStructure 리셋 | ✅ FE에서 타입 범위 체크 후 기본값 설정 |

**결론**: 9개 스키마, 6개 Enum, 3개 엔드포인트, 6개 데이터 흐름 모두 **완전 정합**.

---

## 2절. 도메인 로직 정확성

| ID | 항목 | 판정 | 비고 |
|----|------|------|------|
| D-1 | SHA_TYPES 4종 분류 | ✅ 적절 | POST_BUYOUT/JV/MINORITY + OTHER |
| D-2 | EXIT_STRATEGIES 3종 분류 | ✅ 적절 | IPO/M&A + OTHER (BUYBACK은 OTHER로 포괄) |
| D-3 | ALL_STRUCTURE_TYPES 공유 validator | ⚠️ Minor | SPA+SHA 교차 허용 가능 (LLM 프롬프트로 제어) |
| D-4 | SHA Step 1 변수 목록 충분성 | ✅ 양호 | 핵심 15+ 변수 커버, 자율 발견 규칙 보완 |
| D-5 | SHA Step 2 조항 구조 13개 | ✅ 적절 | 한국 실무 SHA 구조와 대응 |

---

## 3절. 관찰 가능성 (로깅/비용 추적)

| ID | 제목 | 심각도 | 신뢰도 |
|----|------|--------|--------|
| **O-1** | Step 3 로그 "SPA Step 3 완료" 하드코딩 — SHA도 "SPA"로 기록 | Moderate | HIGH |
| **O-2** | 라우터 전체 로깅 부재 (3개 엔드포인트 × 0건 로그) | Moderate | HIGH |
| O-3 | LLM 비용 추적 SHA에서도 정확 | ✅ 이슈 없음 | HIGH |
| O-4 | 세션 생성/만료 시 doc_type 구분 로깅 부재 | Minor | HIGH |
| O-5 | `_call_llm_json` unreachable 반환 경로 | Minor | MEDIUM |
| O-6 | 에러 응답에서 SHA vs SPA 구분 불가 | Minor | HIGH |

---

## 4절. 접근성 & UX

### 양호 사항 (기존 구현 완료)

- ✅ 스텝 인디케이터: `aria-label`, `role="list"`, `aria-current="step"`
- ✅ 분석 중 상태: `aria-live="polite"`, `role="status"`, `sr-only`
- ✅ SpaTextInput: `id="spa-raw-text"` + `htmlFor` 연결
- ✅ 문서 유형/언어 힌트: `id` + `htmlFor` 연결
- ✅ Step 1 분류 select: `id="wizard-doc-type"` + `htmlFor`
- ✅ Step 3 템플릿 입력: `id="tmpl-name"`, `id="tmpl-desc"` + `htmlFor`
- ✅ SHA 분류 패널 3개 select 모두 `id` + `htmlFor`
- ✅ 조항 버튼 (위로/아래/삭제): `aria-label`
- ✅ 스텝 전환 포커스 관리: `tabindex=-1` + `focus()`
- ✅ beforeunload 경고

### 이슈

| ID | 제목 | 심각도 | 신뢰도 |
|----|------|--------|--------|
| **A11Y-5** | 중복 키 경고에 `aria-invalid`/`aria-describedby` 없음 | Moderate | HIGH |
| A11Y-1 | 변수 테이블 편집 모드 input에 label/id 연결 없음 | Minor | HIGH |
| A11Y-2 | 고급 편집 영역 label에 `htmlFor` 연결 없음 | Minor | HIGH |
| A11Y-3 | SelectOptionsEditor textarea에 label `htmlFor` 없음 | Minor | HIGH |
| A11Y-4 | 에러 메시지에 `role="alert"` 없음 | Minor | HIGH |
| A11Y-6 | JSON 파싱 에러에 `aria-invalid` 없음 | Minor | HIGH |
| A11Y-7 | 문자 수 경고 스크린 리더 미접근 | Minor | MEDIUM |

---

## 5절. 테스트 완전성

### 커버리지 통계

- 전체 테스트: **55개**
- SHA 전용 테스트: **~11개** (스키마 7 + 서비스 2 + Step3 1 + 불변검증 2)
- SPA 불변 검증: **2개** (Step 1/Step 2 프롬프트 불변)

### 커버된 시나리오

| 시나리오 | 테스트 | 상태 |
|---------|--------|------|
| SHA Step 1: doc_type_hint="SHA" → SHA 프롬프트 | `test_sha_step1_uses_sha_prompt` | ✅ |
| SHA Step 2: detected_doc_type="SHA" → SHA 프롬프트 | `test_sha_step2_uses_sha_prompt` | ✅ |
| SHA_TYPES 4개 상수 | `test_sha_types_constant` | ✅ |
| EXIT_STRATEGIES 3개 상수 | `test_exit_strategies_constant` | ✅ |
| ALL_STRUCTURE_TYPES 통합 | `test_all_structure_types_includes_both` | ✅ |
| Step 1 응답 sha_type/exit_strategy | `test_step1_response_sha_fields` | ✅ |
| SPA 응답에서 SHA 필드 None | `test_step1_response_spa_sha_fields_null` | ✅ |
| Step 2 SHA_TYPES 값 허용 | `test_step2_request_sha_type_accepted` | ✅ |
| 모든 structure type 허용 | `test_deal_structure_accepts_all_types` | ✅ |
| SPA 프롬프트 불변 (Step 1) | `test_spa_step1_still_uses_spa_prompt` | ✅ |
| SPA 프롬프트 불변 (Step 2) | `test_spa_step2_still_uses_spa_prompt` | ✅ |
| SHA doc_type 템플릿 생성 | `test_sha_doc_type` | ✅ |
| 멀티워커 폴백 (SPA) | `test_step2_fallback_with_spa_text` | ✅ |

### 미커버 시나리오

| ID | 제목 | 심각도 | 신뢰도 |
|----|------|--------|--------|
| **TEST-1** | SHA 멀티워커 폴백 + doc_type_hint="SHA" 테스트 부재 | Moderate | HIGH |
| TEST-2 | sha_type/exit_strategy 유효하지 않은 값 폴백 테스트 부재 | Minor | HIGH |
| TEST-3 | Step 1 실패 시 세션 정리 검증 테스트 부재 | Minor | MEDIUM |

---

## 6절. API 계약 관련 이슈 (통합 완전성에서 발견)

| ID | 제목 | 심각도 | 신뢰도 |
|----|------|--------|--------|
| SHA-R1 | FE doc_type_hint 폴백이 BTA/SSA/MOU 무시 (현재 기능 영향 없음) | Minor | HIGH |
| SHA-R2 | exitStrategy가 Step 2/3에 미전달 (설계 의도) | Info | HIGH |
| SHA-R3 | Step 1 반환 타입 10-tuple 가독성 | Style | MEDIUM |

---

## 전체 이슈 요약 (우선순위 정렬)

### P1 (Moderate — 수정 권장)

| ID | 제목 | 카테고리 | 신뢰도 |
|----|------|---------|--------|
| O-1 | Step 3 로그 "SPA" 하드코딩 → `{doc_type}` 동적 변경 | 관찰 가능성 | HIGH |
| O-2 | 라우터 전체 로깅 부재 (3개 엔드포인트) | 관찰 가능성 | HIGH |
| TEST-1 | SHA 멀티워커 폴백 + doc_type_hint 테스트 부재 | 테스트 | HIGH |
| A11Y-5 | 중복 키 경고 `aria-invalid`/`aria-describedby` 없음 | 접근성 | HIGH |

### P2 (Minor — 개선 권장)

| ID | 제목 | 카테고리 | 신뢰도 |
|----|------|---------|--------|
| O-4 | 세션 생성/만료 doc_type 구분 로깅 부재 | 관찰 가능성 | HIGH |
| O-6 | 에러 응답에서 SHA vs SPA 구분 불가 | 관찰 가능성 | HIGH |
| D-3 | ALL_STRUCTURE_TYPES 교차 허용 (SPA에 SHA값 가능) | 도메인 | HIGH |
| A11Y-1~4,6 | 편집 모드 input label/id 연결 5건 | 접근성 | HIGH |
| TEST-2 | sha_type/exit_strategy 잘못된 값 폴백 테스트 | 테스트 | HIGH |
| SHA-R1 | BTA/SSA/MOU doc_type_hint 폴백 미전달 | 통합 | HIGH |

### P3 (Info/Style — 선택적 개선)

| ID | 제목 | 카테고리 | 신뢰도 |
|----|------|---------|--------|
| O-5 | `_call_llm_json` unreachable 반환 경로 | 관찰 가능성 | MEDIUM |
| A11Y-7 | 문자 수 경고 스크린 리더 미접근 | 접근성 | MEDIUM |
| TEST-3 | Step 1 실패 시 세션 정리 테스트 | 테스트 | MEDIUM |
| SHA-R2 | exitStrategy Step 2/3 미전달 (설계 의도) | 통합 | HIGH |
| SHA-R3 | 10-tuple 반환 타입 가독성 | 스타일 | MEDIUM |

---

## 종합 결론

**SHA 확장의 BE-FE API 계약은 완전 정합 상태**입니다.
- 9개 스키마 56필드, 6개 Enum 29값, 3개 엔드포인트: 양측 100% 일치
- Step 1→2→3 데이터 흐름: sha_type, exit_strategy, doc_type_hint 전달 모두 정확
- 도메인 로직: SHA_TYPES/EXIT_STRATEGIES 분류 적절, 프롬프트 커버리지 양호
- LLM 비용 추적: SHA에서도 정확 동작

**개선이 필요한 영역**:
1. 관찰 가능성 — 라우터 로깅 부재 + Step 3 로그 하드코딩이 운영 추적성을 저해
2. 테스트 — SHA 멀티워커 폴백 경로가 미커버
3. 접근성 — 편집 모드 내 label-input 연결 + ARIA 속성 일부 누락
