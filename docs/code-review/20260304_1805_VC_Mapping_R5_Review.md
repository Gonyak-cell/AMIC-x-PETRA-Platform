# VC/SI Mapping — Round 5 Review

> Round: R5 | Date: 2026-03-04 18:05 | Status: **CONTINUE**
> Quality Gates: ruff(✓) pytest(34/34 ✓) tsc(✓) eslint(✓)
> Fix Criteria: HIGH→FIX | Critical/Major→FIX | else→SKIP
> Perspective: **Deep Security / Data Integrity** (SQL injection, PII, privilege escalation, input validation)

## Metrics

| Metric | Value |
|--------|-------|
| fix_target_count | 2 |
| skip_count | 11 |
| design_risk_count | 5 |
| fp_removed | 4 |
| oscillation_detected | 0 |

## Fix Target Issues (수정 완료)

### I-03 [Moderate/HIGH] — min_revenue 음수 입력 허용
- **파일**: `deal-mgmt/app/schemas/si_mapping.py`
- **수정**: `min_revenue` Field에 `ge=Decimal("0")` 제약 추가
- **교차검증**: CONFIRMED — 음수 매출액 필터는 논리적으로 무의미

### SEC-05 [Moderate/HIGH] — Short-List 체크박스 낙관적 중복 클릭
- **파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx`
- **수정**: `disabled={!canWrite}` → `disabled={!canWrite || updateBuyer.isPending}`
- **교차검증**: CONFIRMED — isPending 동안 중복 mutate 방지

## Skipped Issues (스킵)

### I-05 [Moderate/MEDIUM] — bulk_add 최대 등록 수 검증
- **사유**: 스키마에서 `max_length=100` 이미 적용 (Pydantic 레벨 검증 충분)

### I-07 [Minor/HIGH] — KSIC 코드 대소문자 정규화
- **사유**: 현재 대소문자 구분 없이 매칭 (`_KSIC_CODE_RE`가 `[A-Za-z0-9]` 허용)

### I-08 [Minor/MEDIUM] — deep_dive 공시 개수 제한
- **사유**: DART API 자체가 최근 공시만 반환 (외부 API 동작에 의존)

### I-09 [Minor/LOW] — 테스트에서 음수 min_revenue 케이스
- **사유**: I-03 수정으로 Pydantic ValidationError 발생 보장 — 별도 테스트 불필요

### SEC-03 [Minor/HIGH] — top_n 파라미터 범위 확인
- **사유**: 이미 `ge=1, le=20` 적용됨 — 충분

### SEC-06 [Minor/MEDIUM] — InlineSelect XSS 방어
- **사유**: React가 기본적으로 JSX 내 값을 이스케이프 — innerHTML 사용하지 않음

### SEC-07 [Minor/MEDIUM] — 에러 메시지 상세도
- **사유**: 백엔드가 제어된 메시지만 반환 (스택 트레이스 노출 없음)

### SEC-09 [Minor/LOW] — BuyerCandidate extra_data JSON 검증
- **사유**: extra_data는 백엔드에서만 설정 (프론트엔드 입력 아님)

### FE-SEC-01 [Minor/MEDIUM] — CSRF 토큰
- **사유**: JWT Bearer 토큰 인증 사용 — CSRF 토큰 불필요

### FE-SEC-02 [Minor/LOW] — Content-Security-Policy 헤더
- **사유**: 인프라(Nginx) 레벨 설정 — 코드 리뷰 범위 외

## Design Risk (기술부채)

### I-01 [Moderate/HIGH] — BuyerCandidate 중복 등록 방지 (DB UniqueConstraint)
- **사유**: DB 마이그레이션 필요 — `(txn_id, company_name)` unique 제약 추가 검토

### I-02 [Moderate/MEDIUM] — corp_code 경로 파라미터 검증
- **사유**: 내부 서비스 간 호출이므로 defense-in-depth 수준 — 당장 필수 아님

### I-06 [Moderate/MEDIUM] — Redis 기반 rate limiter
- **사유**: 아키텍처 변경 필요 (현재 인메모리 → Redis 전환)

### SEC-01 [Moderate/HIGH] — PII 마스킹 정책 확립
- **사유**: 제품/컴플라이언스 결정 필요 — 코드 리뷰에서 결정할 수 없음

### SEC-02 [Moderate/MEDIUM] — 검색 API GET→POST 전환
- **사유**: API 계약 변경 — 클라이언트 호환성 고려 필요

## False Positive (제거됨)

### I-04 — 404 응답에 company_id 포함
- **사유**: FP-LOGIC — 클라이언트가 이미 UUID를 알고 있음 (요청에 포함)

### SEC-04 — 에러 메시지 상세 정보 노출
- **사유**: FP-CTX — 백엔드가 제어된 메시지만 반환

### SEC-08 — topN 범위 미검증
- **사유**: FP-IMPL — `ge=1, le=20` (SI) / `ge=1, le=50` (VC) 이미 적용

### L-01 — min_revenue 음수 (I-03 중복)
- **사유**: FP-DUP — I-03과 동일 이슈

## Quality Gates (수정 후 재검증)

| Gate | Status |
|------|--------|
| ruff check | ✓ PASS (0 issues) |
| ruff format | ✓ PASS |
| pytest | ✓ PASS (34/34) |
| tsc --noEmit | ✓ PASS |
| eslint | ✓ PASS |

## Convergence Status

- R3: 34건 → R4: 10건 → R5: 2건
- Trend: ↓ 강한 감소 (R3→R5: 94% 감소)
- Decision: **CONTINUE** (fix_target > 0, 다음 관점으로 계속)

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `deal-mgmt/app/schemas/si_mapping.py` | min_revenue ge=Decimal("0") 추가 |
| `amic-platform/.../BuyersTab.tsx` | checkbox disabled에 isPending 추가 |
