# Code Review — VC/SI Mapping (13관점 통합)

> **Review Date**: 2026-03-04 20:53
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: VC/SI Mapping 전체 코드 (deal-mgmt BE + amic-platform FE)
> **Method**: Quality Gates + 4 Agent Parallel Review + Cross-Verification
> **Quality Gates**: ruff(✓) pytest(34/34 ✓) tsc(✓) eslint(✓)
> **Context**: R4-R8 수렴 루프 완료 후 전체 13관점 통합 리뷰

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|-----------|----------|
| Critical | 0 | — | — |
| Major | 0 | — | — |
| Moderate | 2 | HIGH: 2 | P2: 2 |
| Minor | 4 | HIGH: 4 | P2: 2 / P3: 2 |
| **Total** | **6** | **HIGH: 6** | **P2: 4 / P3: 2** |

**FP Prevention**: 36건 원본 이슈 → 3건 FP 제거 → 14건 SKIP → 13건 DESIGN_RISK → **6건 FIX 대상**

## Phase 2 교차 검증 결과

| 원본 이슈 | 원본 심각도 | 교차 검증 판정 | 사유 |
|----------|-----------|-------------|------|
| CR-SEC-1: .env 평문 API키 | Critical/HIGH | **PARTIAL** → Moderate | .gitignore 적용, git 미추적. 로컬 노출 리스크만 존재 |
| MJ-BE-2: flush→commit 갭 | Major/HIGH | **FP (FP-CTX)** | 의도적 best-effort audit. 주석에 설계 의도 명시 |
| MJ-BE-3: 테스트 revenue int | Major/HIGH | **PARTIAL** → Minor | SQLAlchemy 자동 coercion. 코드 일관성 이슈 |
| MJ-SEC-2: AUTH_ENABLED bypass | Major/HIGH | **FP (FP-CTX)** | ENV 화이트리스트 가드 (local/dev/test만 허용) |
| MJ-SEC-3: deal-level 접근제어 | Major/HIGH | **FP (FP-LOGIC)** | 읽기는 참조 데이터, 쓰기 엔드포인트에 deal 체크 구현됨 |

## 진동 가드 (Oscillation Guard)

| 이슈 | 등장 라운드 | 횟수 | 처리 |
|------|-----------|------|------|
| N+1 VC query (ROW_NUMBER 전환) | R4, R6, 13관점 | 3회 | DESIGN_RISK 유지 |
| 5,000건 인메모리 로딩 | R6, 13관점 | 2회 | DESIGN_RISK 유지 |
| InMemory Rate Limiter → Redis | R5, 13관점 | 2회 | DESIGN_RISK 유지 |
| _mask_reg_no 중복 | R8, 13관점 | 2회 | DESIGN_RISK 유지 |
| extra_data 이중 타입 단언 | R8, 13관점 | 2회 | DESIGN_RISK 유지 |
| audit entity_id 상수 | R8, 13관점 | 2회 | DESIGN_RISK 유지 |

## Fix Target Issues (수정 대상 — 6건)

### FIX-1 [Moderate/HIGH] — VcMappingResult bulkAdd 에러 미표시
- **파일**: `amic-platform/.../VcMappingResult.tsx`
- **위치**: line 312-327
- **설명**: `bulkAddMutation.isError` 시 에러 메시지가 UI에 표시되지 않음. SIMappingPanel의 SI bulk add는 에러 표시 있으나 VC bulk add는 누락
- **Priority**: P2 (40 × 1.0 = 40)
- **교차검증**: CONFIRMED — 코드 직접 읽어 확인. 버튼만 있고 에러 메시지 없음

### FIX-2 [Minor/HIGH] — SIMappingPanel bulkAddMutation role="alert" 누락
- **파일**: `amic-platform/.../SIMappingPanel.tsx`
- **위치**: line 361
- **설명**: R8에서 `role="alert"` 추가 시 패턴 불일치로 누락. `<p className="text-sm text-red-600">`에 `role="alert"` 없음 (다른 에러는 `<p role="alert" className="mt-2 text-sm text-red-600">`)
- **Priority**: P2 (20 × 1.0 = 20)
- **교차검증**: CONFIRMED — R8 replace_all이 `mt-2` 포함 패턴만 매칭

### FIX-3 [Minor/HIGH] — 테스트 revenue int → Decimal 일관성
- **파일**: `deal-mgmt/tests/test_si_mapping.py`
- **위치**: lines 89-119 (5개소: 15_000_000_000, 5_000_000_000, 20_000_000_000, 12_000_000_000, 30_000_000_000)
- **설명**: `Mapped[Decimal | None]` + `Numeric(20,2)` 컬럼에 int 리터럴 사용. VC 테스트(lines 508-530)는 이미 `Decimal("...")` 사용 — 동일 파일 내 불일관
- **Priority**: P2 (20 × 1.0 = 20)
- **교차검증**: PARTIAL (Major→Minor 하향) — SQLAlchemy가 자동 coercion하므로 기능 버그 아님

### FIX-4 [Minor/HIGH] — corp_code 컬럼 comment 오류
- **파일**: `deal-mgmt/app/models/si_company.py`
- **위치**: line 34
- **설명**: `corp_code` 필드의 comment가 "사업자등록번호 (하이픈 제거)"이나 실제로는 DART 기업 고유번호. `biz_reg_no`가 사업자등록번호 필드
- **Priority**: P3 (20 × 1.0 = 20, 코스메틱)
- **교차검증**: CONFIRMED — 모델 코드 직접 확인

### FIX-5 [Moderate/HIGH] — .env 평문 API 키 보안
- **파일**: `deal-mgmt/.env`
- **위치**: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, CLOVA_CLIENT_SECRET
- **설명**: API 키가 평문 저장. .gitignore 적용으로 git 노출은 없으나 로컬 보안 리스크
- **Priority**: P2 (40 × 1.0 = 40)
- **교차검증**: PARTIAL (Critical→Moderate 하향) — .gitignore 적용됨, 코드 범위 밖 운영 이슈
- **권장**: Azure Key Vault 또는 환경변수 주입 전환

### FIX-6 [Minor/HIGH] — total_val falsy 체크 (Decimal("0"))
- **파일**: `deal-mgmt/app/services/si_mapping_service.py`
- **위치**: line 793
- **설명**: `total_val if total_val else Decimal("0")` — `Decimal("0")`은 Python에서 falsy. 결과는 동일하나 `if total_val is not None`이 의미적으로 정확
- **Priority**: P3 (20 × 1.0 = 20, 코드 스멜)
- **교차검증**: CONFIRMED — 기능 영향 없으나 의미적 정확성 개선

## Skipped Issues (14건)

| # | 이슈 | 심각도/신뢰도 | 스킵 사유 |
|---|------|-------------|----------|
| 1 | _lookup_by_ksic reverse prefix range | Moderate/HIGH | 로직 정확 (range(3, len) 의도대로 동작) |
| 2 | audit entity_id 상수 | Moderate/MEDIUM | MEDIUM 신뢰도 + DESIGN_RISK (R8) |
| 3 | Suspense fallback 스타일 | Minor/MEDIUM | MEDIUM 신뢰도 |
| 4 | filteredSuggestions useMemo | Minor/MEDIUM | 목록 소량, 성능 영향 없음 |
| 5 | SSRF via KIIS_API_URL | Moderate/MEDIUM | MEDIUM 신뢰도, params urllib 인코딩 |
| 6 | Log injection via user input | Moderate/HIGH | 구조화 로깅 사용 시 위험 낮음 |
| 7 | CORS localhost defaults | Moderate/HIGH | 개발 환경 기본값, ENV 분기 |
| 8 | Same JWT secret | Moderate/HIGH | 아키텍처 결정 (DESIGN_RISK) |
| 9 | Company names in logs | Minor/HIGH | 운영 정책 이슈 |
| 10 | Expression index alignment | Moderate/HIGH | DB 인프라 이슈, 코드 범위 밖 |
| 11 | extra_data JSONB full load | Moderate/HIGH | 소량 데이터, 최적화 불필요 |
| 12 | Rate limiter sweep O(N) | Minor/MEDIUM | MEDIUM 신뢰도 |
| 13 | formatRevenue year arg | Moderate/HIGH | 코스메틱, 기능 동작 정확 |
| 14 | selectedIds count 표시 | Minor/HIGH | UX 개선, 기능 영향 없음 |

## Design Risk (누적 — 17건)

### R4-R8 기존 (14건)
| # | 이슈 | 최초 라운드 | 필요 조치 |
|---|------|-----------|----------|
| 1 | N+1 쿼리 패턴 (ROW_NUMBER 전환) | R4 | DB 쿼리 구조 변경 |
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

### 13관점 신규 (3건)
| # | 이슈 | 필요 조치 |
|---|------|----------|
| 15 | Sequential DART queries when corp_code exists | 비동기 병렬화 |
| 16 | 3 sequential queries in map_vc_candidates | 쿼리 병합 또는 CTE |
| 17 | as unknown as 이중 타입 단언 | TypeScript 타입 구조 개선 |

## False Positive 제거 (3건)

| # | 원본 이슈 | FP 유형 | 사유 |
|---|----------|---------|------|
| 1 | MJ-BE-2: flush→commit 갭 | FP-CTX | 의도적 best-effort audit, 주석으로 설계 의도 문서화됨 |
| 2 | MJ-SEC-2: AUTH_ENABLED bypass | FP-CTX | ENV 화이트리스트 가드 존재, 프로덕션에서 RuntimeError |
| 3 | MJ-SEC-3: deal-level 접근제어 | FP-LOGIC | 읽기는 참조 데이터(비 deal 스코프), 쓰기에 deal 체크 구현됨 |

## Methodology

- **Agents**: BE code-reviewer, FE code-reviewer, BE security-auditor, BE performance-profiler
- **Files scanned**: 15개 (BE 7 + FE 8)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 2건 + Major 7건 = 9건 검증
- **Oscillation Guard**: 6건 DESIGN_RISK 재등장 확인

## 검증 투명성

### 검증 통계
- 원본 이슈: 36건 (BE-CR:10 + FE-CR:9 + SEC:9 + PERF:8)
- FP 제거: 3건
- SKIP: 14건
- DESIGN_RISK: 13건 (기존 + 진동)
- FIX 대상: 6건

### 교차 검증 결과
| 판정 | 건수 |
|------|------|
| CONFIRMED | 4건 |
| PARTIAL (하향) | 2건 |
| FALSE_POSITIVE | 3건 |

## 수정 우선순위

| 순위 | 이슈 | 점수 | 수정 범위 |
|------|------|------|---------|
| 1 | VcMappingResult 에러 미표시 | P2 (40) | FE 1개 파일 |
| 2 | .env 평문 키 보안 | P2 (40) | 운영 정책 |
| 3 | bulkAdd role="alert" | P2 (20) | FE 1개 파일 |
| 4 | 테스트 revenue int→Decimal | P2 (20) | BE 테스트 1개 파일 |
| 5 | corp_code comment 오류 | P3 (20) | BE 모델 1개 파일 |
| 6 | total_val falsy 체크 | P3 (20) | BE 서비스 1개 파일 |
