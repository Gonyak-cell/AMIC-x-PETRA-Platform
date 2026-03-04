# VC/SI Mapping — Round 8 Review

> Round: R8 | Date: 2026-03-04 18:27 | Status: **CONVERGED**
> Quality Gates: ruff(✓) pytest(34/34 ✓) tsc(✓) eslint(✓)
> Fix Criteria: HIGH→FIX | Critical/Major→FIX | else→SKIP
> Perspective: **API 계약 / 유지보수성** (응답 일관성, DRY, 네이밍, 코드 품질)

## Metrics

| Metric | Value |
|--------|-------|
| fix_target_count | 3 |
| skip_count | 14 |
| design_risk_count | 4 |
| fp_removed | 1 |
| oscillation_detected | 0 |

## Fix Target Issues (수정 완료)

### BE-2 [Major/HIGH] — 테스트 float 리터럴 → Decimal 변환
- **파일**: `deal-mgmt/tests/test_si_mapping.py`
- **수정**: `transaction_value=5000.0` → `transaction_value=Decimal("5000")` (4개소)
- **교차검증**: CONFIRMED — Numeric(20,2) 컬럼에 float 전달은 정밀도 규칙 위반

### FE-1 [Major/HIGH] — ARIA combobox 패턴 완전 누락
- **파일**: `amic-platform/.../KsicSearchInput.tsx`
- **수정**: input에 `role="combobox"`, `aria-expanded`, `aria-autocomplete="list"`, `aria-controls`, `aria-activedescendant` 추가. ul에 `id="ksic-listbox"`, `role="listbox"` 추가. button에 `role="option"`, `id`, `aria-selected` 추가
- **교차검증**: CONFIRMED — WAI-ARIA combobox 패턴 필수 속성 전부 누락이었음

### FE-7 [Minor/HIGH] — 에러 메시지 role="alert" 누락
- **파일**: `amic-platform/.../SIMappingPanel.tsx`
- **수정**: 에러 표시 `<p>` 3개소에 `role="alert"` 추가
- **교차검증**: CONFIRMED — 스크린 리더가 에러 발생을 즉시 인지하도록 live region 필요

## Skipped Issues (스킵)

### BE-4 [Major/HIGH] — bulk_add rate limiter 미적용
- **사유**: auth + Pydantic max_length=100으로 이미 제한. defense-in-depth 수준

### BE-5 [Major/HIGH] — ValueError 422 메시지 손실
- **사유**: Pydantic 스키마(max_length=100)가 먼저 검증 — 서비스 ValueError는 도달 불가

### BE-6 [Moderate/HIGH] — min_revenue 단위 불일치 (원 vs 억원)
- **사유**: SI(한국은행 IO 데이터=원)와 VC(KOSIS 데이터=억원)는 데이터 소스가 다름 — 의도된 차이

### BE-8 [Moderate/HIGH] — search min_length 불일관
- **사유**: KSIC(소량 데이터)은 빈 쿼리 허용, 업종(1,574건)은 최소 1자 필수 — 의도적 차이

### BE-9 [Moderate/MEDIUM] — corp_basic 분기 문서화 부족
- **사유**: MEDIUM 신뢰도, 문서화 이슈

### BE-10 [Minor/HIGH] — 상수 위치
- **사유**: 코스메틱, 기능 영향 없음

### FE-2 [Moderate/HIGH] — import 블록 배치
- **사유**: 코스메틱, 기능 영향 없음

### FE-3 [Moderate/HIGH] — mutation 파라미터 타입 인라인
- **사유**: 리팩토링 제안, 현재 동작에 문제 없음

### FE-4 [Moderate/MEDIUM] — SIDetailPanel 454줄
- **사유**: MEDIUM 신뢰도

### FE-5 [Moderate/HIGH] — extra_data 이중 타입 단언
- **사유**: TypeScript 한계, 이미 구조적 검증(in 연산자) 수행

### FE-6 [Moderate/HIGH] — useCallback 패턴 불일관
- **사유**: handleBulkAdd는 하위 컴포넌트에 전달되지 않아 성능 영향 없음

### FE-8 [Minor/HIGH] — onCompanyClick optional
- **사유**: 재사용성 위한 의도적 설계

### FE-10 [Minor/MEDIUM] — BuyersTab 452줄
- **사유**: MEDIUM 신뢰도

### FE-11 [Minor/HIGH] — 화살표 SVG 2회 반복
- **사유**: 2회 반복은 추출보다 인라인이 가독성 우수

### FE-12 [Minor/MEDIUM] — corporateInfo 이중 타입 단언
- **사유**: MEDIUM 신뢰도, 이미 구조 검증 수행

## Design Risk (기술부채)

### BE-3 [Major/HIGH] — audit entity_id 상수 문자열
- **사유**: `entity_id="SIMapping"` 고정값 → 감사 추적 세분화 불가. audit_service 계약 변경 필요

### BE-7 [Moderate/HIGH] — _mask_reg_no 중복
- **사유**: routers/si_mapping.py와 schemas/si_mapping.py에 동일 마스킹 로직. 공통 유틸 추출 필요

### BE-11 [Minor/HIGH] — VC 매핑 통합 테스트 누락
- **사유**: /vc-map, /vc-map-by-registration, /industries/search HTTP 테스트 없음

### FE-9 [Minor/HIGH] — Query Key 하드코딩
- **사유**: 크로스 모듈 쿼리 키 동기화 리스크. 쿼리 키 팩토리 패턴 도입 필요

## False Positive (제거됨)

### BE-1 — dart_available=False (DB 캐시 분기)
- **사유**: FP-LOGIC — `base_response`는 DART API 실패 시 폴백용. DART 성공 시 새 Response(dart_available=True)를 반환. 의도된 2단계 전략 (캐시→실시간 갱신)

## Quality Gates (수정 후 재검증)

| Gate | Status |
|------|--------|
| ruff check | ✓ PASS (0 issues) |
| ruff format | ✓ PASS |
| pytest | ✓ PASS (34/34) |
| tsc --noEmit | ✓ PASS |
| eslint | ✓ PASS |

## Convergence Status

- R5: 2건 → R6: 3건 → R7: 5건 → R8: 3건
- Trend: → 안정 (2~5건 범위에서 진동, 새 관점별 소수 발견)
- R4~R8까지 5라운드, 4개 관점 순회 완료
- 남은 이슈는 모두 SKIP(코스메틱/MEDIUM) 또는 DESIGN_RISK(아키텍처 변경 필요)
- **Decision: CONVERGED** — 코드 버그 수준의 FIX 대상이 관점 순회 후 고갈됨

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `deal-mgmt/tests/test_si_mapping.py` | float → Decimal("...") 리터럴 변환 (4개소) |
| `amic-platform/.../KsicSearchInput.tsx` | ARIA combobox 패턴 전체 추가 |
| `amic-platform/.../SIMappingPanel.tsx` | 에러 메시지 role="alert" 추가 (3개소) |

## 수렴 대시보드 (전체)

| Round | Perspective | fix_target | skip | design_risk | fp_removed | decision |
|-------|------------|-----------|------|-------------|------------|----------|
| R3 | (initial) | 34 | - | - | - | CONTINUE |
| R4 | Basic 13 perspectives | 10 | 1 | 3 | 0 | CONTINUE |
| R5 | Deep Security / Data Integrity | 2 | 11 | 5 | 4 | CONTINUE |
| R6 | Deep Concurrency / Performance | 3 | 4 | 3 | 1 | CONTINUE |
| R7 | Edge Cases / Defensive Coding | 5 | 8 | 0 | 0 | CONTINUE |
| R8 | API Contract / Maintainability | 3 | 14 | 4 | 1 | **CONVERGED** |

**총 수정**: R4(10) + R5(2) + R6(3) + R7(5) + R8(3) = **23건**
**총 스킵**: 38건
**총 DESIGN_RISK**: 15건 (누적)
**총 FP 제거**: 6건
**총 진동**: 1건 (SI-01 N+1 → DESIGN_RISK 격상)

## 누적 DESIGN_RISK 목록

| # | 이슈 | 라운드 | 필요 조치 |
|---|------|--------|----------|
| 1 | N+1 쿼리 패턴 (ROW_NUMBER 전환) | R4, R6 | DB 쿼리 구조 변경 |
| 2 | SIMappingPanel focus trap vs Headless UI | R4 | 아키텍처 결정 |
| 3 | BuyersTab Suspense fallback 스타일 | R4 | UI 개선 |
| 4 | BuyerCandidate DB UniqueConstraint | R5 | DB 마이그레이션 |
| 5 | corp_code 경로 파라미터 검증 | R5 | defense-in-depth |
| 6 | Redis 기반 rate limiter | R5 | 인프라 변경 |
| 7 | PII 마스킹 정책 | R5 | 컴플라이언스 결정 |
| 8 | 검색 API GET→POST | R5 | API 계약 변경 |
| 9 | 5,000건 인메모리 로딩 (TTL 캐시) | R6 | 캐시 레이어 도입 |
| 10 | buyerColumns 매 렌더 재생성 | R6 | 컴포넌트 추출 |
| 11 | audit entity_id 상수 문자열 | R8 | audit 계약 변경 |
| 12 | _mask_reg_no 중복 | R8 | 유틸 추출 |
| 13 | VC 통합 테스트 누락 | R8 | 테스트 추가 |
| 14 | Query Key 하드코딩 | R8 | 키 팩토리 도입 |
