# 5단계 콘텐츠 통합 리뷰 리포트

> **리뷰 일시**: 2026-03-03 20:07 KST
> **리뷰 범위**: Phase 1~5 전체 (28개 소스 파일, 7개 테스트 파일)
> **리뷰 관점**: 13개 (R2~R6 그룹)
> **리뷰 방법**: 5개 병렬 에이전트 (Phase별 + Cross-cutting)

---

## 1. 종합 요약

| 항목 | 결과 |
|------|------|
| **Critical** | **0건** |
| **Major** | **0건** |
| **Moderate** | **5건** |
| **Minor** | **~15건** |
| **플랜 준수율** | 28/28 파일 (100%), 171/141 테스트 (+21%) |
| **종합 판정** | ✅ 프로덕션 투입 가능 (Moderate 5건 후속 개선 권장) |

---

## 2. Phase별 테스트 달성도

| Phase | 설명 | 계획 | 실제 | 초과 | 파일 수 |
|-------|------|------|------|------|---------|
| Phase 1 | 계약서 5종 템플릿 | 31 | 33 | +2 | 8+1 |
| Phase 2 | IM 완전한 콘텐츠 | 35 | 40 | +5 | 5+1 |
| Phase 3 | TM 완전한 콘텐츠 | 25 | 36 | +11 | 3+1 |
| Phase 4 | DM 완전한 콘텐츠 | 20 | 32 | +12 | 2+1 |
| Phase 5 | AMIC 디자인 + tm_pipeline | 30 | 30 | 0 | 7+2 |
| **합계** | | **141** | **171** | **+30** | **25+6** |

---

## 3. 13개 관점별 분석 결과

### R2 그룹: 보안 + 위협 모델링

#### R2-1: 보안 (Security)

| ID | Phase | 심각도 | 신뢰도 | 위치 | 설명 |
|----|-------|--------|--------|------|------|
| SEC-01 | 1 | Moderate | HIGH | `docx_parser.py:137` | DOCX 텍스트를 `html.escape()` 없이 HTML 변환 → XSS 위험 |
| SEC-02 | 1 | Minor | MEDIUM | `docx_parser.py` | 경로 순회 방어 없음 (파일 경로 검증 부재) |

**양호 사항**:
- Phase 2~5: 보안 위협 없음 (외부 입력 수용 없는 순수 데이터 생성 모듈)
- Phase 1: JWT/인증은 범위 밖 (상위 API 레이어에서 처리)
- 하드코딩된 시크릿, 민감 정보 노출 없음

#### R2-2: 위협 모델링 & 공격 표면 (Threat Modeling)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| TM-01 | 1 | Minor | LOW | DOCX 파서가 악의적 DOCX(ZIP bomb, macro)에 대한 방어 없음 |

**양호 사항**:
- Phase 2~4: 공격 표면 없음 — 순수 데이터 정의 모듈, 외부 입력 없음
- Phase 5: tm_pipeline 입력은 내부 API에서 제공하는 JSON → 공격 표면 최소화
- `DocumentRenderingSpec`에 `_MAX_NARRATIVE_LENGTH=100,000`, `_MAX_NARRATIVE_SECTIONS=30` 제한 존재

---

### R3 그룹: 데이터 흐름 & 무결성 + API 계약

#### R3-1: 데이터 흐름 & 무결성 (Data Flow & Integrity)

| ID | Phase | 심각도 | 신뢰도 | 위치 | 설명 |
|----|-------|--------|--------|------|------|
| DF-01 | 2 | Moderate | HIGH | `narratives_im.py` | Cloud CAGR "30%+" 주장 vs 실제 데이터 28~29% — 내러티브-재무 정합성 불일치 |
| DF-02 | 5 | Moderate | HIGH | `schema.py:283-320` | `DocumentRenderingSpec→IMDocumentData` 변환 시 `market_data`, `growth_strategy`, `contacts` 필드 누락 |

**양호 사항**:
- Phase 2: 산술 교차 검증 20+ 항목 전체 PASS (매출 합계, 세그먼트 비율, 밸류에이션 배수)
- Phase 3: TM 프로포마 예측 → 성장 둔화 반영 (현실적), 기존 IM 재무 데이터와 정합
- Phase 4: DM 분석 데이터 → IM 원본 참조, 독립 왜곡 없음
- Phase 5: `AntiHallucinationValidator` — 산술/출처/일관성 3중 검증 파이프라인

#### R3-2: API 계약 & 호환성 (API Contract)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| AC-01 | 전체 | 양호 | — | `IMDocumentData` 스키마와의 호환성 100% (Phase 2~4 모두 검증 통과) |

**양호 사항**:
- Phase 2: `get_full_im_data()` → `IMDocumentData` 정합성 완벽
- Phase 3: `im_style=TEASER`, `TEASER_SECTION_IDS` 8개 정확히 대응
- Phase 4: `im_style=DM`, `DM_SECTION_IDS` 6개 정확히 대응, 불필요 필드 의도적 제외
- Phase 1: `TemplateData` frozen dataclass — 불변 계약, 외부 API 의존 없음

---

### R4 그룹: 에러 처리 + 관찰 가능성

#### R4-1: 에러 처리 (Error Handling)

| ID | Phase | 심각도 | 신뢰도 | 위치 | 설명 |
|----|-------|--------|--------|------|------|
| EH-01 | 5 | Minor | MEDIUM | `orchestrator.py` | 에러 메시지에 구체적 원인 미포함 — 호출자가 디버깅 어려움 |
| EH-02 | 1 | Minor | LOW | `docx_parser.py` | 빈 DOCX, 손상 DOCX에 대한 명시적 에러 처리 없음 |

**양호 사항**:
- Phase 1: `validate_template_data()` — 5가지 무결성 검증 (빈 이름, 중복 조항, 변수 미참조, 잘못된 참조, 타입 체크)
- Phase 5: `DocumentRenderingSpec` Pydantic 검증 → 자동 에러 생성
- Phase 5: `AntiHallucinationValidator` → `ValidationResult` with issues list

#### R4-2: 관찰 가능성 (Observability)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| OB-01 | 전체 | Minor | LOW | 로깅/트레이싱 부재 — 순수 데이터 모듈이므로 현재 수준 적절, 향후 파이프라인 통합 시 추가 필요 |

**양호 사항**:
- Phase 5: `PipelineOutput` — `validation_result`, `slide_count`, `output_path` 반환 → 결과 추적 가능
- Phase 1: `validate_template_data()` 반환값으로 검증 결과 확인 가능

---

### R5 그룹: 성능 + 배포 안전성 + 의존성

#### R5-1: 성능 (Performance)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| PF-01 | 전체 | 양호 | — | 성능 병목 없음 — 데이터 구조체 정의/생성 모듈, 런타임 부하 무시 가능 |

**양호 사항**:
- Phase 1: Frozen dataclass → 해싱 가능, 메모리 효율적
- Phase 2~4: 함수 호출 시 일회성 데이터 생성, 캐싱 불필요
- Phase 5: 3단계 선형 파이프라인 → O(n) 복잡도, 30~70 슬라이드 규모에서 문제 없음

#### R5-2: 배포 안전성 (Deployment Safety)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| DS-01 | 전체 | 양호 | — | DB 의존 없음, 마이그레이션 불필요, Docker 빌드 영향 없음 |

**양호 사항**:
- Phase 1: DB 독립 설계 (SQLAlchemy 모델 아닌 순수 dataclass)
- Phase 2~4: 외부 서비스/DB 의존 없음
- Phase 5: python-pptx 의존만 존재 (이미 pyproject.toml 등록됨)

#### R5-3: 의존성 & 결합도 (Dependencies & Coupling)

| ID | Phase | 심각도 | 신뢰도 | 위치 | 설명 |
|----|-------|--------|--------|------|------|
| DC-01 | 4 | Minor | LOW | `dm_full.py` | IM 전체 charts를 import 하지만 일부만 사용 — 의도적 설계이나 명시적 문서화 권장 |

**양호 사항**:
- **순환 참조 0건** — 3개 패키지(template_builder, sample_data, tm_pipeline) 전체 검증
- Phase 1: 외부 의존성 `python-docx`만 (동적 import로 Optional 처리)
- Phase 3~4: IM 기반 데이터 재활용 → DRY 원칙 준수, 결합도 최소화
- Phase 5: `im_document.py`만 참조 → 단방향 의존

---

### R6 그룹: 도메인 로직 + 테스트 품질 + 인지 복잡도 + 접근성

#### R6-1: 도메인 로직 (Domain Logic)

| ID | Phase | 심각도 | 신뢰도 | 위치 | 설명 |
|----|-------|--------|--------|------|------|
| DL-01 | 1 | Minor | MEDIUM | `sha_builder.py` | SHA에 Call Option 조항 누락 (Put Option만 존재) |
| DL-02 | 2 | Minor | MEDIUM | `narratives_im.py` | 실제 기업명(삼성SDS, LG CNS 등) + 허구 재무 데이터 사용 — 샘플 데이터 명시 필요 |
| DL-03 | 3 | Minor | MEDIUM | `narratives_tm.py` | 동일 — 실제 기업명 + 허구 배수 |
| DL-04 | 5 | Moderate | MEDIUM | `validators.py:169-174` | `operating_income = GP - SGA` 공식이 실제 재무제표와 불일치 (R&D, 기타비용 미고려 → false positive 가능) |
| DL-05 | 3 | Minor | LOW | `proforma.py` | `build_proforma_financial_statements()` 정의 후 미사용 — 향후 사용 예정으로 문서화됨 |

**양호 사항**:
- Phase 1: M&A 5종 계약서 표준 조항 구조 완비 (SPA 18조항/42변수, SHA 거버넌스 5조항, BTA 사업양수도, SSA RCPS 4조항, MOU 구속/비구속)
- Phase 2: IM 14개 섹션 중립적 톤 일관성 유지
- Phase 3: TM 8개 섹션 마케팅 톤 일관성 유지
- Phase 4: DM 6개 섹션 분석적/비판적 톤, 4대 리스크 카테고리, IC 추천 형식
- Phase 4: 프로포마 예측 성장 둔화 반영 (비현실적 성장 가정 없음)

#### R6-2: 테스트 품질 (Test Quality)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| TQ-01 | 5 | Minor | MEDIUM | TM 파이프라인에 경계값/실패 테스트 부족 (E2E 위주) |
| TQ-02 | 1 | Minor | LOW | `validate_template_data()`에 대한 직접 단위 테스트 부재 |

**양호 사항**:
- **전체 171/141 테스트** — 플랜 대비 21% 초과 달성
- Mock 사용 0건 — 콘텐츠 품질 테스트에 적합한 전략
- 산술 교차 검증 50+ 항목 전체 PASS
- 한국어 f-string assert 메시지 일관 적용
- Phase 2: 스키마 호환성 테스트 포함
- Phase 3~4: 내러티브 톤 일관성 테스트 포함

#### R6-3: 인지 복잡도 (Cognitive Complexity)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| CC-01 | 전체 | 양호 | — | 복잡도 낮음 — 빌더 패턴, 선형 파이프라인, 단일 책임 함수 |

**양호 사항**:
- Phase 1: 5개 빌더 각각 독립적, 공통 base 상속 없이 단순 함수 호출
- Phase 2~4: 각 `get_full_*_data()` 함수가 서브빌더 조합 → 인지 부하 낮음
- Phase 5: 3단계 선형 파이프라인 (Spec→Validate→Render) → 디버깅 용이
- `_CLAUSE_TITLE_RE` 등 명명된 정규식 상수 사용 → 가독성 확보

#### R6-4: 접근성 & UX (Accessibility)

| ID | Phase | 심각도 | 신뢰도 | 설명 |
|----|-------|--------|--------|------|
| AX-01 | 전체 | N/A | — | 백엔드 데이터 모듈 → 접근성 관점 해당 없음 |

**참고**:
- Phase 5 PPTX 출력물의 접근성(대체 텍스트, 색상 대비)은 렌더러(`section_renderers/`) 영역 → 이번 리뷰 범위 밖

---

## 4. Moderate 이슈 상세 (우선순위순)

### MOD-01: XSS 위험 — DOCX 텍스트 미이스케이프 [P2]

- **위치**: `deal-mgmt/app/services/template_builder/docx_parser.py:137`
- **설명**: `_paragraph_to_html()` 함수에서 DOCX 텍스트를 `html.escape()` 없이 HTML 태그에 삽입
- **영향**: 악의적 DOCX 업로드 시 XSS 공격 가능
- **권장**: `import html` + `html.escape(run.text)` 적용
- **신뢰도**: HIGH — 코드 직접 확인

### MOD-02: 내러티브-재무 CAGR 불일치 [P2]

- **위치**: `im/src/design_renderer/sample_data/narratives_im.py`
- **설명**: 클라우드 시장 CAGR "30%+" 주장 vs `financials.py` 실제 데이터 28~29%
- **영향**: IM 문서 신뢰도 저하 (반올림 오차 범위 초과)
- **권장**: 내러티브 문구를 "약 29%" 또는 데이터를 30%로 정렬
- **신뢰도**: HIGH — 산술 교차 검증으로 확인

### MOD-03: DocumentRenderingSpec 필드 매핑 누락 [P3]

- **위치**: `im/src/design_renderer/tm_pipeline/schema.py:283-320`
- **설명**: `to_im_document_data()` 변환 시 `market_data`, `growth_strategy`, `contacts` 필드 미매핑
- **영향**: JSON→PPTX 파이프라인에서 해당 섹션 빈 데이터로 렌더링
- **권장**: 누락 필드 매핑 추가 또는 Optional 필드로 문서화
- **신뢰도**: HIGH — 스키마 대조 확인

### MOD-04: 영업이익 검증 공식 부정확 [P3]

- **위치**: `im/src/design_renderer/tm_pipeline/validators.py:169-174`
- **설명**: `operating_income = gross_profit - sga_expense` 공식이 R&D, 기타비용 미고려 → false positive 유발 가능
- **영향**: 정상 데이터를 검증 실패로 오판할 수 있음
- **권장**: 공식에 tolerance 확대 또는 주요 비용 항목 추가
- **신뢰도**: MEDIUM — 재무제표 구조 기반 추론

### MOD-05: DOCX 리스트 패턴 불완전 [P4]

- **위치**: `deal-mgmt/app/services/template_builder/docx_parser.py`
- **설명**: 번호 리스트 감지가 "1.", "2.", "3."만 하드코딩 — "4." 이후 미감지
- **영향**: 4항 이상의 번호 리스트가 일반 텍스트로 파싱됨
- **권장**: 정규식 패턴 `r'^\d+\.\s'`로 일반화
- **신뢰도**: HIGH — 코드 직접 확인

---

## 5. Minor 이슈 목록

| ID | Phase | 위치 | 설명 |
|----|-------|------|------|
| MIN-01 | 1 | `sha_builder.py` | Call Option 조항 누락 (Put Option만 존재) |
| MIN-02 | 1 | `docx_parser.py` | 경로 순회 방어 없음 |
| MIN-03 | 1 | `docx_parser.py` | 빈/손상 DOCX 명시적 에러 처리 없음 |
| MIN-04 | 1 | 테스트 | `validate_template_data()` 직접 단위 테스트 부재 |
| MIN-05 | 2 | `narratives_im.py` | 실제 기업명 + 허구 재무 데이터 — 샘플 명시 필요 |
| MIN-06 | 2 | `financials.py` | IRR/MOIC 레버리지 가정 미문서화 |
| MIN-07 | 3 | `narratives_tm.py` | 실제 기업명 + 허구 배수 |
| MIN-08 | 3 | `proforma.py` | `build_proforma_financial_statements()` 정의 후 미사용 |
| MIN-09 | 4 | `dm_full.py` | IM charts 전체 import 후 일부만 사용 |
| MIN-10 | 5 | `orchestrator.py` | 에러 메시지 구체적 원인 미포함 |
| MIN-11 | 5 | `analyzer.py` 외 | `_ALLOWED_HEX_COLORS` 3곳 하드코딩 (DRY 위반) |
| MIN-12 | 5 | 테스트 | tm_pipeline 경계값/실패 테스트 부족 |
| MIN-13 | 5 | E2E 테스트 | 샘플 파일 의존 (파일 없으면 skip) |
| MIN-14 | 1 | `docx_parser.py` | 악의적 DOCX (ZIP bomb, macro) 방어 없음 |

---

## 6. Phase × 관점 매트릭스

| 관점 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|------|---------|---------|---------|---------|---------|
| 보안 | ⚠️ MOD-01 | ✅ | ✅ | ✅ | ✅ |
| 위협 모델링 | ℹ️ MIN-14 | ✅ | ✅ | ✅ | ✅ |
| 데이터 흐름 | ✅ | ⚠️ MOD-02 | ✅ | ✅ | ⚠️ MOD-03 |
| API 계약 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 에러 처리 | ℹ️ MIN-03 | ✅ | ✅ | ✅ | ℹ️ MIN-10 |
| 관찰 가능성 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 성능 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 배포 안전성 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 의존성 | ✅ | ✅ | ✅ | ℹ️ MIN-09 | ✅ |
| 도메인 로직 | ℹ️ MIN-01 | ℹ️ MIN-05 | ℹ️ MIN-07,08 | ✅ | ⚠️ MOD-04 |
| 테스트 품질 | ℹ️ MIN-04 | ✅ | ✅ | ✅ | ℹ️ MIN-12 |
| 인지 복잡도 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 접근성 | N/A | N/A | N/A | N/A | N/A |

> ✅ 양호, ⚠️ Moderate, ℹ️ Minor, N/A 해당 없음

---

## 7. Cross-cutting 품질 지표

| 지표 | 결과 | 판정 |
|------|------|------|
| 순환 참조 | 0건 (3개 패키지 전체) | ✅ |
| 타입 힌트 완성도 | 100% (모든 함수/메서드) | ✅ |
| Mock 사용 | 0건 (콘텐츠 품질 테스트 특성에 적합) | ✅ |
| 산술 교차 검증 | 50+ 항목 전체 PASS | ✅ |
| 한국어 assert 메시지 | 일관 적용 (f-string) | ✅ |
| Frozen dataclass | Phase 1 전체 적용 (불변성 보장) | ✅ |
| IMDocumentData 호환성 | Phase 2~4 전체 PASS | ✅ |
| Ruff lint | 0건 (사전 검증) | ✅ |
| 내러티브 톤 일관성 | IM=중립, TM=마케팅, DM=분석적 — 각각 일관 | ✅ |

---

## 8. 권장 후속 조치

### 즉시 (P2)
1. **MOD-01**: `docx_parser.py`에 `html.escape()` 적용 — 보안 위험 제거
2. **MOD-02**: 클라우드 CAGR 수치 정렬 — 데이터 신뢰도 확보

### 단기 (P3)
3. **MOD-03**: `DocumentRenderingSpec` 필드 매핑 보완
4. **MOD-04**: `AntiHallucinationValidator` 영업이익 공식 수정

### 개선 (P4)
5. **MOD-05**: 리스트 패턴 정규식 일반화
6. **MIN-11**: `_ALLOWED_HEX_COLORS` 단일 출처로 통합 (DRY)
7. **MIN-12**: tm_pipeline 경계값/실패 테스트 추가

---

## 9. 결론

5단계 콘텐츠 구현은 **Critical/Major 이슈 0건**으로, 전체적으로 높은 품질을 달성했습니다.

**강점**:
- 플랜 대비 테스트 21% 초과 달성 (171/141)
- 순환 참조 0건, 타입 힌트 100%, IMDocumentData 호환성 완벽
- IM/TM/DM 3종 문서의 톤 분리가 명확하고 일관적
- 50+ 산술 교차 검증 전체 통과 — 도메인 데이터 무결성 확보
- 인지 복잡도 낮음 — 빌더 패턴, 선형 파이프라인, 단일 책임 설계

**개선 필요**:
- Moderate 5건 중 MOD-01(XSS)과 MOD-02(CAGR 불일치)는 조기 수정 권장
- Phase 5 tm_pipeline의 스키마 매핑 완전성(MOD-03)과 검증 공식 정확성(MOD-04) 보완 필요
- 실제 기업명 사용(MIN-05,07)은 운영 환경에서 "샘플 데이터" 워터마크 필요
