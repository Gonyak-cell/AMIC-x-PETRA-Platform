# Code Review — VC/SI Mapping (13관점 통합 R2 — 수렴 확인)

> **Review Date**: 2026-03-04 21:22
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: VC/SI Mapping 전체 코드 (deal-mgmt BE + amic-platform FE)
> **Method**: Quality Gates + 4 Agent Parallel Review + Cross-Verification + Strict FP Prevention
> **Quality Gates**: ruff(✓) pytest(34/34 ✓) tsc(✓) eslint(✓)
> **Context**: 13관점 R1 수정 완료 후 재검증 — "허위 리뷰 반드시 검증" 요청에 따라 SC-1~SC-6 엄격 적용

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|-----------|----------|
| Critical | 0 | — | — |
| Major | 0 | — | — |
| Moderate | 0 | — | — |
| Minor | 0 | — | — |
| **Total** | **0** | — | — |

**fix_target_count = 0 → 수렴 달성**

**FP Prevention**: 24건 원본 이슈 → 3건 FP 제거 → 14건 SKIP → 7건 DESIGN_RISK → **0건 FIX 대상**

## 수렴 판정

| 메트릭 | 값 | 판정 |
|--------|---|------|
| M1 fix_target_count | **0** | **✓ 수렴** |
| M2 plateau | 13관점 R1: 6건 → R2: 0건 | ↓ 감소 |
| M3 max_rounds | R4~R8 + 13관점 R1~R2 = 7라운드 | 8회 미만 |
| M4 oscillation | 0건 신규 진동 | ✓ |
| M5 regression | Quality Gates 전부 PASS | ✓ |

**Decision: CONVERGED** — fix_target_count = 0, Quality Gates 전부 PASS

## Phase 2 교차 검증 결과

| 원본 이슈 | 원본 심각도 | 교차 검증 판정 | 사유 |
|----------|-----------|-------------|------|
| SEC-01: JWT audience 미검증 | Critical/HIGH | **PARTIAL** → DESIGN_RISK | 서비스 토큰 내부 전용, 실질 공격 경로 없음. audience 추가 시 FDD 토큰 파손 위험 |
| FE-SI-04: Escape 이중 핸들러 경합 | Major/HIGH | **FP (FP-HALLUC)** | `<div role="dialog">` 사용, 네이티브 `<dialog>` 없음. onCancel 이벤트 불가. 단일 핸들러만 존재 |
| P-03: IOTransaction 복합 인덱스 누락 | Medium/HIGH | **FP (FP-LOGIC)** | `UniqueConstraint("source_io_code", "target_io_code")` → 복합 인덱스 이미 생성 |

## False Positive 제거 (3건)

| # | 원본 이슈 | FP 유형 | 사유 |
|---|----------|---------|------|
| 1 | FE-SI-04: Escape 이중 핸들러 경합 | FP-HALLUC | `<div role="dialog">` ≠ `<dialog>`, onCancel 불가 |
| 2 | P-03: IOTransaction 복합 인덱스 누락 | FP-LOGIC | UniqueConstraint가 복합 인덱스 역할 |
| 3 | SEC-01: JWT audience Critical | FP-SEV | 실질 공격 경로 없음, DESIGN_RISK로 하향 |

## Skipped Issues (14건)

| # | 이슈 | 심각도/신뢰도 | 스킵 사유 |
|---|------|-------------|----------|
| 1 | BE-SI-02: _build_flat_candidates relation info loss | Minor/HIGH | 의도적 설계 (DIRECT 우선) |
| 2 | BE-SI-03: audit failure info 미반환 | Minor/HIGH | 의도적 best-effort audit |
| 3 | BE-SI-04: dart_available=False for cached | Minor/HIGH | 정보성 제안, 기능 버그 아님 |
| 4 | BE-SI-05: audit commit 동일 세션 risk | Moderate/HIGH | R8 FP-CTX (best-effort audit 의도) |
| 5 | FE-SI-01: SICandidateTable th scope 누락 | Moderate/HIGH | HTML 스펙: thead 단일행 th → scope 선택사항. 기능적 a11y 영향 없음 |
| 6 | FE-SI-02: VcMappingResult table aria-label 누락 | Moderate/HIGH | 패널/탭 구조가 맥락적 레이블 제공 |
| 7 | FE-SI-03: aria-controls 비존재 ID 참조 | Moderate/HIGH | MUI/Headless UI 동일 패턴. aria-expanded=false로 완화 |
| 8 | FE-SI-05: ValueChainDiagram 모바일 overflow | Moderate/HIGH | 디자인 결정, 데스크톱 전용 도구 |
| 9 | FE-SI-06: 탭 전환 선택 초기화 | Minor/HIGH | 의도적 UX (코드에 명시적 reset) |
| 10 | SEC-04: KIIS_API_URL 도메인 검증 | Moderate/LOW | LOW 신뢰도 |
| 11 | SEC-05: DB seed 정보 노출 | Minor/HIGH | 개발 환경 전용 |
| 12 | SEC-06: 동일 JWT secret | Minor/MEDIUM | MEDIUM 신뢰도 |
| 13 | SEC-07: 기업명 열거 | Minor/HIGH | 운영 정책 이슈, 코드 범위 밖 |
| 14 | P-04: JSONB extra_data 전체 로드 | Low/High | 소량 데이터, 최적화 불필요 |

## Design Risk (누적 — 20건)

### R4-R8 기존 (14건)
| # | 이슈 | 최초 라운드 |
|---|------|-----------|
| 1 | N+1 쿼리 패턴 (ROW_NUMBER 전환) | R4 |
| 2 | SIMappingPanel focus trap vs Headless UI | R4 |
| 3 | BuyersTab Suspense fallback 스타일 | R4 |
| 4 | BuyerCandidate DB UniqueConstraint | R5 |
| 5 | corp_code 경로 파라미터 검증 | R5 |
| 6 | Redis 기반 rate limiter | R5 |
| 7 | PII 마스킹 정책 | R5 |
| 8 | 검색 API GET→POST | R5 |
| 9 | 5,000건 인메모리 로딩 (TTL 캐시) | R6 |
| 10 | buyerColumns 매 렌더 재생성 | R6 |
| 11 | audit entity_id 상수 문자열 | R8 |
| 12 | _mask_reg_no 중복 | R8 |
| 13 | VC 통합 테스트 누락 | R8 |
| 14 | Query Key 하드코딩 | R8 |

### 13관점 R1 신규 (3건)
| # | 이슈 |
|---|------|
| 15 | Sequential DART queries when corp_code exists |
| 16 | 3 sequential queries in map_vc_candidates |
| 17 | as unknown as 이중 타입 단언 |

### 13관점 R2 신규 (3건)
| # | 이슈 | 사유 |
|---|------|------|
| 18 | JWT audience claim 미검증 | SEC-01 Critical → DESIGN_RISK 하향. 아키텍처 조율 필요 |
| 19 | 4 endpoints rate limit 미적용 | SEC-02 Known DESIGN_RISK |
| 20 | Rate limiter dict sweep O(N) | P-05 Known DESIGN_RISK |

### 진동 가드 (HALT — 3회+ 등장)

| 이슈 | 총 등장 횟수 | 처리 |
|------|------------|------|
| N+1 VC query | 4회 (R4, R6, 13R1, 13R2) | **HALT** |
| InMemory Rate Limiter | 3회 (R5, 13R1, 13R2) | **HALT** |
| Sequential queries | 2회 (13R1, 13R2) | DESIGN_RISK 유지 |

## Methodology

- **Agents**: BE code-reviewer, FE code-reviewer, BE security-auditor, BE performance-profiler
- **Files scanned**: 15개 (BE 7 + FE 8)
- **Protocol**: Verified Claim Protocol v1.1 (SC-1~SC-6 엄격 적용)
- **Cross-verification**: Critical 1건 + Major 1건 + Medium 1건 = 3건 검증
- **FP Prevention**: 에이전트에 Known Non-Issues 목록 전달, 기존 FP 재보고 방지

## 검증 투명성

### 검증 통계
- 원본 이슈: 24건 (BE-CR:6 + FE-CR:6 + SEC:7 + PERF:5)
- FP 제거: 3건 (FP-HALLUC:1, FP-LOGIC:1, FP-SEV:1)
- SKIP: 14건
- DESIGN_RISK: 7건 (기존 재등장 4건 + 신규 3건)
- FIX 대상: **0건**

### 교차 검증 결과
| 판정 | 건수 |
|------|------|
| FALSE_POSITIVE | 2건 |
| PARTIAL (DESIGN_RISK 하향) | 1건 |

### 에이전트별 FP 비율
| 에이전트 | 보고 | FP | FP율 |
|---------|------|------|------|
| BE code-reviewer | 6 | 0 | 0% |
| FE code-reviewer | 6 | 1 | 17% |
| Security auditor | 7 | 1 (severity) | 14% |
| Performance profiler | 5 | 1 | 20% |

## 수렴 대시보드 (Cross-Round)

| Round | fix_target | skip | design_risk | fp_removed | decision |
|-------|-----------|------|-------------|------------|----------|
| R4 | 10 | 8 | 7 | 0 | CONTINUE |
| R5 | 6 | 10 | 4 | 2 | CONTINUE |
| R6 | 4 | 10 | 2 | 1 | CONTINUE |
| R7 | 2 | 5 | 1 | 1 | CONTINUE |
| R8 | 1 | 5 | 1 | 2 | CONTINUE |
| 13관점 R1 | 6 | 14 | 3 | 3 | CONTINUE |
| **13관점 R2** | **0** | **14** | **7** | **3** | **CONVERGED** |

**트렌드**: 10 → 6 → 4 → 2 → 1 → 6 → **0** (수렴)

## 전체 DoD 확인

- [x] fix_target_count = 0 (수렴)
- [x] Quality Gates 전부 PASS (ruff ✓, pytest 34/34 ✓, tsc ✓, eslint ✓)
- [x] 진동 이슈 전부 DESIGN_RISK/HALT 분류 완료
- [x] 최종 수렴 보고서 작성 완료
